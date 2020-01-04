#!/usr/bin/env python3.6
import pygame
import os
import json
from typing import List
import random
from playlist import load_playlists
import json


base_dir = os.path.dirname(__file__)


with open(os.path.join(base_dir, "settings.json"), "r") as fl:
    settings = json.load(fl)



prev = os.getcwd()
os.chdir(settings["musicDir"])
playlists = load_playlists(os.path.join(settings["musicDir"], "playlists.json"))
os.chdir(prev)


cur_p = playlists[0]
rng = random.SystemRandom()
print('len(cur_p.songs)=',len(cur_p.songs)) 
cur_song_idx = rng.randint(0, len(cur_p.songs) - 1)


pygame.display.init()
pygame.display.set_mode((640, 480))
pygame.mixer.init(frequency=44100)
pygame.mixer.music.set_endevent(pygame.USEREVENT)
pygame.mixer.music.load(cur_p.songs[cur_song_idx])
pygame.mixer.music.play()
print("Playing:", cur_p.songs[cur_song_idx])
playing = True

def back_get(obj, val):
    for k in dir(obj):
        if getattr(obj, k) == val:
            return k
    return "UNKNOWN???"


def playsong(i: int):
    global cur_song_idx
    try:
        pygame.mixer.music.load(cur_p.songs[i])
        pygame.mixer.music.play()
        print("Playing:", cur_p.songs[i])
        playing = True
        cur_song_idx = i
    except:
        pygame.event.post(pygame.event.Event(pygame.USEREVENT))
    

def mainloop():
    global playing, cur_p, rng, cur_song_idx
    while True:
        evt = pygame.event.wait()
        if evt.type == pygame.QUIT:
            break
        elif (evt.type == pygame.KEYDOWN and evt.key == pygame.K_SPACE):
            playing = not playing
            if playing:
                pygame.mixer.music.unpause()
            else:
                pygame.mixer.music.pause()
        elif (evt.type == pygame.KEYDOWN and evt.key == pygame.K_DOWN):
            playsong((cur_song_idx + 1) % len(cur_p.songs))
        elif (evt.type == pygame.KEYDOWN and evt.key == pygame.K_UP):
            playsong((cur_song_idx - 1) % len(cur_p.songs))
        elif evt.type == pygame.USEREVENT or (evt.type == pygame.KEYDOWN and evt.key == pygame.K_RETURN):
            i = rng.randint(0, len(cur_p.songs) - 2)
            if i >= cur_song_idx:
                i += 1
            playsong(i)
mainloop()
pygame.quit()
