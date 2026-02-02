import httpx
import warnings
from typing import List, Optional, Literal

from .exceptions import (AuthenticationError, AuthorizationError, NotFoundError, 
                         ConflictError, VideoLinkParserError, PartialOperationWarning)

BASE_URL = "http://localhost:8000"

class Endpoint():
    def __init__(self, client, url = BASE_URL):
        self.base_url = url
        self.client: httpx.Client = client

    def _check_common_exceptions(self, response):
        if response.status_code == 500:
            raise RuntimeError("Unexpected server error")
        elif response.status_code == 429:
            raise RuntimeError("API received too many requests")
        elif response.status_code == 422:
            # type validation error
            error_message = ""
            for item in response.json()['detail']:
                error_message += f"Expected {item['type']} for {item['loc'][-1]}. "
            raise TypeError(error_message)
        elif response.status_code == 401:
            raise AuthenticationError(response.json()['detail'])
        
class Authentication(Endpoint):
    def __init__(self, client):
        super().__init__(client)
        self.url = self.base_url + '/authentication'

    def post(self, username: str, password: str):
        response = self.client.post(self.url,
                                    data = {'username': username,
                                            'password': password})
        
        self._check_common_exceptions(response)
        
        if response.status_code == 403:
            # invalid credentials
            raise ValueError(f"{response.json()['detail']}")
        
        return response

class Users(Endpoint):
    def __init__(self, client):
        super().__init__(client)
        self.url = self.base_url + '/users'

    def post(self, username: str, password: str):
        response = self.client.post(self.url,
                                    json = {'username': username,
                                            'password': password})
        self._check_common_exceptions(response)
        if response.status_code == 409:
            # username taken
            raise ConflictError(f"{response.json()['detail']}")

        return response

class AltNames(Endpoint):
    def __init__(self, client):
        super().__init__(client)
        self.url = self.base_url + '/alt-names'

    def post(self, title: str, canonical_id: int):
        response = self.client.post(self.url,
                                    json = {'title': title,
                                            'canonical_id': canonical_id})
        
        self._check_common_exceptions(response)

        if response.status_code == 409:
            # alt name taken
            raise ConflictError(response.json()['detail'])
        elif response.status_code == 403:
            # user doesn't have access to resource
            raise AuthorizationError(response.json()['detail'])
        elif response.status_code == 400:
            # invalid canonical_id
            raise ValueError(response.json()['detail'])

        return response

    def get(self, id: int = None, canonical_id: int = None, query_str: str = None):
        url = self.url
        params = dict()

        if id is not None:
            url = url + f'/{id}'
        else:
            if canonical_id is not None:
                params['canonical_id'] = canonical_id
            if query_str is not None:
                params['query_str'] = query_str
        
        response = self.client.get(url,
                                   params = params)
        
        self._check_common_exceptions(response)
        if response.status_code == 404:
            # alt name(s) not found
            raise NotFoundError(f"{response.json()['detail']}")
        elif response.status_code == 403:
            # user does not have access to resource specified by id
            raise AuthorizationError(f"{response.json()['detail']}")

        return response

    def patch(self, id: int, title: str | None = None, canonical_id: int | None = None):
        response = self.client.patch(self.url + f'/{id}',
                                     json = {'title': title,
                                             'canonical_id': canonical_id})
        self._check_common_exceptions(response)
        if response.status_code == 409:
            # alt name taken
            raise ConflictError(response.json()['detail'])
        elif response.status_code == 404:
            # alt name or specified canonical name not found
            raise NotFoundError(response.json()['detail'])
        elif response.status_code == 403:
            # user does not have access to either specified alt name or specified canonical name
            raise AuthorizationError(response.json()['detail'])

        return response

    def delete(self, id: int):
        response = self.client.delete(self.url + f'/{id}')
        self._check_common_exceptions(response)
        if response.status_code == 404:
            # alt name not found
            raise NotFoundError(response.json()['detail'])
        elif response.status_code == 403:
            # user does not have access to alt name
            raise AuthorizationError(response.json()['detail'])
        elif response.status_code == 409:
            # cannot remove canonical title from alt names
            raise ConflictError(response.json()['detail'])
        return response

