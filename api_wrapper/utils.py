from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs, unquote
from .exceptions import VideoLinkParserError

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

def extract_video_id(url: str):
    """
    Extract a YouTube video ID from many possible URL formats.
    Raises VideoLinkParserError if no ID can be found.
    """
    if not url:
        raise VideoLinkParserError(f"Please try a different link format")

    parsed = urlparse(url)

    # Short links: youtu.be/<id>
    if parsed.netloc in {"youtu.be", "www.youtu.be"}:
        return parsed.path.lstrip("/") or None

    if parsed.netloc not in YOUTUBE_NETLOCS:
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

    # if all else fails, raise exception
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

