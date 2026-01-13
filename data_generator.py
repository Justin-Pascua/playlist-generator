import numpy as np
import pandas as pd
from datasets import load_dataset, DatasetDict

import random
from typing import Literal
import re
import json
import os
from dotenv import load_dotenv
load_dotenv()

def get_probabilities_from_original():
    original_data = pd.read_excel('datasets/original_dataset.xlsx')
    original_data.fillna({
        'Date after or before verse': 'After',
        # 'Medley separator type': '\n'
        }, 
        inplace = True)

    p_intro = original_data['Has intro text'].value_counts(normalize = True)['Y']
    p_verse = original_data['Has intro verse'].value_counts(normalize = True)['Y']
    p_date_after = original_data['Date after or before verse'].value_counts(normalize = True)['After']
    p_tag_eng_label = original_data['Has "Taglish" and "English" labels'].value_counts(normalize = True)['Y']
    p_bullet = original_data['Has bullet points'].value_counts(normalize = True)['Y']
    p_singer_label = original_data['Num songs with attached name'].sum()/original_data['Num songs'].sum()

    p_duo = original_data['Num duos'].sum()/original_data['Num songs with attached name'].sum() # probability of duo given song is labeled with singer(s)

    medley_separator_opportunities = original_data['Num songs'].sum()/2 # crude estimate, assumes medleys only consist of 2 songs
    p_medley = original_data['Medley separator count'].sum()/medley_separator_opportunities # probability that two songs are joined as a medley
    medley_sep_counts_by_type = (original_data[['Medley separator type', 'Medley separator count']] # number of times each medley sep occurred
                                .groupby('Medley separator type')
                                .sum())                                
    p_medley_sep_by_type = medley_sep_counts_by_type/original_data['Medley separator count'].sum()  # probability of each medley sep occurring given that a medley sep occurs
    # p_medley_sep_by_type.at['\n', 'Medley separator count'] = 1
    # p_medley_sep_by_type *= p_medley

    p_outro = original_data['Has outro text'].value_counts(normalize = True)['Y']

    result = {
        'p_intro': p_intro,
        'p_verse': p_verse,
        'p_date_after': p_date_after,
        'p_tag_eng_label': p_tag_eng_label,
        'p_bullet': p_bullet,
        'p_singer_label': p_singer_label,
        'p_duo': p_duo,
        'p_medley': p_medley,
        'p_medley_sep_by_type': p_medley_sep_by_type,
        'p_outro': p_outro
    }

    return result

class RandomTextSampler:
    """
    A class which samples batches of random english sentences.
    """
    def __init__(self, dataset: DatasetDict = None):
        """
        Initializes sampler.
        params:
            dataset: a DatasetDict, assumed to be the dataset obtained from
            huggingface.co/datasets/agentlans/expanded-english-sentences. If None, then 
            load_dataset is called to load the dataset from Hugging Face
        """
        self.dataset = None
        if dataset is None:
            filler_text_ds = load_dataset("agentlans/expanded-english-sentences")            
            self.dataset = filler_text_ds['train']
        else:
            self.dataset = dataset['train']
        self.max_unique = len(self.dataset)

    def __call__(self, batch_size: int = 1):
        """
        Returns a list of randomly sampled text.
        params:
            batch_size: number of samples to return. 
        """
        if batch_size < self.max_unique:
            # if number of samples desired is smaller than sample space, then use random.choices
            return random.choices(self.dataset['paragraph'], k = batch_size)
        else:
            # if number of samples desired exceeds size of sample space, 
            # then just return shuffled copies of the sample space 
            # and use random.choices to make up the difference
            result = []
            num_covers = batch_size // self.max_unique
            remainder = batch_size % self.max_unique
            for i in range(num_covers):
                result.extend(self.dataset.shuffle()['paragraph'][:])
            result.extend(random.choices(self.dataset['paragraph'], k = remainder))
            return result

