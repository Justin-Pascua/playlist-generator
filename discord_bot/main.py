import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List, Literal

from .config import settings
from api_wrapper.main import APIWrapper


# from api_wrapper.main import APIWrapper

TOKEN = settings.DISCORD_TOKEN.get_secret_value()
YT_API_KEY = settings.YT_API_KEY.get_secret_value()
SERVER_ID = settings.DISCORD_DEV_SERVER_ID.get_secret_value()
GUILD_ID = discord.Object(SERVER_ID)

class Client(commands.Bot):
    async def on_ready(self):
        """
        Start up function. Called when bot first runs.
        """        
        self.api_client = APIWrapper(YT_API_KEY)
        self.api_client.login('Admin', 'admin123')
        print(f"Logged on as {self.user}!")
        try:
            guild = discord.Object(id = SERVER_ID)
            synced = await self.tree.sync(guild = guild)
            print(f'Synced {len(synced)} commands to {guild.id}')
        except Exception as e:
            print(f'Error syncing commands: {e}')
        

    async def on_message(self, message):
        """
        Called when bot detects a message in server.
        """
        # ignores own messages, prevents infinite loop
        if message.author == self.user:
            return 
        
        if message.content.startswith('hello'):
            await message.channel.send(f'Hi there {message.author}')

    async def on_reaction_add(self, reaction, user):
        await reaction.message.channel.send(f"You reacted")


intents = discord.Intents.default()
intents.message_content = True

client = Client(command_prefix = "/", intents = intents)

# 'SONGS' COMMANDS
@client.tree.command(name = 'songs-get', description = 'Get all your songs in the database.', guild = GUILD_ID)
async def get_songs(interaction: discord.Interaction, starts_with: str = None, 
                    include_alts: Optional[bool] = True, include_links: Optional[bool] = True):
    """
    Args:
        starts_with: type a single letter to get only songs starting with that letter.
        include_alts: type "False" to exclude alternate names.
        include_links: type "False" to exclude video links.
    """
    if starts_with is not None:
        if type(starts_with) != str:
            await interaction.response.send_message('starts_with cannot be more than 1 letter')
            return
        if len(starts_with) > 1:
            await interaction.response.send_message('starts_with cannot be more than 1 letter')
            return
    
    
    result = client.api_client.summarize_songs(starts_with = starts_with, 
                                               include_alts = include_alts,
                                               include_links = include_links)
    output_str = result['detail']
    
    await interaction.response.send_message(output_str)

@client.tree.command(name = 'songs-add', description = 'Add song to the database.', guild = GUILD_ID)
async def add_song(interaction: discord.Interaction, title: str, 
                    alt_titles: Optional[str] = None, video_link: Optional[str] = None):
    """
    Args:
        title: the title of the song 
        alt_titles: a list of titles separated by semi-colons (e.g. Title 1; Title 2; Title 3)
        video_link: a link to a YouTube video 
    """
    if alt_titles is not None:
        alt_titles = [title.strip() for title in alt_titles.split(';') if title.strip() != ""]
    try:
        response = client.api_client.create_song(title = title, alt_names = alt_titles, video_link = video_link)
        await interaction.response.send_message(response['detail'])
    except:
        await interaction.response.send_message('Unexpected error occurred while interacting with APIWrapper!')

@client.tree.command(name = 'songs-edit', description = 'Edit the canonical title of a song.', guild = GUILD_ID)
async def edit_song(interaction: discord.Interaction):
    pass

@client.tree.command(name = 'songs-add-alt', description = 'Add alternate titles for to a song resource.', guild = GUILD_ID)
async def add_alts(interaction: discord.Interaction):
    pass

@client.tree.command(name = 'songs-remove-alt', description = 'Delete specified alternate titles.', guild = GUILD_ID)
async def remove_alts(interaction: discord.Interaction):
    pass

@client.tree.command(name = 'songs-merge', 
                     description = 'Take all the alternate titles of song2 and assign them to song1.', 
                     guild = GUILD_ID)
async def merge_songs(interaction: discord.Interaction):
    pass

@client.tree.command(name = 'songs-splinter', description = 'Remove an alternate title of a song and create a new song resource from it.', guild = GUILD_ID)
async def splinter_song(interaction: discord.Interaction):
    pass

@client.tree.command(name = 'songs-assign-video', description = 'Assigns a video to a song.', guild = GUILD_ID)
async def assign_video(interaction: discord.Interaction):
    pass

# 'PLAYLISTS' COMMANDS
@client.tree.command(name = 'playlists-get', description = 'Get your playlists in database. You can fetch all playlists, or the most recent playlist.', guild = GUILD_ID)
async def get_playlists(interaction: discord.Interaction):
    pass

@client.tree.command(name = 'playlists-edit', description = 'Edit the title and/or the privacy status of a playlist.', guild = GUILD_ID)
async def update_playlist(interaction: discord.Interaction):
    pass


# 'PLAYLIST-ITEMS' COMMANDS
@client.tree.command(name = 'playlists-items-add', description = 'Add a video to an existing playlist.', guild = GUILD_ID)
async def add_to_playlist(interaction: discord.Interaction):
    pass

@client.tree.command(name = 'playlists-items-replace', description = 'Replace a video in an existing playlist.', guild = GUILD_ID)
async def add_to_playlist(interaction: discord.Interaction):
    pass

@client.tree.command(name = 'playlists-items-move', description = 'Move a video within existing playlist.', guild = GUILD_ID)
async def add_to_playlist(interaction: discord.Interaction):
    pass

@client.tree.command(name = 'playlists-items-remove', description = 'Remove a video from an existing playlist.', guild = GUILD_ID)
async def add_to_playlist(interaction: discord.Interaction):
    pass

client.run(TOKEN)
