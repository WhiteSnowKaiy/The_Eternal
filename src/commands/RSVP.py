import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import logging
from typing import List, Dict, Optional

logger: logging.Logger = logging.getLogger("Eternal.RSVP")


class RSVPView(discord.ui.View):
    """A dynamic, (optionally) persistent view for RSVP buttons.

    Notes:
    - You can construct it without a message_id and attach it when sending.
    - For persistence after restarts, the cog registers the view with bot.add_view(view, message_id=...)
    """

    def __init__(self, rsvp_responses: Dict[int, Dict[str, List[str]]], message_id: Optional[int], options: List[Dict]):
        # persistent if timeout is None
        super().__init__(timeout=None)
        self.rsvp_responses = rsvp_responses
        self.message_id = message_id
        self.options = options
        self._add_dynamic_buttons()


    def _add_dynamic_buttons(self):
        self.clear_items()

        for opt in self.options:
            # Every button *must* have a custom_id for persistence
            button = discord.ui.Button(
                label=opt["label"],
                style=opt["style"],
                custom_id=f"rsvp_{opt['key']}"
            )

            def make_callback(key: str):
                async def callback(interaction: discord.Interaction):
                    await self._handle_rsvp(interaction, key)
                return callback

            button.callback = make_callback(opt["key"])
            self.add_item(button)


    async def _handle_rsvp(self, interaction: discord.Interaction, response_type: str):
        # Use mention strings to show in embed; you could also store user IDs instead.
        user_mention = interaction.user.mention

        # Ensure structure exists
        if self.message_id is None:
            # Try to fall back to the message on the interaction (non-persistent case)
            try:
                msg = interaction.message
                if msg and getattr(msg, 'id', None):
                    self.message_id = msg.id
            except Exception:
                pass

        if self.message_id not in self.rsvp_responses:
            self.rsvp_responses[self.message_id] = {opt["key"]: [] for opt in self.options}

        responses = self.rsvp_responses[self.message_id]

        # Toggle RSVP
        if user_mention in responses.get(response_type, []):
            responses[response_type].remove(user_mention)
            await interaction.response.send_message("You have been removed from this RSVP.", ephemeral=True)
        else:
            # Remove user from other response lists
            for key in responses:
                if user_mention in responses[key]:
                    responses[key].remove(user_mention)
            responses[response_type].append(user_mention)
            pretty = response_type.replace('_', ' ').title()
            await interaction.response.send_message(f"You responded: **{pretty}**", ephemeral=True)

        # Update the message embed (fetch the message to be robust)
        await self._update_rsvp_message(interaction.channel, self.message_id)

    async def _update_rsvp_message(self, channel: discord.abc.GuildChannel, message_id: int):
        logger.debug("Updating RSVP message...")
        try:
            message = await channel.fetch_message(message_id)
        except Exception as e:
            logger.exception("Failed to fetch RSVP message: %s", e)
            return

        if not message.embeds:
            logger.warning("RSVP message has no embeds; skipping update")
            return

        embed = message.embeds[0]

        # Defensive copy of old non-RSVP fields
        preserved = []
        rsvp_labels = [opt["label"] for opt in self.options]

        for field in embed.fields:
            if field.name not in rsvp_labels:
                preserved.append((field.name, field.value, field.inline))

        # Build a fresh embed preserving title/description/image/author/footer/color
        new_embed = discord.Embed(
            title=embed.title or "",
            description=embed.description or "",
            color=embed.color or discord.Color.blurple()
        )
        try:
            if embed.author:
                new_embed.set_author(name=embed.author.name, icon_url=getattr(embed.author, 'icon_url', None) or getattr(embed.author, 'icon_url', None))
        except Exception:
            pass
        if embed.image:
            new_embed.set_image(url=embed.image.url)
        if embed.footer:
            new_embed.set_footer(text=embed.footer.text)
        
        # Re-add preserved fields
        for name, value, inline in preserved:
            if name:
                new_embed.add_field(name=name, value=value, inline=inline)

        # Add RSVP lists
        for opt in self.options:
            key = opt["key"]
            responders = "\n".join(self.rsvp_responses.get(message_id, {}).get(key, [])) or "\u200b"
            new_embed.add_field(name=opt["label"], value=responders, inline=True)

        try:
            await message.edit(embed=new_embed)
            logger.debug("RSVP embed updated.")
        except Exception as e:
            logger.exception("Failed to edit RSVP message: %s", e)


