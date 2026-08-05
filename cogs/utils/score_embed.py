from typing import Optional

import discord
from discord import ui

from app.models.beatmap import Beatmap
from app.models.beatmapset import Beatmapset
from app.models.scores import Scores
from app.models.user import User as OsuDbUser
from cogs.osu import client as osu_client
from cogs.utils.calculator import calculate_bpm, calculate_scores
from cogs.utils.user_changes import get_user_changes


async def fix_mods(score: Scores) -> str:
    """
    Formats the mod string from the score object.
    Removes "CL" if present.
    """
    if not score.mods_list:
        return ""

    mods = "".join(score.mods_list)
    if mods == "CL":
        return ""
    return f" __**+ {mods.replace('CL', '').strip()}**__ "


async def is_user_stat_change(db_sess, score: Scores) -> list[str]:
    """
    Check if there was a change in user statistics from API.
    """
    api_user = await osu_client.get_user(score.user_id)
    db_user = await OsuDbUser.get(db_sess, score.user_id)

    if not api_user or not db_user or api_user.statistics is None:
        return []

    # Every tracked stat (global rank, country rank, pp) lives under `statistics`
    changes = await get_user_changes(db_sess, api_user.statistics, score.user_id)
    if changes:
        await OsuDbUser.update_from_stat_change(db_sess, api_user, score.user_id)
    return changes


async def is_new_highscore(score: Scores) -> Optional[int]:
    """
    Returns the position of the score in the user's top plays, if it made it there.

    osu! keeps a single entry per beatmap in the top plays, so the score is only a
    new highscore when the entry is this exact play - `ended_at` identifies it.
    Playing a map you already have a better score on leaves the old entry in place.
    """
    user_top_scores = await osu_client.get_user_highscores(score.user_id, limit=100)
    if not user_top_scores:
        return None

    for idx, top_score in enumerate(user_top_scores, 1):
        if top_score.ended_at.replace(tzinfo=None) == score.score_ended_at:
            return idx
    return None


async def create_score_view(db, score: Scores) -> ui.LayoutView:
    """
    Creates the Components v2 layout for an osu! score.

    Components v2 replaces embeds instead of extending them - a message cannot
    carry both - so this is passed as `send(view=...)` and there is no embed.
    """
    # Fetch necessary data from the database, a stored score always references
    # a stored beatmap and beatmapset
    beatmap = await Beatmap.get(db, score.beatmap_id)
    assert beatmap, f"Beatmap '{score.beatmap_id}' missing for score '{score.id}'"
    beatmapset = await Beatmapset.get(db, beatmap.beatmapset_id)
    assert beatmapset, f"Beatmapset '{beatmap.beatmapset_id}' missing from db"

    # Process mods, scores, and BPM
    mods = await fix_mods(score)
    scores = await calculate_scores(score)
    bpm = await calculate_bpm(score.mods_list, beatmap.bpm or 0.0)

    # Extract and calculate play statistics
    play_accuracy = f"{100 * (score.accuracy or 0):.2f}%"
    played_score_calc = scores["score"]
    play_pp = score.pp if score.pp else played_score_calc["p_attr"]["pp"]
    fc_score_calc = scores["if_fc"]

    # Extract PP values for different accuracies
    pp_ss = f"{scores['100']['p_attr']['pp']:.2f}pp"
    pp_95 = f"{scores['95']['p_attr']['pp']:.2f}pp"
    pp_90 = f"{scores['90']['p_attr']['pp']:.2f}pp"

    # Assign color by beatmap status - the container's accent bar replaces what
    # used to be the embed colour
    status_colors: dict[str | None, int] = {
        "RANKED": 0x0000FF,
        "LOVED": 0xFFC0CB,
        "GRAVEYARD": 0x808080,
    }
    accent_color = status_colors.get(beatmap.status, 0x000000)

    map_max_combo = played_score_calc["d_attr"]["max_combo"]

    # Display changes or achievements
    changes = await is_user_stat_change(db, score)
    new_highscore = await is_new_highscore(score) if changes else None

    # Read after the stat refresh above so the numbers are the ones from after
    # this play
    user = await OsuDbUser.get(db, score.user_id)
    assert user, f"User '{score.user_id}' missing for score '{score.id}'"

    blocks: list[ui.Item] = [
        # The beatmapset banner, full width across the top of the card
        ui.MediaGallery(discord.MediaGalleryItem(beatmap.cover_url)),
        ui.TextDisplay(
            f"-# [{user.username}]({user.url}) | "
            f"#{user.global_rank} - "
            f"{user.pp if user.pp is not None else 'N/A'}pp\n"
            f"### [{beatmapset.artist} - {beatmapset.title}]({beatmap.url})\n"
            f"[{beatmap.version}]{mods}"
            f"({played_score_calc['d_attr']['star_rating']:.2f}⭐)"
        ),
        ui.TextDisplay(
            f"**{play_pp:.2f}pp** / {fc_score_calc['p_attr']['pp']:.2f}pp if FC\n"
            f"🎯 **{play_accuracy}**  ·  "
            f"🔥 {score.max_combo}x / {map_max_combo}x  ·  "
            f"❌ {score.miss}x"
        ),
        ui.Separator(),
        ui.TextDisplay(
            f"`BPM: {int(bpm)} "
            f"AR: {beatmap.ar:.2f} "
            f"OD: {beatmap.accuracy:.2f} "
            f"HP: {beatmap.drain:.2g} "
            f"CS: {beatmap.cs:.2g}`\n"
            f"`SS: {pp_ss} / 95%: {pp_95} / 90%: {pp_90}`"
        ),
    ]

    if changes:
        highscore_str = ""
        if new_highscore:
            highscore_str = f"🥇 **New Highscore! (#{new_highscore})** 🥇\n"
        blocks.append(ui.TextDisplay(highscore_str + "\n".join(changes)))

    blocks.append(
        ui.TextDisplay(
            f"-# {score.great}x300 / {score.ok}x100 / {score.meh}x50 "
            f"(Effective ❌: "
            f"{round(played_score_calc['p_attr']['effective_miss_count'])}x)"
            f"{' - osu! lazer' if score.lazer else ''}"
        )
    )
    blocks.append(
        ui.ActionRow(
            ui.Button(style=discord.ButtonStyle.link, label="Beatmap", url=beatmap.url),
            ui.Button(
                style=discord.ButtonStyle.link, label=user.username, url=user.url
            ),
        )
    )

    # timeout=None: the buttons are links, so the view never needs to stay
    # dispatchable, and a posted score should not expire
    view = ui.LayoutView(timeout=None)
    view.add_item(ui.Container(*blocks, accent_colour=accent_color))
    return view
