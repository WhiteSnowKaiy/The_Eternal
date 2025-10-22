import discord
from discord.ext import commands
import os
import logging

logger: logging.Logger = logging.getLogger("Eternal.RSVP")

class RSVPView(discord.ui.View):    
    def __init__(self, rsvp_responses, message_id):
        super().__init__()
        self.rsvp_responses = rsvp_responses
        self.message_id = message_id


    @discord.ui.button(label="On Time", style=discord.ButtonStyle.green)
    async def rsvp_On_Time(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_rsvp(interaction, 'on_time')

        
    @discord.ui.button(label="Late", style=discord.ButtonStyle.blurple)
    async def rsvp_late(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_rsvp(interaction, 'late')


    @discord.ui.button(label="Day 1 only", style=discord.ButtonStyle.blurple)
    async def rsvp_day1_only(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_rsvp(interaction, 'day_1_only')


    @discord.ui.button(label="Day 2 only", style=discord.ButtonStyle.blurple)
    async def rsvp_day2_only(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_rsvp(interaction, 'day_2_only')


    @discord.ui.button(label="No Show", style=discord.ButtonStyle.red)
    async def rsvp_no_show(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_rsvp(interaction, 'no_show')
        
        
    async def _handle_rsvp(self, interaction: discord.Interaction, response_type: str):
        user_mention = interaction.user.mention
        
        # Ensure the message ID is in the dictionary and properly initialized
        if self.message_id not in self.rsvp_responses:
            self.rsvp_responses[self.message_id] = {
                'on_time': [],
                'late': [],
                'day_1_only': [],
                'day_2_only': [],
                'no_show': []
            }

        # Get the responses for the current message ID
        responses = self.rsvp_responses[self.message_id]

        # Toggle the user in the selected response list
        if user_mention in responses[response_type]:
            responses[response_type].remove(user_mention)
            await interaction.response.send_message("You have been removed from the RSVP list.", ephemeral=True)
        else:
            # Move user from any previous list they might have been in
            for list_name in ['on_time', 'late', 'day_1_only', 'day_2_only', 'no_show']:
                if user_mention in responses[list_name]:
                    responses[list_name].remove(user_mention)
                    break  # Only one list should contain the user

            responses[response_type].append(user_mention)
            await interaction.response.send_message("Reacted successfully", ephemeral=True)

        await self._update_rsvp_message(interaction.message)


    async def _update_rsvp_message(self, message: discord.Message):
        """Update RSVP message to have name of all people that reacted
        
        Args:
        message - The message to edit
        Return: None
        """
        logger.debug("Updating RSVP")
        embed = message.embeds[0]
        fields = {field.name: field.value for field in embed.fields}
        
        embed.clear_fields()
        
        embed.add_field(name="", value="**Please read the entire invite and react when you are done!**", inline=False)
        # TODO: Change thist to be dynamic
        embed.add_field(name="Time of wipe:", value=fields.get("Time of wipe:", "Unknown")) 

        for key in self.rsvp_responses[self.message_id].keys():
            if key != 'channel':
                reactors = "\n".join(self.rsvp_responses[self.message_id][key])
                embed.add_field(name=f"{key.replace('_', ' ').title()}", value=reactors if reactors else "\u200b", inline=True)

        await message.edit(embed=embed)
        logger.debug("RSVP Updated")

class RSVP(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.out_dir = os.path.join(os.path.dirname(__file__), 'out')
        self.rsvp_responses = {}


    @commands.hybrid_command(
        name="creatersvp", 
        usage="/creatersvp <server> <store> <ip> <time>", 
        description="Creates RSVP with given parameters",
    )
    async def creatersvp(self, ctx: commands.Context, time: int):
        logger.debug("Creating RSVP")
        embed = discord.Embed(
            title=f"{ctx.guild.name} - Upcoming RSVP",
            color=discord.Color.gold()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        embed.add_field(name="", value="**Please read the entire invite and react when you are done!**", inline=False)
    
        embed.add_field(name="Starting:", value=f"<t:{time}>")
        embed.set_image(url="https://media.discordapp.net/attachments/1226250497447559338/1227614159080788018/Discord-Banner.png?ex=665fc207&is=665e7087&hm=8823504aee319f650a5edeec3ded3f40abc07d8fd5be62158c7bd0df7cb97b4e&=&format=webp&quality=lossless&width=1440&height=508")
        embed.set_footer(text="Powered by The Eternal Bot")

        # Send the message first
        message = await ctx.send(embed=embed)

        # Create the view and attach it to the message
        view = RSVPView(self.rsvp_responses, message.id)
        await message.edit(view=view)

        # Save message ID to track responses along with channel ID
        self.rsvp_responses[message.id] = {
            'channel': message.channel.id,
            'on_time': [],
            'late': [],
            'day_1_only': [],
            'day_2_only': [],
            'no_show': []
        }
        logger.debug("RSVP Created")


async def setup(bot: commands.Bot):
    await bot.add_cog(RSVP(bot))