class RandomVerseSampler:
    """
    A class which samples random Bible verses.
    """
    def __init__(self):
        """
        Initializes sampler.
        """
        verses_df = pd.read_json('datasets/cleaned_verses.json', lines = True)
    
        verses_df['address'] = '(' + verses_df['book'] + ' ' + verses_df['chapter'].astype(str) + ':' + verses_df['verse'].astype(str) +')'
        verses_df = verses_df[['text', 'address']]
        
        verses_format1 = '"' + verses_df['text'] + '" - ' + verses_df['address']
        verses_format2 = verses_df['address'] + ': "' + verses_df['text'] + '"'
        
        self.verses = pd.concat([verses_format1, verses_format2]).sample(frac = 1).values

    def __call__(self, batch_size: int = 1):
        """
        Returns a list of randomly sampled verses.
        params:
            batch_size: number of samples to return. 
        """
        return random.choices(self.verses, k = batch_size)

class RandomDateSampler:
    """
    A class for sampling random batches of dates between any two specified years
    """
    def __init__(self, start_yr: int = 1900, end_yr: int = 2999):
        """
        Initializes sampler.
        params:
            start_yr: an int indicating the earliest year that can possibly generated
            end_yr: an int indicating the latest year that can possibly generated
        """
        if start_yr < 0:
            raise ValueError(f"Expected non-negative start_yr, but got {start_yr}")
        if end_yr < 0:
            raise ValueError(f"Expected non-negative end_yr, but got {end_yr}")
        if start_yr > end_yr:
            raise ValueError(f"start_yr must precede or be equal to end_yr")
        
        self.months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December",
                       "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        self.days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31,
                              31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        self.start_yr = start_yr
        self.end_yr = end_yr
    
    def __call__(self, batch_size: int = 1):
        """
        Returns a list of random dates.
        params:
            batch_size: number of samples to return
        """
        return list(self._get_generator(batch_size))

    def _get_generator(self, batch_size: int = 1):
        """
        Helper function for __call__. Returns a generator which yields random dates
        params:
            batch_size: number of samples to return
        """
        for i in range(batch_size):
            month_index = random.randint(0, len(self.months) - 1)
            month = self.months[month_index]
            day = random.randint(1, self.days_in_month[month_index])
            date_str = f"{month} {day:02d}"
            if random.randint(0, 1) == 0:
                year = random.randint(self.start_yr, self.end_yr)
                date_str += ', ' + str(year)
            yield date_str

class RandomSongSampler:
    """
    A class which samples batches of random song titles.
    """
    def __init__(self, dataset_dict: DatasetDict = None):
        """
        Initializes sampler.
        params:
            dataset: a DatasetDict, assumed to be the dataset obtained from
            huggingface.co/datasets/vishnupriyavr/spotify-million-song-dataset. 
            If None, then load_dataset is called to load the dataset from Hugging Face
        """
        self.dataset = None
        if dataset_dict is None:
            song_ds = load_dataset("vishnupriyavr/spotify-million-song-dataset")

            # filter out any songs with separator words in title
            separators = ['medley', 'Medley', '/', '&', 'and', 'And']
            song_ds = song_ds.filter(
                lambda x: 
                not any(sep in x['song'] for sep in separators))
            self.dataset = song_ds['train']
        else:
            self.dataset = dataset_dict['train']
        self.max_unique = len(self.dataset)

    def __call__(self, batch_size: int = 1):
        """
        Returns a list of randomly sampled song titles.
        params:
            batch_size: number of samples to return. 
        """
        if batch_size < self.max_unique:
            # if number of samples desired is smaller than sample space, then use random.choices
            return random.choices(self.dataset['song'], k = batch_size)
        else:
            # if number of samples desired exceeds size of sample space, 
            # then just return shuffled copies of the sample space 
            # and use random.choices to make up the difference
            result = []
            num_covers = batch_size // self.max_unique
            remainder = batch_size % self.max_unique
            for i in range(num_covers):
                result.extend(self.dataset.shuffle()['song'][:])
            result.extend(random.choices(self.dataset['song'], k = remainder))
            return result

