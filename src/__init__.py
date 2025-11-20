from typing import List
import asyncio
import logging
import os
import glob

import discord
from discord.ext import commands

from .config import logger_config
from .config.discord_config import BOT_PREFIX

# Configure loggers - This must run before SQLAlchemy is initialized
logger_config.configure_logger(
    [
        "Eternal.Main",
        "Eternal.Database",
        "SQLAlchemy",
        "Discord",
        "discord.http",
        "Eternal.Transcripts",
        "Eternal.Events",
        "Eternal.RSVP",
        "Eternal.Information",
        "Eternal.EventServerController"
    ]
)

from .database import get_session

logger: logging.Logger = logging.getLogger("Eternal.Main")

# Setup bot instance
intents: discord.Intents = discord.Intents.all()
bot: commands.Bot = commands.Bot(BOT_PREFIX, intents=intents)


modules_dir = os.path.join(os.path.dirname(__file__), "commands")
events_dir = os.path.join(os.path.dirname(__file__), "events")
extensions = [
    f.replace(os.path.join(modules_dir, ""), "").replace(".py", "")
    for f in glob.glob(os.path.join(modules_dir, "*.py"))
    if not os.path.basename(f).startswith("__")
]
events = [
    f.replace(os.path.join(events_dir, ""), "").replace(".py", "")
    for f in glob.glob(os.path.join(events_dir, "*.py"))
    if not os.path.basename(f).startswith("__")
]

logger.info("Discovered modules: %s", ", ".join(extensions))
logger.info("Discovered events: %s", ", ".join(events))

async def load_extensions(extensions: List[str]):
    for extension in extensions:
        try:
            await bot.load_extension(f"{__package__}.commands.{extension}")
            logger.info(f"Loaded module {extension}.")
        except Exception as e:
            logger.error(f"Failed to load module {extension}.", exc_info=e)


async def load_events(events: List[str]):
    for event in events:
        try:
            await bot.load_extension(f"{__package__}.events.{event}")
            logger.info(f"Loaded module {event}.")
        except Exception as e:
            logger.error(f"Failed to load module {event}.", exc_info=e)



asyncio.run(load_extensions(extensions))
asyncio.run(load_events(events))


logger.debug("Extentions loaded!")


@bot.event
async def on_ready():
    # Sync commands once possible
    logger.debug("Waiting until bot is ready...")
    await bot.wait_until_ready()
    logger.debug("Syncing commands...")
    await bot.tree.sync()
    logger.debug("Commands synced!")
    # Announce version info and set status
    logger.info("Running discord.py %s", discord.__version__)
    logger.info("We have logged in as %s", bot.user.name) # type: ignore
    await bot.change_presence(
            activity=discord.Activity(
            type=discord.ActivityType.listening, name="to your commands!"
        )
    )
    logger.info("Ready!")


# bot.run is implemented in __main__