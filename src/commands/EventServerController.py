import discord
from discord import app_commands
from discord.ext import commands
import asyncio


class EventServerController(commands.Cog):
    """A cog to manage team-based events and server organization."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(
        name="createteams",
        description="Creates team categories, roles, and channels for an event."
    )
    @commands.has_role("Admin")
    async def create_teams(self, ctx: commands.Context, list_of_teams: str):
        """
        Creates categories, roles, and text/voice channels for each team in the provided list.
        Example: /createteams Red Team, Blue Team, Green Team
        """
        team_names = [team.strip() for team in list_of_teams.split(',')]
        created_categories = []

        await ctx.send(f"🚧 Creating categories for teams: {team_names}")

        for team in team_names:
            # Create category
            category = await ctx.guild.create_category(f"=== {team} ===")
            created_categories.append(category)

            # Deny default role access
            await category.set_permissions(ctx.guild.default_role, read_messages=False, connect=False)

            # Create team role and grant access
            role = await ctx.guild.create_role(name=f"{team}_role")
            await category.set_permissions(role, read_messages=True, connect=True)

            await ctx.send(f"📁 Setting up channels for team: {team}")

            # Create text and voice channels
            await ctx.guild.create_text_channel(f"{team.lower().replace(' ', '_')}_chat", category=category)
            await asyncio.sleep(1)
            await ctx.guild.create_voice_channel(f"{team.lower().replace(' ', '_')}_voice", category=category)
            await asyncio.sleep(1)

            await ctx.send(f"✅ Channels created for team: {team}")


    @commands.hybrid_command(
        name="removeteam",
        description="Removes a team: deletes its category, channels, and role."
    )
    @commands.has_role("Admin")
    async def remove_team(self, ctx: commands.Context, role: discord.Role):
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

        await ctx.send(f"🧹 Starting removal process for team **{team_name}**...")

        # Remove role from all members
        for member in role.members:
            try:
                await member.remove_roles(role, reason="Team removal initiated by admin")
                await ctx.send(f"👢 Removed {member.display_name}'s {role.name} role.")
            except discord.Forbidden:
                await ctx.send(f"⚠️ Couldn't remove role from {member.display_name} (permission issue).")

        # Delete associated category
        category_name = f"=== {team_name} ==="
        category = discord.utils.get(ctx.guild.categories, name=category_name)

        if category:
            await ctx.send(f"🗂️ Deleting category `{category_name}`...")
            try:
                await category.delete()
                await ctx.send(f"✅ Category `{category_name}` deleted.")
            except discord.Forbidden:
                await ctx.send(f"⚠️ Missing permissions to delete category `{category_name}`.")
        else:
            await ctx.send(f"⚠️ Category `{category_name}` not found.")

        # Delete associated text channel
        text_channel_name = f"{base_name}_chat"
        text_channel = discord.utils.get(ctx.guild.text_channels, name=text_channel_name)

        if text_channel:
            await ctx.send(f"🗨️ Deleting text channel `{text_channel_name}`...")
            try:
                await text_channel.delete()
                await ctx.send(f"✅ Text channel `{text_channel_name}` deleted.")
            except discord.Forbidden:
                await ctx.send(f"⚠️ Missing permissions to delete `{text_channel_name}`.")
        else:
            await ctx.send(f"⚠️ Text channel `{text_channel_name}` not found.")

        # Delete associated voice channel
        voice_channel_name = f"{base_name}_voice"
        voice_channel = discord.utils.get(ctx.guild.voice_channels, name=voice_channel_name)

        if voice_channel:
            await ctx.send(f"🎤 Deleting voice channel `{voice_channel_name}`...")
            try:
                await voice_channel.delete()
                await ctx.send(f"✅ Voice channel `{voice_channel_name}` deleted.")
            except discord.Forbidden:
                await ctx.send(f"⚠️ Missing permissions to delete `{voice_channel_name}`.")
        else:
            await ctx.send(f"⚠️ Voice channel `{voice_channel_name}` not found.")

        # Delete the team role itself
        try:
            await role.delete(reason="Team removed by admin")
            await ctx.send(f"🧾 Role `{role.name}` deleted successfully.")
        except discord.Forbidden:
            await ctx.send(f"⚠️ Missing permissions to delete role `{role.name}`.")

        await ctx.send(f"✅ Team **{team_name}** has been fully removed.")



    @commands.hybrid_command(
        name="cleanup",
        description="Performs a full cleanup of the event server (use with caution!)."
    )
    @commands.is_owner()
    async def cleanup_server(self, ctx: commands.Context):
        """Removes all channels, categories, roles, and members (owner only)."""

        await ctx.send("⚠️ Starting full server cleanup...")

        # Kick all members (except owner)
        members = [m async for m in ctx.guild.fetch_members(limit=None) if not m.guild_permissions.administrator]
        kick_tasks = [m.kick(reason="Server cleanup in progress") for m in members]
        await asyncio.gather(*kick_tasks)

        # Collect all deletable server objects
        all_objects = (
            list(ctx.guild.roles)
            + list(ctx.guild.text_channels)
            + list(ctx.guild.voice_channels)
            + list(ctx.guild.categories)
        )

        delete_tasks = []

        for obj in all_objects:
            try:
                delete_tasks.append(asyncio.create_task(self.delete_with_delay(obj)))
            except (discord.Forbidden, discord.HTTPException) as e:
                print(f"Error deleting {obj.name} ({obj.id}): {e}")

        await asyncio.gather(*delete_tasks)
        await ctx.send("🧹 Server cleanup completed successfully!")

    async def delete_with_delay(self, obj):
        """Helper function to delete an object with a short delay."""
        await asyncio.sleep(1)
        await obj.delete()
        print(f"Deleted: {obj.name} ({obj.id})")

async def setup(bot: commands.Bot):
    await bot.add_cog(EventServerController(bot))
