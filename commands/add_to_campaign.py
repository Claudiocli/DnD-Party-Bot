import logging
from discord import Interaction, User, app_commands, SelectOption
from discord.ext import commands
from discord.ui import View, UserSelect, Select
from dotenv import load_dotenv
from asyncio import to_thread

from util.db import TinySync
from util.tools import is_user_admin
from tinydb import Query

load_dotenv()

locales = {
    "it": {
        "user_added": "L'utente è stato inserito nella campagna - ",
        "users_added": "Gli utenti sono stati inseriti nella campagna correttamente. Utenti inseriti: ",
        "user_already": "L'utente è già stato inserito!",
        "player_role_not_found": "Il ruolo player non è stato trovato nel server!",
        "member_not_found": "L'utente non è stato trovato nel server!",
        "generic_error": "Errore verificatosi nel processo del comando.",
    },
    "eng": {
        "user_added": "User added to campaign - ",
        "users_added": "Users were added to campaign succesfully. Users added: ",
        "user_already": " was already added!",
        "player_role_not_found": "Player role not found in the server!",
        "member_not_found": "User not found in the server!",
        "generic_error": "An error occurred while processing the command.",
    }
}


class AddToCampaign(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="add",
        description="Add a user to your campaign"
    )
    async def add(self, interaction: Interaction):
        locale = interaction.locale if interaction.locale in locales else "eng"
        await interaction.response.defer(ephemeral=False)
        logging.info("[INFO] - Trying to add a user to a campaign")

        view = View(timeout=None)

        campaigns = (TinySync.get_all_campaigns() if is_user_admin(interaction.user)
                     else TinySync.get_all_campaigns_with_user(interaction.user.id))
        select_campaign = Select(
            placeholder="Seleziona una campagna",
            min_values=1,
            max_values=1,
            options=[SelectOption(label=c["name"]) for c in campaigns]
        )

        async def campaign_callback(select_interaction: Interaction):
            selected_campaign = select_campaign.values[0]
            players_ids = TinySync.get_users_from_campaign(selected_campaign)
            members = []
            for uid in players_ids:
                try:
                    member = await interaction.guild.fetch_member(uid)
                    if member:
                        members.append(member)
                except:
                    continue

            user_select = UserSelect(
                placeholder="Seleziona utenti da aggiungere",
                min_values=1,
                max_values=25
            )

            async def user_callback(user_interaction: Interaction):
                q = Query()
                campaign_data = await to_thread(TinySync.get_collection().get, q.name == selected_campaign)

                for user in user_select.values:
                    if user.id in campaign_data["players"]:
                        await user_interaction.response.send_message(f"{user.name}{locales[locale]['user_already']}")
                        continue

                    member = interaction.guild.get_member(user.id)
                    if member is None:
                        await user_interaction.response.send_message(locales[locale]["member_not_found"])
                        continue

                    role = next((r for r in interaction.guild.roles if r.name == f"{selected_campaign}_Player"), None)
                    if role:
                        await member.add_roles(role)
                        TinySync.get_collection().update({"players": campaign_data["players"] + [user.id]},
                                                         q.name == selected_campaign)
                    else:
                        await user_interaction.response.send_message(locales[locale]["player_role_not_found"])
                await user_interaction.response.send_message(f"{locales[locale]['users_added']}{', '.join([user.name for user in user_select.values])}")

                TinySync.close()
                view.stop()

            user_select.callback = user_callback

            view.clear_items()
            view.add_item(select_campaign)
            view.add_item(user_select)
            await select_interaction.response.edit_message(view=view)

        select_campaign.callback = campaign_callback
        view.add_item(select_campaign)
        await interaction.followup.send(view=view)

    @add.error
    async def add_error(self, interaction: Interaction, error: Exception):
        logging.error(f"Error in add command: {error}")
        locale = interaction.locale if interaction.locale in locales else "eng"
        await interaction.followup.send(content=locales[locale]["generic_error"])


# Cog setup
async def setup(bot: commands.Bot):
    await bot.add_cog(AddToCampaign(bot))
