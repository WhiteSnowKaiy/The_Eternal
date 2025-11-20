import re
import requests
from typing import Tuple, List, Dict
import discord
from discord.ext import commands
import os
from ..config.transcript_config import createHeader
from logging import Logger, getLogger
from discord import app_commands


transcript_logger: Logger = getLogger("Eternal.Transcripts")

class Transcript(commands.Cog):    
    transcript: app_commands.Group = app_commands.Group(
        name="transcript", description="Manage transcript related commands"
    )
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.out_dir = os.path.join(os.path.dirname(__file__), 'out')            


    def remove_ansi_sequences(self, text: str) -> str:
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    
    def parse_emoji(self, emoji_id: str):
        return f"https://cdn.discordapp.com/emojis/{emoji_id}.webp?size=128&quality=lossless"


    def next_emoji(self,message: str, startIndex: int) -> Tuple[int, int]:
        """
        Returns:
            - start and end index of the nearest emoji ID
        Raises: 
            - IndexError if invalid tag.
        """
        if startIndex != 0:
            startIndex += 1
        emoji = message[startIndex:].split("<")[1].split(">")[0].split(":")[2]
        sIdx = message.index(emoji, startIndex)
        eIdx = sIdx + len(emoji)
        return (sIdx, eIdx)


    def next_emoji_map(self, message: str, startIndex: int) -> Tuple[str, str]:
        """
        Returns:
            - start and end index of the nearest emoji ID
        Raises:
            - IndexError if invalid tag.
        """
        if startIndex != 0:
            startIndex += 1
        emoji_list = message[startIndex:].split("<")[1].split(">")[0]
        emoji = emoji_list.split(":")[2]
        sIdx = message.index(emoji, startIndex)
        eIdx = sIdx + len(emoji)
        emojiId = message[sIdx:eIdx]
        original = "<:" + emoji_list.split(":")[1] + ":" + emojiId + ">"
        return (original, emojiId)


    def get_all_emoji_urls(self, msg: str) -> List[str]:
        msg = msg.replace(" ", "").replace("\r", "\n").replace("\n", "")

        emoji = []

        for i in range(0, len(msg)):
            try:
                idx = self.next_emoji(msg, i)
                emoji_id = msg[idx[0]:idx[1]]
                if emoji_id in emoji:
                    continue
                emoji.append(emoji_id)
            except IndexError:
                pass

        return emoji


    def get_emoji_id_to_url_map(self, msg: str) -> Dict[str, str]:
        msg = msg.replace(" ", "").replace("\r", "\n").replace("\n", "")

        emoji = {}

        for i in range(0, len(msg)):
            try:
                emoji_string, emoji_id = self.next_emoji_map(msg, i)
                if emoji_string in list(emoji.keys()):
                    continue
                emoji_url = self.parse_emoji(emoji_id)
                emoji[emoji_string] = emoji_url
            except IndexError:
                pass

        return emoji


    def url_map_to_html_map(self, url_map: Dict[str, str], width: int | str = 96, height: int | str = 96) -> Dict[str, str]:
        return {k: f'<img class="emoji" src="{v}" width="{width}" height="{height}" />' for k, v in url_map.items()}


    def download_all(self, emoji_urls: List[str], path: str):
        for e in emoji_urls:
            url = self.parse_emoji(e)
            res = requests.get(url)
            with open(f"{path}/{e}.webp", "wb") as f:
                f.write(res.content)


    def populate(self, message: str) -> str:
        id_to_url = self.get_emoji_id_to_url_map(message)

        id_to_img = self.url_map_to_html_map(id_to_url, 24, 24)

        for k, v in id_to_img.items():
            message = message.replace(k, v)

        return message
        
        
    def escape_html(self, text: str) -> str:
            """
            Keep code blocks as <pre>, escape mentions/markdown, preserve newlines,
            and inject custom emoji <img> tags.
            """
            
            def format_code_block(code: str) -> str:
                clean_code = self.remove_ansi_sequences(code)
                return f'<pre>{clean_code}</pre>'

            if not text:
                return ""

            parts = re.split(r'(```(?:[\s\S]*?)```)', text)
            out = []

            for part in parts:
                if part.startswith("```") and part.endswith("```"):
                    out.append(format_code_block(part[3:-3]))
                    continue

                # Normal text
                part = self.remove_ansi_sequences(part)
                part = discord.utils.escape_mentions(part)  # avoid pinging
                # Keep it simple: don't try to re-implement markdown; just preserve lines.
                part = part.replace("\r\n", "\n").replace("\r", "\n")
                part = self.populate(part)  # convert <:custom:123> to <img ...>
                part = part.replace("\n", "<br>")

                out.append(part)

            return "".join(out)


    def escape_attachments(self, attachments):
        """
        Returns a <div class="attachments">...</div> with block images/links.
        """
        if not attachments:
            return ""

        parts = []
        for a in attachments:
            url = discord.utils.escape_markdown(a.url)
            lower = url.lower()
            if lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".avif")):
                parts.append(f'<div class="attachment"><img src="{url}" alt="Attachment"></div>')
            else:
                parts.append(
                    f'<div class="attachment"><a href="{url}" target="_blank" rel="noopener">Download attachment</a></div>'
                )
        return f'<div class="attachments">{"".join(parts)}</div>'

    
    async def removeHTML(self, user: discord.User):
        # Get a list of HTML files in the 'out' directory
        html_files = [file for file in os.listdir(self.out_dir) if file.endswith('.html')]

        # Check if there are HTML files in the 'out' directory
        if not html_files:
            raise "Error: No HTML files found in 'out' directory." # type: ignore

        try:
            # Send each HTML file
            for html_file in html_files:
                html_file_path = os.path.join(self.out_dir, html_file)
                await user.send(file=discord.File(html_file_path))

            transcript_logger.info("Transcripts are being sent to %s", user.name)
        except discord.errors.Forbidden:
            transcript_logger.error("Unable to send files to the specified user. Make sure the user allows direct messages.")
            
        for file_name in html_files:
            try:
                os.remove(os.path.join(self.out_dir, file_name))
                transcript_logger.info("File %s removed successfully.", file_name)
            except FileNotFoundError:
                transcript_logger.error("File %s", file_name, "not found.")
            except Exception as e:
                transcript_logger.error("Error removing file %s", file_name, "%s",e)

    
    def _color_hex(self, color: discord.Color) -> str:
        return f'#{getattr(color, "value", 0):06x}'

                
    @transcript.command(
        name="channel",
        description="creates transcript for a channel",
    )
    async def transcriptchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        with open(os.path.join(self.out_dir, f"{channel.name}.html"), "w", encoding="utf-8") as file:
            # Write header
            file.write(await createHeader(channel.name))

            messages = []
            async for message in channel.history(limit=None):
                content = self.escape_html(message.content or "")
                attachments = self.escape_attachments(message.attachments)
                pfp_url = str(message.author.display_avatar.url)
                color_hex = self._color_hex(message.author.color)
                author_name = message.author.display_name
                messages.append((pfp_url, color_hex, author_name, content, attachments))
                
            
            # Write messages in reverse (oldest → newest)
            for pfp, color, author_name, content, attachments in reversed(messages):
                file.write(
                    f'''
                    <div class="message">
                    <img class="avatar" src="{pfp}" alt="{author_name} avatar">
                    <div class="content">
                        <div class="header">
                        <span class="username" style="color:{color}">{author_name}</span>
                        </div>
                        <div class="message-body">{content}</div>
                        {attachments}
                    </div>
                    </div>
                    '''
                )

            # Close HTML
            file.write("</main></body></html>")

        await self.removeHTML(ctx.author)  # type: ignore

    @transcript.command(
        name="thread", 
        description="creates transcript for a thread",
    ) 
    async def transcriptthread(self, interaction: discord.Interaction, thread: discord.Thread):
        with open(os.path.join(self.out_dir, f"{thread.name}.html"), "w", encoding="utf-8") as file:
            file.write(await createHeader(thread.name))
            file.write(f"<div>Thread ID: {thread.id}, Name: {thread.name}</div>")

            messages = []
            async for message in thread.history(limit=None):
                content = self.escape_html(message.content or "")
                attachments = self.escape_attachments(message.attachments)
                pfp_url = str(message.author.display_avatar.url)
                color_hex = self._color_hex(message.author.color)
                author_name = message.author.display_name
                messages.append((pfp_url, color_hex, author_name, content, attachments))

            for pfp, color, author_name, content, attachments in reversed(messages):
                file.write(
                    f'''
    <div class="message">
    <img class="avatar" src="{pfp}" alt="{author_name} avatar">
    <div class="content">
        <div class="header">
        <span class="username" style="color:{color}">{author_name}</span>
        </div>
        <div class="message-body">{content}</div>
        {attachments}
    </div>
    </div>
    '''
                )

            file.write("</main></body></html>")

        await self.removeHTML(ctx.author)  # type: ignore
        
            
    @transcript.command(
        name="threads", 
        description="creates transcripts for all threads in a channel",
    )
    async def transcriptthreads(self, interaction: discord.Interaction, channel: discord.TextChannel):
        threads = channel.archived_threads()

        async for thread in threads:
            with open(os.path.join(self.out_dir, f"{thread.name}.html"), "w", encoding="utf-8") as file:
                file.write(await createHeader(thread.name))
                file.write(f"<div>Thread ID: {thread.id}, Name: {thread.name}</div>")

                messages = []
                async for message in thread.history(limit=None):
                    content = self.escape_html(message.content or "")
                    attachments = self.escape_attachments(message.attachments)
                    pfp_url = str(message.author.display_avatar.url)
                    color_hex = self._color_hex(message.author.color)
                    author_name = message.author.display_name
                    messages.append((pfp_url, color_hex, author_name, content, attachments))

                for pfp, color, author_name, content, attachments in reversed(messages):
                    file.write(
                        f'''
    <div class="message">
    <img class="avatar" src="{pfp}" alt="{author_name} avatar">
    <div class="content">
        <div class="header">
        <span class="username" style="color:{color}">{author_name}</span>
        </div>
        <div class="message-body">{content}</div>
        {attachments}
    </div>
    </div>
    '''
                    )

                file.write("</main></body></html>")

        await self.removeHTML(ctx.author)  # type: ignore
        
async def setup(bot: commands.Bot):
    await bot.add_cog(Transcript(bot))