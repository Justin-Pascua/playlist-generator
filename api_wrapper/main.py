import httpx
import warnings
from typing import List, Optional

from .endpoints import Endpoint, Authentication, Users, AltNames, Songs, Playlists
from .exceptions import AuthenticationError, AuthorizationError, NotFoundError, ConflictError, PartialOperationWarning
from . import utils

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

    # AUTH
    def login(self, username: str, password: str):
        response = self.authentication.post(username, password)
        print("Successfully logged in")
        self.client.headers["authorization"] = f"Bearer {response.json()['access_token']}"     

    def create_user(self, username: str, password: str):
        response = self.users.post(username, password)
        print("User successfully created")

    # READ
    def get_all_songs(self):
        return self.songs.get().json()

    def get_all_playlists(self):
        return self.playlists.get().json()

    def print_all_songs(self):
        try:
            all_songs = self.get_all_songs()
            for song in all_songs:
                print(f"Song: '{song['title']}'")
                print(f"  Video: {song['link']}")
                print(f"  Alternate titles: ")
                for alt_title in song['alt_names']:
                    print(f"  - '{alt_title['title']}'")
                print("")
        except NotFoundError:
            print("No songs in your database!")

    def print_all_playlists(self):
        try:
            all_playlists = self.get_all_playlists()
            for playlist in all_playlists:
                print(f"Title: '{playlist['playlist_title']}'")
                print(f"  Link: {playlist['link']}")
                print(f"  Created at: {playlist['created_at']}")
                print("")
        except NotFoundError:
            print("No playlists in your database!") 


    # SEARCH
    def db_search_song(self, song_title: str):
        # searches songs by alt names
        return self.songs.get(query_str = song_title).json()[0]

    def db_search_playlist(self, playlist_title: str):
        return self.playlists.get(query_str = playlist_title).json()

    def yt_search_video(self, query_str: str):
        # Search with YT Data API. Throw error if no YT_API_KEY 
        if self.YT_API_KEY is None:
            raise ValueError("self.YT_API_KEY must be set in order to use the YouTube Data API")
        new_video = utils.search_video(query_str, self.YT_API_KEY) 
        return new_video

    # AGGREGATES
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
        all_alt_names = []
        
        # using try-except to allow function to continnue even if database currently has no items
        try:
            all_alt_names = self.alt_names.get().json()
        except:
            pass

        db_search_result = next((item for item in all_alt_names 
                                if item['title'].lower() == song_name.lower()), None)
        
        # case: song found 
        if db_search_result is not None:
            try:
                video_response = self.songs.get_video(db_search_result['canonical_id'])
                # if no error thrown, then video found 
                return video_response.json()
            except NotFoundError:
                # otherwise, search YouTube for video
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
        # ensure that all videos can be obtained without error before creating playlist
        videos = []
        for song_name in song_names:
            video = self.smart_search_video(song_name = song_name,
                                            insert_song_if_na = True,
                                            insert_video_if_na = True)
            videos.append(video)

        # if no error, then create playlist
        response = dict()
        response['log'] = dict()

        playlist_response = self.playlists.post(title, privacy_status)    
        response['log']['playlist_status'] = playlist_response.status_code
        response['playlist'] = playlist_response.json()

        response['log']['video_statuses'] = []
        for video in videos:
            insert_response = self.playlists.post_item(
                id = playlist_response.json()['id'],
                video_id = video['id'])
            response['log']['video_statuses'].append(insert_response.status_code)
    

        return response
    
    def create_song(self, title: str, alt_names: Optional[List[str]] = None, video_details: dict = None):
        new_song_response = self.songs.post(title)
        if alt_names is None:
            return self.songs.get(new_song_response.json()['id']).json()
        
        for alt_name in alt_names:
            try:
                self.alt_names.post(title = alt_name,
                                    canonical_id = new_song_response.json()['id'])
            except ConflictError:
                warnings.warn(f"'{alt_name}' will not be written in as it already exists in the database.")

        if video_details is None:
            return self.songs.get(new_song_response.json()['id']).json()
        
        # insert video

        return self.songs.get(new_song_response.json()['id']).json()
    
    # PLAYLIST OPERATIONS
    def add_to_playlist(self, video_link, playlist_id):
        pass

    def replace_vid_in_playlist(self, video_link, playlist_id):
        pass

    def move_vid_in_playlist(self, init_pos, target_pos, playlist_id):
        pass

    def remove_from_playlist(self, pos, playlist_id):
        pass

    # SONG MANAGEMENT
    def merge_songs(self, priority_song: str, other_song: str):
        song1 = self.db_search_song(priority_song)
        song2 = self.db_search_song(other_song)
        response = self.songs.merge([song2['id']], song1['id'])
        print('Songs successfully merged')
        return response.json()
    
    def splinter_song(self, target_song: str):
        alt_name_response = self.alt_names.get(query_str = target_song)
        splinter_response = self.songs.splinter(alt_name_response.json()[0]['id'])
        print('Song successfully splintered')
        return splinter_response.json()

    def delete_song(self, title: str):
        try:
            song = self.db_search_song(title)
            self.songs.delete(song['id'])
        except NotFoundError:
            print(f"Song '{title}' not found!")

    def delete_alt_names(self, alt_names: List[str]):
        for alt_name in alt_names:
            try:
                target = self.alt_names.get(query_str = alt_name).json()
                self.alt_names.delete(target['id'])
            except NotFoundError:
                print(f"Alt title '{alt_name}' not found!")

    def edit_alt_name(self, old_alt_name: str, new_alt_name: str = None, new_canonical_id: str = None):
        pass

    def modify_title(self, new_title: str):
        # update canonical and corresponding alt name
        pass
        
    def assign_video(self, song_title, video_link):
        pass