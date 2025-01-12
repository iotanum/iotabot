from datetime import datetime, timedelta
from typing import Optional

import discord

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


async def is_user_stat_change(db_sess, score: Scores) -> Optional[list]:
    """
    Check if there was a change in user statistics from API.
    """
    api_user = await osu_client.get_user(score.user_id)
    db_user = await OsuDbUser.get(db_sess, score.user_id)

    if not api_user or not db_user:
        return

    stat_changes = await get_user_changes(db_sess, api_user.statistics, score.user_id)
    rank_changes = await get_user_changes(db_sess, api_user, score.user_id)

    if stat_changes or rank_changes:
        await OsuDbUser.update_from_stat_change(db_sess, api_user, score.user_id)
        user_changes = stat_changes + rank_changes
        return user_changes


async def is_new_highscore(score: Scores) -> Optional[int]:
    """
    Check if the score is a new highscore for the user.
    """
    # Fetch the user's top score
    user_top_scores = await osu_client.get_user_highscores(score.user_id, limit=50)
    if not user_top_scores:
        return

    # Pick out the latest top score
    latest_datetime = None
    latest_index = None
    for idx, score in enumerate(user_top_scores, 1):
        if latest_datetime is None or score.ended_at > latest_datetime:
            latest_datetime = score.ended_at
            latest_index = idx

    # Check the most recent top play if it was made within the last 24 hours
    now = datetime.now()
    if latest_datetime:
        if (
                now - timedelta(days=1)
                <= latest_datetime.replace(tzinfo=None)
                <= now + timedelta(days=1)
        ):
            return latest_index

async def create_score_embed(db, score: Scores) -> discord.Embed:
    """
    Creates a Discord embed for an osu! score.
    """
    # Fetch necessary data from the database
    user = await OsuDbUser.get(db, score.user_id)
    beatmap = await Beatmap.get(db, score.beatmap_id)
    beatmapset = await Beatmapset.get(db, beatmap.beatmapset_id)

    # Process mods, scores, and BPM
    mods = await fix_mods(score)
    scores = await calculate_scores(score)
    bpm = await calculate_bpm(score.mods, beatmap.bpm)

    # Extract and calculate play statistics
    play_accuracy = f"{100 * score.accuracy:.2f}%"
    played_score_calc = scores["score"]
    play_pp = score.pp if score.pp else played_score_calc["p_attr"]["pp"]
    fc_score_calc = scores["if_fc"]

    # Extract PP values for different accuracies
    pp_ss = f"{scores['100']['p_attr']['pp']:.2f}pp"
    pp_95 = f"{scores['95']['p_attr']['pp']:.2f}pp"
    pp_90 = f"{scores['90']['p_attr']['pp']:.2f}pp"

    # Assign color by beatmap status
    embed_color = {
        "RANKED": 0x0000FF,
        "LOVED": 0xFFC0CB,
        "GRAVEYARD": 0x808080,
    }.get(beatmap.status, 0x000000)

    # Create embed with dynamic title and description
    embed = discord.Embed(
        title=f"{beatmapset.artist} - {beatmapset.title}\n[{beatmap.version}]",
        description=(
            f"{mods}({played_score_calc['d_attr']['star_rating']:.2f}⭐), "
            f"**{play_pp:.2f}pp** / {fc_score_calc['p_attr']['pp']:.2f}pp"
        ),
        colour=embed_color,
        url=beatmap.url,
    )

    # Set author details with user info
    embed.set_author(
        name=f"{user.username} | #{user.global_rank} - {user.pp}pp",
        icon_url=user.avatar_url,
        url=user.url,
    )

    # Add fields for accuracy, combo, and misses
    embed.add_field(
        name="🎵Beatmap Stats",
        value=f"**BPM:** {int(bpm)}\n"
        f"`AR: {played_score_calc['d_attr']['approach_rate']:.2f} "
        f"OD: {played_score_calc['d_attr']['overall_difficulty']:.2f} "
        f"HP: {beatmap.drain:.2g} "
        f"CS: {beatmap.cs:.2g}`\n"
        f"`SS: {pp_ss} / 95%: {pp_95} / 90%: {pp_90}`",
        inline=False,
    )
    embed.add_field(name="🎯Accuracy", value=f"**{play_accuracy}**", inline=True)
    embed.add_field(
        name="🔥Combo", value=f"{score.max_combo}x / {beatmap.max_combo}x", inline=True
    )
    embed.add_field(name="❌Miss", value=f"{score.miss}x", inline=True)

    # Display changes or achievements
    if changes := await is_user_stat_change(db, score):
        highscore_str = ""
        if new_highscore := await is_new_highscore(score):
            highscore_str = f"🥇 **New Highscore! (#{new_highscore})** 🥇\n"

        embed.add_field(
            name="📈 Changes! 📈",
            value=f"{highscore_str}" + "\n".join(changes),
            inline=False,
        )

    # Add beatmap thumbnail and footer
    embed.set_thumbnail(url=beatmap.cover_url)
    embed.set_footer(
        text=(
            f"{score.great}x300 / {score.ok}x100 / {score.meh}x50 "
            f"(Effective ❌: {round(played_score_calc['p_attr']['effective_miss_count'])}x)"
            f"{' - osu! lazer' if score.lazer else ''}"
        )
    )

    return embed
