import logging
from typing import List

import discord
from discord.ext import commands
from sqlalchemy import desc, func

from ..database.models.automod_words import AutomodWordsModel

from ..database import get_session
from ..database.models.warning import WarningModel

from discord import app_commands

logger: logging.Logger = logging.getLogger("Eternal.Administration")


class Administration(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    warning: app_commands.Group = app_commands.Group(
        name="warning", description="Manage user warnings and moderation"
    )
    
    ban: app_commands.Group = app_commands.Group(
        name="ban", description="Manage user bans and moderation"
    )
    
    moderation: app_commands.Group = app_commands.Group(
        name="moderation", description="Manage banned words and moderation settings"
    )
    
    
    @warning.command(
        name="warnings",
        description="Shows all warnings for the specified user",
    )
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
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
        await interaction.response.send_message(
            f"{member.mention} has {warning_count} total warnings{' (showing at most 50 latest)' if warning_count > 50 else ''}: \n- "
            + "\n- ".join(warnings_text),
            ephemeral=True,
        )
        logger.info(f"Displayed warnings for member {member} (ID: {member.id})")
        
        
    @warning.command(
        name="clear",
        description="Clears all warnings for the specified user",
    )
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def clearwarnings(self, interaction: discord.Interaction, member: discord.Member): 
        logger.info(f"Clearing warnings for member {member} (ID: {member.id})")
        with get_session() as session:
            deleted_count = (
                session.query(WarningModel)
                .filter_by(memberId=member.id)
                .delete(synchronize_session=False)
            )
            session.commit()
        await interaction.response.send_message(
            f"Cleared {deleted_count} warnings for {member.mention}.",
            ephemeral=True,
        )
        logger.info(f"Cleared warnings for member {member} (ID: {member.id})")
    
    
    @ban.command(
        name="member",
        description="Bans the specified member from the server.",
    )
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def banmember(self, interaction: discord.Interaction, member: discord.Member, *, reason: str
        = "No reason provided"):
        logger.info(f"Banning member {member} (ID: {member.id}) for reason: {reason}")
        await member.ban(reason=reason)
        await interaction.response.send_message(f"{member.mention} has been banned. Reason: {reason}", ephemeral=True)
        logger.info(f"Banned member {member} (ID: {member.id})")
    
    
    @ban.command(
        name="remove",
        description="Unbans the specified user from the server.",
    )
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def unbanmember(self, interaction: discord.Interaction, user_id: int):
        logger.info(f"Unbanning user with ID: {user_id}")
        user = await self.bot.fetch_user(user_id)
        await interaction.guild.unban(user)
        await interaction.response.send_message(f"{user.mention} has been unbanned.", ephemeral=True)
        logger.info(f"Unbanned user with ID: {user_id}")
        
        
    @ban.command(
        name="list",
        description="Lists all banned users in the server.",
    )
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def listbans(self, interaction: discord.Interaction):
        logger.info("Fetching list of banned users...")
        bans = await interaction.guild.bans()
        if not bans:
            await interaction.response.send_message("There are no banned users in this server.", ephemeral=True)
            logger.info("No banned users found.")
            return

        ban_list = "\n".join([f"{ban.user} (ID: {ban.user.id}) - Reason: {ban.reason or 'No reason provided'}" for ban in bans])
        await interaction.response.send_message(f"Banned users:\n{ban_list}", ephemeral=True)
        logger.info("Displayed list of banned users.")
        
        
    @moderation.command(
        name="add",
        description="Adds a word to the banned words list.",
    )
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def addbannedword(self, interaction: discord.Interaction, word: str):
        logger.info(f"Adding banned word: {word}")
        with get_session() as session:
            new_word = AutomodWordsModel(word)
            session.add(new_word)
            session.commit()
        await interaction.response.send_message(f"The word '{word}' has been added to the banned words list.", ephemeral=True)
        logger.info(f"Added banned word: {word}")
        
        
    @moderation.command(
        name="remove",
        description="Removes a word from the banned words list.",
    )
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def removebannedword(self, interaction: discord.Interaction, word: str):
        logger.info(f"Removing banned word: {word}")
        with get_session() as session:
            deleted_count = (
                session.query(AutomodWordsModel)
                .filter_by(word=word)
                .delete(synchronize_session=False)
            )
            session.commit()
        if deleted_count > 0:
            await interaction.response.send_message(f"The word '{word}' has been removed from the banned words list.", ephemeral=True)
            logger.info(f"Removed banned word: {word}")
        else:
            await interaction.response.send_message(f"The word '{word}' was not found in the banned words list.", ephemeral=True)
            logger.info(f"Banned word not found: {word}")
    
    
    @moderation.command(
        name="purge",
        description="Purge x ammount of messages from a channel.",
    )
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def purge(self, interaction: discord.Interaction, amount: int):
        logger.info(f"Purging {amount} messages from channel {interaction.channel} (ID: {interaction.channel.id})")
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.response.send_message(f"Purged {len(deleted)} messages.", ephemeral=True)
        logger.info(f"Purged {len(deleted)} messages from channel {interaction.channel} (ID: {interaction.channel.id})")
        
    

async def setup(bot: commands.Bot):
    await bot.add_cog(Administration(bot))
