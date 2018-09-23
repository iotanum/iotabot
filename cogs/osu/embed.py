import discord
import asyncio
from .performance_points import Calculators
from .pictures import Pictures
from .after_play_changes import AfterSubmit
from .beatmap_difficulities import BeatmapDiff
from .new_top_score import NewScore


class EmbedMessage:
    def __init__(self, bot):
        self.bot = bot

    async def prepare_message(self, user_stuff, recent_score_data, channels, latest_score=None):
        username, user_id, pp_rank = user_stuff
        score = recent_score_data['score']
        beatmap = recent_score_data['beatmap']
        if not latest_score:
            await AfterSubmit.calc_changes(user_id)
            if AfterSubmit.new_stuff:
                await NewScore.check_for_new_play(user_id)
        await Pictures.get_pics(user_id, beatmap.beatmapset_id)
        await Calculators.calculator(score)
        if str(score.enabled_mods) == '':
            score.enabled_mods = "NoMod"

        await self.embed_message(user_stuff, score, beatmap, Pictures,
                                 Calculators, AfterSubmit, latest_score, channels)

    async def embed_color(self, status):
        choices = {'BeatmapStatus.ranked': 0x65c9fb, 'BeatmapStatus.approved': 0xa5cc00,
                   'BeatmapStatus.qualified': 0xa5cc00, 'BeatmapStatus.loved': 0xff66aa}
        return choices[str(status)]

    async def text_length_calc(self, beatmap, score):
        return len(str(score.maxcombo)) + len(str(beatmap.max_combo))

    async def difficulties_string(self, beatmap, mods):
        return await BeatmapDiff.beatmap_difficulties_format(beatmap, mods)

    async def acc_combo_line_string(self, score, beatmap, calculators, length):
        return f"{str(calculators.accuracy) + '%' + '(' + str(score.rank) + ')': ^{length + 2}}", \
               f"{str(score.maxcombo) + 'x/' + str(beatmap.max_combo) + 'x': ^{length}}"

    async def embed_message(self, user_stuff, score, beatmap, pictures, calculators, after_play, map_perc, channels):
        username, user_id, pp_rank = user_stuff
        acc_fc, ss, pp95, pp90 = calculators.possible_pp
        difficulties = await self.difficulties_string(beatmap, str(score.enabled_mods))
        bpm, length = await BeatmapDiff.lenght_and_bpm(beatmap, str(score.enabled_mods))
        accuracy_string, combo_string = await self.acc_combo_line_string(score, beatmap, calculators,
                                                                         await self.text_length_calc(beatmap, score))

        embed = discord.Embed(title=beatmap.artist + " - " + beatmap.title + f" *[{beatmap.version}]*",
                              url=pictures.beatmap_link,
                              color=await self.embed_color(beatmap.approved),
                              description=f"+ __**{score.enabled_mods}**__ ({calculators.star_rating}★), "
                                          f"worth - **{calculators.pp}pp**/**{acc_fc}pp**\n"
                                          f"{map_perc if map_perc else ''}")
        embed.set_author(name=f"{username} #{pp_rank}\U0001f30e",
                         url=pictures.user_link,
                         icon_url=pictures.user_avatar)
        embed.set_thumbnail(url=pictures.beatmap_bg)
        embed.add_field(name='Beatmap',
                        value=f"__{length[0]}:{length[1]}min, {bpm}bpm__\n"
                              f"``{difficulties}``",
                        inline=False)
        embed.add_field(name=f'Score',
                        value=f"```coffeescript\n"
                              f"Accuracy - {accuracy_string}\n"
                              f"Combo    - {combo_string}, {score.countmiss}x\n"
                              f"```",
                        inline=False)
        if after_play.new_stuff:
            embed.add_field(name="Changes",
                            value=f"```fix\n"
                                  f"{after_play.new_stuff}"
                                  f"\n```",
                            inline=False)

        embed.set_footer(text=f"SS - {ss}pp, 95% - {pp95}pp, 90% - {pp90}pp")
        await self.send_message(embed, channels)

    async def format_new_top_score(self):
        if NewScore.new_score_num:
            return f"New top score __**#{NewScore.new_score_num}**__!"

    async def reset_values(self):
        NewScore.new_score_num = None
        AfterSubmit.new_stuff = None

    async def send_message(self, embed, channels):
        for channel_id in channels:
            await self.bot.get_channel(channel_id).send(await self.format_new_top_score(), embed=embed)
            await asyncio.sleep(0.5)
        await self.reset_values()


def setup(bot):
    bot.add_cog(EmbedMessage(bot))
