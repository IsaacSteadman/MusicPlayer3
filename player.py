#!/usr/bin/env python3.6
import pygame
import os
import random
import json
from typing import List, Optional

from PygGUI2.uix.label import Label, X_ALIGN_LEFT, X_ALIGN_MID, X_ALIGN_RIGHT
from PygGUI2.uix.progressbar import ProgressBar, TooltipInfo
from playlist import load_playlists, Playlist
from song_picker import SongPicker
from pygame.mixer import music
from PygGUI2.pyg_app import App
from PygGUI2.uix.pressbutton import PressButton
from PygGUI2.uix.togglebutton import ToggleButton
from PygGUI2.base.pyg_types import Number, IntPoint, Color
from mp3meta import Mp3Info


base_dir = os.path.dirname(__file__)


try:
    with open(os.path.join(base_dir, "settings.json"), "r") as fl:
        settings = json.load(fl)
except FileNotFoundError:
    settings = {
        "musicDir": ".",
        "volume": 128,
        "max_ban": 12
    }
    with open(os.path.join(base_dir, "settings.json"), "w") as fl:
        json.dump(settings, fl)
    


prev = os.getcwd()
os.chdir(settings["musicDir"])
playlists = load_playlists(os.path.join(settings["musicDir"], "playlists.json"))
os.chdir(prev)


class VolumeControl(Label):
    def __init__(self, pos: IntPoint, fnt: pygame.font.FontType, centered: int):
        self.vol = int(music.get_volume() * 128)
        super().__init__("Vol: %u/128" % self.vol, pos, fnt, centered=centered)

    def on_evt_global(self, app: "PlayerApp", evt: pygame.event.EventType) -> bool:
        if evt.type == pygame.KEYDOWN and evt.mod & pygame.KMOD_CTRL:
            amt = 10 if evt.mod & pygame.KMOD_SHIFT else 1
            vol = self.vol
            if evt.key == pygame.K_DOWN:
                vol = max(0, min(128, vol - amt))
            elif evt.key == pygame.K_UP:
                vol = max(0, min(128, vol + amt))
            if vol != self.vol:
                self.vol = vol
                self.lbl = "Vol: %u/128" % vol
                music.set_volume(self.vol / 128)
                return True
        return False


