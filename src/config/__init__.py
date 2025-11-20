from datetime import datetime

import discord

def relative_dt(dt: datetime) -> str:
    """Format the datetime in the relative timestamp form."""

    return discord.utils.format_dt(dt, style="R")