class RandomNameSampler:
    """
    A class which randomly samples first names. 
    """
    def __init__(self, names = None):
        """
        Initializes sampler.
        params:
            names: a container of unique names. If None, then names are obtained from a local csv.
        """
        self.names = None
        if names is None:
            names_df = pd.read_csv('datasets/NationalNames.csv')
            names = names_df.sample(1000)['Name'].unique()
            self.names = names
        else:
            self.names = names

    def __call__(self, batch_size: int = 1):
        """
        Returns a list of random names.
        params:
            batch_size: number of samples to return. 
        """
        return random.choices(self.names, k = batch_size)
 
class RandomSepSampler:
    """
    A class for randomly generating separators for songs and names.
    """
    def __init__(self, mode: Literal["medley", "duo"]):
        """
        Initializes sampler.
        params:
            mode: a string, which is either "medley" or "duo." 
            If mode == "medley," then the underlying values are ['&', '/', 'and', 'medley with', 'with'],
            and are weighted by counts from the original dataset.
            If mode == "duo," then the underlying values are ['&', '/'], and are weighted evenly.
        """
        if mode not in ("medley", "duo"):
            raise ValueError(f"Received {mode} for mode, but expected one of {("medley", "duo")}")
        
        self.mode = mode
        self.values = None
        if mode == "medley":
            probabilities = get_probabilities_from_original()
            p_medley_sep_by_type = probabilities['p_medley_sep_by_type']
            self.values = p_medley_sep_by_type.index
            self.weights = p_medley_sep_by_type.values.flatten()
        elif mode == 'duo':
            self.values = ['&', '/']
            self.weights = [0.5, 0.5]

    def __call__(self, batch_size: int = 1):
        """
        Returns a list of random separators.
        params:
            batch_size: number of samples to return. 
        """
        return random.choices(self.values, self.weights, k = batch_size)



rand_text = RandomTextSampler()
rand_verse = RandomVerseSampler()
rand_date = RandomDateSampler()
rand_songs = RandomSongSampler()
rand_medley_sep = RandomSepSampler(mode = 'medley')
rand_names = RandomNameSampler()
rand_duo_sep = RandomSepSampler(mode = 'duo')
p = get_probabilities_from_original()

def generate_preambles(batch_size: int = 1):
    """
    Randomly generates preambles
    params:
        batch_size: number of samples to generate
    """
    intro_batch = np.array(rand_text(batch_size)).reshape(-1, 1)
    verse_batch = np.array(rand_verse(batch_size)).reshape(-1, 1)
    date_batch = np.array(rand_date(batch_size)).reshape(-1, 1)
    preamble_batch = np.column_stack((intro_batch, date_batch, verse_batch, date_batch))

    has_intro = np.random.binomial(1, p = p['p_intro'], size = (batch_size, 1))
    date_after = np.random.binomial(1, p = p['p_date_after'], size = (batch_size, 1))
    has_verse = np.random.binomial(1, p = p['p_verse'], size = (batch_size, 1))
    mask = np.column_stack((has_intro, 1-date_after, has_verse, date_after)).astype(int)
    preamble_batch = np.strings.multiply(preamble_batch, mask)

    preamble_strings = preamble_batch[:, 0] + '\n' + preamble_batch[:, 1] + '\n' + preamble_batch[:, 2] + '\n' + preamble_batch[:, 3]
    preamble_strings = np.char.replace(preamble_strings, '\n\n', '\n')
    preamble_strings = np.char.strip(preamble_strings).astype(object)
    return date_batch, preamble_strings