class RSVP(commands.Cog):
    RSVP: app_commands.Group = app_commands.Group(
        name="rsvp", description="Create and manage RSVP events"
    )

    DEFAULT_OPTIONS = [
        {"label": "Going", "style": discord.ButtonStyle.green, "key": "going"},
        {"label": "Maybe", "style": discord.ButtonStyle.blurple, "key": "maybe"},
        {"label": "Not Going", "style": discord.ButtonStyle.red, "key": "not_going"},
    ]

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.out_dir = os.path.join(os.path.dirname(__file__), 'out')
        os.makedirs(self.out_dir, exist_ok=True)
        self._store_path = os.path.join(self.out_dir, 'rsvp_responses.json')

        # message_id -> { key -> [mention, ...] }
        self.rsvp_responses: Dict[int, Dict[str, List[str]]] = {}

        # load persisted responses if available
        self._load_store()

        # keep the options on the cog so cog_load can recreate views
        self.options = RSVP.DEFAULT_OPTIONS

    def _load_store(self):
        try:
            if os.path.exists(self._store_path):
                with open(self._store_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # keys saved as strings — convert back to int
                    self.rsvp_responses = {int(k): v for k, v in data.items()}
                    logger.debug("Loaded RSVP store with %d messages", len(self.rsvp_responses))
        except Exception:
            logger.exception("Failed loading RSVP store")
            self.rsvp_responses = {}

    def _save_store(self):
        try:
            with open(self._store_path, 'w', encoding='utf-8') as f:
                json.dump({str(k): v for k, v in self.rsvp_responses.items()}, f, ensure_ascii=False, indent=2)
        except Exception:
            logger.exception("Failed saving RSVP store")

    async def cog_load(self) -> None:
        """Register persistent views for any known message IDs so buttons survive restarts."""
        # Re-create and register views for persisted RS vps
        for message_id in list(self.rsvp_responses.keys()):
            view = RSVPView(self.rsvp_responses, message_id, self.options)
            try:
                # Register the view with discord.py to listen for component interactions
                self.bot.add_view(view, message_id=message_id)
                logger.debug("Registered persistent RSVP view for message %s", message_id)
            except Exception:
                logger.exception("Failed to register persistent view for %s", message_id)

    async def cog_unload(self) -> None:
        # Save current state
        self._save_store()

    @RSVP.command(
        name="create",
        description="Create a universal RSVP with custom options.",
    )
    @app_commands.describe(title='Event title', description='Event description', banner_url='Optional image url', timestamp='Unix timestamp (seconds)')
    async def create(self, interaction: discord.Interaction, title: str, description: str, banner_url: Optional[str] = None, timestamp: Optional[int] = None):
        logger.debug("Creating universal RSVP")

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blurple()
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        if timestamp:
            embed.add_field(name="Event Time", value=f"<t:{timestamp}:F>", inline=False)
        if banner_url:
            embed.set_image(url=banner_url)
        embed.set_footer(text="Powered by Eternal Bot")

        # Use options from cog
        options = self.options

        # Create a view WITHOUT message_id; we'll attach it to the sent message, then register it
        view = RSVPView(self.rsvp_responses, None, options)

        # Send the message as the *interaction response* so the user sees success immediately
        await interaction.response.send_message(embed=embed, view=view)

        # Retrieve the created message so we can store the message ID and register the persistent view
        try:
            message = await interaction.original_response()
        except Exception:
            # Fallback: attempt to fetch the last message in the channel (not ideal)
            # Prefer the `original_response()` path above
            channel = interaction.channel
            message = None
            try:
                async for msg in channel.history(limit=5):
                    if msg.author.id == self.bot.user.id and msg.embeds and msg.embeds[0].title == title:
                        message = msg
                        break
            except Exception:
                logger.exception("Couldn't find the sent message for RSVP creation")

        if not message:
            # We couldn't determine the message ID — inform the command user
            logger.error("Failed to locate the RSVP message after sending")
            return

        # Set view message_id and register to persist
        view.message_id = message.id
        try:
            self.bot.add_view(view, message_id=message.id)
        except Exception:
            logger.exception("Failed to register view after create")

        # Initialize the response store for this message and save
        self.rsvp_responses[message.id] = {opt["key"]: [] for opt in options}
        self._save_store()

        logger.debug("RSVP created successfully for message %s.", message.id)


async def setup(bot: commands.Bot):
    await bot.add_cog(RSVP(bot))
