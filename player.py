#!/usr/bin/env python3.6
import pygame
import os
import random
from playlist import load_playlists
from song_picker import SongPicker
from pygame.mixer import music
import json


base_dir = os.path.dirname(__file__)


with open(os.path.join(base_dir, "settings.json"), "r") as fl:
    settings = json.load(fl)


prev = os.getcwd()
os.chdir(settings["musicDir"])
playlists = load_playlists(os.path.join(settings["musicDir"], "playlists.json"))
os.chdir(prev)


cur_p = SongPicker(playlists[0], 12)
rng = random.SystemRandom()
cur_p.pick(rng)
playing = False

cur_off = 0


def seek(pos: float = 0, rel: bool = True):
    global cur_off
    if rel:
        if pos == 0:
            return
        elif pos > 0:
            cur_off += music.get_pos() + pos
            music.play(start=pos/1000)
            return
        else:
            pos = max(music.get_pos() + cur_off + pos, 0)
            print("relative seek backward absolute=", pos)
    music.rewind()
    music.play(start=pos/1000)
    cur_off = pos


def play_song():
    global playing, cur_off
    try:
        music.load(cur_p.cur_song)
        music.play()
        cur_off = 0
        print("Playing:", cur_p.cur_song)
        playing = True
    except:
        pygame.event.post(pygame.event.Event(pygame.USEREVENT, {}))


def mainloop():
    global playing, rng, cur_off
    while True:
        evt = pygame.event.wait()
        if evt.type == pygame.QUIT:
            break
        elif evt.type == pygame.USEREVENT:
            print("Next song (REASON: USEREVENT)")
            cur_p.pick(rng)
            play_song()
        elif evt.type == pygame.KEYDOWN:
            if evt.key == pygame.K_RETURN:
                print("Next song (REASON: K_RETURN)")
                cur_p.pick(rng)
                play_song()
            elif evt.key == pygame.K_SPACE:
                playing = not playing
                if playing:
                    music.unpause()
                else:
                    music.pause()
            elif evt.key == pygame.K_DOWN:
                cur_p.pick_manual((cur_p.idx + 1) % cur_p.num_songs)
                play_song()
            elif evt.key == pygame.K_UP:
                cur_p.pick_manual((cur_p.idx - 1) % cur_p.num_songs)
                play_song()
            elif evt.key == pygame.K_RIGHT:
                seek(10000 if evt.mod & pygame.KMOD_SHIFT else 5000)
            elif evt.key == pygame.K_LEFT:
                seek(-1000 *(10 if evt.mod & pygame.KMOD_SHIFT else 5))
            elif evt.key == pygame.K_r:
                music.rewind()
                cur_off = 0
        elif evt.type == pygame.KEYDOWN and evt.key == pygame.K_UP:
            cur_p.pick_manual((cur_p.idx - 1) % cur_p.num_songs)
            play_song()


if __name__ == "__main__":
    pygame.display.init()
    pygame.display.set_mode((640, 480))
    pygame.mixer.init(frequency=44100)
    music.set_endevent(pygame.USEREVENT)
    cur_p.pick(rng)
    play_song()
    mainloop()
    pygame.quit()
