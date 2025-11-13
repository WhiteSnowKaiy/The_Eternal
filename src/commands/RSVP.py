import discord
from discord.ext import commands
import os
import logging

logger: logging.Logger = logging.getLogger("Universal.RSVP")

class RSVPView(discord.ui.View):
    def __init__(self, rsvp_responses, message_id, options):
        super().__init__(timeout=None)
        self.rsvp_responses = rsvp_responses
        self.message_id = message_id
        self.options = options  # list of dicts: [{'label': str, 'style': discord.ButtonStyle, 'key': str}]
        self._add_dynamic_buttons()

    def _add_dynamic_buttons(self):
        """Create buttons dynamically from the provided options."""
        for opt in self.options:
            button = discord.ui.Button(label=opt["label"], style=opt["style"])
            async def callback(interaction: discord.Interaction, key=opt["key"]):
                await self._handle_rsvp(interaction, key)
            button.callback = callback
            self.add_item(button)

    async def _handle_rsvp(self, interaction: discord.Interaction, response_type: str):
        user_mention = interaction.user.mention
        
        if self.message_id not in self.rsvp_responses:
            self.rsvp_responses[self.message_id] = {opt["key"]: [] for opt in self.options}

        responses = self.rsvp_responses[self.message_id]

        # Toggle RSVP
        if user_mention in responses[response_type]:
            responses[response_type].remove(user_mention)
            await interaction.response.send_message("You have been removed from this RSVP.", ephemeral=True)
        else:
            # Remove user from other response lists
            for key in responses:
                if user_mention in responses[key]:
                    responses[key].remove(user_mention)
            responses[response_type].append(user_mention)
            await interaction.response.send_message(f"You responded: **{response_type.replace('_', ' ').title()}**", ephemeral=True)

        await self._update_rsvp_message(interaction.message)

    async def _update_rsvp_message(self, message: discord.Message):
        logger.debug("Updating RSVP message...")
        embed = message.embeds[0]
        fields = {field.name: field.value for field in embed.fields}

        embed.clear_fields()
        embed.add_field(
            name="",
            value="**Please read the invite details and respond using the buttons below!**",
            inline=False
        )

        # Preserve static fields
        for name, value in fields.items():
            if name not in [opt["label"] for opt in self.options]:
                embed.add_field(name=name, value=value, inline=False)

        # Add RSVP lists
        for opt in self.options:
            key = opt["key"]
            responders = "\n".join(self.rsvp_responses[self.message_id][key]) or "\u200b"
            embed.add_field(name=opt["label"], value=responders, inline=True)

        await message.edit(embed=embed)
        logger.debug("RSVP embed updated.")


class RSVP(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.out_dir = os.path.join(os.path.dirname(__file__), 'out')
        self.rsvp_responses = {}

    @commands.hybrid_command(
        name="creatersvp",
        usage="/creatersvp <title> <description> <banner_url> <timestamp>",
        description="Create a universal RSVP with custom options.",
    )
    async def creatersvp(self, ctx: commands.Context, title: str, description: str, banner_url: str, timestamp: int):
        logger.debug("Creating universal RSVP")
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blurple()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.add_field(name="Event Time", value=f"<t:{timestamp}:F>")
        embed.set_image(url=banner_url)
        embed.set_footer(text="Powered by your friendly bot")

        # Define your RSVP options (easily modifiable)
        options = [
            {"label": "Going", "style": discord.ButtonStyle.green, "key": "going"},
            {"label": "Maybe", "style": discord.ButtonStyle.blurple, "key": "maybe"},
            {"label": "Not Going", "style": discord.ButtonStyle.red, "key": "not_going"}
        ]

        message = await ctx.send(embed=embed)
        view = RSVPView(self.rsvp_responses, message.id, options)
        await message.edit(view=view)

        self.rsvp_responses[message.id] = {opt["key"]: [] for opt in options}
        logger.debug("RSVP created successfully.")


async def setup(bot: commands.Bot):
    await bot.add_cog(RSVP(bot))
