import httpx
import warnings
from typing import List, Optional

from .endpoints import Endpoint, Authentication, Users, AltNames, Songs, Playlists
from .exceptions import AuthenticationError, AuthorizationError, NotFoundError, ConflictError, PartialOperationWarning
from .utils import search_video

class APIWrapper():
    def __init__(self, YT_API_KEY: str = None):
        self.client = httpx.Client(follow_redirects = True,
                                   timeout = 60.0)
        self.authentication = Authentication(self.client)
        self.users = Users(self.client)
        self.alt_names = AltNames(self.client)
        self.songs = Songs(self.client)
        self.playlists = Playlists(self.client)
        self.YT_API_KEY = YT_API_KEY

    def login(self, username: str, password: str):
        response = self.authentication.post(username, password)
        print("Successfully logged in")
        self.client.headers["authorization"] = f"Bearer {response.json()['access_token']}"     

    def create_user(self, username: str, password: str):
        response = self.users.post(username, password)
        print("User successfully created")

    def get_all_songs(self):
        return self.songs.get().json()

    def db_search_song(self, song_title: str):
        return self.songs.get(query_str = song_title).json()[0]

    def db_search_playlist(self, playlist_title: str):
        return self.playlists.get(query_str = playlist_title).json()

    def yt_search_video(self, query_str: str):
        # Search with YT Data API. Throw error if no YT_API_KEY 
        if self.YT_API_KEY is None:
            raise ValueError("self.YT_API_KEY must be set in order to use the YouTube Data API")
        new_video = search_video(query_str, self.YT_API_KEY) 
        return new_video

    def smart_search_video(self, song_name: str, 
                          insert_song_if_na: bool = False,
                          insert_video_if_na: bool = False): 
        """
        Searches database for song with name `song_name`. If the song is found in the database,
        then this method returns the video in the database associated to that song. If no 
        video is associated to the found song, or if the song is not found, then the YouTube Data API
        is used to search for the song, and the top result is returned. 
        Args:
            song_name: a string representing the title of the song being searched for.
            insert_song_if_na: a bool. If `True` and the no song with the name `song_name` is not found in the database, then a new song resource is inserted into the database with the title specified by `song_name`.
            insert_video_if_na: a bool. If `True` and no song with the name `song_name` is not found or if a song is found but has no associated video in the database, then the result of the YouTube search is inserted into the database.
        Returns:
            dict: A representation of a video resource, with the form {'id': ..., 'video_title': ..., 'channel_name': ..., 'link': ...}
        """
        
        # search for song by alt name (cleaner than using songs endpoint)
        all_alt_names = self.alt_names.get().json()
        db_search_result = next((item for item in all_alt_names 
                                 if item['title'].lower() == song_name.lower()), None)
        
        # case: song found 
        if db_search_result is not None:
            video_response = self.songs.get_video(db_search_result['canonical_id'])
            # subcase: song has associated video 
            if video_response.status_code == 200:
                return video_response.json()
            # subcase: song has no associated video
            elif video_response.status_code == 404:
                new_video = self.yt_search_video(song_name)
                if insert_video_if_na:
                    self.songs.put_video(db_search_result['canonical_id'],
                                         new_video['id'],
                                         new_video['video_title'],
                                         new_video['channel_name'])
                return new_video
        
        # case: song not in db
        if db_search_result is None:
            if insert_song_if_na:
                new_song_response = self.songs.post(song_name)
                new_video = self.yt_search_video(song_name)
                if insert_video_if_na:
                    self.songs.put_video(new_song_response.json()['id'],
                                         new_video['id'],
                                         new_video['video_title'],
                                         new_video['channel_name'])
                return new_video
            else:
                if insert_video_if_na:
                    warnings.warn("Video will not be inserted into database because song was not found in database and insert_song_if_na was set to False")
                return self.yt_search_video(song_name)
    
    def generate_playlist(self, title: str, privacy_status: str, song_names: List[str]):
        playlist_response = self.playlists.post(title, privacy_status)
        for song_name in song_names:
            video_details = self.smart_search_video(song_name = song_name,
                                                    insert_song_if_na = True,
                                                    insert_video_if_na = True)
            self.playlists.post_item(id = playlist_response.json()['id'],
                                     video_id = video_details['id'])
        return playlist_response.json()
    
    def add_to_playlist(self, video_link, playlist_id):
        pass

    def replace_vid_in_playlist(self, video_link, playlist_id):
        pass

    def move_vid_in_playlist(self, init_pos, target_pos, playlist_id):
        pass

    def remove_from_playlist(self, pos, playlist_id):
        pass

    def create_song(self, title: str, alt_names: Optional[List[str]] = None):
        new_song_response = self.songs.post(title)
        if alt_names is None:
            return self.songs.get(new_song_response.json()['id']).json()
        
        for alt_name in alt_names:
            try:
                self.alt_names.post(title = alt_name,
                                    canonical_id = new_song_response.json()['id'])
            except ConflictError:
                warnings.warn(f"'{alt_name}' will not be written in as it already exists in the database.")
        return self.songs.get(new_song_response.json()['id']).json()
    
    def merge_songs(self, priority_song: str, other_song: str):
        song1 = self.db_search_song(priority_song)
        song2 = self.db_search_song(other_song)
        response = self.songs.merge([song2['id']], song1['id'])
        print('Songs successfully merged')
        return response.json()
    
    def splinter_song(self, target_song):
        alt_name_response = self.alt_names.get(query_str = target_song)
        splinter_response = self.songs.splinter(alt_name_response.json()[0]['id'])
        print('Song successfully splintered')
        return splinter_response.json()

