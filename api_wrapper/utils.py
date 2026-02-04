from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs, unquote
from .exceptions import VideoLinkParserError
import pandas as pd
import numpy as np

def search_video(query_string: str, api_key: str):
    """
    Searches for a YouTube video via the YouTube Data API search endpoint.
    Args:
        query_str: the string passed to the YouTube Data API for searching
        api_key: an API key for the YouTube Data API
    Returns:
        dict: a representation of the video resource corresponding to the top search result. This has
        the keys 'id', 'video_title', 'channel_name', and 'link'
    """
    root = 'http://youtu.be/'
    with build('youtube', 'v3', developerKey = api_key) as yt_service:
        request = yt_service.search().list(
            part = "snippet",
            q = query_string,
            type = "video"
        )
        response = request.execute()
        
        top_vid = response['items'][0]

        id = top_vid['id']['videoId']
        title = top_vid['snippet']['title']
        channel = top_vid['snippet']['channelTitle']
        link = root + id
        
        return {'id': id,
                'video_title': title,
                'channel_name': channel,
                'link': link}
    
YOUTUBE_NETLOCS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}

def extract_video_id(url: str, fallback_to_none: bool = False):
    """
    Extract a YouTube video ID from many possible URL formats.
    Args:
        url: the string to be parsed.
        fallback_to_none: a bool. If True, then returns None in the case that the parser fails.
            If False, then raises VideoLinkParserError if no ID can be found.
    """
    if not url or type(url) != str:
        if fallback_to_none:
            return None
        else:
            raise VideoLinkParserError(f"Please try a different link format")

    parsed = urlparse(url)

    # Short links: youtu.be/<id>
    if parsed.netloc in {"youtu.be", "www.youtu.be"}:
        return parsed.path.lstrip("/") or None

    if parsed.netloc not in YOUTUBE_NETLOCS:
        if fallback_to_none:
            return None
        else:
            raise VideoLinkParserError(f"Please try a different link format")

    # Standard watch URLs
    if parsed.path == "/watch":
        return parse_qs(parsed.query).get("v", [None])[0]

    # Nonstandard watch URLs: /watch/<id>
    if parsed.path.startswith("/watch/"):
        return parsed.path.split("/")[2]

    # Embed-style paths
    path_parts = parsed.path.split("/")

    if len(path_parts) >= 3 and path_parts[1] in {
        "embed",
        "v",
        "e",
        "shorts",
        "live",
    }:
        return path_parts[2]

    # oEmbed URLs: ?url=<encoded watch url>
    if parsed.path == "/oembed":
        inner_url = parse_qs(parsed.query).get("url", [None])[0]
        if inner_url:
            return extract_video_id(unquote(inner_url))

    # Attribution links: ?u=<encoded path or url>
    if parsed.path == "/attribution_link":
        u = parse_qs(parsed.query).get("u", [None])[0]
        if u:
            u = unquote(u)
            # u may be a path or full URL
            if u.startswith("/"):
                return extract_video_id(f"https://www.youtube.com{u}")
            return extract_video_id(u)

    # if all else fails, raise exception or return None
    if fallback_to_none:
        return None
    else:
        raise VideoLinkParserError(f"Please try a different link format")

def get_video_details(video_id: str, api_key: str):
    """
    Given a YouTube video id, this method fetches the video title and channel name from YouTube Data API.
    Args:
        video_id: the video's YouTube video id
        api_key: an API key for the YouTube Data API
    Returns:
        dict: a representation of the video resource corresponding to the top search result. This has
        the keys 'id', 'video_title', 'channel_name', and 'link'
    """
    with build('youtube', 'v3', developerKey = api_key) as yt_service:
        request = yt_service.videos().list(
            part = 'id,snippet',
            id = video_id
        )
        response = request.execute()

    result = {'id': video_id,
              'link': 'https://youtu.be' + f'/{video_id}',
              'video_title': response['items'][0]['snippet']['title'],
              'channel_name': response['items'][0]['snippet']['channelTitle']
              }
    
    return result

def process_songs_df(raw_df: pd.DataFrame, api_key: str):
    # rename cols to match param names expected by APIWrapper.create_song()
    raw_df.rename(columns = {'Song': 'title', 'Alt Names': 'alt_names', 'Link': 'video_link'}, inplace = True)
    raw_df.dropna(how = 'all', inplace = True)

    # propogate titles down
    raw_df['title'] = raw_df['title'].ffill()

    # get video id from links
    raw_df['video_id'] = raw_df['video_link'].apply(lambda x: extract_video_id(x, True))

    # group based on title
    grouped_info = raw_df.groupby('title')[['alt_names', 'video_id']].agg({
        'alt_names': lambda x: list(x,) if any(pd.notna(val) for val in x) else None,
        'video_id': lambda x: x.dropna().iloc[0] if x.dropna().any() else None,
    })
    grouped_info.reset_index(inplace = True)

    # take non-None video ids, and get details from YouTube Data API
    # make calls in chunks to prevent rate limiting
    indices = np.array(range(len(grouped_info)))
    mask = grouped_info['video_id'].notna().values
    non_none_indices = indices[mask]
    all_video_ids = grouped_info[mask]['video_id'].values

    video_titles = []
    channel_names = []
    chunk_size = 20
    for i in range((len(all_video_ids) // chunk_size) + 1):
        current_id_chunk = ','.join(all_video_ids[i*chunk_size: (i+1)*chunk_size])
        with build('youtube', 'v3', developerKey = api_key) as yt_service:
            request = yt_service.videos().list(
                part = 'id,snippet',
                id = current_id_chunk
            )
            response = request.execute()
            for item in response['items']:
                video_titles.append(item['snippet']['title'])
                channel_names.append(item['snippet']['channelTitle'])

    grouped_info['video_title'] = None
    grouped_info.loc[non_none_indices, 'video_title'] = video_titles
    grouped_info['channel_name'] = None
    grouped_info.loc[non_none_indices, 'channel_name'] = channel_names

    return grouped_info
