import discord
from discord.ext import commands
from discord import app_commands
from .config import settings
from api_wrapper.main import APIWrapper
from typing import Optional, List, Literal

# from api_wrapper.main import APIWrapper

TOKEN = settings.DISCORD_TOKEN.get_secret_value()
YT_API_KEY = settings.YT_API_KEY.get_secret_value()
SERVER_ID = settings.DISCORD_DEV_SERVER_ID.get_secret_value()
GUILD_ID = discord.Object(SERVER_ID)

api_client = APIWrapper(YT_API_KEY)
api_client.login('Admin', 'admin123')

class Client(commands.Bot):
    async def on_ready(self):
        """
        Start up function. Called when bot first runs.
        """        
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


@client.tree.command(name = "hello", description = "Say hello!", guild = GUILD_ID)
async def say_hello(interaction: discord.Interaction):
    await interaction.response.send_message("Hello")

@client.tree.command(name = "printer", description = "I will print whatever you give me!", guild = GUILD_ID)
async def printer(interaction: discord.Interaction, input: str):
    # specifying a param allows the bot to prompt the user for an argument
    await interaction.response.send_message(input)

@client.tree.command(name = 'foo', description = 'wuz good foo', guild = GUILD_ID)
async def foo(interaction: discord.Interaction, x: str, y: int):
    """
    Test docstring
    Args:
        x: a string 
        y: an int
    """
    await interaction.response.send_message(x * y)

# 'SONGS' COMMANDS
@client.tree.command(name = 'songs-get', description = 'Get all your songs in the database.', guild = GUILD_ID)
async def get_songs(interaction: discord.Interaction):
    pass

@client.tree.command(name = 'songs-add', description = 'Add song to the database.', guild = GUILD_ID)
async def add_song(interaction: discord.Interaction):
    pass

@client.tree.command(name = 'songs-edit', description = 'Edit canonical title of a song.', guild = GUILD_ID)
async def edit_song(interaction: discord.Interaction):
    pass

@client.tree.command(name = 'songs-add-alt', description = 'Add alternate titles for to a song resource.', guild = GUILD_ID)
async def add_alts(interaction: discord.Interaction):
    pass

@client.tree.command(name = 'songs-remove-alt', description = 'Delete specified alternate titles.', guild = GUILD_ID)
async def add_song(interaction: discord.Interaction):
    pass

@client.tree.command(name = 'songs-merge', 
                     description = 'Merge two songs. This takes all the alternate titles of the second song'
                     ' and assigns them to the first song. The YouTube link of the second song is discarded.', 
                     guild = GUILD_ID)
async def add_song(interaction: discord.Interaction):
    pass

@client.tree.command(name = 'songs-splinter', description = 'Remove an alternate title of a song and create a new song resource from it.', guild = GUILD_ID)
async def add_song(interaction: discord.Interaction):
    pass

@client.tree.command(name = 'songs-assign-video', description = 'Assigns a video to a song.', guild = GUILD_ID)
async def add_song(interaction: discord.Interaction):
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
