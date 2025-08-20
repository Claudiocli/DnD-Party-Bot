import logging
import traceback
from discord import InteractionMessage, PrivacyLevel, app_commands, Interaction, Poll
from discord.ext import commands
from discord.utils import utcnow
from datetime import timedelta
import asyncio

DURATION_CHOICES = [
    app_commands.Choice(name="1 hour", value=1),
    app_commands.Choice(name="2 hours", value=2),
    app_commands.Choice(name="4 hours", value=4),
    app_commands.Choice(name="8 hours", value=8),
    app_commands.Choice(name="12 hours", value=12),
    app_commands.Choice(name="1 day", value=24),
    app_commands.Choice(name="2 day", value=48),
    app_commands.Choice(name="3 day", value=72),
    app_commands.Choice(name="1 week", value=168),
]

WEEKDAYS = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
]

def next_weekday_datetime(target_weekday: str, hour: int, minute: int = 0):
    weekday_map = {
        "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
        "Friday": 4, "Saturday": 5, "Sunday": 6
    }
    now = utcnow()
    today_idx = now.weekday()
    target_idx = weekday_map[target_weekday.capitalize()]
    days_ahead = (target_idx - today_idx + 7) % 7
    if days_ahead == 0:
        days_ahead = 7  # Always get the next occurrence, not today
    next_date = now + timedelta(days=days_ahead)
    return next_date.replace(hour=hour, minute=0, second=0, microsecond=0)

def validate_interval(interval: str):
    # Accepts formats like "18-22"
    return interval and interval.strip() and interval.strip().count('-') == 1 and all(
        part.isdigit() and 0 <= int(part) <= 23 for part in interval.strip().split('-')
    )

class CreateSurvey(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="survey",
        description="Create a survey for your session scheduling!"
    )
    @app_commands.describe(
        question="Question for the poll",
        duration_hours="Poll duration",
        monday="Time interval for Monday (e.g. '18-22')",
        tuesday="Time interval for Tuesday (e.g. '20-23')",
        wednesday="Time interval for Wednesday",
        thursday="Time interval for Thursday",
        friday="Time interval for Friday",
        saturday="Time interval for Saturday",
        sunday="Time interval for Sunday",
        allow_multiselect="Allow users to select multiple options"
    )
    async def survey(
        self,
        interaction: Interaction,
        question: str,
        duration_hours: int = 1,
        monday: str = None,
        tuesday: str = None,
        wednesday: str = None,
        thursday: str = None,
        friday: str = None,
        saturday: str = None,
        sunday: str = None,
        allow_multiselect: bool = True
    ):
        opts = []
        for day, interval in zip(WEEKDAYS, [monday, tuesday, wednesday, thursday, friday, saturday, sunday]):
            if interval:
                if not validate_interval(interval):
                    await interaction.response.send_message(
                        f"Invalid interval for {day}: '{interval}'. Use format like '18-22'.",
                        ephemeral=True
                    )
                    return
                opts.append(f"{day} {interval}")
        if len(opts) < 2:
            await interaction.response.send_message(
                "Please provide at least two valid weekday intervals.",
                ephemeral=True
            )
            return

        poll = Poll(
            question=question,
            multiple=allow_multiselect,
            duration=timedelta(hours=duration_hours)
        )
        for o in opts:
            poll.add_answer(text=o)
        await interaction.response.send_message(
            content=f"Poll created!",
            poll=poll
        )
        msg = await interaction.original_response()

        # Schedule the action
        asyncio.create_task(self.on_poll_end(msg, duration_hours * 3600))

    async def on_poll_end(self, msg: InteractionMessage, delay_seconds: int):
        await asyncio.sleep(delay_seconds + 30) # Adding 30 sec delay to avoid internet shenanigans
        channel = self.bot.get_channel(msg.channel_id)
        if channel:
            await channel.send(f"Poll {msg.message_id} has ended! Now I'm gonna create the event!")
            name = channel.name.split("_organize")[0]
            if not name:    return
            stage = None
            # Getting stage channel
            for c in msg.guild.channels:
                if c.name == f"{name}_vocal":
                    stage = c
                    break
            if not stage:   return
            # Calculating start and end times
            v = msg.poll.victor_answer.text.split(' ')
            day, t = v[0], v[1].split('-')
            s, e = next_weekday_datetime(day, int(t[0])), next_weekday_datetime(day, int(t[1]))
            # Creating the event
            logging.info(f"Creating scheduled event for {name} from {s} to {e}")
            try:
                await msg.guild.create_scheduled_event(
                    name=f"{name} - Session",
                    description=f"A session for the campaign {name} organized by the bot",
                    channel=stage,
                    start_time=s,
                    end_time=e,
                    privacy_level=PrivacyLevel.guild_only
                )
            except Exception as e:
                logging.error(f"Failed to create scheduled event: {e}")
                logging.error(traceback.print_exc())
                return


    @survey.autocomplete('duration_hours')
    async def duration_autocomplete(
        self,
        interaction: Interaction,
        current: str
    ):
        current = current.lower()
        return [
            choice for choice in DURATION_CHOICES
            if current in choice.name.lower()
        ][:25]

async def setup(bot: commands.Bot):
    await bot.add_cog(CreateSurvey(bot))
