import logging
from typing import List

import discord
from discord.ext import commands
from sqlalchemy import desc, func

from ..database import get_session
from ..database.models.warning import WarningModel


logger: logging.Logger = logging.getLogger("Eternal.Administration")


class Administration(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @commands.hybrid_command(
        name="warnings",
        usage="warnings <member>",
        description="Shows all warnings for the specified user",
    )
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def warnings(self, ctx: commands.Context, member: discord.Member):
        logger.info(f"Fetching warnings for member {member} (ID: {member.id})")
        warnings: List[WarningModel] = []
        warnings_text: List[str] = ["none :)"]
        with get_session() as session:
            warnings = (
                session.query(WarningModel)
                .filter_by(memberId=member.id)
                .order_by(desc(WarningModel.time)) # type: ignore
                .limit(50)
                .all()
            )
            warning_count = (
                session.query(func.count(WarningModel.warningId))
                .filter_by(memberId=member.id)
                .scalar()
            )
            if len(warnings) > 0:
                warnings_text: List[str] = [
                    f"<t:{round(warning.time.timestamp())}> {warning.reason}"
                    for warning in warnings
                ]
        # TODO: If a member has way too many warnings, we might need to handle messages longer than 2000 chars by sending multiple messages.
        # The terrible ternary will add "(showing at most 50 latest)" to the message if the user has more than 50 warnings
        await ctx.send(
            f"{member.mention} has {warning_count} total warnings{' (showing at most 50 latest)' if warning_count > 50 else ''}: \n- "
            + "\n- ".join(warnings_text),
            ephemeral=True,
        )
        logger.info(f"Displayed warnings for member {member} (ID: {member.id})")
        
        
    @commands.hybrid_command(
        name="clearwarnings",
        usage="clearwarnings <member>",
        description="Clears all warnings for the specified user",
    )
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def clearwarnings(self, ctx: commands.Context, member: discord.Member): 
        logger.info(f"Clearing warnings for member {member} (ID: {member.id})")
        with get_session() as session:
            deleted_count = (
                session.query(WarningModel)
                .filter_by(memberId=member.id)
                .delete(synchronize_session=False)
            )
            session.commit()
        await ctx.send(
            f"Cleared {deleted_count} warnings for {member.mention}.",
            ephemeral=True,
        )
        logger.info(f"Cleared warnings for member {member} (ID: {member.id})")
    
    
    @commands.hybrid_command(
        name="banmember",
        usage="banmember <member> [reason]",
        description="Bans the specified member from the server.",
    )
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def banmember(self, ctx: commands.Context, member: discord.Member, *, reason
        = "No reason provided"):
        logger.info(f"Banning member {member} (ID: {member.id}) for reason: {reason}")
        await member.ban(reason=reason)
        await ctx.send(f"{member.mention} has been banned. Reason: {reason}", ephemeral=True)
        logger.info(f"Banned member {member} (ID: {member.id})")
    
    @commands.hybrid_command(
        name="unbanmember",
        usage="unbanmember <user_id>",
        description="Unbans the specified user from the server.",
    )
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def unbanmember(self, ctx: commands.Context, user_id: int):
        logger.info(f"Unbanning user with ID: {user_id}")
        user = await self.bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.send(f"{user.mention} has been unbanned.", ephemeral=True)
        logger.info(f"Unbanned user with ID: {user_id}")
    

async def setup(bot: commands.Bot):
    await bot.add_cog(Administration(bot))
