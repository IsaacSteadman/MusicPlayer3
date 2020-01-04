from typing import List, Optional, Set, Union
from pyfsutils import get_files_exts
import os
import json

class Playlist(object):
    @classmethod
    def from_json(cls, obj: dict):
        return cls(obj["searchPaths"], obj.get("defaultSearchExt", [".mp3"]))
    
    
    def __init__(self, search_paths: Optional[List[str]]=None, search_ext: Optional[Union[List[str], Set[str]]]=None):
        self.search_ext = [".mp3"] if search_ext is None else search_ext
        self.search_paths = [] if search_paths is None else search_paths
        songs: Optional[List[str]] = None
        self.songs = songs

    def find_songs(self):
        # DEFFER TO FS SIDE if connection to FS is high latency
        if self.songs is not None:
            raise ValueError("Songs already found")
        songs = []
        exts = self.search_ext
        for s in self.search_paths:
            path = os.path.abspath(s)
            songs.extend(get_files_exts(path, exts))
        self.songs = songs


def load_playlists(f_name: str) -> List[Playlist]:
    with open(f_name, "r") as fl:
        playlists = json.load(fl)
    playlists1: List[Playlist] = [None] * len(playlists)
    for i in range(len(playlists)):
        playlists1[i] = Playlist.from_json(playlists[i])
        playlists1[i].find_songs()
    return playlists1
