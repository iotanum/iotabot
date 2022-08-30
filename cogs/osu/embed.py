import discord
from discord.ext import commands

from .helpers.after_play_changes import AfterSubmitChanges
from .helpers.new_top_score import NewTopPlay
from .helpers.performance_points import PP
from .helpers.beatmap_difficulities import BeatmapDifficulty
from .helpers.pictures import Pics

import asyncio


class EmbedMessage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.after_submit_changes = AfterSubmitChanges(self.bot)
        self.new_top_play = NewTopPlay(self.bot)
        self.beatmap_calculator = PP()
        self.beatmap_diff = BeatmapDifficulty()
        self.pictures = Pics()

    async def prepare_message(self, user_stuff, recent_score_data, channels, latest_score=None):
        username, user_id, pp_rank = user_stuff
        score = recent_score_data['score']
        beatmap = recent_score_data['beatmap']
        if not latest_score:
            await self.after_submit_changes.calc_changes(user_id)
            if self.after_submit_changes.new_stuff:
                await self.new_top_play.check_for_new_play(user_id)

        await self.pictures.get_pics(user_id, beatmap.beatmapset_id)
        await self.beatmap_calculator.calculator(score, beatmap)
        if str(score.enabled_mods) == '':
            score.enabled_mods = "NoMod"

        await self.embed_message(user_stuff, score, beatmap, latest_score, channels)

    async def embed_color(self, status):
        choices = {'BeatmapStatus.ranked': 0x65c9fb, 'BeatmapStatus.approved': 0xa5cc00,
                   'BeatmapStatus.qualified': 0xa5cc00, 'BeatmapStatus.loved': 0xff66aa,
                   'BeatmapStatus.graveyard': 0xe1d4d4, 'BeatmapStatus.wip': 0xe1d4d4,
                   'BeatmapStatus.pending': 0xe1d4d4}
        return choices[str(status)]

    async def text_length_calc(self, beatmap, score):
        return len(str(score.maxcombo)) + len(str(beatmap.max_combo))

    async def difficulties_string(self, beatmap, mods):
        return await self.beatmap_diff.beatmap_difficulties_format(beatmap, mods)

    async def acc_combo_line_string(self, score, beatmap, length):
        return f"{str(self.beatmap_calculator.accuracy) + '%' + '(' + str(score.rank) + ')': ^{length + 2}}", \
               f"{str(score.maxcombo) + 'x/' + str(beatmap.max_combo) + 'x': ^{length}}"

    async def beatmap_link(self, score):
        return f"https://osu.ppy.sh/b/{score.beatmap_id}"

    async def embed_message(self, user_stuff, score, beatmap, map_perc, channels):
        username, user_id, pp_rank = user_stuff
        acc_fc, ss, pp95, pp90 = self.beatmap_calculator.possible_pp
        difficulties = await self.difficulties_string(beatmap, str(score.enabled_mods))
        bpm, length = await self.beatmap_diff.get_map_length_and_bpm(beatmap, str(score.enabled_mods))
        accuracy_string, combo_string = await self.acc_combo_line_string(score, beatmap,
                                                                         await self.text_length_calc(beatmap, score))
        acc_no_misses = f"{self.beatmap_calculator.acc_if_no_misses}%"

        embed = discord.Embed(title=beatmap.artist + " - " + beatmap.title + f" *[{beatmap.version}]*",
                              url=await self.beatmap_link(score),
                              color=await self.embed_color(beatmap.approved),
                              description=f"+ __**{score.enabled_mods}**__ ({self.beatmap_calculator.star_rating}★), "
                                          f"worth - **{self.beatmap_calculator.pp}pp**/**{acc_fc}pp**\n"
                                          f"{map_perc if map_perc else ''}")
        embed.set_author(name=f"{username} #{pp_rank}\U0001f30e",
                         url=self.pictures.user_link,
                         icon_url=self.pictures.user_avatar)
        embed.set_thumbnail(url=self.pictures.beatmap_bg)
        embed.add_field(name='Beatmap',
                        value=f"\U0001f53a__{length[0]}:{length[1]}min, {bpm}bpm__\n"
                              f"\U0001f53a``{difficulties}``\n"
                              f"\U0001f53a``SS - {ss}pp, 95% - {pp95}pp, 90% - {pp90}pp``",
                        inline=False)
        embed.add_field(name=f'Score',
                        value=f"```coffeescript\n"
                              f"Accuracy - {accuracy_string}\n"
                              f"Combo    - {combo_string}\n"
                              f"{'Miss  ' if score.countmiss == 1 else 'Misses'}   - {score.countmiss}x\n"
                              f"```",
                        inline=False)
        if self.after_submit_changes.new_stuff:
            embed.add_field(name="Changes",
                            value=f"```coffeescript\n"
                                  f"{self.after_submit_changes.new_stuff}"
                                  f"\n```",
                            inline=False)

        embed.set_footer(text=f"{score.count300}x300 / {score.count100}x100 / {score.count50}x50"
                              f"{', accuracy w/o misses - ' + acc_no_misses if score.countmiss > 0 else ''}")
        await self.send_message(embed, channels)

    async def format_new_top_score(self):
        if self.new_top_play.new_score_num:
            return f"New top score __**#{self.new_top_play.new_score_num}**__!"

    async def reset_values(self):
        self.new_top_play.new_score_num = None
        self.after_submit_changes.new_stuff = None

    async def send_message(self, embed, channels):
        for channel_id in channels:
            await self.bot.get_channel(channel_id).send(await self.format_new_top_score(), embed=embed)
            await asyncio.sleep(0.5)
        await self.reset_values()


async def setup(bot):
    await bot.add_cog(EmbedMessage(bot))
