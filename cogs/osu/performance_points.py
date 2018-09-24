import aiohttp
import pyttanko

p = pyttanko.parser()


class PP:
    def __init__(self):
        self.star_rating = ""
        self.pp = ""
        self.accuracy = ""
        self.possible_pp = []

    async def submitted_score_calc(self, get_user_recent):
        accuracy_real = (((get_user_recent.count300 * 300) + (get_user_recent.count100 * 100) +
                    (get_user_recent.count50 * 50) + (get_user_recent.countmiss * 0)) /
                    ((get_user_recent.count300 + get_user_recent.count100 + get_user_recent.count50 +
                      get_user_recent.countmiss) * 300)) * 100

        return round(accuracy_real, 2)

    # needed for the pyttanko pp calc for accurate pepes
    async def possible_score_values(self, accuracy, parsed_beatmap, misses):
        n300, n100, n50 = await pyttanko.acc_round(accuracy, len(parsed_beatmap.hitobjects), misses)
        return n300, n100, n50

    async def beatmap_file(self, beatmap_id):
        async with aiohttp.request('GET', f"https://osu.ppy.sh/osu/{beatmap_id}") as response:
            data = await response.text()
        return data

    async def parse_beatmap_file(self, beatmap_id):
        return await p.map(await self.beatmap_file(beatmap_id))

    async def submitted_play_stuff(self, get_user_recent):
        if str(get_user_recent.enabled_mods) == 'NoMod':
            get_user_recent.enabled_mods = None

        return str(get_user_recent.enabled_mods), int(get_user_recent.maxcombo), int(get_user_recent.countmiss)

    async def submitted_play_star_calc(self, bmap, mods):
        return await pyttanko.diff_calc().calc(bmap, mods)

    async def submitted_play_mods(self, mods):
        return await pyttanko.mods_from_str(str(mods))

    async def calculate_pp(self, stars, bmap, mods, n50, n100, n300, combo, misses):
        calc = await pyttanko.ppv2(stars.aim, stars.speed, bmap=bmap, mods=mods, n50=n50,
                                   n100=n100, n300=n300, combo=combo, nmiss=misses)
        pp = round(calc[0], 2)
        return pp

    # returns speed_multiplier, ar, od, cs, hp
    async def beatmap_difficulity_with_mods(self, mods, beatmap_default):
        mods_from_str = await self.submitted_play_mods(mods)
        ar, od, hp, cs = beatmap_default
        return await pyttanko.mods_apply(mods_from_str, ar=ar, od=od, cs=cs, hp=hp)

    async def calculator(self, get_user_recent):
        mods, combo, misses = await self.submitted_play_stuff(get_user_recent)
        self.accuracy = await self.submitted_score_calc(get_user_recent)
        bmap = await self.parse_beatmap_file(get_user_recent.beatmap_id)
        mods = await self.submitted_play_mods(mods)
        stars = await self.submitted_play_star_calc(bmap, mods)
        self.star_rating = round(stars.total, 2)
        n300, n100, n50 = await self.possible_score_values(self.accuracy, bmap, misses)
        self.pp = await self.calculate_pp(stars, bmap, mods, n50, n100, n300, combo, misses)
        await self.possible_pp_calculator(self.accuracy, bmap, stars, mods)

    async def possible_pp_calculator(self, accuracy, bmap, stars, mods):
        self.possible_pp = []
        for acc in accuracy, 100, 95, 90:
            n300, n100, n50 = await self.possible_score_values(acc, bmap, 0)
            self.possible_pp.append(await self.calculate_pp(stars, bmap, mods, n50, n100, n300, await bmap.max_combo(), 0))


Calculators = PP()
