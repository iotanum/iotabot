import os

# The grade strings osu! reports, each with the icon in assets/ranks that shows
# it. "X"/"XH" are SS and silver SS, "SH" is a silver S
RANK_ICONS = {
    "X": "assets/ranks/X.png",
    "XH": "assets/ranks/XH.png",
    "S": "assets/ranks/S.png",
    "SH": "assets/ranks/SH.png",
    "A": "assets/ranks/A.png",
    "B": "assets/ranks/B.png",
    "C": "assets/ranks/C.png",
    "D": "assets/ranks/D.png",
    "F": "assets/ranks/F.png",
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
