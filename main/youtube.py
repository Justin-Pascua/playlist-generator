from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from .config import settings

from typing import Literal
import os
import ast
import pickle

API_KEY = settings.YT_API_KEY

def get_credentials(as_json: bool = False):
    credentials = None

    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            credentials = pickle.load(token)

    if not credentials.valid:
        credentials.refresh(Request())
        
    if as_json:
        return ast.literal_eval(credentials.to_json())

    return credentials

def get_yt_service():
    yt_service = build('youtube', 'v3', 
                       credentials = get_credentials(), 
                       developerKey = API_KEY)
    try:
        yield yt_service
    finally:
        yt_service.close()

class PlaylistEditor:
    """
    A class representing YouTube playlists. Instances of this class maintain information concerning the playlist 
    (i.e. its title, id, and link) and the items within the playlist (i.e. their kind, etag, id, and title).
    """
    def __init__(self, mode = Literal['create_new', 'from_existing'], **kwargs):
        """
        Initializes object in one of two ways by calling one of two helper methods.
        params:
            mode: a string specifying how to initialize the object. 
            If 'create_new', then a new playlist is created through the YouTube Data API. In this case, kwargs should
            contain `title` and `privacy_status` arguments.
            If 'from_existing', then the object is initialized by fetching data through the YouTube Data API 
            concerning an existing playlist. In this case, kwargs should contain a `playlist_id` argument.  
            kwargs: arguments passed to the chosen initializer helper method.
        """
        if mode not in ['create_new', 'from_existing']:
            raise ValueError(f"mode must be one of 'create_new', 'from_existing', but received {mode}")
        
        self.title = None   # string title of playlist
        self.link = None    # link to playlist
        self.id = None      # playlist id
        self.items = None   # list of dicts of form {'kind': ..., 'etag': ..., 'id': ..., 'title': ...}

        if mode == 'create_new':
            self._init_create_new(**kwargs)
        elif mode == 'from_existing':
            self._init_from_existing(**kwargs)

    def _init_create_new(self, title: str, 
                         privacy_status: Literal["public", "private", "unlisted"] = "private"):
        """
        Helper function for __init__ which initializes instance by creating a new YouTube playlist
        using the YouTube Data API.
        params:
            title: a string used to set the title of the playlist
            privacy_status: a string among `["public", "private", "unlisted"]` used to set the status of the playlist
        """

        if type(title) != str:
            raise TypeError(f"title must be a string, but received {type(title)}")
        if privacy_status not in ["public", "private", "unlisted"]:
            raise ValueError(f'privacy_status must be one of "public", "private", "unlisted", but received {privacy_status}')

        response = None
        with build('youtube', 'v3', credentials = get_credentials(), developerKey = API_KEY) as yt_service:
            request = yt_service.playlists().insert(
                part = "id,snippet,status",
                body = {"snippet": {"title": title},
                        "status": {"privacyStatus": privacy_status}
                        }
            )
            response = request.execute()

        root = "https://youtube.com/playlist?list="

        self.title = response['snippet']['title']
        self.link = root + response['id']
        self.id = response['id']
        self.items = []

    def _init_from_existing(self, playlist_id: str):
        """
        Helper function for __init__ which initializes instance by fetching data from the 
        YouTube Data API concerning an existing YouTube playlist
        params:
            playlist_id: a string representing the playlist_id of an existing YouTube playlist
        """
        
        playlist_response = None
        playlist_items_response = None
        
        # check if playlist exists and get title, link, and id
        with build('youtube', 'v3', credentials = get_credentials(), developerKey = API_KEY) as yt_service:
            request = yt_service.playlists().list(
                part = "id,snippet",
                id = playlist_id
            )
            playlist_response = request.execute()

        try:
            # if playlist doesn't exist, then indexing at 0 throws IndexError
            self.title = playlist_response['items'][0]['snippet']['title']

            # if no error thrown, then playlist exists, so we can 
            # safely assume its id is equal to the argument provided to this function 
            self.id = playlist_id
            root = "https://youtube.com/playlist?list="
            self.link = root + playlist_id
        except IndexError:
            raise ValueError(f"Found no playlists with id {playlist_id}")
        except KeyError as e:
            raise e
        
        # get items in existing playlist
        with build('youtube', 'v3', credentials = get_credentials(), developerKey = API_KEY) as yt_service:
            request = yt_service.playlistItems().list(
                part = "id,snippet",
                playlistId = playlist_id
            )
            playlist_items_response = request.execute()
        
        # get relevant items from response
        self.items = [{'kind': item['kind'], 
                       'etag': item['etag'], 
                       'id': item['id'], 
                       'title': item['snippet']['title']} 
                       for item in playlist_items_response['items']]

    def insert_video(self, video_id: str, pos: int = None):
        """
        Inserts a video into the playlist. 
        params:
            video_id: a string representing the id of an existing YouTube video
            pos: a zero-indexed int or `None` indicating what position to insert the video. 
            If `None`, then video is inserted at the end of the playlist.
            If an int, then must be non-negative and stricly less than the current length of the playlist. If so, then
            the video is inserted at the specified position. 
        """
        if pos:
            if pos > len(self.items):
                raise ValueError(f"pos ({pos}) must not exceed length of playlist ({len(self.items)})")
            if pos < 0:
                raise ValueError(f"pos ({pos}) must be non-negative")
        
        response = None

        with build('youtube', 'v3', credentials = get_credentials(), developerKey = API_KEY) as yt_service:
            request = yt_service.playlistItems().insert(
                part = 'id,snippet,status',
                body = {
                    "snippet": {
                        "playlistId": self.id,
                        "position": pos,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id}
                    }
                }
            )
            response = request.execute()

        new_item = {'kind': response['kind'],
                    'etag': response['etag'],
                    'id': response['id'],
                    'title': response['snippet']['title']}

        if pos:
            self.items.insert(pos, new_item)
        else:
            self.items.append(new_item)

    def delete_video(self, pos: int):
        """
        Deletes a video from the playlist.
        params:
            pos: a zero-indexed, int which is non-negative and <= the current length of the playlist. 
            This specifies the position of the video to be deleted.
        """
        if pos >= len(self.items):
            raise ValueError(f"pos ({pos}) must be less than length of playlist ({len(self.items)})")
        if pos < 0:
            raise ValueError(f"pos ({pos}) must be non-negative")

        playlist_item_id = self.items[pos]['id']
        response = None

        with build('youtube', 'v3', credentials = get_credentials(), developerKey = API_KEY) as yt_service:
            request = yt_service.playlistItems().delete(
                id = playlist_item_id
            )
            response = request.execute()
        
        self.items.pop(pos)

    def move_video(self, init_pos: int, target_pos: int):
        pass

    def replace_video(self, video_id: str, pos: int):
        """
        Replaces a video in the playlist with a new video. The YouTube Data API does not provide a 
        way of doing this with an update method, so this is done by first deleting the video from the playlist,
        and inserting the new video at the target position.
        params:
            video_id: a string representing the video id of the new YouTube video.
            pos: a zero-indexed integer representing the position of the video to be replaced.
        """
        self.delete_video(pos)
        self.insert_video(video_id, pos)

    def __str__(self):
        return f"PlaylistEditor({self.title})"

    def summarize(self):
        """
        Prints the title of the playlist, its videos, and the playlist link 
        """
        print(f"Title: {self.title}")
        print(f"Videos:")
        for i, item in enumerate(self.items):
            print(f"\t({i}) {item['title']}")
        print(f"Link: {self.link}")

