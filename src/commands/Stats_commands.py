from typing import List

import discord
from discord.ext import commands
from sqlalchemy import desc, func

from ..database import get_session
from ..database.models.user import UserStats


class Statistics_commands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @commands.hybrid_command(
        name="userstats",
        usage="userstats <member>",
        description="Shows all stats for the specified user",
    )
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def getMemberStats(self, ctx: commands.Context, member: discord.Member):
        """
        Shows all stats for the specified user.
        """
        print(f"Fetching stats for user {member.id}...")
        with get_session() as session:
            users = (
                session.query(UserStats)
                .filter_by(user_id=member.id)
                .order_by(desc(UserStats.time)) # type: ignore
                .limit(50)
                .all()
            )
            warning_count = (
                session.query(func.count(UserStats.id))
                .filter_by(user_id=member.id)
                .scalar()
            )
        await ctx.send(
            f"{member.mention}" if warning_count > 50 else "\n- "
            + "\n- ".join(users.map(lambda w: f"ID {w.id} on {w.time.strftime('%Y-%m-%d %H:%M:%S')}")),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Statistics_commands(bot))
