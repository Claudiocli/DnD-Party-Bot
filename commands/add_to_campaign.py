import os
import logging
from discord import Interaction, User, app_commands
from discord.ext import commands
from dotenv import load_dotenv
from asyncio import to_thread

from util.db import TinySync
from tinydb import Query

load_dotenv()

locales = {
    "it": {
        "user_added": "L'utente è stato inserito nella campagna - ",
        "user_already": "L'utente è già stato inserito!",
        "player_role_not_found":"Il ruolo player non è stato trovato nel server!",
        "member_not_found":"L'utente non è stato trovato nel server!",
        "generic_error":"Errore verificatosi nel processo del comando.",
    },
    "eng": {
        "user_added": "User added to campaign - ",
        "user_already": " was already added!",
        "player_role_not_found":"Player role not found in the server!",
        "member_not_found":"User not found in the server!",
        "generic_error":"An error occurred while processing the command.",
    }
}

# def get_campaigns_collection() -> "Collection":
#     # client = MongoSync.get_client()
#     # db = client[os.getenv("MONGO_DB_NAME")]
#     # return db[os.getenv("MONGO_COLLECTION_NAME")], client
#     return TinySync.get_collection()

class AddToCampaign(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="add",
        description="Add a user to your campaign"
    )
    async def add(self, interaction: "Interaction", name: str, user: "User"):
        locale = interaction.locale if interaction.locale in locales else "eng"

        await interaction.response.defer(ephemeral=False)

        logging.info("[INFO] - Trying to add a user to a campaign")
        # campaigns, client_mongo = get_campaigns_collection()
        campaigns = TinySync.get_collection()
        cq = Query()

        try:
            result = await to_thread(campaigns.get, cq.name == name)
            logging.info("[INFO] - Finding a campaign")
            guild = interaction.guild
            if result:
                member = guild.get_member(user.id)
                if member is None:
                    await interaction.followup.send(content=locales[locale]["member_not_found"])
                    return

                role = next((r for r in guild.roles if r.name == f"{name}_Player"), None)
                if role:
                    await member.add_roles(role)
                    logging.info(f"[INFO : {guild.name}] - Player Role assigned")
                    campaigns.update({"players": result["players"] + [user.id]}, cq.name == name)
                    # campaigns.update_one({"name": name}, {"$push": {"players": user.id}})
                    await interaction.followup.send(content=f"{locales[locale]['user_added']}{user.name}")
                else:
                    await interaction.followup.send(content=locales[locale]["player_role_not_found"])
            else:
                await interaction.followup.send(content=f"{user.name}{locales[locale]['user_already']}")
        except Exception as e:
            logging.error(f"[ERROR] - {e}")
            await interaction.followup.send(content=locales[locale]["generic_error"])
        finally:
            # MongoSync.close_client()
            TinySync.close()

    @add.autocomplete("name")
    async def add_name_autocomplete(self, interaction: "Interaction", current: str):
        return []

    @add.error
    async def add_error(self, interaction: "Interaction", error: Exception):
        logging.error(f"Error in add command: {error}")
        locale = interaction.locale if interaction.locale in locales else "eng"
        await interaction.followup.send(content=locales[locale]["generic_error"])

# Cog setup
async def setup(bot: commands.Bot):
    await bot.add_cog(AddToCampaign(bot))
