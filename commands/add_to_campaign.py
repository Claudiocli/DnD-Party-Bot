import logging
from discord import Interaction, User, app_commands, SelectOption
from discord.ext import commands
from discord.ui import View, UserSelect, Select
from dotenv import load_dotenv
from asyncio import to_thread
import traceback

from util.db import TinySync
from util.tools import check_is_user_admin
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
        "select_campaign_placeholder": "Seleziona una campagna",
        "select_users_placeholder": "Seleziona utenti da aggiungere",
    },
    "eng": {
        "user_added": "User added to campaign - ",
        "users_added": "Users were added to campaign succesfully. Users added: ",
        "user_already": " was already added!",
        "player_role_not_found": "Player role not found in the server!",
        "member_not_found": "User not found in the server!",
        "generic_error": "An error occurred while processing the command.",
        "select_campaign_placeholder": "Select a campaign",
        "select_users_placeholder": "Select users to add",
    }
}


class AddToCampaign(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def get_campaign_select(self, interaction: Interaction, locale: str, campaigns, on_select):
        select_campaign = Select(
            placeholder=locales[locale]['select_campaign_placeholder'],
            min_values=1,
            max_values=1,
            options=[SelectOption(label=c["name"]) for c in campaigns]
        )
        select_campaign.callback = on_select
        return select_campaign

    def get_user_select(self, interaction: Interaction, locale: str, campaign_name):
        user_select = UserSelect(
            placeholder=locales[locale]['select_users_placeholder'],
            min_values=1,
            max_values=25
        )

        async def user_callback(user_interaction: Interaction):
            q = Query()
            campaign_data = await to_thread(TinySync.get_collection().get, q.name == campaign_name)
            for user in user_select.values:
                if user.id in campaign_data["players"]:
                    await user_interaction.response.send_message(f"{user.name}{locales[locale]['user_already']}")
                    continue
                member = interaction.guild.get_member(user.id)
                if member is None:
                    await user_interaction.response.send_message(locales[locale]["member_not_found"])
                    continue
                role = next((r for r in interaction.guild.roles if r.name == f"{campaign_name}_Player"), None)
                if role:
                    await member.add_roles(role)
                    TinySync.get_collection().update({"players": campaign_data["players"] + [str(user.id)]},
                                                     q.name == campaign_name)
                else:
                    await user_interaction.response.send_message(locales[locale]["player_role_not_found"])
            await user_interaction.response.send_message(
                f"{locales[locale]['users_added']}{', '.join([user.name for user in user_select.values])}"
            )
            TinySync.close()
            user_select.view.stop()

        user_select.callback = user_callback
        return user_select

    @app_commands.command(
        name="add",
        description="Add a user to your campaign"
    )
    async def add(self, interaction: Interaction):
        try:
            locale = interaction.locale if interaction.locale in locales else "eng"
            await interaction.response.defer(ephemeral=False)
            logging.info("[INFO] - Trying to add a user to a campaign")

            if check_is_user_admin(interaction.user):
                campaigns = TinySync.get_all_campaigns()
            else:
                campaigns = TinySync.get_all_campaigns_with_user(interaction.user.id)

            campaign_view = View(timeout=120)

            async def campaign_callback(select_interaction: Interaction):
                selected_campaign = select_campaign.values[0]
                user_view = View(timeout=180)
                user_view.add_item(self.get_user_select(interaction, locale, selected_campaign))
                await select_interaction.response.edit_message(
                    content=locales[locale]['select_users_placeholder'],
                    view=user_view
                )

            select_campaign = self.get_campaign_select(
                interaction, locale, campaigns, campaign_callback
            )
            campaign_view.add_item(select_campaign)
            await interaction.followup.send(
                content=locales[locale]['select_campaign_placeholder'],
                view=campaign_view
            )
        except Exception as e:
            logging.error(f"Error in add command: {e}")
            logging.error(traceback.format_exc())

    @add.error
    async def add_error(self, interaction: Interaction, error: Exception):
        logging.error(f"Error in add command: {error}")
        logging.error(traceback.format_exc())
        locale = interaction.locale if interaction.locale in locales else "eng"
        await interaction.followup.send(content=locales[locale]["generic_error"])


# Cog setup
async def setup(bot: commands.Bot):
    await bot.add_cog(AddToCampaign(bot))
