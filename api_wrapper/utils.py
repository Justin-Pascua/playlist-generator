from googleapiclient.discovery import build

def search_video(query_string: str, api_key: str):
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
    
