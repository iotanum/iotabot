import discord
from discord import ui


def get_profile_url(user_id):
    return f"https://osu.ppy.sh/users/{user_id}"


class ProfileButtonView(ui.View):
    def __init__(self, user_profile_url):
        super().__init__()
        self.add_item(
            ui.Button(
                label="View Profile",
                url=user_profile_url,
                style=discord.ButtonStyle.link,
            )
        )


async def create_user_embed(user):
    embed = discord.Embed(
        title=f"osu! Profile: {user.username}",
        description=f"Profile information for {user.username}",
        color=discord.Color.blue(),  # You can set this to any color you'd like
    )

    embed.set_thumbnail(url=user.avatar_url)  # Set avatar as thumbnail

    # Add fields with data
    embed.add_field(name="Username", value=user.username, inline=True)
    embed.add_field(name="User ID", value=user.id, inline=True)
    embed.add_field(name="Country", value=user.country_code, inline=True)

    # Handle optional global and country rank
    embed.add_field(
        name="Global Rank",
        value=user.statistics.global_rank if user.statistics.global_rank else "N/A",
        inline=True,
    )
    embed.add_field(
        name="Country Rank",
        value=user.statistics.country_rank if user.statistics.country_rank else "N/A",
        inline=True,
    )

    embed.add_field(
        name="Accuracy", value=f"{user.statistics.hit_accuracy:.2f}%", inline=True
    )
    embed.add_field(name="Play Count", value=user.statistics.play_count, inline=True)
    embed.add_field(
        name="Play Time",
        value=f"{user.statistics.play_time // 3600} hours",
        inline=True,
    )
    embed.add_field(
        name="Performance Points (PP)", value=f"{user.statistics.pp:.2f}", inline=True
    )

    # Previous usernames (if they exist)
    if user.previous_usernames:
        embed.add_field(
            name="Previous Usernames", value=user.previous_usernames, inline=False
        )

    profile_url = get_profile_url(user.id)
    return embed, ProfileButtonView(profile_url)
