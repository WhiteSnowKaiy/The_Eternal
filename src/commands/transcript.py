import re
import requests
from typing import Tuple, List, Dict
import discord
from discord.ext import commands
import os
from ..config.transcript_config import createHeader
from logging import Logger, getLogger

transcript_logger: Logger = getLogger("Eternal.Transcripts")

class Transcripts(commands.Cog):
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
        return {k: f"<img src=\"{v}\" width=\"{width}\" height=\"{height}\" />" for k, v in url_map.items()}

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
        Escapes markdown, mentions, and emoji, and formats code blocks properly while removing ANSI sequences.
        """
        def format_code_block(code: str) -> str:
            # Clean ANSI sequences and preserve newlines, wrap in <pre>
            clean_code = self.remove_ansi_sequences(code)
            return f'<pre style="background-color:#2f3136;color:#f8f8f2;padding:10px;border-radius:5px;overflow-x:auto;">{clean_code}</pre>'

        # Split around triple backticks
        parts = re.split(r'(```(?:[\s\S]*?)```)', text)

        result = ""
        for part in parts:
            if part.startswith("```") and part.endswith("```"):
                # It's a code block
                code = part[3:-3]  # Strip the backticks
                result += format_code_block(code)
            else:
                # It's normal text — escape markdown and mentions
                part = self.remove_ansi_sequences(part)
                part = discord.utils.escape_markdown(discord.utils.escape_mentions(part))

                # Replace some markdown manually
                part = part.replace('__', '<br>')
                part = part.replace('**', '<strong>').replace('**', '</strong>')
                part = part.replace(r'\*\*', '<strong>').replace(r'\*\*', '</strong>')
                part = part.replace(r'\_\_', '')
                part = part.replace(r'\> ', '<br>')
                part = part.replace('```', '')

                # Replace emojis
                part = self.populate(part)

                result += part

        return result




    def escape_attachments(self, attachments):
        """
        Escapes the URLs of attachments for embedding in Discord messages.

        Parameters:
            - attachments (list): A list of attachments, where each attachment is an object with a 'url' attribute.

        Returns:
            str: A string containing HTML img tags for each attachment, with escaped URLs and styling.
                If no attachments are provided, an empty string is returned.
        """
        if not attachments:
            return ""

        attachment_list = [
            f'<img src="{discord.utils.escape_markdown(attachment.url)}" style="max-width: 800px; max-height: 600px; margin: 5px" alt="Attachment">'
            for attachment in attachments
        ]
        return " ".join(attachment_list)
    
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


    @commands.hybrid_command(
        name="transcriptchannel", 
        usage="/transcriptchannel <channel name>", 
        description="creates transcript for a channel",
    )
    async def transcriptchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """
        Creates transcript for a given channel.

        Args:
            ctx (commands.Context): The context of the command.
            channel (discord.TextChannel): The channel for which to create transcripts.

        Returns:
            None

        Examples:
            # Create transcripts for a channel
            /transcriptChannel #general
        """
        with open(os.path.join(self.out_dir, f"{channel.name}.html"), "w", encoding="utf-8") as file:
            file.write(
                await createHeader(channel.name)
            )
            messages = []
            async for message in channel.history(limit=None):
                
                content = self.escape_html(message.content)
                attachments = self.escape_attachments(message.attachments)
                
                pfp = message.author.display_avatar
                color = message.author.color
                messages.append((pfp, color, message.author.name, content, attachments))
                    
            # Write messages to HTML file in reverse order
            for msg in reversed(messages):
                pfp, color, author_name, content, attachments = msg
                # Add a container div and use CSS to center-align text relative to the image
                file.write('<div style="display: flex; align-items: center;">')
                file.write(f'<img src="{pfp}" style="max-width: 40px; max-height: 40px; border-radius: 50%;">')
                file.write(f'<div style="margin-left: 10px;">')
                file.write(f'<strong><a style="color: {color}">{author_name}</a>:</strong> {content}')
                file.write(f'{attachments}')
                file.write('</div></div>')
                    
        await self.removeHTML(ctx.author) # type: ignore

    
    
    @commands.hybrid_command(
        name="transcriptthread", 
        usage="/transcriptthread <channel name>", 
        description="creates transcript for a channel",
    ) 
    async def transcriptthread(self, ctx: commands.Context, thread: discord.Thread):
        """
        Creates transcript for a given channel.

        Args:
            ctx (commands.Context): The context of the command.
            channel (discord.TextChannel): The channel for which to create transcripts.

        Returns:
            None

        Examples:
            # Create transcripts for a channel
            /transcriptChannel #general
        """
        with open(os.path.join(self.out_dir, f"{thread.name}.html"), "w", encoding="utf-8") as file:
            # Creating head tag
            file.write(
                await createHeader(thread.name)
            )
            # Thread ID and Name
            file.write(f"Thread ID: {thread.id}, Name: {thread.name}")
            messages = []
            async for message in thread.history(limit=None):
                content = self.escape_html(message.content)
                attachments = self.escape_attachments(message.attachments)
                pfp = message.author.display_avatar
                color = message.author.color
                messages.append((pfp, color, message.author.name, content, attachments))

            # Write messages to HTML file in reverse order
            for msg in reversed(messages):
                pfp, color, author_name, content, attachments = msg
                file.write(f'<div><img src="{pfp}" style="max-width: 40px; max-height: 40px; border-radius: 50%;"> <strong><a style="color: {color}">{author_name}</a>:</strong> {content}</div>')
                if attachments:
                    file.write(f'<div>{attachments}</div>')

        await self.removeHTML(ctx.author) # type: ignore
        
        
    @commands.hybrid_command(
        name="transcriptthreads", 
        usage="/transcriptthreads <channel name>", 
        description="creates transcripts for all threads in a channel",
    )
    async def transcriptthreads(self, ctx: commands.Context, channel: discord.TextChannel):
        """
        Creates transcripts for a given channel.

        Args:
            ctx (commands.Context): The context of the command.
            channel (discord.TextChannel): The channel for which to create transcripts.

        Returns:
            None

        Examples:
            # Create transcripts for a channel
            /transcriptChannel #general
        """
        threads = channel.archived_threads()

        async for thread in threads:
            with open(os.path.join(self.out_dir, f"{thread.name}.html"), "w", encoding="utf-8") as file:
                # Creating head tag
                file.write(await createHeader(thread.name))
                messages = []
                # Thread ID and Name
                file.write(f"Thread ID: {thread.id}, Name: {thread.name}")
                async for message in thread.history(limit=None):
                    content = self.escape_html(message.content)
                    attachments = self.escape_attachments(message.attachments)
                    pfp = message.author.display_avatar
                    color = message.author.color
                    messages.append((pfp, color, message.author.name, content, attachments))

                # Write messages to HTML file in reverse order
                for msg in reversed(messages):
                    pfp, color, author_name, content, attachments = msg
                    file.write(
                            f'''
                                <div>
                                    <img src="{pfp}" style="max-width: 40px; max-height: 40px; border-radius: 50%;"> 
                                    <strong>
                                        <a style="color: {color}">
                                            {author_name}
                                        </a>:
                                    </strong> 
                                    {content}
                                </div>
                                '''
                            )
                    if attachments:
                        file.write(f'<div>{attachments}</div>')

        await self.removeHTML(ctx.author) # type: ignore
        
async def setup(bot: commands.Bot):
    await bot.add_cog(Transcripts(bot))