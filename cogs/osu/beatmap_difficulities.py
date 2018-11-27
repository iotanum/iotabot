from .performance_points import Calculators


class BeatmapDifficulities:
    async def beatmap_mod_check(self, mods):
        possible_modifications = ["DT", "NC", "HT", "HR", "EZ"]
        for modification in possible_modifications:
            if mods.find(modification) != -1:
                return modification

    async def length_calculator(self, beatmap, mods=False):
        minutes, seconds = divmod((beatmap.total_length - (beatmap.total_length * 0.33))
                                  if mods else beatmap.total_length, 60)
        seconds = int(round(seconds, 0))
        if seconds < 10:
            seconds = f"0{seconds}"
        elif seconds == 60:
            minutes += 1
            seconds = 0
        return int(minutes), seconds

    async def difficulties_without_mods(self, beatmap):
        return await self.types_change([beatmap.diff_approach, beatmap.diff_overall,
                                        beatmap.diff_drain, beatmap.diff_size])

    async def difficulties_with_mods(self, beatmap, mods):
        default_difficulties = await self.difficulties_without_mods(beatmap)
        speed_multi, ar, od, cs, hp = await Calculators.beatmap_difficulity_with_mods(mods, default_difficulties)
        return await self.types_change([round(ar, 2), round(od, 2), round(hp, 2), round(cs, 2)])

    async def type_check(self, diff):
        return type(diff) != str and diff % 1 == 0

    async def types_change(self, diff_list):
        counter = 0
        for diff in diff_list:
            if await self.type_check(diff):
                diff_list[0 + counter] = int(diff)
            counter += 1
        return diff_list

    async def beatmap_difficulties_format(self, beatmap, mods):
        formatted_diffs = ""
        counter = 0
        if await self.beatmap_mod_check(mods):
            new_diffs = await self.difficulties_with_mods(beatmap, mods)
            for new_diff in new_diffs:
                formatted_diffs += await self.magic_counter(counter) + f": {new_diff}, "
                counter += 1
            return formatted_diffs[:-2]
        else:
            original_diffs = await self.difficulties_without_mods(beatmap)
            for original_diff in original_diffs:
                formatted_diffs += await self.magic_counter(counter) + f": {original_diff}, "
                counter += 1
            return formatted_diffs[:-2]

    async def magic_counter(self, counter):
        choices = ['AR', 'OD', 'HP', 'CS']
        return choices[counter]

    async def bpm_calculator(self, bpm, mods=False):
        return int(round(bpm * 1.5, 0)) if mods else int(bpm)

    async def custom_check_for_calcs(self, mods):
        modifications = ["DT", "NC", "HT", "EZ"]
        if not [mod for mod in modifications if mod in mods]:
            return False
        return True

    async def lenght_and_bpm(self, beatmap, mods):
        check = await self.custom_check_for_calcs(mods)
        return await self.bpm_calculator(beatmap.bpm, mods=check), await self.length_calculator(beatmap, mods=check)


BeatmapDiff = BeatmapDifficulities()
