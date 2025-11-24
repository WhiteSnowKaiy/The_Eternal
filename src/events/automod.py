import re
from string import ascii_letters as STANDARD_CHARACTERS
from typing import List

import discord
from discord.ext import commands

from ..config.automod_config import BANNED_WORDS
from ..database import get_session
from ..database.models.warning import WarningModel
from .. database.models.automod_words import AutomodWordsModel

from ..config.discord_config import DEFAULT_ROLE, GUILD, WELCOME_CHANNEL


def remove_non_standard_characters(s: str) -> str:
    return re.sub(f"[^{re.escape(STANDARD_CHARACTERS)}]", "", s)


def get_banned_words_from_db() -> List[str]:
    banned_words: List[str] = []
    with get_session() as session:
        words = session.query(AutomodWordsModel).all()
        banned_words = [word.word for word in words]
    return banned_words


class AutoModeration(commands.Cog):
    banned_words: List[str]

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.banned_words = [remove_non_standard_characters(i) for i in BANNED_WORDS]


    # Listeners 
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        author: discord.Member = message.author # type: ignore
        content: str = message.content
        channel: discord.TextChannel = message.channel # type: ignore
        if self.is_string_blacklisted(content.lower()):
            await message.delete()
            # Warn the sender
            warning = WarningModel(
                author, self.bot.user, "Sending inappropriate messages (Automod)" # type: ignore
            )
            with get_session() as session:
                session.add(warning)
                session.commit()
            await channel.send(
                f"Don't send inappropriate messages, {author.mention}", delete_after=5.0
            )


    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.moderate_nickname(member)
        await member.add_roles(self._guild().get_role(DEFAULT_ROLE))
        await self._guild().get_channel(WELCOME_CHANNEL).send(f"Welcome to the server {member.name}")
    

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.nick == after.nick:
            return
        await self.moderate_nickname(after)


    # Methods - Moderation
    async def moderate_nickname(self, member: discord.Member):
        """Checks whether the member's nickname contains a banned word. If it does, renames the user.

        Args:
            member (discord.Member): The member to check
        """
        if any(bw in remove_non_standard_characters(member.display_name.lower()) for bw in self.banned_words):
            await member.edit(nick="Moderated Nickname")
            # Warn the member
            warning = WarningModel(
                member, self.bot.user, "Inappropriate nickname or username (Automod)" # type: ignore
            )
            with get_session() as session:
                session.add(warning)
                session.commit()


    def is_string_blacklisted(self, s: str) -> bool:
        """Checks whether the given string contains any banned words."""

        banned_from_db = get_banned_words_from_db()

        # Clean banned words from config + DB
        # Use the correct instance variable
        self.banned_words = [remove_non_standard_characters(i) for i in BANNED_WORDS]
        self.banned_words.extend(remove_non_standard_characters(i) for i in banned_from_db)

        # Clean the input string
        s = remove_non_standard_characters(s)

        # Build safe regex
        pattern = "|".join(re.escape(word) for word in self.banned_words if word)

        return bool(re.search(pattern, s, re.IGNORECASE))


    # Methods - Helper
    def _guild(self):
        return self.bot.get_guild(GUILD)

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoModeration(bot))