class PlayerApp(App):
    def __init__(self, surf: pygame.SurfaceType, playlists_obj: List[Playlist], settings_obj: dict, mixer_freq: int):
        super().__init__(surf)
        self.mixer_freq = mixer_freq
        self.playlists = playlists_obj
        self.settings = settings_obj
        vol = settings_obj.get("volume", 128)
        if not isinstance(vol, int):
            print("WARN: expected settings.volume to be an integer")
            vol = 128
        elif vol < 0:
            print("WARN: settings.volume too low (must be non-negative)")
            vol = 0
        elif vol > 128:
            print("WARN: settings.volume too high (must be less than or equal to 128)")
            vol = 128
        music.set_volume(vol)
        self.main_fnt = pygame.font.SysFont("Courier New", 31)
        self.sub_fnt = pygame.font.SysFont("Courier New", 16)
        self.loop_btn = ToggleButton("Loop", (32, 64), self.main_fnt, lst_actions=[None, None], default_state=1)
        self.loop_btn.add_glob_capture(pygame.KEYDOWN, {
            "key": pygame.K_l
        })
        self.song_btn = ToggleButton("Song", (108, 64), self.main_fnt, lst_actions=[None, None], default_state=0)
        self.song_btn.add_glob_capture(pygame.KEYDOWN, {
            "key": pygame.K_s
        })
        self.play_btn = PressButton("Play", self.play_btn_action, (32, 134), self.main_fnt)
        self.play_btn.add_glob_capture(pygame.KEYDOWN, {
            "key": pygame.K_RETURN
        })
        self.pause_btn = ToggleButton(
            "Pause", (32, 169), self.main_fnt,
            lst_actions=[self.unpause_music_action, self.pause_music_action],
            default_state=0
        )
        self.pause_btn.add_glob_capture(pygame.KEYDOWN, {
            "key": pygame.K_SPACE
        })
        self.prog_bar = ProgressBar(
            (64, 240), (512, 4), ((127, 127, 127), (0, 255, 255)), self.prog_bar_action,
            TooltipInfo(
                self.prog_bar_hover, self.sub_fnt, ((127, 127, 127), (0, 255, 255))
            )
        )
        self.time_elapse_lbl = Label("", (64, 244), self.sub_fnt, centered=X_ALIGN_LEFT)
        self.time_left_lbl = Label("", (512 + 64, 244), self.sub_fnt, centered=X_ALIGN_RIGHT)
        self.total_time_lbl = Label("", (64 + 512 // 2, 244), self.sub_fnt, centered=X_ALIGN_MID)
        self.vol_ctrl = VolumeControl((64 + 512 // 2, 244 + 16 + 3), self.sub_fnt, centered=X_ALIGN_MID)
        self.next_in_list_btn = PressButton(
            "Next In Playlist", self.next_in_list_action,
            (64, 244 + 19), self.sub_fnt
        )
        self.next_in_list_btn.add_glob_capture(pygame.KEYDOWN, {
            "key": pygame.K_DOWN,
            "mod!&": pygame.KMOD_CTRL
        })
        self.prev_in_list_btn = PressButton(
            "Prev In Playlist", self.prev_in_list_action,
            (64, 244 + 19 + 35), self.sub_fnt
        )
        self.prev_in_list_btn.add_glob_capture(pygame.KEYDOWN, {
            "key": pygame.K_UP,
            "mod!&": pygame.KMOD_CTRL
        })
        self.prev_5_sec_btn = PressButton(
            "Back 5s", lambda btn, pos: self.seek(-5000), (400, 244 + 19 + 19), self.sub_fnt
        )
        self.prev_5_sec_btn.add_glob_capture(pygame.KEYDOWN, {
            "key": pygame.K_LEFT,
            "mod!&": pygame.KMOD_SHIFT,
            "mod!&": pygame.KMOD_ALT
        })
        self.prev_10_sec_btn = PressButton(
            "Back 10s", lambda btn, pos: self.seek(-10000), (500, 244 + 19 + 19), self.sub_fnt
        )
        self.prev_10_sec_btn.add_glob_capture(pygame.KEYDOWN, {
            "key": pygame.K_LEFT,
            "mod&": pygame.KMOD_SHIFT,
            "mod!&": pygame.KMOD_ALT
        })
        self.skip_5_sec_btn = PressButton(
            "Skip 5s", lambda btn, pos: self.seek(5000), (400, 244 + 19 + 19 + 19), self.sub_fnt
        )
        self.skip_5_sec_btn.add_glob_capture(pygame.KEYDOWN, {
            "key": pygame.K_RIGHT,
            "mod!&": pygame.KMOD_SHIFT,
            "mod!&": pygame.KMOD_ALT
        })
        self.skip_10_sec_btn = PressButton(
            "Skip 10s", lambda btn, pos: self.seek(10000), (500, 244 + 19 + 19 + 19), self.sub_fnt
        )
        self.skip_10_sec_btn.add_glob_capture(pygame.KEYDOWN, {
            "key": pygame.K_RIGHT,
            "mod&": pygame.KMOD_SHIFT,
            "mod!&": pygame.KMOD_ALT
        })
        self.ctls = [
            self.loop_btn,
            self.song_btn,
            self.play_btn,
            self.pause_btn,
            self.prog_bar,
            self.time_elapse_lbl,
            self.time_left_lbl,
            self.total_time_lbl,
            self.vol_ctrl,
            self.next_in_list_btn,
            self.prev_in_list_btn,
            self.prev_5_sec_btn,
            self.prev_10_sec_btn,
            self.skip_5_sec_btn,
            self.skip_10_sec_btn
        ]
        max_ban = self.settings.get("max_ban", 12)
        if not isinstance(max_ban, int):
            max_ban = 12
            print("WARN: expected integer for max_ban in settings.json")
        self.cur_p = SongPicker(self.playlists[0], max_ban)
        self.rng = random.SystemRandom()
        self.cur_song_duration: Number = 1
        self.cur_off: int = 0
        self.dct_global_event_func[pygame.USEREVENT] = self.on_music_done
        self.dct_global_event_func[pygame.USEREVENT + 1] = self.on_tick
        pygame.time.set_timer(pygame.USEREVENT + 1, 1000 // 20)
        self.pick_song()
        self.play_song()

    def on_music_done(self, evt):
        self.next_song()
        return True

    def next_in_list_action(self, btn, pos):
        self.cur_p.pick_manual((self.cur_p.idx + 1) % self.cur_p.num_songs)
        self.play_song()

    def prev_in_list_action(self, btn, pos):
        self.cur_p.pick_manual((self.cur_p.idx - 1) % self.cur_p.num_songs)
        self.play_song()

    def next_song(self):
        if self.loop_btn.cur_state == 0 and self.song_btn.cur_state == 0:
            return
        if self.loop_btn.cur_state and self.song_btn.cur_state:
            pass
        elif self.loop_btn.cur_state:
            self.pick_song()
        elif self.song_btn.cur_state:
            self.cur_p.pick_manual((self.cur_p.idx + 1) % self.cur_p.num_songs)
        self.play_song()

    def on_tick(self, evt):
        self.prog_bar.set_value(self, (self.cur_off + music.get_pos()) / (self.cur_song_duration * 1000))
        pos = (self.cur_off + music.get_pos()) / 1000
        self.time_elapse_lbl.set_lbl(self, "%u:%02u" % divmod(int(pos), 60))
        self.time_left_lbl.set_lbl(self, "%u:%02u" % divmod(int(self.cur_song_duration - pos), 60))
        return True

    @property
    def playing(self) -> bool:
        return self.pause_btn.cur_state == 0

    @playing.setter
    def playing(self, v: bool):
        if self.playing == v:
            return
        self.pause_btn.cur_state = 1 if v else 0
        self.set_redraw(self.pause_btn)

    def prog_bar_action(self, prog_bar, frac: Number):
        pos = int(frac * self.cur_song_duration * 1000)
        self.seek(pos, False)

    def prog_bar_hover(self, prog_bar, frac: Number) -> str:
        pos = int(frac * self.cur_song_duration)
        return "%u:%02u" % divmod(pos, 60)

    def pause_music_action(self, btn, pos):
        music.pause()

    def unpause_music_action(self, btn, pos):
        music.unpause()

    def play_song(self):
        self.cur_off = 0
        with open(self.cur_p.cur_song, "rb") as fl:
            info = Mp3Info(fl)
        self.cur_song_duration = info.duration
        if info.sample_rate != self.mixer_freq:
            print("This file has a different sample rate reloading mixer subsystem with appropriate sample rate")
            prev_end_evt = music.get_endevent()
            prev_volume = music.get_volume()
            pygame.mixer.quit()
            pygame.mixer.init(frequency=info.sample_rate)
            self.mixer_freq = info.sample_rate
            music.set_endevent(prev_end_evt)
            music.set_volume(prev_volume)
            print("Mixer reinitialized with sample_rate = %u" % info.sample_rate)
        self.total_time_lbl.set_lbl(self, "%u:%02u" % divmod(int(self.cur_song_duration), 60))
        try:
            music.load(self.cur_p.cur_song)
            music.play()
            self.cur_off = 0
            print("Playing:", self.cur_p.cur_song)
            self.playing = True
        except Exception as exc:
            print(exc)
            pygame.event.post(pygame.event.Event(pygame.USEREVENT, {}))

    def seek(self, pos: Number = 0, rel: bool = True):
        if rel:
            if pos == 0:
                return
            elif pos > 0:
                self.cur_off += music.get_pos() + pos
                music.play(start=pos / 1000)
                print("relative seek forward by %.15g seconds" % (pos / 1000))
                self.playing = True
                return
            else:
                pos = max(music.get_pos() + self.cur_off + pos, 0)
                print("relative seek backward")
        music.rewind()
        print("seek absolute = %.15g seconds" % (pos / 1000))
        music.play(start=pos / 1000)
        self.playing = True
        self.cur_off = pos

    def pick_song(self):
        self.cur_p.pick(self.rng)

    def play_btn_action(self, btn, pos):
        self.next_song()


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
    # noinspection PyBroadException
    try:
        music.load(cur_p.cur_song)
        music.play()
        cur_off = 0
        print("Playing:", cur_p.cur_song)
        playing = True
    except Exception:
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
                seek(-1000 * (10 if evt.mod & pygame.KMOD_SHIFT else 5))
            elif evt.key == pygame.K_r:
                music.rewind()
                cur_off = 0
        elif evt.type == pygame.KEYDOWN and evt.key == pygame.K_UP:
            cur_p.pick_manual((cur_p.idx - 1) % cur_p.num_songs)
            play_song()


job = 1


if __name__ == "__main__":
    if job == 0:
        cur_p = SongPicker(playlists[0], 12)
        rng = random.SystemRandom()
        cur_p.pick(rng)
        playing = False
        cur_off = 0
        pygame.display.init()
        pygame.display.set_mode((640, 480))
        pygame.mixer.init(frequency=44100)
        music.set_endevent(pygame.USEREVENT)
        cur_p.pick(rng)
        play_song()
        mainloop()
        pygame.quit()
    else:
        pygame.display.init()
        surf = pygame.display.set_mode((640, 480))
        pygame.mixer.init(frequency=44100)
        pygame.font.init()
        music.set_endevent(pygame.USEREVENT)
        app = PlayerApp(surf, playlists, settings, 44100)
        app.run()
        pygame.quit()
