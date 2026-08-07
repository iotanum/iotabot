using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using McMaster.Extensions.CommandLineUtils;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Hosting;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using osu.Framework.IO.Network;
using osu.Framework.Logging;
using osu.Game.Beatmaps;
using osu.Game.Beatmaps.Formats;
using osu.Game.Rulesets.Difficulty;
using osu.Game.Rulesets.Mods;
using osu.Game.Scoring;
using PerformanceCalculator;
using PerformanceCalculator.Simulate;

namespace IotaBot.PpCalculator;

/// <summary>
/// Serves `simulate osu` over HTTP from a process that stays up.
///
/// A request is a set of named runs, each one the argument list the command line
/// takes, plus the beatmap's md5 so a reworked map can be spotted:
///
///     {"checksum": "5b0...",
///      "runs": {"score": ["252238", "--mod", "HD", "--accuracy", "92", "--json"],
///               "100":   ["252238", "--mod", "HD", "--json"]}}
///
/// and the reply maps those names to what the command prints. One argument per
/// array element, the way a shell would hand them over; the parser also takes an
/// option and its value joined into one element, but nothing here relies on that.
///
/// Runs sharing a beatmap and mods share one decode and one difficulty
/// calculation, which is all a simulation costs; the rest is process start-up and
/// JIT, which a process that stays up pays once. Within a request the runs are
/// evaluated one after another on purpose: sharing has already removed what was
/// expensive about them, so a request costs about one core and the only thing
/// deciding load is how many requests the caller has in flight.
///
/// Only osu! standard is served, because the runs are parsed as
/// <see cref="OsuSimulateCommand"/>.
/// </summary>
public static class CalculatorServer
{
    /// <summary>
    /// Where downloaded .osu files are kept. Mounted from the host, so that
    /// rebuilding the image does not make every beatmap download again.
    /// </summary>
    private static readonly string cache_directory = Environment.GetEnvironmentVariable("BEATMAP_CACHE_DIR") ?? "cache";

    /// <summary>Set once start-up is done, whether or not warm-up succeeded.</summary>
    private static volatile bool ready;

    public static async Task Main()
    {
        // The command line's own start-up, from PerformanceCalculator/Program.cs.
        // Registering the decoder changes how .osu files parse, so leaving it out
        // would quietly change every result: re-read that file whenever the
        // pinned osu-tools revision moves.
        Console.OutputEncoding = Encoding.UTF8;
        Logger.Enabled = false;
        LegacyDifficultyCalculatorBeatmapDecoder.Register();

        var app = WebApplication.CreateBuilder().Build();

        // Readiness rather than liveness: a cold process answers in ~3s where a
        // warm one answers in ~0.2s, and a container swap is the one time that
        // difference is visible.
        app.MapGet("/", () => ready ? Results.Ok("ready") : Results.StatusCode(503));

        app.MapPost("/", async (HttpRequest request) =>
        {
            using var reader = new StreamReader(request.Body);
            string body = await reader.ReadToEndAsync();

            try
            {
                return Results.Text(handle(JObject.Parse(body)).ToString(Formatting.None), "application/json");
            }
            catch (Exception e)
            {
                return Results.Text(new JObject { ["error"] = e.ToString() }.ToString(Formatting.None),
                    "application/json", statusCode: 500);
            }
        });

        // Listening before warming up, so the wait costs no availability
        await app.StartAsync();
        warmUp();
        await app.WaitForShutdownAsync();
    }

    private static JObject handle(JObject request)
    {
        string? checksum = (string?)request["checksum"];

        if (request["runs"] is not JObject runs)
            throw new ArgumentException("Request has no `runs` object.");

        var prepared = new Dictionary<string, SharedDifficulty>();
        var response = new JObject();

        foreach (var run in runs)
        {
            var cli = parse(run.Value!.ToObject<string[]>()!);
            var command = cli.Model;

            string key = $"{command.Beatmap}\n{string.Join(",", command.Mods)}\n{string.Join(",", command.ModOptions)}";

            if (!prepared.TryGetValue(key, out var shared))
                prepared[key] = shared = prepare(command, checksum);

            command.Shared = shared;

            var output = new ConsoleBuffer();
            command.OnExecute(cli, output);

            response[run.Key] = JToken.Parse(output.ToString());
        }

        return response;
    }

