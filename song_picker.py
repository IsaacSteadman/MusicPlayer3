from playlist import Playlist
from random import Random
from typing import List


class SongPicker(object):
    def __init__(self, playlist: Playlist, max_ban: int):
        self.playlist = playlist
        self.idx: int = 0
        self.max_ban = max_ban
        self.num_songs = len(playlist.songs)
        self.chances: List[int] = [max_ban] * self.num_songs
        self.total: int = self.chance_mapper(self, self.max_ban) * self.num_songs

    @staticmethod
    def chance_mapper(self: "SongPicker", stage: int) -> int:
        return 1 if stage >= self.max_ban else 0

    def pick(self, rng: Random) -> int:
        selected_idx = self.rand_song_idx(rng)
        self.pick_manual(selected_idx)
        return selected_idx

    def pick_manual(self, selected_idx: int):
        diff_total: int = 0
        for i, stage in enumerate(self.chances):
            if stage < self.max_ban:
                prev = stage
                stage += 1
                diff_total += self.chance_mapper(self, stage) - self.chance_mapper(self, prev)
                self.chances[i] = stage
        prev = self.chances[self.idx]
        stage = 0
        self.chances[self.idx] = 0
        diff_total += self.chance_mapper(self, stage) - self.chance_mapper(self, prev)
        self.total += diff_total
        self.idx = selected_idx
        return self.idx

    def rand_song_idx(self, rng: Random) -> int:
        value = rng.randint(0, self.total - 1)
        partial = 0
        for i, stage in enumerate(self.chances):
            partial += self.chance_mapper(self, stage)
            if partial > value:
                print("select", i)
                selected_idx = i
                break
        else:
            selected_idx = 0
        return selected_idx

    @property
    def cur_song(self) -> str:
        return self.playlist.songs[self.idx]