def generate_unnamed_setlists(batch_size: int = 1, songs_per_setlist: int = 4, return_num_lines: bool = True):
    """
    Randomly generates song setlists not including labels of singers/duos.
    Returns two or three arrays depending on `return_num_lines`. 
    The first is a (`batch_size`, `songs_per_setlist`) array, where the ij-th entry is the title of the j'th song in the i'th setlist.
    The second is a (`batch_size`,) array, where the i'th element is the i'th setlist combined into a single string, including medley separators.
    The third (optional) is a (`batch_size`,) array, where the i'th element is an int indicating the number of lines in the i'th playlist string
    params:
        batch_size: int representing number of setlists to generate
        songs_per_setlist: int representing the number of songs to include in each setlist
        return_num_lines: a bool. If true, then returns an array indicating the number of lines in each setlist string
    """
    # get song names
    # reshape to group songs into setlists
    song_batch = np.array(rand_songs(batch_size*songs_per_setlist), dtype = object).reshape(-1, songs_per_setlist)

    # generate medley separators, and mask out some portion using probability computed from original dataset
    medley_sep_batch = np.array(rand_medley_sep(batch_size*(songs_per_setlist - 1)), dtype = object).reshape(-1, songs_per_setlist - 1)
    medley_sep_batch = ' ' + medley_sep_batch + ' '
    medley_mask = np.random.binomial(n = 1, p = p['p_medley'], size = medley_sep_batch.shape).astype(bool)
    medley_sep_batch[~ medley_mask] = '\n'

    # num of lines in each setlist
    num_lines = songs_per_setlist - medley_mask.astype(int).sum(axis = 1)

    # combine song and medley separators into setlist_batch
    song_and_sep_batch = np.zeros((batch_size, 2*songs_per_setlist - 1), dtype = object)
    song_and_sep_batch[:, 0::2] = song_batch
    song_and_sep_batch[:, 1::2] = medley_sep_batch
    setlist_batch = song_and_sep_batch.sum(axis = 1) + '\n'

    if return_num_lines:
        return song_batch, setlist_batch, num_lines
    else:
        return song_batch, setlist_batch

def generate_singer_labels(batch_size: int = 1):
    """
    Randomly generates singer labels
    params:
        batch_size: number of labels to generate
    """
    # randomly sample song names and separators
    # We generate twice as many as the batch size because a label
    # can possibly have
    name_batch = np.array(rand_names(2*batch_size)).reshape(-1, 2)
    duo_sep_batch = np.array(rand_duo_sep(batch_size)).reshape(-1, 1)

    # array whose rows are of the form [name1, separator, name2]
    assigned_singers_batch = np.empty((batch_size, 3), dtype = name_batch.dtype)
    assigned_singers_batch[:, 0::2] = name_batch
    assigned_singers_batch[:, [1]] = duo_sep_batch

    # create mask whose rows are of the form [1, bernoulli_i, bernoulli_i], 
    # where the 2nd and 3rd columns indicate whether or not to keep second singer
    ones_col = np.ones(batch_size)
    has_second_singer = np.random.binomial(1, p = p['p_duo'], size = (batch_size, 1)) * np.array([1,1])
    is_duo_mask = np.column_stack((ones_col, has_second_singer)).astype(int)

    # apply mask
    assigned_singers_batch = np.strings.multiply(assigned_singers_batch, is_duo_mask)

    # join strings along rows and strip whitespace
    result = assigned_singers_batch[:, 0] + ' ' + assigned_singers_batch[:, 1] + ' ' + assigned_singers_batch[:, 2]
    result = np.char.strip(result)

    return result

def add_labels_to_setlist(setlist_batch: np.ndarray, num_lines: np.ndarray):
    """
    Generates singer labels and applies them to setlist strings.
    params:
        setlist_batch: a 1D array of setlist strings
        num_lines: a 1D array of ints representing the number of lines in each string of `setlist_batch`
    """
    # get singer labels. Mask out some portion using probability computed from original dataset
    singer_labels = ' - ' + generate_singer_labels(batch_size = num_lines.sum()) + '\n'
    singer_mask = np.random.binomial(n = 1, p = p['p_singer_label'], size = singer_labels.shape).astype(bool)
    singer_labels[~ singer_mask] = '\n'

    # combine into one string
    full = setlist_batch.sum()

    # apply singer labels to songs
    singer_label_iter = iter(singer_labels.tolist())
    labeled_songs = re.sub(r'\n', lambda _: next(singer_label_iter), full)

    # split string by lines
    lines = labeled_songs.splitlines(keepends = True)

    partitions = []
    bounds = num_lines.cumsum()
    lower, upper = None, None
    for i in range(len(num_lines)):
        if i == 0:
            lower = 0
            upper = bounds[0]
        else:
            lower = bounds[i-1]
            upper = bounds[i]
        partitions.append(''.join(lines[lower: upper]))

    formatted_setlists = np.array(partitions, dtype = object)
    return formatted_setlists

