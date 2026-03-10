import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import logging
from typing import List, Dict, Optional

logger: logging.Logger = logging.getLogger("Eternal.RSVP")


# =========================
# RSVP VIEW
# =========================
class RSVPView(discord.ui.View):
    def __init__(
        self,
        rsvp_responses: Dict[int, Dict[str, List[int]]],
        message_id: Optional[int],
        options: List[Dict],
        save_callback,
    ):
        super().__init__(timeout=None)
        self.rsvp_responses = rsvp_responses
        self.message_id = message_id
        self.options = options
        self.save_callback = save_callback
        self._add_dynamic_buttons()

    def _add_dynamic_buttons(self):
        self.clear_items()

        for opt in self.options:
            button = discord.ui.Button(
                label=opt["label"],
                style=opt["style"],
                custom_id=f"rsvp_{opt['key']}"
            )

            async def callback(interaction: discord.Interaction, key=opt["key"]):
                await self._handle_rsvp(interaction, key)

            button.callback = callback
            self.add_item(button)

    async def _handle_rsvp(self, interaction: discord.Interaction, response_type: str):
        user_id = interaction.user.id

        # Ensure message_id exists
        if self.message_id is None:
            if interaction.message and interaction.message.id:
                self.message_id = interaction.message.id
            else:
                await interaction.response.send_message(
                    "Error: Could not determine RSVP message.",
                    ephemeral=True
                )
                return

        # Ensure structure exists
        if self.message_id not in self.rsvp_responses:
            self.rsvp_responses[self.message_id] = {
                opt["key"]: [] for opt in self.options
            }

        responses = self.rsvp_responses[self.message_id]

        # Toggle RSVP
        if user_id in responses.get(response_type, []):
            responses[response_type].remove(user_id)
            msg = "You have been removed from this RSVP."
        else:
            for key in responses:
                if user_id in responses[key]:
                    responses[key].remove(user_id)
            responses[response_type].append(user_id)
            pretty = response_type.replace('_', ' ').title()
            msg = f"You responded: **{pretty}**"

        await interaction.response.send_message(msg, ephemeral=True)

        # Persist immediately
        self.save_callback()

        # Update embed
        await self._update_rsvp_message(interaction.channel, self.message_id)

    async def _update_rsvp_message(self, channel: discord.abc.GuildChannel, message_id: int):
        try:
            message = await channel.fetch_message(message_id)
        except Exception as e:
            logger.exception("Failed to fetch RSVP message: %s", e)
            return

        if not message.embeds:
            return

        old_embed = message.embeds[0]
        embed = discord.Embed.from_dict(old_embed.to_dict())
        embed.clear_fields()

        # Preserve non-RSVP fields
        rsvp_labels = [opt["label"] for opt in self.options]
        for field in old_embed.fields:
            if field.name not in rsvp_labels:
                embed.add_field(name=field.name, value=field.value, inline=field.inline)

        # Add RSVP fields
        guild = message.guild
        for opt in self.options:
            key = opt["key"]
            user_ids = self.rsvp_responses.get(message_id, {}).get(key, [])

            mentions = []
            for uid in user_ids:
                member = guild.get_member(uid)
                mentions.append(member.mention if member else f"<@{uid}>")

            value = "\n".join(mentions) or "\u200b"
            embed.add_field(name=opt["label"], value=value, inline=True)

        try:
            await message.edit(embed=embed)
        except Exception as e:
            logger.exception("Failed to edit RSVP message: %s", e)


# =========================
# COG
# =========================
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

        # message_id -> { key -> [user_id, ...] }
        self.rsvp_responses: Dict[int, Dict[str, List[int]]] = {}

        self._load_store()
        self.options = RSVP.DEFAULT_OPTIONS

    # -------------------------
    # Persistence
    # -------------------------
    def _load_store(self):
        try:
            if os.path.exists(self._store_path):
                with open(self._store_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.rsvp_responses = {
                        int(k): {rk: list(map(int, rv)) for rk, rv in v.items()}
                        for k, v in data.items()
                    }
        except Exception:
            logger.exception("Failed loading RSVP store")
            self.rsvp_responses = {}

    def _save_store(self):
        try:
            with open(self._store_path, 'w', encoding='utf-8') as f:
                json.dump(self.rsvp_responses, f, indent=2)
        except Exception:
            logger.exception("Failed saving RSVP store")

    # -------------------------
    # Lifecycle
    # -------------------------
    async def cog_load(self) -> None:
        for message_id in list(self.rsvp_responses.keys()):
            view = RSVPView(
                self.rsvp_responses,
                message_id,
                self.options,
                self._save_store
            )
            self.bot.add_view(view, message_id=message_id)

            # 🔥 Rebuild embeds on startup
            channel = self.bot.get_channel  # resolved lazily later

    async def cog_unload(self) -> None:
        self._save_store()

    # -------------------------
    # Commands
    # -------------------------
    @RSVP.command(name="create", description="Create RSVP event")
    @app_commands.describe(
        title='Event title',
        description='Event description',
        banner_url='Optional image url',
        timestamp='Unix timestamp (seconds)'
    )
    async def create(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        banner_url: Optional[str] = None,
        timestamp: Optional[int] = None
    ):
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blurple()
        )
        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url
        )

        if timestamp:
            embed.add_field(name="Event Time", value=f"<t:{timestamp}:F>", inline=False)

        if banner_url:
            embed.set_image(url=banner_url)

        embed.set_footer(text="Powered by Eternal Bot")

        view = RSVPView(
            self.rsvp_responses,
            None,
            self.options,
            self._save_store
        )

        await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()

        view.message_id = message.id
        self.bot.add_view(view, message_id=message.id)

        self.rsvp_responses[message.id] = {
            opt["key"]: [] for opt in self.options
        }
        self._save_store()


async def setup(bot: commands.Bot):
    await bot.add_cog(RSVP(bot))
