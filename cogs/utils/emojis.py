import os

# Keyed on the grade as it is stored on a score, which is ossapi's Grade *name*
# rather than the value the API sends: Grade.SS is "X" and Grade.SSH is "XH",
# but the scores table holds "SS" and "SSH". "SSH"/"SH" are the silver SS and S.
#
# The icons are osu!'s own, from the legacy skin in ppy/osu-resources. There is
# no glyph for F - osu! stable has none - so a failed score falls back to the
# letter, which `create_score_view` handles
RANK_ICONS = {
    "SS": "assets/ranks/SS.png",
    "SSH": "assets/ranks/SSH.png",
    "S": "assets/ranks/S.png",
    "SH": "assets/ranks/SH.png",
    "A": "assets/ranks/A.png",
    "B": "assets/ranks/B.png",
    "C": "assets/ranks/C.png",
    "D": "assets/ranks/D.png",
}


# Grade string -> `<:rank_a:1234>`, filled in by `upload_rank_emojis` on
# startup. Emoji render by id, not by name, so the ids have to be known at all
# and this is where they are kept. Importers hold a reference to this dict, so
# it is only ever mutated in place, never reassigned
RANK_EMOJIS: dict[str, str] = {}


async def upload_rank_emojis(bot) -> None:
    """
    Upload custom rank emojies as application emojies
    """
    uploaded = {emoji.name: emoji for emoji in await bot.fetch_application_emojis()}

    for grade, path in RANK_ICONS.items():
        name = f"rank_{grade.lower()}"

        if name not in uploaded:
            with open(os.path.join(os.getcwd(), path), "rb") as icon:
                uploaded[name] = await bot.create_application_emoji(
                    name=name, image=icon.read()
                )

        RANK_EMOJIS[grade] = str(uploaded[name])