def generate_named_setlists(batch_size: int = 1, songs_per_setlist: int = 4):
    """
    Randomly generates song setlists including labels of singers/duos.
    Returns two arrays. 
    The first is a (`batch_size`, `songs_per_setlist`) array, where the ij-th entry is the title of the j'th song in the i'th setlist.
    The second is a (`batch_size`,) array, where the i'th element is the i'th setlist combined into a single string, including medley separators.
    params:
        batch_size: int representing number of setlists to generate
        songs_per_setlist: int representing the number of songs to include in each setlist
    """
    setlist_songs, setlist_strings, num_lines = generate_unnamed_setlists(batch_size, songs_per_setlist, True)
    setlist_strings = add_labels_to_setlist(setlist_strings, num_lines)
    return setlist_songs, setlist_strings

def generate_outros(batch_size: int = 1):
    """
    Randomly generate random text for outros
    """
    outro_batch = np.array(rand_text(batch_size), dtype = object)
    outro_mask = np.random.binomial(n = 1, p = p['p_outro'], size = batch_size).astype(bool)
    outro_batch[~outro_mask] = ''
    return outro_batch

def generate_positive_data(batch_size: int = 1, songs_per_setlist: int = 4):
    """
    Generate artificial data for training model. Returns array of artificial messages
    and array of targets
    params:
        batch_size: number of samples to generate
        songs_per_setlist: number of songs in each setlist
    """
    date_batch, preamble_batch = generate_preambles(batch_size)

    setlist_song_batch, setlist_string_batch = generate_named_setlists(2*batch_size, songs_per_setlist)
    # axis 1: batch num, axis 2: Taglish or English, axis 3: song num
    setlist_song_batch = setlist_song_batch.reshape(batch_size, 2, songs_per_setlist)
    setlist_string_batch = setlist_string_batch.reshape(batch_size, 2)

    outro_batch = generate_outros(batch_size)

    X = preamble_batch + '\n\nTaglish\n' + setlist_string_batch[:, 0] + '\nEnglish\n' + setlist_string_batch[:, 1] + '\n' + outro_batch
    y = np.concat([date_batch, setlist_song_batch[: , 0], setlist_song_batch[:, 1]], axis = 1)

    return X, y

def generate_tampered_text(batch_size: int = 1):
    """
    Samples paragraphs using `RandomTextSampler`, and randomly inserts newline characters
    into each string.
    params:
        batch_size: number of samples to return. 
    """
    result = []
    text_batch = rand_text(batch_size)
    for raw_text in text_batch:
        chars = list(raw_text)
        num_inserts = np.random.binomial(n = 5, p = 0.5)
        insert_indices = random.sample(range(len(chars)), k = num_inserts)
        for i in insert_indices:
            chars[i] = '\n'
        result.append(''.join(chars))
    return result
        
def generate_negative_data(batch_size: int = 1):
    """
    Generates text that does not contain a setlist of songs.
    params:
        batch_size: number of samples to return.
    """
    tampered_text = np.array(generate_tampered_text(2*batch_size), dtype = object).reshape(-1, 2)
    dates = ' ' + np.array(rand_date(batch_size), dtype = object) + ' '
    
    stacked = np.column_stack((tampered_text[:, 0], dates, tampered_text[:, 1]))
    negatives = stacked.sum(axis = 1)
    targets = np.full_like(negatives, "negative")
    
    return negatives, targets