    /// <summary>
    /// Reads one run's arguments with the command line's own parser, so a run
    /// served here and the same arguments typed into a shell cannot disagree.
    /// </summary>
    private static CommandLineApplication<SharedCommand> parse(string[] args)
    {
        var cli = new CommandLineApplication<SharedCommand>();
        cli.Conventions.UseDefaultConventions();
        cli.Parse(args);

        // Parsing binds the model but does not validate it; that only happens on
        // the path through Execute, which this does not take. Without it a
        // request with no beatmap argument fails much later and less clearly.
        var invalid = cli.GetValidationResult();

        if (invalid != null)
            throw new ArgumentException(invalid.ErrorMessage ?? "Invalid arguments.");

        return cli;
    }

    private static SharedDifficulty prepare(SharedCommand command, string? checksum)
    {
        var ruleset = command.Ruleset;
        var working = load(command.Beatmap, checksum);
        var mods = ProcessorCommand.ParseMods(ruleset, command.Mods, command.ModOptions);
        var playable = working.GetPlayableBeatmap(ruleset.RulesetInfo, mods);

        return new SharedDifficulty
        {
            Playable = playable,
            MaxCombo = playable.GetMaxCombo(),
            Mods = mods,
            Attributes = ruleset.CreateDifficultyCalculator(working).Calculate(mods)
        };
    }

    /// <summary>
    /// Resolves the `beatmap` argument to a decoded beatmap, bringing the cached
    /// .osu up to date with <paramref name="checksum"/> first when it is an id.
    ///
    /// This deliberately does not call ProcessorWorkingBeatmap.FromFileOrId.
    /// That method downloads only when the file is missing, so a map reworked in
    /// place would keep its old difficulty for the life of the process, and it
    /// resolves the cache against a *relative* path, so it agrees with this one
    /// only as long as the process runs from the right directory. Building the
    /// working beatmap from a path we own removes both. The id is still passed
    /// on, so `beatmap_id` in the output is unchanged.
    /// </summary>
    private static ProcessorWorkingBeatmap load(string beatmap, string? checksum)
    {
        if (int.TryParse(beatmap, out int id))
        {
            string path = Path.Combine(cache_directory, $"{id}.osu");

            if (!File.Exists(path) || (checksum != null && md5(path) != checksum))
                download(id, path);

            return new ProcessorWorkingBeatmap(path, id);
        }

        // The argument can also be a path to a .osu, which is the caller's own
        // file and not ours to fetch or replace.
        if (!beatmap.EndsWith(".osu", StringComparison.Ordinal))
            throw new ArgumentException($"`{beatmap}` is neither a beatmap ID nor a path to a .osu file.");

        return new ProcessorWorkingBeatmap(beatmap);
    }

    /// <summary>
    /// Puts a fresh copy of <paramref name="id"/> at <paramref name="path"/>.
    ///
    /// The download goes to a temporary name and is renamed into place, so a
    /// request reading the cache never sees a half-written file and two requests
    /// for the same map cannot interleave their writes.
    /// </summary>
    private static void download(int id, string path)
    {
        Directory.CreateDirectory(cache_directory);
        string temp = $"{path}.{Guid.NewGuid():N}.tmp";

        try
        {
            new FileWebRequest(temp, $"{Program.ENDPOINT_CONFIGURATION.WebsiteUrl}/osu/{id}").Perform();

            // A beatmap that does not exist answers 200 with an empty body.
            // Renaming that into place would cache it, and a cached file is only
            // re-read against a checksum the caller may not have, so it could go
            // on failing every request until the container is replaced.
            if (new FileInfo(temp).Length == 0)
                throw new InvalidOperationException($"Beatmap {id} came back empty; it probably does not exist.");

            File.Move(temp, path, overwrite: true);
        }
        finally
        {
            // Nothing else knows this name, so a failure part-way would otherwise
            // leave it in the cache directory for good.
            if (File.Exists(temp))
                File.Delete(temp);
        }
    }

    private static string md5(string path)
    {
        using var stream = File.OpenRead(path);
        return Convert.ToHexString(MD5.HashData(stream)).ToLowerInvariant();
    }

