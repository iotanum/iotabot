from .performance_points import PP


class BeatmapDifficulty:
    def __init__(self):
        self.beatmap_calculator = PP()

    async def beatmap_mod_check(self, mods):
        possible_modifications = ["DT", "NC", "HT", "HR", "EZ"]
        for modification in possible_modifications:
            if mods.find(modification) != -1:
                return modification

    async def calculate_map_length(self, beatmap, multiplier):
        length_with_multiplier = beatmap.total_length / multiplier
        minutes, seconds = divmod(length_with_multiplier, 60)
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
        speed_multi, ar, od, cs, hp = await self.beatmap_calculator.beatmap_difficulity_with_mods(mods,
                                                                                                  default_difficulties)
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

    async def calculate_map_bpm(self, bpm, mods):
        multiplier = await self.bpm_calculation_multipliers(mods)
        final_map_bpm = bpm * multiplier
        return int(round(final_map_bpm, 0)), multiplier

    async def bpm_calculation_multipliers(self, mods):
        mods_with_multipliers = ['DT', 'NC', 'HT']
        for mod in mods_with_multipliers:
            if 'HT' in mods:
                return 0.75
            elif mod in mods:
                return 1.5
        return 1

    async def get_map_length_and_bpm(self, beatmap, mods):
        bpm, multiplier = await self.calculate_map_bpm(beatmap.bpm, mods)
        return bpm, await self.calculate_map_length(beatmap, multiplier)

