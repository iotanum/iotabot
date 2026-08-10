import asyncio
from datetime import timezone
from typing import Optional

import discord
from discord import ui
from discord.enums import SeparatorSpacing

from app.models.beatmap import Beatmap
from app.models.beatmapset import Beatmapset
from app.models.scores import Scores
from app.models.user import User as OsuDbUser
from cogs.osu import client as osu_client
from cogs.utils.calculator import calculate_bpm, calculate_scores
from cogs.utils.emojis import RANK_EMOJIS
from cogs.utils.user_changes import get_user_changes


async def fix_mods(score: Scores) -> str:
    """
    Formats the mod string from the score object.
    Removes "CL" if present.

    Returns the bare acronyms - the caller decides how to mark them up.
    """
    if not score.mods_list:
        return ""

    mods = "".join(score.mods_list)
    if mods == "CL":
        return ""
    return f"+{mods.replace('CL', '').strip()}"


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
    # Started here and awaited below. The stat lookups in between take a few
    # seconds of their own and do not read the calculator's result, so they run
    # alongside it instead of after it
    calculation = asyncio.create_task(
        calculate_scores(score, checksum=beatmap.checksum)
    )

    # Display changes or achievements
    changes = await is_user_stat_change(db, score)
    new_highscore = await is_new_highscore(score) if changes else None

    scores = await calculation
    bpm = await calculate_bpm(score.mods_list, beatmap.bpm or 0.0)

    # Extract and calculate play statistics
    play_accuracy = f"{100 * (score.accuracy or 0):.2f}%"
    played_score_calc = scores["score"]
    play_pp = score.pp if score.pp else played_score_calc["p_attr"]["pp"]
    fc_score_calc = scores["if_fc"]

    # Extract PP values for different accuracies. Left as numbers - the row they
    # end up on prints them without decimals or a unit
    pp_ss = scores["100"]["p_attr"]["pp"]
    pp_95 = scores["95"]["p_attr"]["pp"]
    pp_90 = scores["90"]["p_attr"]["pp"]
    pp_fc = fc_score_calc["p_attr"]["pp"]

    # Assign color by beatmap status - the container's accent bar replaces what
    # used to be the embed colour
    status_colors: dict[str | None, int] = {
        "RANKED": 0x0000FF,
        "LOVED": 0xFFC0CB,
        "GRAVEYARD": 0x808080,
    }
    accent_color = status_colors.get(beatmap.status, 0x000000)

    map_max_combo = played_score_calc["d_attr"]["max_combo"]

    # Read after the stat refresh above so the numbers are the ones from after
    # this play
    user = await OsuDbUser.get(db, score.user_id)
    assert user, f"User '{score.user_id}' missing for score '{score.id}'"

    # Falls back to the letter before the icons finish uploading, if that
    # failed, and always for F - osu! ships no fail glyph. SSH and SH are the
    # silver SS and S, which players read as plain SS and S
    grade = RANK_EMOJIS.get(
        score.rank, {"SSH": "SS", "SH": "S"}.get(score.rank, score.rank)
    )

    global_rank = f"#{user.global_rank:,}" if user.global_rank is not None else "#N/A"
    user_pp = f"{user.pp:,.0f}pp" if user.pp is not None else "N/A"

    # Stored naive and in UTC, so the timestamp has to be told which zone it is
    # in before Discord can render it as "2 minutes ago" in each reader's own
    played_at = (
        f"<t:{int(score.score_ended_at.replace(tzinfo=timezone.utc).timestamp())}:R>"
        if score.score_ended_at
        else ""
    )

    # A full combo has nothing left to reach for, so the combo row folds up into
    # the difficulty line and the targets below it stop saying anything
    misses = score.miss or 0
    full_combo = not misses and score.max_combo >= map_max_combo

    # Markdown headings are line-scoped, so everything sharing this line renders
    # at heading size - there is no way to mix sizes inline. Custom emoji scale
    # with the line, which is what makes the grade read as a badge here
    header = f"## {grade} {play_pp:,.0f}pp · {play_accuracy}"
    if new_highscore:
        # Subtext, the one size below body text, so the placement reads as an
        # annotation on the pp above it rather than as another stat
        header += f"\n-# #{new_highscore} top play"

    # Balanced brackets are legal link text, so the difficulty can sit inside
    # the link, where it reads as part of the map's name
    map_lines = [
        f"**[{beatmapset.artist} - {beatmapset.title} "
        f"[{beatmap.version}]]({beatmap.url})**",
        f"{f'`{mods}` · ' if mods else ''}"
        f"{played_score_calc['d_attr']['star_rating']:.2f}★",
    ]
    if full_combo:
        map_lines[-1] += f" · 🔗 {map_max_combo:,}x FC"

    blocks: list[ui.Item] = [
        # The beatmapset banner, full width across the top of the card
        ui.MediaGallery(discord.MediaGalleryItem(beatmap.cover_url)),
        ui.TextDisplay(header),
        ui.TextDisplay("\n".join(map_lines)),
    ]

    # The calculator counts slider breaks that never showed up as a miss, so
    # it only earns room on the line when it disagrees with the count
    effective_misses = round(played_score_calc["p_attr"]["effective_miss_count"])
    miss_note = f" ({effective_misses} eff.)" if effective_misses != misses else ""

    blocks += [
        ui.TextDisplay(
            f"🔗 {score.max_combo:,}/{map_max_combo:,}x · ❌ {misses}{miss_note}"
        ),
        ui.Separator(spacing=SeparatorSpacing.large),
        # What the play was missing out on. All four are body text: they are
        # the one row meant to be compared against the pp in the header
        ui.TextDisplay(
            f"{pp_ss:,.0f} SS · {pp_fc:,.0f} FC · "
            f"{pp_95:,.0f} @95% · {pp_90:,.0f} @90%"
        ),
    ]

    # Both footer lines in one block - separate ones would be pushed apart, and
    # these belong together underneath everything else
    blocks.append(
        ui.TextDisplay(
            f"-# {score.great or 0:,}-{score.ok or 0:,}-{score.meh or 0:,} · "
            f"BPM {int(bpm)} · AR {beatmap.ar:.1f} · OD {beatmap.accuracy:.1f} · "
            f"CS {beatmap.cs:.1f} · HP {beatmap.drain:.1f}\n"
            f"-# [{user.username}]({user.url}) · {global_rank} · {user_pp}"
            f"{f' · {played_at}' if played_at else ''}"
            f"{' · osu! lazer' if score.lazer else ''}"
        )
    )

    if changes:
        blocks.append(ui.TextDisplay("\n".join(changes)))

    # One row along the bottom now that neither link has a section to sit beside
    blocks.append(
        ui.ActionRow(
            ui.Button(style=discord.ButtonStyle.link, label="Profile", url=user.url),
            ui.Button(style=discord.ButtonStyle.link, label="Beatmap", url=beatmap.url),
        )
    )

    # timeout=None: the buttons are links, so the view never needs to stay
    # dispatchable, and a posted score should not expire
    view = ui.LayoutView(timeout=None)
    view.add_item(ui.Container(*blocks, accent_colour=accent_color))
    return view
