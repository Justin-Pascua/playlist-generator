import discord
from discord.ext import commands

import pandas as pd

import io
import sys
from typing import Optional, Literal
import datetime as dt
import time
import httpx

from .config import settings
from . import utils
from api_wrapper.main import APIWrapper, ping
from api_wrapper.exceptions import AuthenticationError

TOKEN = settings.DISCORD_TOKEN.get_secret_value()
YT_API_KEY = settings.YT_API_KEY.get_secret_value()
SERVER_ID = settings.DISCORD_DEV_SERVER_ID.get_secret_value()
BUFFER = 300

if len(sys.argv) < 2:
    print("Error: No arguments provided.")
    print("Options: DEV or PROD")
    sys.exit(1)

GUILD_ID = None
if sys.argv[1] == 'DEV':
    GUILD_ID = discord.Object(SERVER_ID)
elif sys.argv[1] == 'PROD':
    GUILD_ID = None
else:
    print(f"Error: Invalid argument provided: '{sys.argv[1]}'")
    print("Options: DEV or PROD")
    sys.exit(1)


class Client(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_clients = dict()       # keys are guild id's, values are instances of APIWrapper
        self.guild_credentials = dict() # keys are guild id's, values are dict of form {'username': ..., 'password': ...}
        self.token_exp_times = dict()   # keys are guild id's, values are expiry times 
        self._YT_API_KEY = YT_API_KEY

    async def setup_hook(self):
        """
        Start up function called only once.
        """
        try:
            synced = await self.tree.sync(guild = GUILD_ID)
            print(f'Synced {len(synced)} commands')
        except Exception as e:
            print(f'Error syncing commands: {e}')
    
    async def on_ready(self):
        """
        Start up function. Called after initialization (after steup_hook) 
        and after reconnects 
        """        
        print(f"Logged on as {self.user}!")

    async def get_api_client(self, interaction: discord.Interaction) -> APIWrapper:
        """
        Fetch an API client specific to a Discord server.
        If the client exists, then it is fetched from `self.api_clients` and its JWT is refreshed.
        If the client doesn't exist, then one is created by either logging in or by creating a user. In either case, it will be added to `self.api_clients`
        """
        # verify that API is up
        if not ping():
            raise httpx.ConnectError("Main API is down!")
        
        current_guild_id = interaction.guild_id
        # if api client exists for current guild, then use existing
        if current_guild_id in self.api_clients:
            current_client = self.api_clients[current_guild_id]

            # if client's token is expired, then refresh
            current_time = int(time.time())
            if current_time >= self.token_exp_times[current_guild_id] - BUFFER:
                current_credentials = self.guild_credentials[current_guild_id]
                response = await current_client.login(**current_credentials)
                self.token_exp_times[current_guild_id] = response['exp_time']

            return current_client
        # otherwise, create new api client
        else:
            new_credentials = {'username': f'{interaction.guild.name} {str(current_guild_id)[-4:]}',
                               'password': str(current_guild_id)}
            self.guild_credentials[current_guild_id] = new_credentials
            new_client = APIWrapper(self._YT_API_KEY)
            try:
                # try logging in
                response = await new_client.login(**new_credentials)
                self.token_exp_times[current_guild_id] = response['exp_time']
            except AuthenticationError:
                # if user doesn't exist in main API, then create new user
                await new_client.create_user(**new_credentials)
                response = await new_client.login(**new_credentials)
                self.token_exp_times[current_guild_id] = response['exp_time']
            
            self.api_clients[interaction.guild_id] = new_client
            return new_client

intents = discord.Intents.default()
intents.message_content = True

client = Client(command_prefix = "/", intents = intents)

# General commands
@client.tree.command(name = 'help', description = 'Get general info about this bot', guild = GUILD_ID)
async def help(interaction: discord.Interaction):
    guide_url = 'https://docs.google.com/document/d/10KG11KKhcBYBdYKiKbL_IoNlYHDFSJ2uJuIrS26gFWA/edit?usp=sharing'
    output_str = "This bot helps teams by automating the process of creating YouTube playlists. " \
    "It records which songs and which videos your team uses in order to better match your " \
    "preferences. Users can add, edit, delete, merge, and split songs. For a comprehensive explanation " \
    f"of all the commands, and how the bot works, please refer to {guide_url}"
    
    await interaction.response.send_message(output_str)

# Song commands
@client.tree.command(name = 'view-songs', description = 'Get all your songs in the database.', guild = GUILD_ID)
async def summarize_songs(interaction: discord.Interaction, 
                          query_str: str = None, starts_with: str = None,
                          include_alts: Optional[bool] = True, include_links: Optional[bool] = True):
    """
    Args:
        query_str: Used to search songs by their canonical title and/or alternate titles.
        starts_with: Type a single letter to get only songs starting with that letter.
        include_alts: Type "False" to exclude alternate names.
        include_links: Type "False" to exclude video links.
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
        api_client = await client.get_api_client(interaction)
    except httpx.ConnectError as e:
        await interaction.followup.send(f"Operation aborted. {e}")
        return 

    try:
        response = await api_client.summarize_songs(
            query_str = query_str,
            starts_with = starts_with, 
            include_alts = include_alts,
            include_links = include_links)
        output_str = response['detail']
        if len(output_str) < 2000:
            await interaction.followup.send(output_str,
                                            suppress_embeds = True)
            return
        
        output_chunks = utils.partition_song_summary_str(output_str, slack = 100)
        for i, chunk in enumerate(output_chunks):
            await interaction.followup.send(
                f"**__Part {i+1}/{len(output_chunks)}__** \n{chunk}",
                suppress_embeds = True
            )

    except Exception as e:
        await interaction.followup.send(f"Unexpected error occurred. {e}")

@client.tree.command(name = 'add-song', description = 'Add song to the database.', guild = GUILD_ID)
async def create_song(interaction: discord.Interaction, title: str, 
                      alt_titles: Optional[str] = None, video_link: Optional[str] = None):
    """
    Args:
        title: The title of the song. 
        alt_titles: A list of titles separated by semi-colons (e.g. Title 1; Title 2; Title 3).
        video_link: A link to a YouTube video. 
    """
    
    await interaction.response.defer(thinking = True)
    try:
        api_client = await client.get_api_client(interaction)
    except httpx.ConnectError as e:
        await interaction.followup.send(f"Operation aborted. {e}")
        return 
    
    try:
        title = title.strip()
        if alt_titles is not None:
            alt_titles = [title.strip() for title in alt_titles.split(';') if title.strip() != ""]

        response = await api_client.create_song(title = title, alt_names = alt_titles, video_link = video_link)
        output_str = ""
        for i, item in enumerate(response['detail']):
            if i == 0:
                output_str += f"{item} \n"
            else:
                output_str += f"- {item} \n"
        await interaction.followup.send(output_str)
    except Exception as e:
        await interaction.followup.send(f"Unexpected error occurred. {e}")

@client.tree.command(name = 'edit-song-title', description = 'Edit the canonical title of a song.', guild = GUILD_ID)
async def modify_title(interaction: discord.Interaction, old_title: str, new_title: str):
    """
    Args:
        old_title: The current title (or one of the alternate titles) of the song you want to edit.
        new_title: The new title to be assigned. 
    """
    await interaction.response.defer(thinking = True)
    try:
        api_client = await client.get_api_client(interaction)
    except httpx.ConnectError as e:
        await interaction.followup.send(f"Operation aborted. {e}")
        return 
    
    try:
        new_title = new_title.strip()
        response = await api_client.modify_title(old_title, new_title)
        await interaction.followup.send(response['detail'])
    except Exception as e:
        await interaction.followup.send(f"Unexpected error occurred. {e}")

@client.tree.command(name = 'delete-song', 
                     description = 'Remove a song (along with its associated video and alt titles) from the database.',
                     guild = GUILD_ID)
async def delete_song(interaction: discord.Interaction, title: str):
    """
    Args:
        title: The current title (or one of the alternate titles) of the song you want to delete.
    """
    await interaction.response.defer(thinking = True)
    try:
        api_client = await client.get_api_client(interaction)
    except httpx.ConnectError as e:
        await interaction.followup.send(f"Operation aborted. {e}")
        return 

    try:
        response = await api_client.delete_song(title)
        await interaction.followup.send(response['detail'])
    except Exception as e:
        await interaction.followup.send(f"Unexpected error occurred. {e}")

@client.tree.command(name = 'add-alt-titles', description = 'Add alternate titles for to a song resource.', guild = GUILD_ID)
async def add_alt_names(interaction: discord.Interaction, song_title: str, alt_titles: str):
    """
    Args: 
        song_title: The title (or one of the alternate titles) of the song you want to modify.
        alt_titles: A list of alternate titles separated by semi-colons (e.g. Title 1; Title 2; Title 3).
    """
    
    await interaction.response.defer(thinking = True)
    try:
        api_client = await client.get_api_client(interaction)
    except httpx.ConnectError as e:
        await interaction.followup.send(f"Operation aborted. {e}")
        return 
    
    try:
        alt_titles = [title.strip() for title in alt_titles.split(';') if title.strip() != ""]
        response = await api_client.add_alt_names(
            target_title = song_title, 
            alt_names = alt_titles)
        output_str = ""
        for item in response['detail']:
            output_str += f"- {item} \n"
        await interaction.followup.send(output_str)
    except Exception as e:
        await interaction.followup.send(f"Unexpected error occurred. {e}")

@client.tree.command(name = 'delete-alt-title', description = 'Delete specified alternate titles.', guild = GUILD_ID)
async def delete_alt_names(interaction: discord.Interaction, alt_title: str):
    """
    Args: 
        alt_titles: The title to be deleted.
    """
    await interaction.response.defer(thinking = True)
    try:
        api_client = await client.get_api_client(interaction)
    except httpx.ConnectError as e:
        await interaction.followup.send(f"Operation aborted. {e}")
        return 
    
    try:
        response = await api_client.delete_alt_name(alt_name = alt_title)
        await interaction.followup.send(response['detail'])
    except Exception as e:
        await interaction.followup.send(f"Unexpected error occurred. {e}")

@client.tree.command(name = 'merge-songs', 
                     description = 'Take all the alternate titles of second song and assigns them to first song.', 
                     guild = GUILD_ID)
async def merge_songs(interaction: discord.Interaction, priority_song: str, other_song: str):
    """
    Args:
        priority_song: The title (or one of the alternate titles) of the song whose link and canonical title will be kept.
        other_song: The title (or one of the alternate titles) of the song which will be merged into `priority_song`. 
            Note that if this song has been assigned a video, then it will be discarded after merging.
    """
    await interaction.response.defer(thinking = True)
    try:
        api_client = await client.get_api_client(interaction)
    except httpx.ConnectError as e:
        await interaction.followup.send(f"Operation aborted. {e}")
        return 
    
    try:
        response = await api_client.merge_songs(priority_song, other_song)
        await interaction.followup.send(response['detail'])
    except Exception as e:
        await interaction.followup.send(f"Unexpected error occurred. {e}")

@client.tree.command(name = 'splinter-song', description = 'Remove an alternate title of a song and create a new song resource from it.', guild = GUILD_ID)
async def splinter_song(interaction: discord.Interaction, alt_title: str):
    """
    Args:
        alt_title: The alternate title that will be splintered off of its song.
    """
    await interaction.response.defer(thinking = True)
    try:
        api_client = await client.get_api_client(interaction)
    except httpx.ConnectError as e:
        await interaction.followup.send(f"Operation aborted. {e}")
        return 
    
    try:
        response = await api_client.splinter_song(target_song = alt_title)
        await interaction.followup.send(response['detail'])
    except Exception as e:
        await interaction.followup.send(f"Unexpected error occurred. {e}")

@client.tree.command(name = 'assign-video', description = 'Assigns a video to a song.', guild = GUILD_ID)
async def assign_video(interaction: discord.Interaction, song_title: str, video_link: str):
    """
    Args:
        song_title: The title (or one of the alternate titles) of song that will be assigned the video.
        video_link: A link to a YouTube video.
    """
    await interaction.response.defer(thinking = True)
    try:
        api_client = await client.get_api_client(interaction)
    except httpx.ConnectError as e:
        await interaction.followup.send(f"Operation aborted. {e}")
        return 
    
    try:
        response = await api_client.assign_video(song_title, video_link)
        await interaction.followup.send(response['detail'])
    except Exception as e:
        await interaction.followup.send(f"Unexpected error occurred. {e}")

# Playlist commands
@client.tree.command(name = 'create-playlist', description = 'Create a playlist', guild = GUILD_ID)
async def generate_playlist(interaction: discord.Interaction, playlist_title: str, song_titles: str, privacy_status: Literal['public', 'private', 'unlisted'] = 'unlisted',):
    """
    Args:
        playlist_title: The title assigned to the playlist.
        song_titles: A semi-colon separated list of titles of the songs to be added to the playlist
            (e.g. Title 1; Title 2; Title 3).
        privacy_status: The privacy status of the playlist.
    """
    await interaction.response.defer(thinking = True)
    try:
        api_client = await client.get_api_client(interaction)
    except httpx.ConnectError as e:
        await interaction.followup.send(f"Operation aborted. {e}")
        return 
    
    try:
        song_titles = [title.strip() for title in song_titles.split(';') if title.strip() != ""]
        response = await api_client.generate_playlist(
            title = playlist_title,
            privacy_status = privacy_status,
            song_titles = song_titles)
        output_str = f"Title: {response['content']['playlist_title']} \n"
        output_str += f"Link: {response['content']['link']} \n"
        output_str += f"Summary: \n"
        for song, message in zip(song_titles, response['detail']):
            output_str += f"- {song}: {message} \n"
        await interaction.followup.send(output_str)
    except Exception as e:
        await interaction.followup.send(f"Unexpected error occurred. {e}")
    

@client.tree.command(name = 'view-playlists', description = 'Get your playlists in database. You can fetch all playlists, or the most recent playlist.', guild = GUILD_ID)
async def summarize_playlists(interaction: discord.Interaction, mode: Literal['all', 'recent'] = 'recent'):
    """
    Args:
        mode: Type "all" to get all playlists you've created, or "recent" to get the most recent playlist.
    """
    await interaction.response.defer(thinking = True)
    try:
        api_client = await client.get_api_client(interaction)
    except httpx.ConnectError as e:
        await interaction.followup.send(f"Operation aborted. {e}")
        return 
    
    try:
        response = await api_client.summarize_playlists(latest_only = (mode == 'recent'))
        await interaction.followup.send(response['detail'],
                                        suppress_embeds = (mode == 'all'))
    except Exception as e:
        await interaction.followup.send(f"Unexpected error occurred. {e}")

@client.tree.command(name = 'edit-playlist', description = 'Edit the title of a playlist.', guild = GUILD_ID)
async def edit_playlist_title(interaction: discord.Interaction, old_title: str, new_title: str):
    """
    Args:
        old_title: The current title of the playlist you want to edit.
        new_title: The new title to be assigned to the playlist.
    """
    await interaction.response.defer(thinking = True)
    try:
        api_client = await client.get_api_client(interaction)
    except httpx.ConnectError as e:
        await interaction.followup.send(f"Operation aborted. {e}")
        return 
    
    try:
        new_title = new_title.strip()
        response = await api_client.edit_playlist_title(old_title, new_title)
        await interaction.followup.send(response['detail'])
    except Exception as e:
        await interaction.followup.send(f"Unexpected error occurred. {e}")


#Playlist item commands
@client.tree.command(name = 'add-to-playlist', description = 'Add a video to an existing playlist.', guild = GUILD_ID)
async def add_to_playlist(interaction: discord.Interaction, playlist_title: str, video_link: str):
    """
    Args:
        playlist_title: The title of the playlist you want to edit. 
        video_link: The link of the video to be added.
    """
    await interaction.response.defer(thinking = True)
    try:
        api_client = await client.get_api_client(interaction)
    except httpx.ConnectError as e:
        await interaction.followup.send(f"Operation aborted. {e}")
        return 
    
    try:
        response = await api_client.add_to_playlist(
            playlist_title = playlist_title,
            video_link = video_link,
            record_in_db = True)
        await interaction.followup.send(response['detail'])
    except Exception as e:
        await interaction.followup.send(f"Unexpected error occurred. {e}")

@client.tree.command(name = 'replace-playlist-video', description = 'Replace a video in an existing playlist.', guild = GUILD_ID)
async def replace_vid_in_playlist(interaction: discord.Interaction, playlist_title: str, position: int, video_link: str):
    """
    Args:
        playlist_title: The title of the playlist.
        position: The position of the video that should be replaced (e.g. if you want to replace the second video, then enter 2). 
        video_link: The link of the video to be added.
    """
    await interaction.response.defer(thinking = True)
    try:
        api_client = await client.get_api_client(interaction)
    except httpx.ConnectError as e:
        await interaction.followup.send(f"Operation aborted. {e}")
        return 
    
    try:
        # subtract 1 from position because we use 0-indexing, while users use 1-indexing
        response = await api_client.replace_vid_in_playlist(
            playlist_title = playlist_title,
            pos = position - 1,
            video_link = video_link)
        await interaction.followup.send(response['detail'])
    except Exception as e:
        await interaction.followup.send(f"Unexpected error occurred. {e}")
    
@client.tree.command(name = 'move-in-playlist', description = 'Move a video within existing playlist.', guild = GUILD_ID)
async def move_vid_in_playlist(interaction: discord.Interaction, playlist_title: str, initial_position: int, final_position: int):
    """
    Args:
        playlist_title: The title of the playlist you want to edit.
        initial_position: The current position of the video within the playlist 
            (e.g. if you want to move the second video in the plalyist, set this to 2).
        final_position: The position you want to move the video to
            (e.g. if you want to move the video to be the third in the playlist, set this to 3).
    """
    await interaction.response.defer(thinking = True)
    try:
        api_client = await client.get_api_client(interaction)
    except httpx.ConnectError as e:
        await interaction.followup.send(f"Operation aborted. {e}")
        return 
    
    try:
        # subtract 1 from position because we use 0-indexing, while users use 1-indexing
        response = await api_client.move_vid_in_playlist(
            playlist_title = playlist_title,
            init_pos = initial_position - 1,
            target_pos = final_position - 1)
        await interaction.followup.send(response['detail'])
    except Exception as e:
        await interaction.followup.send(f"Unexpected error occurred. {e}")

@client.tree.command(name = 'remove-from-playlist', description = 'Remove a video from an existing playlist.', guild = GUILD_ID)
async def remove_from_playlist(interaction: discord.Interaction, playlist_title: str, position: int):
    """
    Args:
        playlist_title: The title of the playlist you want to edit.
        position: The position of the video that should be removed (e.g. if you want to remove the second video, then enter 2). 
    """
    await interaction.response.defer(thinking = True)
    try:
        api_client = await client.get_api_client(interaction)
    except httpx.ConnectError as e:
        await interaction.followup.send(f"Operation aborted. {e}")
        return 
    
    try:
        # subtract 1 from position because we use 0-indexing, while users use 1-indexing
        response = await api_client.remove_from_playlist(
            playlist_title = playlist_title,
            pos = position - 1)
        await interaction.followup.send(response['detail'])
    except Exception as e:
        await interaction.followup.send(f"Unexpected error occurred. {e}")

# Import/export commands
@client.tree.command(name = 'import-songs', description = 'Import songs from a .csv file and save into the database', guild = GUILD_ID)
async def import_csv(interaction: discord.Interaction, file: discord.Attachment):
    """
    Args:
        file: A .csv file containing the songs to be added to the database. 
            For a formatting guide, see https://docs.google.com/spreadsheets/d/1nRShEulUUMzuYSU3Ju_UkTgAW-cJqx7gKBS5VXy8hdE/edit?usp=sharing
    """
    await interaction.response.defer(thinking = True)
    try:
        api_client = await client.get_api_client(interaction)
    except httpx.ConnectError as e:
        await interaction.followup.send(f"Operation aborted. {e}")
        return 
    
    guide_link = 'https://docs.google.com/spreadsheets/d/1nRShEulUUMzuYSU3Ju_UkTgAW-cJqx7gKBS5VXy8hdE/edit?usp=sharing'
    
    # verfiy file format
    if not file.filename.lower().endswith('.csv'):
        await interaction.followup.send(f"Operation aborted. Please upload a .csv file! For a guide, please refer to {guide_link}")
        return
    
    status_msg = await interaction.followup.send("*Processing data. This might take a while :/*",
                                                 suppress_embeds = True)
    
    try:
        # read into df and check col names
        file_bytes = await file.read()
        df = pd.read_csv(io.BytesIO(file_bytes))
        if not all(df.columns == ['Song', 'Alt Names', 'Link']):
            await status_msg.edit(
                content = f"""Error: expected the column titles 'Song', 'Alt Names', and 'Link', 
                but instead got {', '.join(df.columns.to_list())}. 
                Please refer to the guide at {guide_link}"""
            )
            return
        
        response = await api_client.import_songs(df)
        await status_msg.edit(content = f"{response['detail']}")
    except Exception as e:
        await status_msg.edit(content = f"Unexpected error: {e}")

@client.tree.command(name = 'export-songs', description = 'Export all songs in your database into a .csv file', guild = GUILD_ID)
async def export_csv(interaction: discord.Interaction):
    await interaction.response.defer(thinking = True)
    try:
        api_client = await client.get_api_client(interaction)
    except httpx.ConnectError as e:
        await interaction.followup.send(f"Operation aborted. {e}")
        return 
    
    try:
        songs = await api_client.get_all_songs()
        if len(songs) == 0:
            await interaction.followup.send(content = "No songs in your database, so no file generated!")
            return
        
        df = utils.json_songs_to_df(songs)
        csv_string = df.to_csv(index = False)
        csv_bytes = csv_string.encode('utf-8')
        csv_file = discord.File(
            io.BytesIO(csv_bytes),
            filename = f"{interaction.user.name}_data_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        await interaction.followup.send(
            content = f"Your data is ready!",
            file = csv_file
        )
    except Exception as e:
        await interaction.followup.send(content = f"Unexpected error occured: {e}")

client.run(TOKEN)
