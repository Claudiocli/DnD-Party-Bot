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
        self.selected_campaign = ''
        self.campaigns = None


    def get_user_select(self, interaction: Interaction, locale: str) -> UserSelect:
            user_select = UserSelect(
                placeholder=locales[locale]['select_users_placeholder'],
                min_values=1,
                max_values=25
            )

            async def user_callback(user_interaction: Interaction):
                q = Query()
                campaign_data = await to_thread(TinySync.get_collection().get, q.name == self.selected_campaign)

                for user in user_select.values:
                    if user.id in campaign_data["players"]:
                        await user_interaction.response.send_message(f"{user.name}{locales[locale]['user_already']}")
                        continue

                    member = interaction.guild.get_member(user.id)
                    if member is None:
                        await user_interaction.response.send_message(locales[locale]["member_not_found"])
                        continue

                    role = next((r for r in interaction.guild.roles if r.name == f"{self.selected_campaign}_Player"), None)
                    if role:
                        await member.add_roles(role)
                        TinySync.get_collection().update({"players": campaign_data["players"] + [user.id]},
                                                         q.name == self.selected_campaign)
                    else:
                        await user_interaction.response.send_message(locales[locale]["player_role_not_found"])
                await user_interaction.response.send_message(f"{locales[locale]['users_added']}{', '.join([user.name for user in user_select.values])}")

                TinySync.close()
                user_select.view.stop()

            user_select.callback = user_callback
            user_select.disabled = True
            self.user_select = user_select


    def get_campaign_select(self, interaction: Interaction, locale: str) -> Select:
        select_campaign = Select(
            placeholder=locales[locale]['select_campaign_placeholder'],
            min_values=1,
            max_values=1,
            options=[SelectOption(label=c["name"]) for c in self.campaigns]
        )

        async def campaign_callback(select_interaction: Interaction):
            self.selected_campaign = select_campaign.values[0]
            players_ids = TinySync.get_users_from_campaign(self.selected_campaign)
            members = []
            for uid in players_ids:
                try:
                    member = await interaction.guild.fetch_member(uid)
                    if member:
                        members.append(member)
                except:
                    continue

        select_campaign.callback = campaign_callback
        
        return select_campaign


    @app_commands.command(
        name="add",
        description="Add a user to your campaign"
    )
    async def add(self, interaction: Interaction):
        locale = interaction.locale if interaction.locale in locales else "eng"
        await interaction.response.defer(ephemeral=False)
        logging.info("[INFO] - Trying to add a user to a campaign")
        # 5 min (300 sec) to process input and close the interaction
        view = View(timeout=300)

        if is_user_admin(interaction.user):
            self.campaigns = TinySync.get_all_campaigns()
        else:
            self.campaigns = TinySync.get_all_campaigns_with_user(interaction.user.id)
        
        view.add_item(self.get_campaign_select(interaction, locale))
        view.add_item(self.get_user_select(interaction, locale))
        await interaction.followup.send(view=view)


    @add.error
    async def add_error(self, interaction: Interaction, error: Exception):
        logging.error(f"Error in add command: {error}")
        locale = interaction.locale if interaction.locale in locales else "eng"
        await interaction.followup.send(content=locales[locale]["generic_error"])


# Cog setup
async def setup(bot: commands.Bot):
    await bot.add_cog(AddToCampaign(bot))
