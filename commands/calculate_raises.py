import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

locales = {
    "it":   {
        "invalid_number": "Numero inserito non valido",
    },
    "eng":  {
        "invalid_number": "Invalid number inserted",
    }
}



def calculate_optimal_raises(dice_results, double_raise_15=False):
    """
    Calculate the maximum possible raises from a list of dice results,
    handling duplicate values correctly.
    
    Args:
        dice_results (list): List of integers representing dice roll results
        double_raise_15 (bool): If True, combinations summing to at least 15 give 2 raises
        
    Returns:
        int: Maximum number of raises
        list: List of dice combinations used to form raises
    """
    # Sort dice in descending order
    dice = sorted(dice_results, reverse=True)
    
    # Convert dice list to a list of (value, index) pairs to track individual dice
    indexed_dice = [(value, i) for i, value in enumerate(dice)]
    
    # Store results
    best_raises = 0
    best_combinations = []
    
    def backtrack(remaining_dice, current_combinations, current_raises):
        nonlocal best_raises, best_combinations
        
        # If we've achieved more raises than our previous best, update it
        if current_raises > best_raises:
            best_raises = current_raises
            best_combinations = current_combinations.copy()
        elif current_raises == best_raises and len(current_combinations) > len(best_combinations):
            # If same raises but fewer unused dice, prefer this solution
            best_combinations = current_combinations.copy()
        
        # If no more dice, or can't improve on best solution, return
        if not remaining_dice:
            return
        
        # Try to form a raise with the first die
        
        # Try using dice as part of combinations
        if double_raise_15:
            # First try to form a 15+ combination (double raise)
            potential_15_combos = find_combinations_with_sum(remaining_dice, 15)
            for combo in potential_15_combos:
                # Remove these dice from remaining
                new_remaining = remove_dice(remaining_dice, combo)
                combo_values = [v for v, _ in combo]
                backtrack(new_remaining, 
                         current_combinations + [(combo_values, sum(combo_values), "double")],
                         current_raises + 2)
        
        # Try to form a 10+ combination (standard raise)
        potential_10_combos = find_combinations_with_sum(remaining_dice, 10)
        for combo in potential_10_combos:
            # Check if this would be a double raise
            combo_sum = sum(v for v, _ in combo)
            raise_type = "double" if double_raise_15 and combo_sum >= 15 else "standard"
            raise_value = 2 if raise_type == "double" else 1
            
            # Remove these dice from remaining
            new_remaining = remove_dice(remaining_dice, combo)
            combo_values = [v for v, _ in combo]
            backtrack(new_remaining,
                     current_combinations + [(combo_values, sum(combo_values), raise_type)],
                     current_raises + raise_value)
        
        # Try skipping the first die
        if remaining_dice:
            backtrack(remaining_dice[1:], current_combinations, current_raises)
    
    def find_combinations_with_sum(dice_list, min_sum):
        """Find combinations of dice that sum to at least min_sum"""
        result = []
        
        # Try combinations of different sizes
        for size in range(1, min(5, len(dice_list) + 1)):
            find_combos_recursive(dice_list, [], 0, size, min_sum, result)
        
        return result
    
    def find_combos_recursive(dice_list, current_combo, start_idx, size, min_sum, result):
        """Recursively find all combinations of the given size that sum to at least min_sum"""
        # If we've reached the desired size
        if len(current_combo) == size:
            combo_sum = sum(v for v, _ in current_combo)
            if combo_sum >= min_sum:
                result.append(current_combo.copy())
            return
        
        # Try adding each remaining die
        for i in range(start_idx, len(dice_list)):
            current_combo.append(dice_list[i])
            find_combos_recursive(dice_list, current_combo, i + 1, size, min_sum, result)
            current_combo.pop()
    
    def remove_dice(dice_list, to_remove):
        """Remove specific dice (value, index) from the list"""
        result = dice_list.copy()
        for die in to_remove:
            result.remove(die)
        return result
    
    # Start the backtracking algorithm
    backtrack(indexed_dice, [], 0)
    
    # Find unused dice - we need to extract the indices of used dice
    used_indices = set()
    for combo_values, _, _ in best_combinations:
        # Extract the original dice from the combination values
        remaining_indices = list(range(len(dice)))
        
        # For each value in our combo, find a matching die that hasn't been used yet
        for value in combo_values:
            for i in remaining_indices:
                if i not in used_indices and dice[i] == value:
                    used_indices.add(i)
                    remaining_indices.remove(i)
                    break
    
    unused_dice = [dice[i] for i in range(len(dice)) if i not in used_indices]
    
    return best_raises, best_combinations, unused_dice

async def display_raises_result(dice_roll, double_raise_15=False):
    """Display the optimal raises calculation results"""
    raises, combos, unused_dice = calculate_optimal_raises(dice_roll, double_raise_15)
    
    result_str = ""

    result_str += f"Dice Roll: {dice_roll} \n"
    result_str += f"Total Raises: {raises} \n"
    result_str += "Combinations used: \n"
    
    for combo, total, raise_type in combos:
        if raise_type == "double":
            result_str += f"  {combo} -> Sum: {total} -> Double raise! \n"
        else:
            result_str += f"  {combo} -> Sum: {total} -> 1 raise \n"
    
    if unused_dice:
        result_str += f"Unused dice: {unused_dice} \n"

    return result_str


class CalculateRaises(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="7sr",
        description="Calculate 7th sea raises given a list of roll dice"
    )
    @app_commands.describe(rolls="Comma separeted dice roll results")
    @app_commands.describe(use_15="Pass true if your skill has 3 points or more")
    async def seven_sea_raises(self, interaction: discord.Interaction, rolls: str, use_15: Optional[bool] = False):
        await interaction.response.defer(ephemeral=False)

        if rolls is None:
            locale = interaction.locale if interaction.locale in locales else "eng"
            await interaction.followup.send(content=locales[locale]["invalid_number"], ephemeral=True)
            return
        
        rolls_int: list[int]
        try:
            rolls_int = [int(x) for x in rolls.replace(' ','').split(',')]
        except ValueError:
            # mammt
            locale = interaction.locale if interaction.locale in locales else "eng"
            await interaction.followup.send(content=locales[locale]["invalid_number"], ephemeral=True)
            return

        await interaction.followup.send(str( await display_raises_result(rolls_int, use_15)))

async def setup(bot: commands.Bot):
    await bot.add_cog(CalculateRaises(bot))
