from discord import app_commands, Interaction, Poll, Guild
from discord.ext import commands
from datetime import datetime, time, timedelta
from enum import Enum
import asyncio
import logging

from util.db import SqlDB

WEEKDAY = {
    "lunedì": 0,
    "martedì": 1,
    "mercoledì": 2,
    "giovedì": 3,
    "venerdì": 4,
    "sabato": 5,
    "domenica": 6
}

class Duration(Enum):
    One = 1
    Four = 4
    Eight = 8
    Twelve = 12
    Twentyfour = 24
    TwoDays = 48
    ThreeDays = 76
    OneWeek = 168
    TwoWeek = 336
    def get_duration(dur: str) -> timedelta:
        if dur == "1 Hour":
            return Duration.One.__get_deltatime_from_now()
        if dur == "4 Hours":
            return Duration.Four.__get_deltatime_from_now()
        if dur == "8 Hours":
            return Duration.Eight.__get_deltatime_from_now()
        if dur == "12 Hours":
            return Duration.Twelve.__get_deltatime_from_now()
        if dur == "24 Hours":
            return Duration.Twentyfour.__get_deltatime_from_now()
        if dur == "2 Days":
            return Duration.TwoDays.__get_deltatime_from_now()
        if dur == "3 Days":
            return Duration.ThreeDays.__get_deltatime_from_now()
        if dur == "1 Week":
            return Duration.OneWeek.__get_deltatime_from_now()
        if dur == "2 Week":
            return Duration.TwoWeek.__get_deltatime_from_now()
    def __get_deltatime_from_now(self):
        return timedelta(hours = self.value)
    
async def duration_autocomplete(self, interaction: Interaction) -> list[app_commands.Choice[str]]:
    choices = ["1 Hour", "4 Hours", "8 Hours", "12 Hours", "24 Hours", "2 Days", "3 Days", "1 Week", "2 Week"]
    return [ app_commands.Choice(name=choice, value=choice) for choice in choices ]

class CreateSurvey(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name = "survey",
        description = "Crea un sondaggio per organizzare le tue sessioni!",
    )
    @app_commands.describe(
        question = "Question to ask for the survey",
        duration = "Duration of the survey",
        additional_message = "Optional additional message to add to the survey",
        mon = "Monday",
        tue = "Tuesday",
        wed = "Wednesday",
        thu = "Thursday",
        fri = "Friday",
        sat = "Saturday",
        sun = "Sunday"
    )
    @app_commands.autocomplete(duration=duration_autocomplete)
    async def create_survey(self, interaction: Interaction, question: str, duration: str, additional_message: str = '', mon: str = '', tue: str = '', wed: str = '', thu: str = '', fri: str = '', sat: str = '', sun: str = ''):
        if not (mon or tue or wed or thu or fri or sat or sun):
            await interaction.response.send_message(content = "Nessun orario inserito" , ephemeral = True)
            return
        p = Poll(question = question, multiple = True, duration = Duration.get_duration(duration))

        for i, day_text in enumerate([mon, tue, wed, thu, fri, sat, sun]):
            if day_text:
                d = next(k.capitalize() for k,v in WEEKDAY.items() if v == i)
                p.add_answer(text = f"{d} ~ {day_text}")

        if additional_message != '':
            await interaction.response.send_message(content = additional_message, poll = p)
        else:
            await interaction.response.send_message(poll = p)
        
        sent = interaction.original_response()
        end_time: datetime = (datetime.now() + Duration.get_duration(duration))

        SqlDB.add_poll(
            question = question,
            guild_id = interaction.guild_id,
            channel_id = interaction.channel_id,
            message_id = sent.id,
            end_time = end_time.isoformat()
        )

def __get_next_week_datetime(target_day: str, start_hour: int, end_hour: int):
    today = datetime.now().date()
    today_weekday = today.weekday()

    target_day = target_day.lower()
    if target_day not in WEEKDAY:
        raise ValueError(f"Invalid Day: {target_day}")
    
    day_index = WEEKDAY[target_day]

    days_ahead = (day_index - today_weekday + 7) % 7
    if days_ahead == 0:
        days_ahead = 7

    target_date = today + timedelta(days = days_ahead)

    start_time = datetime.combine(target_date, time(start_hour))
    end_time = datetime.combine(target_date, time(end_hour))

    return start_time, end_time

async def poll_watcher(bot: commands.bot):
    await bot.wait_unitl_ready()
    while not bot.is_closed():
        next_poll = SqlDB.get_next_poll()
        if not next_poll:
            await asyncio.sleep(1000)
            continue
        
        end_time = datetime.fromisoformat(next_poll[5])
        wait_seconds = (end_time - datetime.now()).total_seconds() + 120 # 2 minutes buffer

        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)
        
        for poll in SqlDB.get_expired_polls():
            guild: Guild = bot.get_guild(poll[2])
            channel = guild.get_channel(poll[3])

            await channel.send(f"🎉 Il sondaggio '{poll[1]}' è terminato! 🎉")

            try:
                message = await channel.fetch_message(poll[4])
                if not message.poll:
                    continue
                winning_option = max(message.poll.answers, key=lambda a: a.vote_count())
                day_part, time_range = winning_option.text.split('~')
                day = day_part.strip()
                start_hour, end_hour = map(lambda x: int(x.strip(), time_range.strip().split('-')))
                start, end = __get_next_week_datetime(day, start_hour, end_hour)

                await guild.create_scheduled_event(
                    name = f"Session: {message.poll.question}",
                    description = "Auto generated event",
                    start_time = start,
                    end_time = end,
                    channel = channel,
                )
            except Exception as e:
                logging.error(f"[ERROR SURVEY] - {e}")

            SqlDB.mark_poll_processed(poll[0])

# Cog setup
# async def setup(bot: commands.Bot):
#     await bot.add_cog(CreateSurvey(bot))
#     bot.loop.create_task(poll_watcher(bot))
