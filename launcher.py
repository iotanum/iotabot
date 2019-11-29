from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio

load_dotenv("vars.env")
bot = commands.Bot(command_prefix='>')
initial_extensions = ['cogs.osu.extensions',
                      'cogs.fun.extensions',
                      'cogs.status',
                      'cogs.command_error_handle']


if __name__ == '__main__':
    for extension in initial_extensions:
        try:
            bot.load_extension(extension)

        except Exception as e:
            print(e)
            print(f'Failed to load extension "{extension}"')


@commands.is_owner()
@bot.group(hidden=True)
async def cog(ctx):
    if not ctx.invoked_subcommand:
        await ctx.send("Invalid cog option passed.")


@commands.is_owner()
@cog.command(hidden=True)
async def load(ctx, o_extension: str):
    try:
        bot.load_extension(o_extension)
        await ctx.message.add_reaction("\U0001f44d")

    except Exception as e:
        await ctx.send(f"Failed to load extension '{o_extension}'")


@commands.is_owner()
@cog.command(hidden=True)
async def unload(ctx, o_extension: str):
    try:
        bot.unload_extension(o_extension)
        await ctx.message.add_reaction("\U0001f44d")

    except Exception as e:
        await ctx.send(f"Failed to unload extension '{o_extension}'")


@commands.is_owner()
@cog.command(hidden=True)
async def reload(ctx, o_extension: str):
    try:
        bot.unload_extension(o_extension)
        await asyncio.sleep(0.5)
        bot.load_extension(o_extension)
        await ctx.message.add_reaction("\U0001f44d")

    except Exception as e:
        await ctx.send(f"Failed to reload extension '{o_extension}'")


@bot.event
async def on_ready():
    print(f'Logged in as: {bot.user.name} - {bot.user.id}')
    print("----------------------------------------------------\n")


bot.run(os.getenv("discord_token"), bot=True, reconnect=True)
