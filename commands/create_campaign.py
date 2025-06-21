import os
import random
import logging
import discord
from discord import app_commands, ChannelType, Permissions, Colour
from discord.ext import commands
from dotenv import load_dotenv

from util.db import MongoSync

load_dotenv()

def get_random_color() -> Colour:
    return Colour(random.randint(0, 0xFFFFFF))

class CreateCampaign(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.self.locales = {
            "it": {
                "already_exists": "Il nome selezionato esiste già",
                "created_success": "La campagna è stata creata correttamente",
                "Newbie": "Sei di livello troppo basso per creare una campagna!",
                "Paladin_already": "Hai già una campagna! Sali di livello per poterne creare delle altre!",
                "generic_error": "Si è verificato un errore",
            },
            "eng": {
                "already_exists": "Name selected already exists",
                "created_success": "Campaign created successfully",
                "Newbie": "You have too low level to create a campaign!",
                "Paladin_already": "You already have a campaign! Level up to create other campaign!",
                "generic_error": "An error has occurred",
            }
        }

    @app_commands.command(
        name="create_campaign",
        description="Create your DND campaign!"
    )
    @app_commands.describe(name="Name of your campaign")
    async def create_campaign(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=False)
                
        member = interaction.user
        
        if any(role.name == "Newbie" for role in member.roles):
            locale = interaction.locale if interaction.locale in self.locales else "eng"
            await interaction.followup.send(content=self.locales[locale]["Newbie"])
            return

        mongo_client = MongoSync.get_client()
        db = mongo_client[os.getenv("MONGO_DB_NAME")]
        campaigns = db[os.getenv("MONGO_COLLECTION_NAME")]

        try:
            if campaigns.find_one({"name": name}):
                locale = interaction.locale if interaction.locale in self.locales else "eng"
                await interaction.followup.send(content=self.locales[locale]["already_exists"], ephemeral=True)
                logging.warning("Campaign already exists")
                return
            else:
                campaigns.insert_one({
                    "name": name,
                    "elements": {
                        "dm": interaction.user.id,
                        "players": []
                    }
                })
                guild = interaction.guild
                logging.info(f"[INFO : {guild.name}] - Starting to create roles")

                role_dm = await guild.create_role(
                    name=f"{name}_DM",
                    colour=get_random_color(),
                    permissions=Permissions(view_channel=True, mute_members=True)
                )
                role_pl = await guild.create_role(
                    name=f"{name}_Player",
                    colour=get_random_color(),
                    permissions=Permissions(view_channel=True)
                )
                role_e = guild.default_role  # "@everyone"

                logging.info(f"[INFO : {guild.name}] - Starting to create channels")
                category = await guild.create_category(name=name)
                await category.set_permissions(role_dm, view_channel=True, mute_members=True)
                await category.set_permissions(role_pl, view_channel=True)
                await category.set_permissions(role_e, view_channel=False)

                await guild.create_voice_channel(name=f"{name}_vocal", category=category, type=ChannelType.stage_voice)
                await guild.create_text_channel(name=f"{name}_text", category=category)
                await guild.create_text_channel(name=f"{name}_meme", category=category)
                await guild.create_text_channel(name=f"{name}_organize", category=category)

                await member.add_roles(role_dm)

                locale = interaction.locale if interaction.locale in self.locales else "eng"
                await interaction.followup.send(content=self.locales[locale]["created_success"], ephemeral=False)
                logging.info("Campaign successfully created")
        except Exception as e:
            logging.error(f"[CreateCampaign] An error occurred: {e}")
            await interaction.followup.send(content=self.locales[locale]["generic_error"], ephemeral=False)
        finally:
            mongo_client.close()
            logging.info("Mongo Connection closed")

# Cog setup
async def setup(bot: commands.Bot):
    await bot.add_cog(CreateCampaign(bot))
