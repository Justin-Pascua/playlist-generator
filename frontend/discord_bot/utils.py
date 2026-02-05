import pandas as pd
import numpy as np
from typing import List

def json_songs_to_df(songs: List[dict]):
    """
    Converts a list of dicts of song responses into a dataframe. Used for /export-songs command
    Args:
        songs: a list of songs as returned by the main API
    """
    # flatten into rows
    rows = []
    for song in songs:
        canonical_title = song['title']
        link = song['link']
        for item in song['alt_names']:
            alt_title = item['title']
            if alt_title == canonical_title:
                if len(song['alt_names']) > 1:
                    continue
                else:
                    alt_title = None
            rows.append((canonical_title, alt_title, link))

    # construct df and process to match format specified by guide 
    df = pd.DataFrame(data = rows, columns = ['Song', 'Alt Names', 'Link'])
    df = df.sort_values(by = ['Song', 'Alt Names'], ascending = [True, True], 
                        key = lambda col: col.str.lower())
    dup_mask = df.duplicated(subset = 'Song', keep = 'first')
    df.loc[dup_mask, ['Song', 'Link']] = None
    return df


MAX_MESSAGE_LEN = 2000
def partition_song_summary_str(full_output_str: str, slack: int):
    """
    Partitions a string into chunks (separated by '\\n\\n') and merges them such that
    each merged chunk is no longer than 2000 characters. Returns a list of strings.
    Args:
        full_output_str: the string to be partitioned
        slack: an int which is subtracted the maximum message length. This is used to ensure
            that each message does not exceed 2000 - slack characters
    """
    constraint = MAX_MESSAGE_LEN - slack

    # chop full message into chunks split by \n\n
    chunks = full_output_str.split('\n\n')
    merged_chunks = []

    # greedy merging
    current = ""
    for chunk in chunks:
        sep = "\n\n" if current else ""
        if len(current) + len(sep) + len(chunk) <= constraint:
            current += sep + chunk
        else: 
            merged_chunks.append(current)
            current = chunk
    if current:
        merged_chunks.append(current)

    return merged_chunks