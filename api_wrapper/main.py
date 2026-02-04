import httpx
import warnings
from typing import List, Optional
import pandas as pd

from .endpoints import Endpoint, Authentication, Users, AltNames, Songs, Playlists
from .exceptions import (AuthenticationError, AuthorizationError, NotFoundError, 
                         ConflictError, VideoLinkParserError, PartialOperationWarning)
from . import utils


TAB_STR = " "*4
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
    def login_status(self):
        try:
            response = self.authentication.get()
        except AuthenticationError:
            return {'status': False}
        return {'status': True}

    def login(self, username: str, password: str):
        # raises 403 if user doesn't exist or bad credentials
        response = self.authentication.post(username, password)
        self.client.headers["authorization"] = f"Bearer {response.json()['access_token']}"     
        return {'detail': 'Successfully logged in'}

    def create_user(self, username: str, password: str):
        response = self.users.post(username, password)
        return {'detail': 'User successfully created'}

    # READ
    def get_all_songs(self, starts_with: str = None):
        if starts_with is not None:
            if type(starts_with) != str:
                raise ValueError('starts_with must be a string of length 1')
            if len(starts_with) > 1:
                raise ValueError('starts_with must be a string of length 1')
        try:
            return self.songs.get(starts_with = starts_with).json()
        except NotFoundError:
            return []

    def get_all_playlists(self):
        try:
            return self.playlists.get().json()
        except NotFoundError:
            return []

    def get_latest_playlist(self):
        try:
            return self.playlists.get_latest().json()
        except NotFoundError:
            return None

    def summarize_songs(self, starts_with: str = None,
                        include_alts: bool = True,
                        include_links: bool = True, 
                        print_result: bool = False):
        all_songs = self.get_all_songs(starts_with = starts_with)

        output_str = ""
        if len(all_songs) == 0:
            output_str += "No results!"
            if print_result:
                print(output_str)
            else:
                return {"detail": output_str}
        
        for song in all_songs:
            canonical_title = song['title']
            alt_names = [f"{item['title']}" for item in song['alt_names'] if item['title'] != canonical_title]
            link = song['link']

            output_str += f"**Song**: {canonical_title} \n" 
            if len(alt_names) > 0 and include_alts:
                output_str += "- *Alternate titles*: " + ", ".join(alt_names) + "\n"
            if link is not None and include_links:
                output_str += f"- *Video*: {link} \n"
            output_str += "\n"

        if print_result:
            print(output_str)
        else:
            return {"detail": output_str}
            
    def summarize_playlists(self, latest_only: bool = True, print_result: bool = False):
        all_playlists = None
        if latest_only:
            all_playlists = self.get_latest_playlist()
            all_playlists = [all_playlists] # turn into list with one element for compatibility
        else:
            all_playlists = self.get_all_playlists()

        output_str = ""
        if len(all_playlists) == 0:
            output_str += "No playlists in your database!" 
            if print_result:
                print(output_str)
            else:
                return {"detail": output_str}

        for playlist in all_playlists:
            output_str += f"**Title**: {playlist['playlist_title']} \n"
            output_str += f"- *Link*: {playlist['link']} \n"
            output_str += f"- *Created at*: {playlist['created_at']} \n"
            output_str += "\n"

        if print_result:
            print(output_str)
        else:
            return {"detail": output_str}


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
        response = {'content': None, 'detail': None}
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
                response['content'] = video_response.json() 
                response['detail'] = 'Fetched from database'
                return response
            except NotFoundError:
                # otherwise, search YouTube for video
                new_video = self._yt_search_video(song_title)
                if insert_video_if_na:
                    self.songs.put_video(db_search_result['id'],
                                         new_video['id'],
                                         new_video['video_title'],
                                         new_video['channel_name'])
                response['content'] = new_video
                response['detail'] = 'Fetched from YouTube'
                return response
        
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
                response['content'] = new_video
                response['detail'] = 'Fetched from YouTube'
                return response
            else:
                if insert_video_if_na:
                    print("Video will not be inserted into database because song was not found in database and insert_song_if_na was set to False")
                response['content'] = self._yt_search_video(song_title)
                response['detail'] = 'Fetched from YouTube'
                return response 
    
    def generate_playlist(self, title: str, privacy_status: str, song_titles: List[str]):
        response = {'content': None, 'detail': []}
        
        # ensure that all videos can be obtained without error before creating playlist
        videos = []
        for song_title in song_titles:
            search_response = self.smart_search_video(song_title = song_title,
                                            insert_song_if_na = True,
                                            insert_video_if_na = True)
            videos.append(search_response['content'])
            response['detail'].append(search_response['detail'])

        # if no error, then create playlist
        playlist_response = self.playlists.post(title, privacy_status)    
        response['content'] = playlist_response.json()

        for video in videos:
            insert_response = self.playlists.post_item(
                id = playlist_response.json()['id'],
                video_id = video['id'])

        return response
    
    def create_song(self, title: str, alt_names: Optional[List[str]] = None, 
                    video_link: str = None,
                    video_id: str = None, video_title: str = None, channel_name: str = None):
        final_response = {'detail': []}
        # insert new song resource
        new_song_response = None
        try:
            new_song_response = self.songs.post(title)
        except ConflictError:
            final_response['detail'].append(f"Operation aborted. There is already a song with the title '{title}'!")
            return final_response
        final_response['detail'].append('Song created!')

        # insert alt names
        if alt_names is None:
            alt_names = []
        for alt_name in alt_names:
            try:
                self.alt_names.post(title = alt_name,
                                    canonical_id = new_song_response.json()['id'])
            except ConflictError:
                final_response['detail'].append(f"'{alt_name}' not added as an alt title because it exists as a title for another song! \n")

        # insert video
        try:
            if all([video_id is not None, video_title is not None, channel_name is not None]):
                self.songs.put_video(
                    id = new_song_response.json()['id'],
                    video_id = video_id,
                    video_title = video_title,
                    channel_name = channel_name
                )
            elif video_link is not None:
                video_id = utils.extract_video_id(video_link)
                self._check_yt_api_key()
                video = utils.get_video_details(video_id, self.YT_API_KEY) 
                self.songs.put_video(
                    id = new_song_response.json()['id'],
                    video_id = video['id'],
                    video_title = video['video_title'],
                    channel_name = video['channel_name']
                    )
            elif any([video_id is not None, video_title is not None, channel_name is not None]):
                final_response['detail'].append(
                    f"""Video not inserted. Please provide either 
                    i) a 'video_link', 
                    or ii) 'id', 'video_title', and 'channel_name'""")
        except VideoLinkParserError as e:
            final_response["detail"].append(f"Video not inserted. {e}")
        except ValueError as e:
            final_response["detail"].append(f"Video not inserted. {e}")
        
        return final_response

    def import_songs(self, raw_df: pd.DataFrame):
        self._check_yt_api_key()
        grouped_df = utils.process_songs_df(raw_df, self.YT_API_KEY)
        for i in range(len(grouped_df)):
            song_details = dict(grouped_df.iloc[i])
            self.create_song(**song_details)
        return {'detail': 'Successfully imported songs!'}

    # PLAYLIST OPERATIONS
    def edit_playlist_title(self, old_title: str, new_title: str):
        try:
            playlist = self._db_search_playlist(old_title)
        except NotFoundError:
            return {"detail": f"Aborted operation. Could not find playlist with title '{old_title}'!"}
            
        try:
            self.playlists.patch(id = playlist['id'],
                                 title = new_title)
            return {"detail": f"Successfully changed playlist title!"}
        except:
            return {"detail": f"Abandoned operation. Unexpected error while calling YouTube Data API"}
            
    def add_to_playlist(self, playlist_title: str, video_link: str, record_in_db: bool = False):
        self._check_yt_api_key()
        # fetch playlist id by searching db by name
        try:
            playlist = self._db_search_playlist(playlist_title)
        except NotFoundError:
            return {"detail": f"Aborted operation. Could not find playlist titled '{playlist_title}'!"} 
        
        # get yt video by calling yt data api
        try:
            video_id = utils.extract_video_id(video_link)
            video = utils.get_video_details(video_id, self.YT_API_KEY)
        except VideoLinkParserError as e:
            return {"detail": f"Aborted operation. {e}"}
            
        except:
            return {"detail": f"Aborted operation. Unexpected error while calling YouTube Data API"}
        
        # insert into playlist
        try:
            self.playlists.post_item(id = playlist['id'],
                                     video_id = video['id'])
        except:
            return {"detail": "Unexpected error occured while calling YouTube Data API"}
        
        if not record_in_db:
            return {"detail": "Successfully added video!"}

        # try creating new song for provided video
        try:
            new_song_response = self.songs.post(video['video_title'])
            self.songs.put_video(id = new_song_response.json()['id'],
                                 video_id = video['id'],
                                 video_title = video['video_title'],
                                 channel_name = video['channel_name'])
        except ConflictError:
            # if song already exists, use put method to modify associated song
            existing_song = self._db_search_song(video['video_title'])
            self.songs.put_video(id = existing_song['id'],
                                 video_id = video['id'],
                                 video_title = video['video_title'],
                                 channel_name = video['channel_name'])
        return {"detail": "Successfully added video!"}

    def replace_vid_in_playlist(self, playlist_title: str, pos: int, video_link: str, record_in_db: bool = False):
        self._check_yt_api_key()
        # fetch playlist id by searching db by name
        try:
            playlist = self._db_search_playlist(playlist_title)
        except NotFoundError:
            return {"detail": f"Aborted operation. Could not find playlist titled '{playlist_title}'!"}
            
        # get yt video by calling yt data api
        try:
            video_id = utils.extract_video_id(video_link)
            video = utils.get_video_details(video_id, self.YT_API_KEY)
        except VideoLinkParserError as e:
            return {"detail": f"Aborted operation. {e}"}
            
        except:
            return {"detail": f"Aborted operation. Unexpected error while calling YouTube Data API"}
            
        # insert video into playlist
        try:
            self.playlists.patch_item(id = playlist['id'],
                                      mode = 'Replace',
                                      sub_details = {'video_id': video['id'],
                                                     'pos': pos})
        except ValueError as e:
            # raised when init_pos and target_pos are out of bounds 
            return {"detail": f"Aborted operation. {e}"}
        except:
            return {"detail": "Unexpected error occured while calling YouTube Data API"}
        
        if not record_in_db:
            return {"detail": "Successfully replaced video!"}

        # try creating new song for provided video
        try:
            new_song_response = self.songs.post(video['video_title'])
            self.songs.put_video(id = new_song_response.json()['id'],
                                 video_id = video['id'],
                                 video_title = video['video_title'],
                                 channel_name = video['channel_name'])
        except ConflictError:
            # if song already exists, use put method to modify associated song
            existing_song = self._db_search_song(video['video_title'])
            self.songs.put_video(id = existing_song['id'],
                                 video_id = video['id'],
                                 video_title = video['video_title'],
                                 channel_name = video['channel_name'])
        return {"detail": "Successfully replaced video!"}
        
    def move_vid_in_playlist(self, playlist_title: str, init_pos: int, target_pos: int):
        try:
            playlist = self._db_search_playlist(playlist_title)
        except NotFoundError:
            return {"detail": f"Aborted operation. Could not find playlist titled '{playlist_title}'!"}
        
        try:
            self.playlists.patch_item(id = playlist['id'],
                                      mode = 'Move',
                                      sub_details = {'init_pos': init_pos,
                                                     'target_pos': target_pos})
        except ValueError as e:
            # raised when init_pos and target_pos are out of bounds 
            return {"detail": f"Aborted operation. {e}"}
        except:
            return {"detail": "Unexpected error occured while calling YouTube Data API"}
        
        return {"detail": "Successfully edited playlist!"}

    def remove_from_playlist(self, playlist_title: str, pos: int):
        try:
            playlist = self._db_search_playlist(playlist_title)
        except NotFoundError:
            return {"detail": f"Aborted operation. Could not find playlist titled '{playlist_title}'!"}
        
        try:
            self.playlists.delete_item(playlist['id'], pos)
        except ValueError as e:
            # raised when pos is out of bounds 
            return {"detail": f"Playlist not edited. {e}"}
        except:
            return {"detail": "Unexpected error occured while calling YouTube Data API"}
        
        return {"detail": "Successfuly removed video from playlist!"}

    # SONG MANAGEMENT
    def merge_songs(self, priority_song: str, other_song: str):
        song1, song2 = None, None
        try:
            song1 = self._db_search_song(priority_song)
        except NotFoundError:
            return {"detail": f"Merge failed. Could not find song with the title '{priority_song}'"}
        try:
            song2 = self._db_search_song(other_song)
        except NotFoundError:
            return {"detail": f"Merge failed. Could not find song with the title '{other_song}'"}

        self.songs.merge([song2['id']], song1['id'])
        return {"detail": "Songs successfully merged!"}
        
    def splinter_song(self, target_song: str):
        try:
            alt_name = self.alt_names.get(query_str = target_song).json()[0]
        except NotFoundError:
            return {"detail": f"Splinter failed. Could not find the alternate title '{target_song}'"}
        
        try:
            self.songs.splinter(alt_name['id'])
            return {"detail": "Song successfully splintered!"}
        except ConflictError as e:
            return {"detail": f"Splinter failed. {e}"}

    def delete_song(self, title: str):
        try:
            song = self._db_search_song(title)
            self.songs.delete(song['id'])
        except NotFoundError:
            return {"detail": f"Song '{title}' not found!"}
        return {"detail": "Successfully deleted song!"}

    def add_alt_names(self, target_title: str, alt_names: List[str]):
        response = {'detail': []}
        song = None
        try:
            song = self._db_search_song(target_title)
        except NotFoundError:
            response['detail'].append(f"Operation aborted. Found no song with the title '{target_title}'!")
            return response
        
        for alt_name in alt_names:
            try:
                self.alt_names.post(alt_name, song['id'])
                response['detail'].append(f"Successfully added '{alt_name}'!")
            except ConflictError:
                response['detail'].append(f"Did not add '{alt_name}' because it's already assigned to another song!")
        
        return response

    def delete_alt_name(self, alt_name: str):
        try:
            target = self.alt_names.get(query_str = alt_name).json()[0]
            self.alt_names.delete(target['id'])
        except NotFoundError:
            return {"detail": f"Alt title '{alt_name}' not found!"}
        except ConflictError:
            return {"detail": f"Cannot delete the title '{alt_name}' because it is the canonical title of the overlying song!"}
            
        return {"detail": f"Successfully deleted the title {alt_name}!"}

    def modify_title(self, old_title: str, new_title: str):
        try:
            song = self._db_search_song(old_title)
        except NotFoundError:
            return {"detail": f"Update failed. Could not find song with title '{old_title}'"}
        
        try:
            self.songs.patch(song['id'], new_title)
            alt_name = self._db_search_alt(old_title)
            self.alt_names.patch(alt_name['id'], new_title)
        except ConflictError:
            return {"detail": f"Update failed. The title '{new_title}' is already taken!"}
        
        return {"detail": "Successfully updated song title!"}
  
    def assign_video(self, song_title: str, video_link: str):
        try:
            song = self._db_search_song(song_title)          # raises NotFoundError if song not found
            video_id = utils.extract_video_id(video_link)   # raises VideoLinkParserError if can't find video_id
            video = utils.get_video_details(video_id, self.YT_API_KEY)
            self.songs.put_video(song['id'], 
                                 video['id'],
                                 video['video_title'],
                                 video['channel_name'])
            return {"detail": "Successfully assigned video!"}
        except NotFoundError:
            return {"detail": f"Assignment failed. Could not find song with title '{song_title}'"}
        except VideoLinkParserError:
            return {"detail": f"Assignment failed. Could not identify video id from the provided link. Please try a different link format"}
        