def output_formatter(raw: list | str):
    """
    Converts a target created by `generate_positive_data` or `generate_negative_data`
    into a string of the form "Date: <DATE> \nSongs: <SONG1> | ... | <SONGn>"
    params: 
        raw: a list or string representing a target generated by `generate_positive_data` or `generate_negative_data`
    """
    if type(raw) != list:
        raw = ['None', 'None']
        
    output_str = f'Date: {raw[0]} \nSongs: {' | '.join(song for song in raw[1:])}'
    return output_str

def write_dummy_data(batch_size: int = 1, songs_per_setlist: int = 4, path: str = 'datasets/data.jsonl', mode = 'a',
                     include_negatives: bool = True, negatives_frac: float = 0.3, format_targets: bool = True):
    """
    Generates dummy data and writes/appends to a .jsonl file.
    params:
        batch_size: number of samples to generate.
        songs_per_setlist: number of songs to generate in each setlist.
        path: a string indicating the path of the file to append to or create. This is assumed to end in '.jsonl'
        mode: mode to pass to open(). This should be "a" or "w".
        include_negatives: a bool indicating whether or not to generate negative data (i.e. text not containing a song setlist).
        negatives_frac: a float between 0 and 1 indicating what portion of the `batch_size` should be used to create negative samples. 
    """
    if mode not in ['a', 'w']:
        raise ValueError(f'Mode must be one "a" or "w" for writing data')
    if type(include_negatives) != bool:
        raise TypeError(f"include_negatives must be a boolean")
    if negatives_frac < 0 or negatives_frac > 1:
        raise ValueError(f"negatives_frac must be a number in [0, 1]")
    if type(path) != str:
        raise TypeError(f"path must be a string")
    if not path.endswith('.jsonl'):
        raise ValueError(f"path must end in '.jsonl'")

    X, y = None, None
    if not include_negatives:
        X, y = generate_positive_data(batch_size, songs_per_setlist)
        X = X.tolist()
        y = y.tolist()
    else:
        num_negatives = int(batch_size*negatives_frac)
        num_positives = batch_size - num_negatives
        negative_X, negative_y = generate_negative_data(num_negatives)
        positive_X, positive_y = generate_positive_data(num_positives, songs_per_setlist)
        X = negative_X.tolist() + positive_X.tolist()
        y = negative_y.tolist() + positive_y.tolist()

    if format_targets:
        y = [output_formatter(item) for item in y]

    with open(path, mode, encoding = 'utf-8') as f:
        for i in range(len(X)):
            sample = {'X': X[i], 'y': y[i]}
            f.write(json.dumps(sample) + '\n')

def read_dummy_data_ds(path: str = 'datasets/data.jsonl', shuffle: bool = True):
    """
    Reads dummy data into a DatasetDict
    params:
        path: a string indicating the path of the file to read. This is assumed to end in '.jsonl'
        shuffle: a bool indicating whether or not to shuffle the data before returning
    """
    
    if type(path) != str:
        raise TypeError(f"path must be a string")
    if not path.endswith('.jsonl'):
        raise ValueError(f"path must end in '.jsonl'")

    ds = load_dataset(path = 'json', data_files = path, split = 'train')
    if shuffle:
        ds = ds.shuffle()

    # split full dataset into 80% train, 20% val + test
    split1 = ds.train_test_split(0.2, shuffle = shuffle)
    ds_train = split1['train']
    ds_test_and_val = split1['test']

    # split val + test into 10% val, 10% test
    split2 = ds_test_and_val.train_test_split(0.5, shuffle = shuffle)
    ds_val = split2['train']
    ds_test = split2['test']

    ds_dict = DatasetDict({
        'train': ds_train,
        'valid': ds_val,
        'test': ds_test
    })

    return ds_dict

def read_dummy_data_df(path: str = 'datasets/data.jsonl', shuffle: bool = True):
    """
    Reads dummy data into a Dataframe
    params:
        path: a string indicating the path of the file to read. This is assumed to end in '.jsonl'
        shuffle: a bool indicating whether or not to shuffle the data before returning
    """
    df = pd.read_json(path, orient = 'records', lines = True)
    
    if shuffle:
        df = df.sample(frac = 1).reset_index(drop = True)
    return df