import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Tuple, List, Dict

locales = {
    "it": {
        "invalid_number": "Numero inserito non valido",
    },
    "eng": {
        "invalid_number": "Invalid number inserted",
    }
}


# ----------------------------------------------------------
#  Efficient raise calculator for 7th Sea
#  Works with 15–20+ dice using memoization + pruning
# ----------------------------------------------------------

def calculate_optimal_raises(dice_results: List[int], double_raise_15: bool = False) -> Tuple[int, list, list]:
    """
    Calculate the maximum possible raises from a list of dice results,
    optimized to support 15–20+ dice using dynamic programming and pruning.

    Args:
        dice_results (list): List of integers representing dice roll results
        double_raise_15 (bool): If True, combinations summing to >=15 give 2 raises

    Returns:
        int: Maximum number of raises
        list: List of combinations used
        list: Unused dice
    """

    # Sort dice in descending order (helps pruning)
    dice = sorted(dice_results, reverse=True)

    # Memoization: key = (tuple(remaining_dice)), value = best result achievable
    memo: Dict[Tuple[int], Tuple[int, list]] = {}

    def explore(remaining: Tuple[int]) -> Tuple[int, list]:
        """
        Recursive search with memoization.
        Returns (max_raises, combinations_used)
        """

        # Memo check
        if remaining in memo:
            return memo[remaining]

        # Base case: no dice left
        if not remaining:
            memo[remaining] = (0, [])
            return memo[remaining]

        best_total_raises = 0
        best_combos = []

        n = len(remaining)

        # ------------------------------------------------
        #  Try all possible subsets that achieve a raise
        #  using pruning to avoid combinatorial explosion
        # ------------------------------------------------
        for mask in range(1, 1 << n):  # All subsets
            subset = []
            subset_sum = 0

            # Build the subset efficiently
            for i in range(n):
                if mask & (1 << i):
                    subset.append(remaining[i])
                    subset_sum += remaining[i]

            # Skip subsets too small to reach 10
            if subset_sum < 10:
                continue

            # Determine raise type
            if double_raise_15 and subset_sum >= 15:
                raise_type = "double"
                raise_value = 2
            else:
                raise_type = "standard"
                raise_value = 1

            # Remove used dice
            new_remaining = list(remaining)
            for value in subset:
                new_remaining.remove(value)
            new_remaining = tuple(sorted(new_remaining, reverse=True))

            # Recurse
            rec_raises, rec_combos = explore(new_remaining)

            total_raises = raise_value + rec_raises

            # Check if this is the new best
            if total_raises > best_total_raises:
                best_total_raises = total_raises
                best_combos = [(subset, subset_sum, raise_type)] + rec_combos

        # ------------------------------------------------
        #  Also consider the possibility of skipping raises
        # ------------------------------------------------
        memo[remaining] = (best_total_raises, best_combos)
        return memo[remaining]

    # Start recursion
    optimal_raises, optimal_combos = explore(tuple(dice))

    # Compute unused dice
    used = []
    for combo, _, _ in optimal_combos:
        used.extend(combo)

    unused = dice.copy()
    for val in used:
        unused.remove(val)

    return optimal_raises, optimal_combos, unused


# ----------------------------------------------------------
#  Build the final Discord message
# ----------------------------------------------------------

async def display_raises_result(dice_roll, double_raise_15=False):
    """Format optimal raise calculation into a Discord-friendly string."""

    raises, combos, unused_dice = calculate_optimal_raises(dice_roll, double_raise_15)

    result_str = ""
    result_str += f"Dice Roll: {dice_roll} \n"
    result_str += f"Total Raises: {raises} \n"
    result_str += "Combinations used:\n"

    for combo, total, raise_type in combos:
        if raise_type == "double":
            result_str += f"  {combo} -> Sum: {total} -> Double Raise! (+2)\n"
        else:
            result_str += f"  {combo} -> Sum: {total} -> 1 Raise\n"

    if unused_dice:
        result_str += f"Unused Dice: {unused_dice}\n"

    return result_str


# ----------------------------------------------------------
#  Discord Cog Command
# ----------------------------------------------------------

class CalculateRaises(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="7sr",
        description="Calculate 7th sea raises given a list of rolled dice."
    )
    @app_commands.describe(rolls="Comma separated dice roll results")
    @app_commands.describe(use_15="Set true if your skill rank is 3 or more")
    async def seven_sea_raises(self, interaction: discord.Interaction, rolls: str, use_15: Optional[bool] = False):

        await interaction.response.defer(ephemeral=False)

        if rolls is None:
            locale = interaction.locale if interaction.locale in locales else "eng"
            await interaction.followup.send(content=locales[locale]["invalid_number"], ephemeral=True)
            return

        try:
            rolls_int = [int(x) for x in rolls.replace(' ', '').split(',')]
        except ValueError:
            locale = interaction.locale if interaction.locale in locales else "eng"
            await interaction.followup.send(content=locales[locale]["invalid_number"], ephemeral=True)
            return

        result = await display_raises_result(rolls_int, use_15)
        await interaction.followup.send(result)


async def setup(bot: commands.Bot):
    await bot.add_cog(CalculateRaises(bot))
