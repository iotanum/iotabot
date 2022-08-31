import aiohttp
import pyttanko
import json


class PP:
    def __init__(self):
        self.beatmap_parser = pyttanko.parser()
        self.star_rating = ""
        self.pp = ""
        self.accuracy = ""
        self.acc_if_no_misses = ""
        self.possible_pp = []

    async def format_payload(self, beatmap, mods, score):
        map_id = {"map_id": beatmap.beatmap_id}
        mods = [mods[i:i+2] for i in range(0, len(mods), 2)]
        mods = {"mods": mods}
        combo_stuff = {"good": score['100'], 'meh': score['50'], 'ok': score['100']}
        misses = {"miss": score['miss']}
        combo = {"combo": score['combo']}
        rework = {"rework": "live"}

        payload = {**map_id, **mods, **combo_stuff, **misses, **combo, **rework}
        return json.dumps(payload)

    async def send_request(self, payload):
        connector = aiohttp.TCPConnector(verify_ssl=False)
        headers = {"Content-Type": "application/json"}
        async with aiohttp.request('POST', f"http://pp/calculate",
                                   data=payload, connector=connector,
                                   headers=headers) as response:
            data = await response.json()
            print(data)
            await connector.close()
        return data

    async def submitted_accuracy_calc(self, get_user_recent, if_miss=False):
        accuracy_real = (((get_user_recent.count300 * 300) + (get_user_recent.count100 * 100) +
                          (get_user_recent.count50 * 50) + ((get_user_recent.countmiss if if_miss is False else 0) * 0)) /
                         ((get_user_recent.count300 + get_user_recent.count100 + get_user_recent.count50 +
                           (get_user_recent.countmiss if if_miss is False else 0)) * 300)) * 100

        return round(accuracy_real, 2)

    # needed for the pyttanko pp calc for accurate pepes
    async def possible_score_values(self, accuracy, beatmap, misses):
        hit_objects = beatmap.count_slider + beatmap.count_normal + beatmap.count_spinner
        n300, n100, n50 = pyttanko.acc_round(accuracy, hit_objects, misses)
        return n300, n100, n50

    async def beatmap_file(self, beatmap_id):
        async with aiohttp.request('GET', f"https://osu.ppy.sh/osu/{beatmap_id}") as response:
            data = await response.text()
        return data

    async def parse_beatmap_file(self, beatmap_id):
        return await self.beatmap_parser.map(await self.beatmap_file(beatmap_id))

    async def submitted_play_stuff(self, get_user_recent):
        if str(get_user_recent.enabled_mods) == 'NoMod':
            get_user_recent.enabled_mods = None

        return str(get_user_recent.enabled_mods), int(get_user_recent.maxcombo), int(get_user_recent.countmiss)

    async def submitted_play_star_calc(self, bmap, mods):
        return pyttanko.diff_calc().calc(bmap, mods)

    async def submitted_play_mods(self, mods):
        return pyttanko.mods_from_str(str(mods))

    # returns speed_multiplier, ar, od, cs, hp
    async def beatmap_difficulity_with_mods(self, mods, beatmap_default):
        mods_from_str = await self.submitted_play_mods(mods)
        ar, od, hp, cs = beatmap_default
        return pyttanko.mods_apply(mods_from_str, ar=ar, od=od, cs=cs, hp=hp)

    async def calculator(self, get_user_recent, beatmap):
        mods, combo, misses = await self.submitted_play_stuff(get_user_recent)

        score = {"mods": mods, "combo": combo, "miss": misses, "300": get_user_recent.count300,
                 "100": get_user_recent.count100, "50": get_user_recent.count50}
        json_payload = await self.format_payload(beatmap, mods, score)
        calcd_score = await self.send_request(json_payload)
        self.accuracy = round(calcd_score['accuracy'], 2)

        self.pp = round(calcd_score['local_pp'], 2)
        self.star_rating = round(calcd_score['newSR'], 2)

        self.acc_if_no_misses = await self.submitted_accuracy_calc(get_user_recent, if_miss=True)
        await self.possible_pp_calculator(self.acc_if_no_misses, beatmap, mods, score)

    async def possible_pp_calculator(self, accuracy, bmap, mods, score):
        self.possible_pp = []
        for acc in accuracy, 100, 95, 90:
            if acc == accuracy:
                n300, n100, n50 = await self.possible_score_values(acc, bmap, 0)
                score['100'] = n100
                score['50'] = n50
                score['miss'] = 0
                score['combo'] = bmap.max_combo
                print(score, "possible score")
                json_payload = await self.format_payload(bmap, mods, score)
                calcd_score = await self.send_request(json_payload)
                pp = round(calcd_score['local_pp'], 2)
            else:
                pp = 0

            self.possible_pp.append(pp)
