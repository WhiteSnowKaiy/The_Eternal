import discord
from discord import app_commands
from discord.ext import commands
import asyncio


class EventServerController(commands.Cog):
    """A cog to manage team-based events and server organization."""
    
    team: app_commands.Group = app_commands.Group(
        name="team", description="Manage teams and related resources"
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @team.command(
        name="create",
        description="Creates team categories, roles, and channels for an event."
    )
    @commands.has_role("Admin")
    async def create_teams(self, interaction: discord.Interaction, list_of_teams: str):
        """
        Creates categories, roles, and text/voice channels for each team in the provided list.
        Example: /createteams Red Team, Blue Team, Green Team
        """
        team_names = [team.strip() for team in list_of_teams.split(',')]
        created_categories = []

        await interaction.response.send_message(f"🚧 Creating categories for teams: {team_names}")

        for team in team_names:
            # Create category
            category = await interaction.guild.create_category(f"=== {team} ===")
            created_categories.append(category)

            # Deny default role access
            await category.set_permissions(interaction.guild.default_role, read_messages=False, connect=False)
            # Create team role and grant access
            role = await interaction.guild.create_role(name=f"{team}_role")
            await category.set_permissions(role, read_messages=True, connect=True)

            await interaction.followup.send(f"📁 Setting up channels for team: {team}")

            # Create text and voice channels
            await interaction.guild.create_text_channel(f"{team.lower().replace(' ', '_')}_chat", category=category)
            await asyncio.sleep(1)
            await interaction.guild.create_voice_channel(f"{team.lower().replace(' ', '_')}_voice", category=category)
            await asyncio.sleep(1)

            await interaction.followup.send(f"✅ Channels created for team: {team}")

    @team.command(
        name="remove",
        description="Removes a team: deletes its category, channels, and role."
    )
    @commands.has_role("Admin")
    async def remove_team(self, interaction: discord.Interaction, role: discord.Role):
        """
        Removes all members from a team role and deletes its associated category,
        text channel, and voice channel. The expected naming pattern:
          - Category: ===TeamName===
          - Text channel: teamname_general
          - Voice channel: teamname_voice
          - Role: TeamName_role
        """
        team_name = role.name.replace("_role", "")
        base_name = team_name.lower().replace(" ", "_")

        await interaction.response.send_message(f"🧹 Starting removal process for team **{team_name}**...")

        # Remove role from all members
        for member in role.members:
            try:
                await member.remove_roles(role, reason="Team removal initiated by admin")
                await interaction.followup.send(f"👢 Removed {member.display_name}'s {role.name} role.")
            except discord.Forbidden:
                await interaction.followup.send(f"⚠️ Couldn't remove role from {member.display_name} (permission issue).")

        # Delete associated category
        category_name = f"=== {team_name} ==="
        category = discord.utils.get(interaction.guild.categories, name=category_name)
        if category:
            await interaction.followup.send(f"🗂️ Deleting category `{category_name}`...")
            try:
                await category.delete()
                await interaction.followup.send(f"✅ Category `{category_name}` deleted.")
            except discord.Forbidden:
                await interaction.followup.send(f"⚠️ Missing permissions to delete category `{category_name}`.")
        else:
            await interaction.followup.send(f"⚠️ Category `{category_name}` not found.")
        # Delete associated text channel
        text_channel_name = f"{base_name}_chat"
        text_channel = discord.utils.get(interaction.guild.text_channels, name=text_channel_name)

        if text_channel:
            await interaction.followup.send(f"🗨️ Deleting text channel `{text_channel_name}`...")
            try:
                await text_channel.delete()
                await interaction.followup.send(f"✅ Text channel `{text_channel_name}` deleted.")
            except discord.Forbidden:
                await interaction.followup.send(f"⚠️ Missing permissions to delete `{text_channel_name}`.")
        else:
            await interaction.followup.send(f"⚠️ Text channel `{text_channel_name}` not found.")

        # Delete associated voice channel
        voice_channel_name = f"{base_name}_voice"
        voice_channel = discord.utils.get(interaction.guild.voice_channels, name=voice_channel_name)
        if voice_channel:
            await interaction.followup.send(f"🎤 Deleting voice channel `{voice_channel_name}`...")
            try:
                await voice_channel.delete()
                await interaction.followup.send(f"✅ Voice channel `{voice_channel_name}` deleted.")
            except discord.Forbidden:
                await interaction.followup.send(f"⚠️ Missing permissions to delete `{voice_channel_name}`.")
        else:
            await interaction.followup.send(f"⚠️ Voice channel `{voice_channel_name}` not found.")
        # Delete the team role itself
        try:
            await role.delete(reason="Team removed by admin")
            await interaction.followup.send(f"🧾 Role `{role.name}` deleted successfully.")
        except discord.Forbidden:
            await interaction.followup.send(f"⚠️ Missing permissions to delete role `{role.name}`.")

        await interaction.followup.send(f"✅ Team **{team_name}** has been fully removed.")

async def setup(bot: commands.Bot):
    await bot.add_cog(EventServerController(bot))