    /// <summary>
    /// Runs throwaway calculations until the difficulty code is compiled.
    ///
    /// It starts out interpreted and only reaches full speed once it has run
    /// enough times: the first request of a fresh process takes ~3s and the
    /// fortieth ~0.2s. Traffic is a couple of posts an hour, so a process left to
    /// warm up on real requests would stay slow for days.
    /// </summary>
    private static void warmUp()
    {
        const int iterations = 40;

        var request = new JObject
        {
            ["runs"] = new JObject
            {
                ["played"] = new JArray("129891", "--accuracy", "95", "--misses", "5", "--json"),
                ["perfect"] = new JArray("129891", "--json")
            }
        };

        try
        {
            var elapsed = Stopwatch.StartNew();

            for (int i = 0; i < iterations; i++)
                handle(request);

            Console.WriteLine($"Warmed up in {elapsed.Elapsed.TotalSeconds:N1}s");
        }
        catch (Exception e)
        {
            // Nothing to warm up on - no network at boot, most likely. The early
            // requests are then slow, which is not worth refusing to serve over.
            Console.WriteLine($"Warm-up skipped: {e.Message}");
        }
        finally
        {
            ready = true;
        }
    }

    /// <summary>Everything the runs of one request have in common.</summary>
    private class SharedDifficulty
    {
        public required IBeatmap Playable { get; init; }
        public required int MaxCombo { get; init; }
        public required Mod[] Mods { get; init; }
        public required DifficultyAttributes Attributes { get; init; }
    }

    /// <summary>
    /// `simulate osu` with the decode and the difficulty calculation lifted out.
    ///
    /// <see cref="Execute"/> is copied from SimulateCommand.Execute, with the
    /// working beatmap, the playable beatmap, the maximum combo and the
    /// difficulty attributes replaced by their prepared equivalents. Everything
    /// that decides what the answer is - the hit results, the accuracy, the pp,
    /// the output - stays inherited.
    ///
    /// This is the one place where upstream can change results without anything
    /// here failing to build, and the checkout is master, so it can happen on any
    /// rebuild. Nothing catches that automatically. To check by hand, run the
    /// same arguments through the real command and diff:
    ///
    ///     dotnet PerformanceCalculator.dll simulate osu 252238 --accuracy 92 --json
    /// </summary>
    private class SharedCommand : OsuSimulateCommand
    {
        public SharedDifficulty Shared { get; set; } = null!;

        public override void Execute()
        {
            var ruleset = Ruleset;

            var statistics = GenerateHitResults(Shared.Playable, Shared.Mods);
            var scoreInfo = new ScoreInfo(Shared.Playable.BeatmapInfo, ruleset.RulesetInfo)
            {
                Accuracy = GetAccuracy(Shared.Playable, statistics, Shared.Mods),
                MaxCombo = Combo ?? (int)Math.Round(PercentCombo / 100 * Shared.MaxCombo),
                Statistics = statistics,
                LegacyTotalScore = LegacyTotalScore,
                Mods = Shared.Mods
            };

            var performanceCalculator = ruleset.CreatePerformanceCalculator();
            var performanceAttributes = performanceCalculator?.Calculate(scoreInfo, Shared.Attributes);

            OutputPerformance(scoreInfo, performanceAttributes, Shared.Attributes);
        }
    }

    /// <summary>
    /// Where one run's result is collected. Commands write through IConsole
    /// rather than returning, and requests are served at the same time, so each
    /// run gets its own instead of sharing the process console.
    /// </summary>
    private class ConsoleBuffer : IConsole
    {
        public TextWriter Out { get; } = new StringWriter();

        // Only Out is read back as JSON, so anything written here is dropped
        // rather than mixed into it.
        public TextWriter Error => TextWriter.Null;

        public TextReader In => TextReader.Null;
        public bool IsInputRedirected => true;
        public bool IsOutputRedirected => true;
        public bool IsErrorRedirected => true;
        public ConsoleColor ForegroundColor { get; set; }
        public ConsoleColor BackgroundColor { get; set; }

        public void ResetColor()
        {
        }

        public event ConsoleCancelEventHandler? CancelKeyPress
        {
            add { }
            remove { }
        }

        public override string ToString() => Out.ToString()!;
    }
}
