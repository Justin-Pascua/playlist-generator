import httpx
import warnings
from typing import List, Optional

from .endpoints import Endpoint, Authentication, Users, AltNames, Songs, Playlists
from .exceptions import (AuthenticationError, AuthorizationError, NotFoundError, 
                         ConflictError, VideoLinkParserError, PartialOperationWarning)
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

    def _check_yt_api_key(self):
        if self.YT_API_KEY is None:
            raise ValueError("Method requires a YouTube Data API key!")

    def set_yt_api_key(self, key: str):
        self.YT_API_KEY = key

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
        try:
            return self.songs.get().json()
        except NotFoundError:
            return []

    def get_all_playlists(self):
        try:
            return self.playlists.get().json()
        except NotFoundError:
            return []

    def print_all_songs(self):
        all_songs = self.get_all_songs()
        if len(all_songs) == 0:
            print("No songs in your database!")
            return 
        
        for song in all_songs:
            print(f"Song: '{song['title']}'")
            print(f"  Video: {song['link']}")
            print(f"  Alternate titles: ")
            for alt_title in song['alt_names']:
                print(f"  - '{alt_title['title']}'")
            print("")
            
    def print_all_playlists(self):
        all_playlists = self.get_all_playlists()
        if len(all_playlists) == 0:
            print("No playlists in your database!") 
            return

        for playlist in all_playlists:
            print(f"Title: '{playlist['playlist_title']}'")
            print(f"  Link: {playlist['link']}")
            print(f"  Created at: {playlist['created_at']}")
            print("")


    # SEARCH
    def _db_search_song(self, song_title: str):
        # searches songs by alt names, returns full song resource
        return self.songs.get(query_str = song_title).json()[0]

    def _db_search_alt(self, alt_title: str):
        # searches alt_names table, returns alt_name resource
        return self.alt_names.get(query_str = alt_title).json()[0]

    def _db_search_playlist(self, playlist_title: str):
        return self.playlists.get(query_str = playlist_title).json()[0]

    def _yt_search_video(self, query_str: str):
        # Search with YT Data API. Throw error if no YT_API_KEY 
        self._check_yt_api_key()
        new_video = utils.search_video(query_str, self.YT_API_KEY) 
        return new_video

    # AGGREGATES
    def smart_search_video(self, song_title: str, 
                          insert_song_if_na: bool = False,
                          insert_video_if_na: bool = False): 
        """
        Searches database for song with name `song_title`. If the song is found in the database,
        then this method returns the video in the database associated to that song. If no 
        video is associated to the found song, or if the song is not found, then the YouTube Data API
        is used to search for the song, and the top result is returned. 
        Args:
            song_title: a string representing the title of the song being searched for.
            insert_song_if_na: a bool. If `True` and the no song with the name `song_title` is not found in the database, then a new song resource is inserted into the database with the title specified by `song_title`.
            insert_video_if_na: a bool. If `True` and no song with the name `song_title` is not found or if a song is found but has no associated video in the database, then the result of the YouTube search is inserted into the database.
        Returns:
            dict: A representation of a video resource, with the form {'id': ..., 'video_title': ..., 'channel_name': ..., 'link': ...}
        """
        
        # search for song 
        db_search_result = None
        try:
            db_search_result = self._db_search_song(song_title) # raises NotFoundError if no results found
        except:
            pass    # if no results, allow db_search_result = None

        # case: song found 
        if db_search_result is not None:
            try:
                video_response = self.songs.get_video(db_search_result['id'])   # raises NotFoundError if given song does not have a video
                return video_response.json()
            except NotFoundError:
                # otherwise, search YouTube for video
                new_video = self._yt_search_video(song_title)
                if insert_video_if_na:
                    self.songs.put_video(db_search_result['id'],
                                         new_video['id'],
                                         new_video['video_title'],
                                         new_video['channel_name'])
                return new_video
        
        # case: song not in db
        if db_search_result is None:
            if insert_song_if_na:
                new_song_response = self.songs.post(song_title)
                new_video = self._yt_search_video(song_title)
                if insert_video_if_na:
                    self.songs.put_video(new_song_response.json()['id'],
                                         new_video['id'],
                                         new_video['video_title'],
                                         new_video['channel_name'])
                return new_video
            else:
                if insert_video_if_na:
                    print("Video will not be inserted into database because song was not found in database and insert_song_if_na was set to False")
                return self._yt_search_video(song_title)
    
    def generate_playlist(self, title: str, privacy_status: str, song_titles: List[str]):
        # ensure that all videos can be obtained without error before creating playlist
        videos = []
        for song_title in song_titles:
            video = self.smart_search_video(song_title = song_title,
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
    
    def create_song(self, title: str, alt_names: Optional[List[str]] = None, video_link: str = None):
        # insert new song resource
        new_song_response = None
        try:
            new_song_response = self.songs.post(title)
        except ConflictError:
            print(f"Operation aborted. There is already a song with the title '{title}'!")
            return

        # insert alt names
        if alt_names is None:
            alt_names = []
        
        for alt_name in alt_names:
            try:
                self.alt_names.post(title = alt_name,
                                    canonical_id = new_song_response.json()['id'])
            except ConflictError:
                print(f"'{alt_name}' will not be written in as it already exists in the database!")

        if video_link is None:
            return
        
        # insert video
        try:
            video_id = utils.extract_video_id(video_link)

            self._check_yt_api_key()
            video = utils.get_video_details(video_id, self.YT_API_KEY)
            
            self.songs.put_video(
                id = new_song_response.json()['id'],
                video_id = video['id'],
                video_title = video['video_title'],
                channel_name = video['channel_name']
                )
        except VideoLinkParserError as e:
            print(f"Song created, but video not inserted. {e}")
        except ValueError as e:
            print(f"Song created, but video not inserted. {e}")
        
    
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
        song1, song2 = None, None
        try:
            song1 = self._db_search_song(priority_song)
        except NotFoundError:
            print(f"Merge failed. Could not find song with the title '{priority_song}'")
            return
        try:
            song2 = self._db_search_song(other_song)
        except NotFoundError:
            print(f"Merge failed. Could not find song with the title '{other_song}'")
            return

        self.songs.merge([song2['id']], song1['id'])
        print('Songs successfully merged')
        
    def splinter_song(self, target_song: str):
        try:
            alt_name = self.alt_names.get(query_str = target_song).json()[0]
        except NotFoundError:
            print(f"Splinter failed. Could not find the alternate title '{alt_name}'")
            return
        
        try:
            self.songs.splinter(alt_name['id'])
            print('Song successfully splintered')
        except ConflictError as e:
            print(f"Splinter failed. {e}")
            return

    def delete_song(self, title: str):
        try:
            song = self._db_search_song(title)
            self.songs.delete(song['id'])
        except NotFoundError:
            print(f"Song '{title}' not found!")

    def add_alt_names(self, target_title: str, alt_names: List[str]):
        song = None
        try:
            song = self._db_search_song(target_title)
        except NotFoundError:
            print(f"Found no song with the title '{target_title}!'")
        
        for alt_name in alt_names:
            try:
                self.alt_names.post(alt_name, song['id'])
            except ConflictError:
                print(f"The title '{alt_name}' is already assigned to a song!")

    def delete_alt_names(self, alt_names: List[str]):
        for alt_name in alt_names:
            try:
                target = self.alt_names.get(query_str = alt_name).json()[0]
                self.alt_names.delete(target['id'])
            except NotFoundError:
                print(f"Alt title '{alt_name}' not found!")
            except ConflictError:
                print(f"Cannot delete the title '{alt_name}' because it is the canonical title of the overlying song!")

    def modify_title(self, old_title: str, new_title: str):
        try:
            song = self._db_search_song(old_title)
        except NotFoundError:
            print(f"Update failed. Could not find song with title '{old_title}'")
            return
        
        try:
            self.songs.patch(song['id'], new_title)
            alt_name = self._db_search_alt(old_title)
            self.alt_names.patch(alt_name['id'], new_title)
        except ConflictError:
            print(f"Update failed. The title '{new_title}' is already taken!")
            return
        
        print("Successfully updated song title!")
  
    def assign_video(self, song_title: str, video_link: str):
        try:
            song = self._db_search_song(song_title)          # raises NotFoundError if song not found
            video_id = utils.extract_video_id(video_link)   # raises VideoLinkParserError if can't find video_id
            video = utils.get_video_details(video_id, self.YT_API_KEY)
            self.songs.put_video(song['id'], 
                                 video['id'],
                                 video['video_title'],
                                 video['channel_name'])
            print("Successfully assigned video!")
        except NotFoundError:
            print(f"Assignment failed. Could not find song with title '{song_title}'")
        except VideoLinkParserError:
            print(f"Assignment failed. Could not identify video id from the provided link. Please try a different link format")
        