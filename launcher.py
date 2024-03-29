from discord.ext import commands
import psycopg2
from psycopg2.extras import wait_select
from dotenv import load_dotenv

import os
import asyncio
import discord

if not os.getenv("DISCORD_TOKEN"):
    load_dotenv(dotenv_path="vars.env")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=os.getenv("COMMAND_PREFIX"), intents=intents)
initial_extensions = ['cogs.osu.extensions',
                      'cogs.fun.extensions',
                      'cogs.gw.commands',
                      'cogs.status',
                      'cogs.command_error_handle',
                      'cogs.http_server']


def load_database():
    aconn = psycopg2.connect(dbname=os.getenv("DB"), user=os.getenv("LOGIN"),
                             password=os.getenv("PASSW"), async_=True)
    wait_select(aconn)
    return aconn.cursor()


async def load_extensions():
    for extension in initial_extensions:
        try:
            print(f"loading {extension}")
            await bot.load_extension(extension)

        except Exception as e:
            print(e)
            print(f'Failed to load extension "{extension}"')


async def main():
    async with bot:
        bot.db = load_database()
        await load_extensions()
        bot.loop.create_task(bot.get_cog("HTTPServer").http_server())
        await bot.start(os.getenv("DISCORD_TOKEN"), reconnect=True)

if __name__ == '__main__':
    asyncio.run(main())


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

