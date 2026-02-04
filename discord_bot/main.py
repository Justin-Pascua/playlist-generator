import discord
from discord.ext import commands
from discord import app_commands

import pandas as pd

import io
import asyncio
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
@client.tree.command(name = 'view-songs', description = 'Get all your songs in the database.', guild = GUILD_ID)
async def summarize_songs(interaction: discord.Interaction, starts_with: str = None, 
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
        
    await interaction.response.defer(thinking = True)
    try:
        response = client.api_client.summarize_songs(starts_with = starts_with, 
                                                     include_alts = include_alts,
                                                     include_links = include_links)
    except:
        response = {'detail': 'Unexpected error occurred while interacting with the main API!'}        
    
    await interaction.followup.send(response['detail'],
                                    suppress_embeds = True)

@client.tree.command(name = 'add-song', description = 'Add song to the database.', guild = GUILD_ID)
async def create_song(interaction: discord.Interaction, title: str, 
                      alt_titles: Optional[str] = None, video_link: Optional[str] = None):
    """
    Args:
        title: the title of the song 
        alt_titles: a list of titles separated by semi-colons (e.g. Title 1; Title 2; Title 3)
        video_link: a link to a YouTube video 
    """
    if alt_titles is not None:
        alt_titles = [title.strip() for title in alt_titles.split(';') if title.strip() != ""]
    
    await interaction.response.defer(thinking = True)
    try:
        response = client.api_client.create_song(title = title, alt_names = alt_titles, video_link = video_link)
        output_str = ""
        for i, item in enumerate(response['detail']):
            if i == 0:
                output_str += f"{item} \n"
            else:
                output_str += f"- {item} \n"
    except:
        output_str = 'Unexpected error occurred while interacting with the main API!'
    await interaction.followup.send(output_str)

@client.tree.command(name = 'edit-song-title', description = 'Edit the canonical title of a song.', guild = GUILD_ID)
async def modify_title(interaction: discord.Interaction, old_title: str, new_title: str):
    """
    Args:
        old_title: the current title of the song
        new_title: the new title to be assigned 
    """
    await interaction.response.defer(thinking = True)
    try:
        response = client.api_client.modify_title(old_title, new_title)
    except:
        response = {'detail': 'Unexpected error occurred while interacting with the main API!'}
    await interaction.followup.send(response['detail'])

@client.tree.command(name = 'add-alt-titles', description = 'Add alternate titles for to a song resource.', guild = GUILD_ID)
async def add_alt_names(interaction: discord.Interaction, song_title: str, alt_titles: str):
    """
    Args: 
        song_title: title of the song you want to modify
        alt_titles: a list of alternate titles separated by semi-colons (e.g. Title 1; Title 2; Title 3)
    """
    
    alt_titles = [title.strip() for title in alt_titles.split(';') if title.strip() != ""]
    await interaction.response.defer(thinking = True)
    try:
        response = client.api_client.add_alt_names(target_title = song_title, 
                                                   alt_names = alt_titles)
        output_str = ""
        for item in response['detail']:
            output_str += f"- {item} \n"
    except:
        output_str = 'Unexpected error occurred while interacting with the main API!'
    await interaction.followup.send(output_str)

@client.tree.command(name = 'delete-alt-title', description = 'Delete specified alternate titles.', guild = GUILD_ID)
async def delete_alt_names(interaction: discord.Interaction, alt_title: str):
    """
    Args: 
        alt_titles: the title to be deleted
    """
    await interaction.response.defer(thinking = True)
    try:
        response = client.api_client.delete_alt_name(alt_name = alt_title)
    except Exception as e:
        response = {'detail': 'Unexpected error occurred while interacting with the main API!'}
        print(e)
    await interaction.followup.send(response['detail'])

@client.tree.command(name = 'merge-songs', 
                     description = 'Take all the alternate titles of second song and assigns them to first song.', 
                     guild = GUILD_ID)
async def merge_songs(interaction: discord.Interaction, priority_song: str, other_song: str):
    """
    Args:
        priority_song: title of the song whose link and canonical title will be kept
        other_song: title of the song which will be merged into `priority_song`. 
            Note that if this song has been assigned a video, then it will be discarded after merging.
    """
    await interaction.response.defer(thinking = True)
    try:
        response = client.api_client.merge_songs(priority_song, other_song)
    except:
        response = {'detail': 'Unexpected error occurred while interacting with the main API!'}
    await interaction.followup.send(response['detail'])

@client.tree.command(name = 'splinter-song', description = 'Remove an alternate title of a song and create a new song resource from it.', guild = GUILD_ID)
async def splinter_song(interaction: discord.Interaction, alt_title: str):
    """
    Args:
        alt_title: the alternate title that will be splintered off of its song
    """
    await interaction.response.defer(thinking = True)
    try:
        response = client.api_client.splinter_song(target_song = alt_title)
    except:
        response = {'detail': 'Unexpected error occurred while interacting with the main API!'}
    await interaction.followup.send(response['detail'])

@client.tree.command(name = 'assign-video', description = 'Assigns a video to a song.', guild = GUILD_ID)
async def assign_video(interaction: discord.Interaction, song_title: str, video_link: str):
    """
    Args:
        song_title: the title of song that will be assigned the video
        video_link: a link to a YouTube video
    """
    await interaction.response.defer(thinking = True)
    try:
        response = client.api_client.assign_video(song_title, video_link)
    except:
        response = {'detail': 'Unexpected error occurred while interacting with the main API!'}
    await interaction.followup.send(response['detail'])

# 'PLAYLISTS' COMMANDS
@client.tree.command(name = 'create-playlist', description = 'Create a playlist', guild = GUILD_ID)
async def generate_playlist(interaction: discord.Interaction, playlist_title: str, song_titles: str, privacy_status: Literal['public', 'private', 'unlisted'] = 'private',):
    """
    Args:
        playlist_title: the title assigned to the playlist
        song_titles: a semi-colon separated list of titles of the songs to be added to the playlist
            (e.g. Title 1; Title 2; Title 3)
        privacy_status: the privacy status of the playlist
    """
    await interaction.response.defer(thinking = True)
    song_titles = [title.strip() for title in song_titles.split(';') if title.strip() != ""]
    try:
        response = client.api_client.generate_playlist(title = playlist_title,
                                                       privacy_status = privacy_status,
                                                       song_titles = song_titles)
        output_str = f"Link: {response['content']['link']} \n"
        output_str += f"Summary: \n"
        for song, message in zip(song_titles, response['detail']):
            output_str += f"- {song}: {message} \n"
        await interaction.followup.send(output_str)
    except:
        response = {'detail': 'Unexpected error occurred while interacting with the main API!'}
        await interaction.followup.send(response['detail'])
    

@client.tree.command(name = 'view-playlists', description = 'Get your playlists in database. You can fetch all playlists, or the most recent playlist.', guild = GUILD_ID)
async def summarize_playlists(interaction: discord.Interaction, mode: Literal['all', 'recent'] = 'recent'):
    """
    Args:
        mode: type "all" to get all playlists you've created, or "recent" to get the most recent playlist.
    """
    await interaction.response.defer(thinking = True)
    try:
        response = client.api_client.summarize_playlists(latest_only = (mode == 'recent'))
    except:
        response = {'detail': 'Unexpected error occurred while interacting with the main API!'}
    await interaction.followup.send(response['detail'],
                                    suppress_embeds = (mode == 'all'))
    

@client.tree.command(name = 'edit-playlist', description = 'Edit the title of a playlist.', guild = GUILD_ID)
async def edit_playlist_title(interaction: discord.Interaction, old_title: str, new_title: str):
    """
    Args:
        old_title: the current title of the playlist, used to identify the playlist
        new_title: the new title to be assigned to the playlist
    """
    await interaction.response.defer(thinking = True)
    try:
        response = client.api_client.edit_playlist_title(old_title, new_title)
    except:
        response = {'detail': 'Unexpected error occurred while interacting with the main API!'}
    await interaction.followup.send(response['detail'])


# 'PLAYLIST-ITEMS' COMMANDS
@client.tree.command(name = 'add-to-playlist', description = 'Add a video to an existing playlist.', guild = GUILD_ID)
async def add_to_playlist(interaction: discord.Interaction, playlist_title: str, video_link: str):
    """
    Args:
        playlist_title: the title of the playlist. 
        video_link: the link of the video to be added.
    """
    await interaction.response.defer(thinking = True)
    try:
        response = client.api_client.add_to_playlist(playlist_title = playlist_title,
                                                     video_link = video_link,
                                                     record_in_db = True)
    except:
        response = {'detail': 'Unexpected error occurred while interacting with the main API!'}
    await interaction.followup.send(response['detail'])

@client.tree.command(name = 'replace-playlist-video', description = 'Replace a video in an existing playlist.', guild = GUILD_ID)
async def replace_vid_in_playlist(interaction: discord.Interaction, playlist_title: str, position: int, video_link: str):
    """
    Args:
        playlist_title: the title of the playlist.
        position: the position of the video that should be replaced (e.g. if you want to replace the second video, then enter 2). 
        video_link: the link of the video to be added.
    """
    await interaction.response.defer(thinking = True)
    try:
        # subtract 1 from position because we use 0-indexing, while users use 1-indexing
        response = client.api_client.replace_vid_in_playlist(playlist_title = playlist_title,
                                                             pos = position - 1,
                                                             video_link = video_link)
    except:
        response = {'detail': 'Unexpected error occurred while interacting with the main API!'}
    await interaction.followup.send(response['detail'])
    

@client.tree.command(name = 'move-in-playlist', description = 'Move a video within existing playlist.', guild = GUILD_ID)
async def move_vid_in_playlist(interaction: discord.Interaction, playlist_title: str, initial_position: int, final_position: int):
    """
    Args:
        playlist_title: the title of the playlist.
        initial_position: the current position of the video within the playlist 
            (e.g. if you want to move the second video in the plalyist, set this to 2).
        final_position: the position you want to move the video to
            (e.g. if you want to move the video to be the third in the playlist, set this to 3).
    """
    await interaction.response.defer(thinking = True)
    try:
        # subtract 1 from position because we use 0-indexing, while users use 1-indexing
        response = client.api_client.move_vid_in_playlist(playlist_title = playlist_title,
                                                          init_pos = initial_position - 1,
                                                          target_pos = final_position - 1)
    except:
        response = {'detail': 'Unexpected error occurred while interacting with the main API!'}
    await interaction.followup.send(response['detail'])

@client.tree.command(name = 'remove-from-playlist', description = 'Remove a video from an existing playlist.', guild = GUILD_ID)
async def remove_from_playlist(interaction: discord.Interaction, playlist_title: str, position: int):
    """
    Args:
        playlist_title: the title of the playlist.
        position: the position of the video that should be removed (e.g. if you want to remove the second video, then enter 2). 
    """
    await interaction.response.defer(thinking = True)
    try:
        # subtract 1 from position because we use 0-indexing, while users use 1-indexing
        response = client.api_client.remove_from_playlist(playlist_title = playlist_title,
                                                          pos = position - 1)
    except Exception as e:
        print(e)
        response = {'detail': 'Unexpected error occurred while interacting with the main API!'}
    await interaction.followup.send(response['detail'])

@client.tree.command(name = 'import-songs', description = 'Import songs from a .csv file and save into the database', guild = GUILD_ID)
async def import_csv(interaction: discord.Interaction, file: discord.Attachment):
    """
    Args:
        file: a .csv file 
    """
    await interaction.response.defer()
    # verfiy file format
    if not file.filename.lower().endswith('.csv'):
        await interaction.followup.send("❌ Please upload a .csv file")
        return
    
    status_msg = await interaction.followup.send("*This might take a while*",
                                                 suppress_embeds = True)
    guide_link = 'https://docs.google.com/spreadsheets/d/1nRShEulUUMzuYSU3Ju_UkTgAW-cJqx7gKBS5VXy8hdE/edit?usp=sharing'
    try:
        file_bytes = await file.read()
        df = pd.read_csv(io.BytesIO(file_bytes))
        if not all(df.columns == ['Song', 'Alt Names', 'Link']):
            await status_msg.edit(
                content = f"Error: expected the column titles 'Song', 'Alt Names', and 'Link', but got {', '.join(df.columns.to_list())}"
            )
    except Exception as e:
        await status_msg.edit(content = f"Error: {str(e)}")



client.run(TOKEN)
