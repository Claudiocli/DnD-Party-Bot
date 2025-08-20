import os
import logging
from discord import Interaction, app_commands
from discord.ext import commands
from dotenv import load_dotenv

# from util.db import MongoSync

load_dotenv()

class SelectAnnouncementsChannel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Register events listeners one by one (if not already registered)
        self.bot.add_listener(self.on_guild_scheduled_event_create, "on_guild_scheduled_event_create")
        self.bot.add_listener(self.on_guild_scheduled_event_update, "on_guild_scheduled_event_update")
        self.bot.add_listener(self.on_guild_scheduled_event_delete, "on_guild_scheduled_event_delete")
        self.announcements_channels = {}  # key: guild_id, value: channel id

    async def on_guild_scheduled_event_create(self, event):
        guild = event.guild
        channel_id = self.announcements_channels.get(guild.id)
        if channel_id:
            channel = guild.get_channel(channel_id)
            if channel:
                await channel.send(f"Hey @everyone, è stata programmata una sessione! :eyes:\n"
                                   f"Tenetevi pronti per {event.scheduled_start_at}!")
                logging.info(f"ScheduledEvent created in guild {guild.name}")

    async def on_guild_scheduled_event_update(self, before, after):
        guild = after.guild
        channel_id = self.announcements_channels.get(guild.id)
        if channel_id:
            channel = guild.get_channel(channel_id)
            if channel:
                formatted_time = after.scheduled_start_at.strftime("%H:%M")
                formatted_date = after.scheduled_start_at.strftime("%A, %d %B")
                await channel.send(f"Cambio di programmi @everyone! La sessione {before.name} si terrà "
                                   f"alle ore {formatted_time} di {formatted_date}.")
                logging.info(f"ScheduledEvent updated in guild {guild.name}")

    async def on_guild_scheduled_event_delete(self, event):
        guild = event.guild
        channel_id = self.announcements_channels.get(guild.id)
        if channel_id:
            channel = guild.get_channel(channel_id)
            if channel:
                await channel.send(f"@everyone, mi dispiace informarvi che la sessione {event.name} è stata cancellata")
                logging.info(f"ScheduledEvent deleted in guild {guild.name}")

    @app_commands.command(
        name="select_announcements_channel",
        description="Select this channel as the announcements channel"
    )
    async def select_announcements_channel(self, interaction: "Interaction"):
        # Setup listeners (already registered) updating channels' map
        self.announcements_channels[interaction.guild.id] = interaction.channel.id

        # Update MongoDB
        # client_mongo = MongoSync.get_client()
        # db = client_mongo[os.getenv("MONGO_DB_NAME")]
        # ann = db[os.getenv("MONGO_A_COLLECTION_NAME")]
        # try:
        #     ann.update_one({"guild": interaction.guild.id},
        #                    {"$set": {"channel": interaction.channel.id}},
        #                    upsert=True)
        #     await interaction.response.send_message("Channel successfully selected", ephemeral=False)
        #     logging.info(f"Announcements channel set for guild {interaction.guild.name}")
        # except Exception as e:
        #     logging.error(f"[MONGODB ERROR] Error on inserting announcement channel in db: {e}")
        #     await interaction.response.send_message("An error occurred while updating the database", ephemeral=False)
        # finally:
        #     MongoSync.close_client()

# Cog setup
# async def setup(bot: commands.Bot):
#     await bot.add_cog(SelectAnnouncementsChannel(bot))