class Songs(Endpoint):
    def __init__(self, client):
        super().__init__(client)
        self.url = self.base_url + '/songs'

    def post(self, title: str):
        response = self.client.post(self.url,
                                    json = {'title': title})
        self._check_common_exceptions(response)
        if response.status_code == 409:
            # title taken
            raise ConflictError(f"{response.json()['detail']}")

        return response

    def get(self, id: int = None, query_str: str = None):
        response = None
        if id is not None:
            response = self.client.get(self.url + f'/{id}')
        else:
            params = dict()
            if query_str is not None:
                params['query_str'] = query_str
            response = self.client.get(self.url,
                                       params = params)
        
        self._check_common_exceptions(response)
        if response.status_code == 404:
            # song not found
            raise NotFoundError(f"{response.json()['detail']}")
        elif response.status_code == 403:
            # user does not have access to resource specified by id
            raise AuthorizationError(f"{response.json()['detail']}")
        
        return response
        
    def patch(self, id: int, title: str):
        response = self.client.patch(self.url + f'/{id}',
                                     json = {'title': title})
        self._check_common_exceptions(response)
        if response.status_code == 409:
            # title taken
            raise ConflictError(response.json()['detail'])
        elif response.status_code == 404:
            # resource not found
            raise NotFoundError(response.json()['detail'])
        elif response.status_code == 403:
            # user does not have access to specified canonical name
            raise AuthorizationError(response.json()['detail'])
        return response

    def delete(self, id: int):
        response = self.client.delete(self.url + f'/{id}')
        self._check_common_exceptions(response)
        if response.status_code == 404:
            # song not found
            raise NotFoundError(response.json()['detail'])
        elif response.status_code == 403:
            # user does not have access to song
            raise AuthorizationError(response.json()['detail'])
        return response

    def splinter(self, alt_name_id: int):
        response = self.client.post(self.url + '/splinters',
                                    json = {'alt_name_id': alt_name_id})
        self._check_common_exceptions(response)
        if response.status_code == 404:
            # alt name not found
            raise NotFoundError(response.json()['detail'])
        elif response.status_code == 403:
            # user does not have access to alt name
            raise AuthorizationError(response.json()['detail'])
        elif response.status_code == 409:
            # title taken
            raise ConflictError(f"{response.json()['detail']}")
        return response

    def merge(self, canonical_ids: List[int], priority_id: int):
        response = self.client.post(self.url + '/merges',
                                    json = {'canonical_ids': canonical_ids,
                                            'priority_id': priority_id})
        # check 422 first because this route throws a different type of error message  
        if response.status_code == 422:
            try:
                # if canonical_ids contains more than 5 elements, API sends error response 
                # of the from {'detail': {'message': ...}}
                raise ValueError(response.json()['detail']['message'])
            except KeyError:
                # on usual 422 exception (i.e. wrong input types), defer back to _check_common_exceptions
                pass
        self._check_common_exceptions(response)
        if response.status_code == 404:
            # invalid ids
            raise NotFoundError(response.json()['detail'])
        elif response.status_code == 403:
            # user does not have access to song specified by id
            raise AuthorizationError(response.json()['detail'])
        return response

    def put_video(self, id: int, video_id: str, video_title: str, channel_name: str):
        response = self.client.put(self.url + f'/{id}' + '/videos',
                                   json = {'id': video_id,
                                           'video_title': video_title,
                                           'channel_name': channel_name})
        self._check_common_exceptions(response)
        if response.status_code == 404:
            raise NotFoundError(response.json()['detail'])
        elif response.status_code == 403:
            raise AuthorizationError(response.json()['detail'])
        return response

    def get_video(self, id: int):
        response = self.client.get(self.url + f'/{id}' + '/videos')
        self._check_common_exceptions(response)
        if response.status_code == 404:
            raise NotFoundError(response.json()['detail'])
        elif response.status_code == 403:
            raise AuthorizationError(response.json()['detail'])
        return response

    def delete_video(self, id: int):
        response = self.client.delete(self.url + f'/{id}' + '/videos')
        self._check_common_exceptions(response)
        if response.status_code == 404:
            raise NotFoundError(response.json()['detail'])
        elif response.status_code == 403:
            raise AuthorizationError(response.json()['detail'])
        return response

