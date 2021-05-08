import os
import ctypes


def resolve(primary, secondary, k: str):
    v = getattr(primary, k, None)
    if v is None:
        v = getattr(secondary, k, None)
    return v


def find_sdl_mixer_name() -> str:
    res = []
    if os.name == "nt":
        k32 = ctypes.windll.kernel32
        psapi = ctypes.windll.Psapi
        GetModuleFileNameA = resolve(k32, psapi, "GetModuleFileNameA")
        GetModuleFileNameA.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_ulong]
        EnumProcessModules = resolve(k32, psapi, "EnumProcessModules")
        hProc = k32.GetCurrentProcess()
        size = ctypes.c_ulong()
        size_ptr = ctypes.pointer(size)
        EnumProcessModules(hProc, None, 0, size_ptr)
        q, r = divmod(size.value, ctypes.sizeof(ctypes.c_void_p))
        assert r == 0
        arr_t = ctypes.ARRAY(ctypes.c_void_p, q)
        arr_inst = arr_t()
        EnumProcessModules(hProc, arr_inst, ctypes.sizeof(arr_inst), size_ptr)
        arr1_t = ctypes.ARRAY(ctypes.c_char, 1024)
        arr_inst1 = arr1_t()
        for i in range(q):
            GetModuleFileNameA(arr_inst[i], arr_inst1, ctypes.sizeof(arr_inst1))
            try:
                y = arr_inst1.value.decode("utf8")
                if "SDL_mixer" in y or "SDL2_mixer" in y:
                    if len(res):
                        if res[0] != y:
                            raise OSError("Too many SDL_mixer instances found: %s and %s" % (res[0], y))
                    else:
                        res.append(y)
            except UnicodeDecodeError:
                continue
    elif os.name == "posix":
        path = "/proc/%u/map_files" % os.getpid()
        for x in os.listdir(path):
            y = os.readlink(path + "/" + x)
            if "SDL_mixer" in y:
                if len(res):
                    if res[0] != y:
                        raise OSError("Too many SDL_mixer instances found: %s and %s" % (res[0], y))
                else:
                    res.append(y)
    else:
        raise OSError("OS not supported")
    if len(res) == 0:
        raise FileNotFoundError("Could not find SDL_mixer")
    return res[0]

Mix_SetPostMix_CB = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int16), ctypes.c_int)
Mix_EffectFunc_t = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.POINTER(ctypes.c_int16), ctypes.c_int, ctypes.c_void_p)

import time
last_time = time.time()

def callback(udata, stream, length: int):
    global last_time
    t = time.time()
    length >>= 1
    total = 0
    for i in range(length):
        total += abs(stream[i])
    print(("Mix_SetPostMix  avg=%.6f\tbitrate=%.9f\tlen=%u" % (total / length, length * 16 / (t - last_time), length)).expandtabs(17))
    last_time = t


def callback1(chan: int, stream, length: int, udata):
    callback(udata, stream, length)


cb = Mix_SetPostMix_CB(callback)
cb1 = Mix_EffectFunc_t(callback1)
MIX_CHANNEL_POST = -2
