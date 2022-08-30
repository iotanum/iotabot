from discord.ext import commands
import discord

from .gbf_wiki import GbfWiki


class GbfCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gbf_wiki = GbfWiki()

    @commands.command(brief="Check GW predictions", aliases=['p', "predickt"])
    async def predict(self, ctx, tier: str):
        possible_predictions = ['t2k', 't80k', 't140k', 't180k', 't270k', 't370k']
        if tier in possible_predictions:
            tier = tier.split('t')[1].split('k')[0]
            predictions = await self.gbf_wiki.get_preditions()

            for prediction in predictions['Tier'].keys():
                if prediction.startswith(tier):
                    tier_prediction = predictions['Tier'][prediction]
                    tier_prediction["Previous"] = tier_prediction.pop("PreviousPrevious GW's Honors at the current time")
                    tier_prediction["Current"] = tier_prediction.pop("CurrentCurrent GW's Honors")
                    tier_prediction["Prev_Ending"] = tier_prediction.pop("Prev EndingPrevious GW's Final Honors")

                    prev_curr_vs_current = f'{tier_prediction["Previous"]} **|** {tier_prediction["Current"]}'
                    embed = discord.Embed(title=f"__**Tier '{prediction}' Predictions**__", color=0x03f8fc,
                                          description=prev_curr_vs_current)
                    embed.add_field(name="Previous Ending", value=tier_prediction["Prev_Ending"], inline=True)
                    embed.add_field(name="Prediction", value=tier_prediction["Prediction"], inline=True)
                    embed.set_footer(text=predictions['Time'])

                    await ctx.send(embed=embed)
                    return


async def setup(bot):
    await bot.add_cog(GbfCommands(bot))
