#!/usr/bin/env python3.6
import pygame
import os
import random
import json
import time
from threading import Thread
from typing import List, Optional, Tuple, Sequence

from PygGUI2.uix.label import Label, X_ALIGN_LEFT, X_ALIGN_MID, X_ALIGN_RIGHT
from PygGUI2.uix.progressbar import ProgressBar, TooltipInfo
from playlist import load_playlists, Playlist
from song_picker import SongPicker
from pygame.mixer import music
from PygGUI2.pyg_app import App
from PygGUI2.uix.pressbutton import PressButton
from PygGUI2.uix.togglebutton import ToggleButton
from PygGUI2.base.pyg_types import Number, IntPoint, Color
from PygGUI2.uix.pyg_ctl import PygCtl
from mp3meta import Mp3Info
import find_SDL_Mixer
import ctypes
from math import log2


base_dir = os.path.dirname(__file__)


if os.name == "posix":
    fmp = ctypes.CDLL(os.path.join(base_dir, "linux", "libFastMusicPlayer.so"))
elif os.name == "nt":
    fmp = ctypes.CDLL(os.path.join(base_dir, "win32", "FastMusicPlayer.dll"))
    PROCESS_PER_MONITOR_DPI_AWARE = 2
    shcore = ctypes.windll.shcore
    shcore.SetProcessDpiAwareness.argtypes = [ctypes.c_size_t]
    shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)
else:
    raise OSError("Unsupported OS '%s'" % os.name)


fmp.get_sdl_mixer_registered.restype = ctypes.c_void_p
fmp.get_sdl_mixer_registered.argtypes = []
fmp.fft.restype = None
fmp.fft.argtypes = [ctypes.POINTER(ctypes.c_double), ctypes.c_size_t]
fmp.fill_output_buf.restype = ctypes.c_bool
fmp.fill_output_buf.argtypes = [ctypes.POINTER(ctypes.c_double)]
fmp.thread_function.restype = None
fmp.thread_function.argtypes = []
fmp.fmp_init.restype = ctypes.c_bool
fmp.fmp_init.argtypes = [ctypes.c_size_t, ctypes.c_double]
fmp.fmp_shutdown.restype = ctypes.c_bool
fmp.fmp_shutdown.argtypes = []
fmp.get_total_bytes_out.restype = ctypes.c_size_t
fmp.get_total_bytes_out.argtypes = []
fmp.get_expected_out_buf_size.restype = ctypes.c_size_t
fmp.get_expected_out_buf_size.argtypes = []
fmp.fmp_pause.restype = None
fmp.fmp_pause.argtypes = []
fmp.fmp_unpause.restype = None
fmp.fmp_unpause.argtypes = []


try:
    with open(os.path.join(base_dir, "settings.json"), "r") as fl:
        settings = json.load(fl)
except FileNotFoundError:
    settings = {
        "musicDir": ".",
        "volume": 128,
        "max_ban": 12,
        "size": "normal"
    }
    with open(os.path.join(base_dir, "settings.json"), "w") as fl:
        json.dump(settings, fl)
    

prev = os.getcwd()
os.chdir(settings["musicDir"])
playlists = load_playlists(os.path.join(settings["musicDir"], "playlists.json"))
os.chdir(prev)


RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


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