class Playlists(Endpoint):
    def __init__(self, client):
        super().__init__(client)
        self.url = self.base_url + '/playlists'

    def post(self, title: str, privacy_status: str):
        
        response = self.client.post(self.url,
                                    json = {'title': title,
                                            'privacy_status': privacy_status})
        self._check_common_exceptions(response)
        return response

    def get(self, id: str = None, query_str: str = None):
        url = self.url
        params = dict()
        if id is not None:
            url = self.url + f'/{id}'
        else:
            if query_str is not None:
                params['query_str'] = query_str

        response = self.client.get(url,
                                   params = params)

        self._check_common_exceptions(response)
        if response.status_code == 404:
            raise NotFoundError(response.json()['detail'])
        elif response.status_code == 403:
            raise AuthorizationError(response.json()['detail'])
        return response

    def get_latest(self):
        response = self.client.get(self.url + '/latest')
        self._check_common_exceptions(response)
        if response.status_code == 404:
            raise NotFoundError(response.json()['detail'])
        elif response.status_code == 403:
            raise AuthorizationError(response.json()['detail'])
        return response

    def patch(self, id: str, title: str | None = None, privacy_status: str | None = None):
        if title is None and privacy_status is None:
            return
        response = self.client.patch(self.url + f'/{id}',
                                     json = {'title': title,
                                             'privacy_status': privacy_status})
        self._check_common_exceptions(response)
        if response.status_code == 404:
            raise NotFoundError(response.json()['detail'])
        elif response.status_code == 403:
            raise AuthorizationError(response.json()['detail'])
        return response

    def delete(self, id: str):
        response = self.client.delete(self.url + f'/{id}')
        self._check_common_exceptions(response)
        if response.status_code == 404:
            raise NotFoundError(response.json()['detail'])
        elif response.status_code == 403:
            raise AuthorizationError(response.json()['detail'])
        return response

    def get_items(self, id: str):
        response = self.client.get(self.url + f'/{id}' + '/items')
        self._check_common_exceptions(response)
        if response.status_code == 404:
            raise NotFoundError(response.json()['detail'])
        elif response.status_code == 403:
            raise AuthorizationError(response.json()['detail'])
        return response

    def post_item(self, id: str, video_id: str, pos: int | None = None):
        response = self.client.post(self.url + f'/{id}' + '/items',
                                    json = {'video_id': video_id,
                                            'pos': pos})
        self._check_common_exceptions(response)
        if response.status_code == 404:
            raise NotFoundError(response.json()['detail'])
        elif response.status_code == 403:
            raise AuthorizationError(response.json()['detail'])
        return response

    def patch_item(self, id: str, mode: Literal["Replace", "Move"], sub_details: dict):
        """
        Calls patch method at /playlist/{id}/ route. This is used to replace a video within a playlist
        or adjust its position.
        Args:
            id: id of playlist 
            mode: a string, either "Replace" or "Move", indicating what type of patch to perform.
            sub_details: a dict containing the details used to perform either the replace or move operation.
                - If `mode` is "Replace", then `sub_details` is of the form {'video_id': str, 'pos': int}.
                - If `mode` is "Move", then `sub_details` is of the form {'init_pos': int, 'target_pos': int} 
        """
        response = self.client.patch(self.url + f'/{id}' + '/items',
                                     json = {'mode': mode,
                                             'sub_details': sub_details})
        self._check_common_exceptions(response)
        if response.status_code == 404:
            raise NotFoundError(response.json()['detail'])
        elif response.status_code == 403:
            raise AuthorizationError(response.json()['detail'])
        elif response.status_code == 400:
            raise ValueError(response.json()['detail'])
        return response

    def delete_item(self, id: str, pos: int):
        # need to use .request() because .delete() doesn't accept a request body
        response = self.client.request(method = "DELETE",
                                       url = self.url + f'/{id}' + '/items',
                                       json = {'pos': pos})
        self._check_common_exceptions(response)
        if response.status_code == 404:
            raise NotFoundError(response.json()['detail'])
        elif response.status_code == 403:
            raise AuthorizationError(response.json()['detail'])
        elif response.status_code == 400:
            raise ValueError(response.json()['detail'])
        return response