# horizontal data visualizer
#   an array of numbers are displayed across the x axis
#   with vertical bars representing their magnitudes
#   this control accepts pre-normalized input (values between 0 and 1 inclusive)
class VisualizerControl(PygCtl):
    def __init__(self, height: int, width: int, bar_width: int, pos: Tuple[int, int], zero_color: Color, one_color: Color):
        super().__init__()
        self.height = height
        self.width = width
        self.tot_rect = pygame.Rect(pos, (width, height))
        self.pos = pos
        self.zero_color = zero_color
        self.one_color = one_color
        self.bar_width = bar_width
        self.data = [0.0] * (width // bar_width)
    
    # only uses __len__ and __getitem__
    def update_data(self, app: "PlayerApp", data: Sequence[float], start: Optional[int]=None, end: Optional[int]=None, step: Optional[int]=None):
        if start is None:
            start = 0
        if end is None:
            end = len(data)
        if step is None:
            step = 1
        end = min(end, (start + len(self.data)) * step)
        for self_idx, i in enumerate(range(start, end, step)):
            self.data[self_idx] = max(0.0, min(1.0, data[i]))
        app.set_redraw(self)
    
    def draw(self, app: "PlayerApp"):
        Rect = pygame.Rect
        zr, zg, zb = self.zero_color
        yr, yg, yb = self.one_color
        posx, posy = self.pos
        height = self.height
        bottom = posy + height
        bw = self.bar_width
        for i, v in enumerate(self.data):
            xr = max(0, min(255, int(v * yr + (1 - v) * zr)))
            xg = max(0, min(255, int(v * yg + (1 - v) * zg)))
            xb = max(0, min(255, int(v * yb + (1 - v) * zb)))
            app.surf.fill((xr, xg, xb), Rect((i * bw + posx, bottom - int(height * v)), (bw, int(height * v))))
        return [self.tot_rect]
    
    def pre_draw(self, app: "PlayerApp"):
        return [app.draw_background_rect(self.tot_rect)]


def bound_int(v: float, mn: int, mx: int) -> int:
    return min(mx, max(mn, int(v)))


def linear_mix(a: float, pt0: float, pt1: float) -> float:
    return (1 - a) * pt0 + a * pt1


def linear_multi_mix(a: float, data: List[float]) -> float:
    assert len(data) >= 2
    return  linear_mix(a, data[0], data[1]) + sum(data[1:-1])/float(len(data) - 1)


class VisualizerControl2(PygCtl):
    def __init__(self, height: int, width: int, bar_width: int, num_points: int, pos: Tuple[int, int], zero_color: Color, one_color: Color):
        super().__init__()
        self.height = height
        self.width = width
        self.tot_rect = pygame.Rect(pos, (width, height))
        self.pos = pos
        self.zero_color = zero_color
        self.one_color = one_color
        self.bar_width = bar_width
        self.data = [0.0] * num_points
        self.zero_idx = 1
        self.prev_time = 0
        self.max_idx = len(self.data) - 1
        self.single_mix = linear_mix
        self.multi_mix = linear_multi_mix
        start = 1
        stop = num_points
        scale_start = log2(start)
        scale_stop = log2(stop)
        scale_step = (scale_stop - scale_start) / width
        self.lst_pt_ranges = [
            (
                max(0, 2 ** ((x - 0.5) * scale_step) * start),
                min(num_points - 1, 2 ** ((x + 0.5) * scale_step) * start)
            )
            for x in range(width // bar_width)
        ]
    
    def get_at_pt(self, pt: float) -> float:
        data = self.data
        l_pt = int(pt)
        if 0 <= pt < len(data) and pt == l_pt:
            return data[pt]
        a = pt - l_pt
        u_pt = int(pt) + 1
        l_v = self.get_at_pt(l_pt)
        u_v = self.get_at_pt(u_pt)
        return self.single_mix(a, l_v, u_v)
    
    def get_at_pt_range(self, pt0: float, pt1: float) -> float:
        ipt0 = int(pt0)
        ipt1 = int(pt1)
        if ipt0 == ipt1:
            return (self.get_at_pt(pt0) + self.get_at_pt(pt1)) / 2.0
        a = pt0 - ipt0
        return self.multi_mix(a, self.data[ipt0:ipt1 + 1])
    
    # only uses __len__ and __getitem__
    def update_data(self, app: "PlayerApp", data: Sequence[float], start: Optional[int]=None, end: Optional[int]=None, step: Optional[int]=None):
        if start is None:
            start = 0
        if end is None:
            end = len(data)
        if step is None:
            step = 1
        end = min(end, (start + len(self.data)) * step)
        for self_idx, i in enumerate(range(start, end, step)):
            self.data[self_idx] = max(0.0, min(1.0, data[i]))
        app.set_redraw(self)
    
    def draw(self, app: "PlayerApp"):
        Rect = pygame.Rect
        zr, zg, zb = self.zero_color
        yr, yg, yb = self.one_color
        posx, posy = self.pos
        height = self.height
        bottom = posy + height
        bw = self.bar_width
        data = self.data
        current = time.time()
        disp = current - self.prev_time > 15
        if disp:
            self.prev_time = current
        disp = False
        for x, (pt0, pt1) in enumerate(self.lst_pt_ranges):
            v = self.get_at_pt_range(pt0, pt1)
            if v < 0:
                v = 0
            elif v > 1:
                v = 1
            xr = bound_int(v * yr + (1 - v) * zr, 0, 255)
            xg = bound_int(v * yg + (1 - v) * zg, 0, 255)
            xb = bound_int(v * yb + (1 - v) * zb, 0, 255)
            app.surf.fill((xr, xg, xb), Rect((x * bw + posx, bottom - int(height * v)), (bw, int(height * v))))
        return [self.tot_rect]
    
    def pre_draw(self, app: "PlayerApp"):
        return [app.draw_background_rect(self.tot_rect)]
    
    def on_evt_global(self, app: "PlayerApp", evt):
        if evt.type == pygame.VIDEORESIZE:
            width, height = evt.size
            self.height = min(256, max(64, height - 416))
            self.pos = (0, height - self.height)
            self.width = width
            self.tot_rect = pygame.Rect(self.pos, (self.width, self.height))
            start = 1
            stop = len(self.data)
            scale_start = log2(start)
            scale_stop = log2(stop)
            scale_step = (scale_stop - scale_start) / width
            self.lst_pt_ranges = [
                (
                    max(0, 2 ** ((x - 0.5) * scale_step) * start),
                    min(stop - 1, 2 ** ((x + 0.5) * scale_step) * start)
                )
                for x in range(self.width // self.bar_width)
            ]
            print("resize", evt.size)
            app.on_resize(evt.size)
            return True
        return False


def thread_function_runner():
    fmp.thread_function()
    print("Thread is dead")


class PlayerApp(App):
    def __init__(self, surf: pygame.SurfaceType, playlists_obj: List[Playlist], size_code: int, settings_obj: dict, mixer_freq: int):
        super().__init__(surf)
        self.mixer_freq = mixer_freq
        self.playlists = playlists_obj
        self.settings = settings_obj
        self.fx_cb = fmp.get_sdl_mixer_registered()
        self.num_fft_points = 2048
        self.size_code = size_code
        fmp.fmp_init(self.num_fft_points, 44100.0);
        self.expected_bytes = fmp.get_expected_out_buf_size()
        self.fft_out_buf = (ctypes.c_double * (self.expected_bytes // ctypes.sizeof(ctypes.c_double)))();
        self.fft_counters = (ctypes.c_size_t * 3)();
        self.thread = Thread(target=thread_function_runner,args=())
        self.thread.start()
        self.visual_left = VisualizerControl2(64 if size_code != SIZE_LARGER else 256, 512 if size_code != SIZE_LARGER else 1024, 1, (self.num_fft_points >> 1) - 1, (320 - 256, 480 - 64), BLUE, GREEN)
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
        width = 1024 if size_code == SIZE_LARGER else 512
        self.prog_bar = ProgressBar(
            (64, 240), (width, 4), ((127, 127, 127), (0, 255, 255)), self.prog_bar_action,
            TooltipInfo(
                self.prog_bar_hover, self.sub_fnt, ((127, 127, 127), (0, 255, 255))
            )
        )
        self.time_elapse_lbl = Label("", (64, 244), self.sub_fnt, centered=X_ALIGN_LEFT)
        self.time_left_lbl = Label("", (width + 64, 244), self.sub_fnt, centered=X_ALIGN_RIGHT)
        self.total_time_lbl = Label("", (64 + width // 2, 244), self.sub_fnt, centered=X_ALIGN_MID)
        self.vol_ctrl = VolumeControl((64 + width // 2, 244 + 16 + 3), self.sub_fnt, centered=X_ALIGN_MID)
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
        self.prev_in_hist_btn = PressButton(
            "Prev Song", self.prev_song_action,
            (64, 244 + 19 + 35 + 35), self.sub_fnt
        )
        self.prev_in_hist_btn.add_glob_capture(pygame.KEYDOWN, {
            "key": pygame.K_LEFT,
            "mod!&": pygame.KMOD_SHIFT,
            "mod&": pygame.KMOD_ALT
        })
        self.next_in_hist_btn = PressButton(
            "Next Song", self.next_song_action,
            (64, 244 + 19 + 35 + 35 + 35), self.sub_fnt
        )
        self.next_in_hist_btn.add_glob_capture(pygame.KEYDOWN, {
            "key": pygame.K_RIGHT,
            "mod!&": pygame.KMOD_SHIFT,
            "mod&": pygame.KMOD_ALT
        })
        self.loop_btn.lst_colors = [(BLUE, WHITE), (GREEN, BLACK)]
        self.song_btn.lst_colors = [(BLUE, WHITE), (GREEN, BLACK)]
        self.play_btn.off_color = (BLUE, WHITE)
        self.play_btn.on_color = (GREEN, BLACK)
        self.pause_btn.lst_colors = [(BLUE, WHITE), (GREEN, BLACK)]
        self.next_in_list_btn.off_color = (BLUE, WHITE)
        self.next_in_list_btn.on_color = (GREEN, BLACK)
        self.prev_in_list_btn.off_color = (BLUE, WHITE)
        self.prev_in_list_btn.on_color = (GREEN, BLACK)
        self.prev_5_sec_btn.off_color = (BLUE, WHITE)
        self.prev_5_sec_btn.on_color = (GREEN, BLACK)
        self.prev_10_sec_btn.off_color = (BLUE, WHITE)
        self.prev_10_sec_btn.on_color = (GREEN, BLACK)
        self.skip_5_sec_btn.off_color = (BLUE, WHITE)
        self.skip_5_sec_btn.on_color = (GREEN, BLACK)
        self.skip_10_sec_btn.off_color = (BLUE, WHITE)
        self.skip_10_sec_btn.on_color = (GREEN, BLACK)
        self.prev_in_hist_btn.off_color = (BLUE, WHITE)
        self.prev_in_hist_btn.on_color = (GREEN, BLACK)
        self.next_in_hist_btn.off_color = (BLUE, WHITE)
        self.next_in_hist_btn.on_color = (GREEN, BLACK)
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
            self.skip_10_sec_btn,
            self.prev_in_hist_btn,
            self.next_in_hist_btn,
            self.visual_left
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
        self.tps = 50
        self.exp_tick_t = 1.0 / self.tps
        self.tick_num = 0
        self.record_busy_time_interval = 2.0
        pygame.time.set_timer(pygame.USEREVENT + 1, 1000 // self.tps)
        # self.pick_song()
        song_idx = 0
        for song_idx, song_name in enumerate(self.cur_p.playlist.songs):
            if song_name.endswith("Stardust.fast.mp3"):
                break
        self.cur_p.pick_manual(song_idx)
        self.song_hist_idx = 0
        self.song_hist = [self.cur_p.idx]
        self.SDL_mixer = find_SDL_Mixer.ctypes.CDLL(find_SDL_Mixer.find_sdl_mixer_name())
        self.SDL_mixer.Mix_UnregisterEffect.restype = ctypes.c_int
        self.SDL_mixer.Mix_UnregisterEffect.argtypes = [ctypes.c_int, ctypes.c_void_p]
        self.SDL_mixer.Mix_RegisterEffect.restype = ctypes.c_int
        self.SDL_mixer.Mix_RegisterEffect.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        self.play_song()

    def on_resize(self, size: Tuple[int, int]):
        width, height = size
        self.time_left_lbl.set_lbl(self, self.time_left_lbl.lbl, pos=(width - 128 + 64, 244))
        self.total_time_lbl.set_lbl(self, self.total_time_lbl.lbl, pos=(64 + (width - 128) // 2, 244))
        self.vol_ctrl.set_lbl(self, self.vol_ctrl.lbl, pos=(64 + (width - 128) // 2, 244 + 16 + 3))
        self.prog_bar.set_pos_size(self, None, (width - 128, 4))

    def on_music_done(self, evt):
        self.next_song()
        return True

    def next_in_list_action(self, btn, pos):
        self.cur_p.pick_manual((self.cur_p.idx + 1) % self.cur_p.num_songs)
        self.log_song_hist()
        self.play_song()

    def prev_in_list_action(self, btn, pos):
        self.cur_p.pick_manual((self.cur_p.idx - 1) % self.cur_p.num_songs)
        self.log_song_hist()
        self.play_song()
    
    def log_song_hist(self):
        if self.song_hist[self.song_hist_idx] == self.cur_p.idx:
            self.song_hist[self.song_hist_idx + 1:] = []
            return
        self.song_hist_idx += 1
        self.song_hist[self.song_hist_idx:] = [self.cur_p.idx]

    def prev_song_action(self, btn, pos):
        song_hist_idx = max(0, self.song_hist_idx - 1)
        if self.song_hist_idx == song_hist_idx:
            return
        self.song_hist_idx = song_hist_idx
        self.cur_p.pick_manual(self.song_hist[song_hist_idx])
        self.play_song()

    def next_song_action(self, btn, pos):
        song_hist_idx = min(len(self.song_hist) - 1, self.song_hist_idx + 1)
        if self.song_hist_idx == song_hist_idx:
            return
        self.song_hist_idx = song_hist_idx
        self.cur_p.pick_manual(self.song_hist[song_hist_idx])
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
        self.log_song_hist()
        self.play_song()

    def on_tick(self, evt):
        self.tick_num += 1
        if self.tick_num % 5 == 0:
            self.prog_bar.set_value(self, (self.cur_off + music.get_pos()) / (self.cur_song_duration * 1000))
            pos = (self.cur_off + music.get_pos()) / 1000
            self.time_elapse_lbl.set_lbl(self, "%u:%02u" % divmod(int(pos), 60))
            self.time_left_lbl.set_lbl(self, "%u:%02u" % divmod(int(self.cur_song_duration - pos), 60))
        if fmp.get_total_bytes_out() >= self.expected_bytes:
            if not fmp.fill_output_buf(self.fft_out_buf):
                print("False")
            else:
                out_buf = self.fft_out_buf
                if self.num_recorded > 10 and self.non_busy_time < 0.005:
                    print("Dropped a tick %u" % self.tick_num)
                    return True
                self.visual_left.update_data(self, out_buf, 1, self.num_fft_points >> 1)
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
        self.pause()
    
    def pause(self):
        fmp.fmp_pause()
        music.pause()

    def unpause_music_action(self, btn, pos):
        self.unpause()
    
    def unpause(self):
        fmp.fmp_unpause()
        music.unpause()

    def play_song(self):
        self.cur_off = 0
        while True:
            try:
                with open(self.cur_p.cur_song, "rb") as fl:
                    info = Mp3Info(fl)
            except:
                self.next_song()
            else:
                break
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
            pygame.display.set_caption("Music Player - " + self.cur_p.cur_song.replace("\\", "/").rsplit("/", 1)[-1])
            self.playing = True
        except Exception as exc:
            print(exc)
            pygame.event.post(pygame.event.Event(pygame.USEREVENT, {}))
        self.SDL_mixer.Mix_UnregisterEffect(find_SDL_Mixer.MIX_CHANNEL_POST, self.fx_cb)
        self.SDL_mixer.Mix_RegisterEffect(find_SDL_Mixer.MIX_CHANNEL_POST, self.fx_cb, 0, 0)
        if self.pause_btn.cur_state:
            self.pause()
        # self.SDL_mixer.Mix_SetPostMix(find_SDL_Mixer.cb, 0)

    def seek(self, pos: Number = 0, rel: bool = True):
        if rel:
            if pos == 0:
                return
            elif pos > 0:
                self.cur_off += music.get_pos() + pos
                music.play(start=pos / 1000)
                print("relative seek forward by %.15g seconds" % (pos / 1000))
                self.playing = True
                self.SDL_mixer.Mix_UnregisterEffect(find_SDL_Mixer.MIX_CHANNEL_POST, self.fx_cb)
                self.SDL_mixer.Mix_RegisterEffect(find_SDL_Mixer.MIX_CHANNEL_POST, self.fx_cb, 0, 0)
                # self.SDL_mixer.Mix_SetPostMix(find_SDL_Mixer.cb, 0)
                if self.pause_btn.cur_state:
                    self.pause()
                return
            else:
                pos = max(music.get_pos() + self.cur_off + pos, 0)
                print("relative seek backward")
        music.rewind()
        print("seek absolute = %.15g seconds" % (pos / 1000))
        music.play(start=pos / 1000)
        self.playing = True
        self.cur_off = pos
        self.SDL_mixer.Mix_UnregisterEffect(find_SDL_Mixer.MIX_CHANNEL_POST, self.fx_cb)
        self.SDL_mixer.Mix_RegisterEffect(find_SDL_Mixer.MIX_CHANNEL_POST, self.fx_cb, 0, 0)
        if self.pause_btn.cur_state:
            self.pause()
        # self.SDL_mixer.Mix_SetPostMix(find_SDL_Mixer.cb, 0)

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
SIZE_NORMAL = 2
SIZE_LARGER = 3


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
        try:
            size_code = {
                "normal": SIZE_NORMAL,
                "larger": SIZE_LARGER
            }[settings["size"]]
        except KeyError:
            size_code = SIZE_NORMAL
        if size_code == SIZE_NORMAL:
            width, height = 640, 480
        elif size_code == SIZE_LARGER:
            width, height = 640 - 512 + 1024, 480 - 64 + 256
        else:
            raise ValueError("expected size_code to be one of [SIZE_NORMAL, SIZE_LARGER]")
        surf = pygame.display.set_mode((width, height))
        pygame.mixer.init(frequency=44100)
        pygame.font.init()
        music.set_endevent(pygame.USEREVENT)
        app = PlayerApp(surf, playlists, size_code, settings, 44100)
        app.run()
        fmp.fmp_shutdown()
        pygame.quit()
