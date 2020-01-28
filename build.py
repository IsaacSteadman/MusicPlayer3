import os
from subprocess import call
import sys
import json
from os.path import join, dirname, splitext
from typing import List


base_dir = dirname(__file__)
obj_name = "FastMusicPlayer"


def get_sources(d: str) -> List[str]:
    res = []
    for f in os.listdir(d):
        base, ext = splitext(f)
        if ext in ["c", "cpp"]:
            res.append(join(d, f))
    return res


lst_sources = get_sources(join(base_dir, "common"))


if os.name == "nt":
    with open(join(base_dir, "win32", "config.json"), "r") as fl:
        data = json.load(fl)
    msvc_dir = data["msvc_dir"]
    compiler_args = [
        "%s/VC/bin/amd64/cl.exe" % msvc_dir, "/Wall",
        "/D", "NDEBUG", "/D", "_WINDOWS", "/D", "_USRDLL",
        "/D", "_WINDLL", "/D", "_UNICODE", "/D", "UNICODE"
    ]
    dylib_args = [
        "/LD",
    ]
    at_end = [
        "/link", "/MACHINE:X64",
        "/OUT:%s" % join(base_dir, "win32". "./%s.dll" % obj_name),
        "/SUBSYSTEM:WINDOWS",
        "/DYNAMICBASE", "kernel32.lib", "user32.lib",
        "gdi32.lib", "winspool.lib", "comdlg32.lib",
        "advapi32.lib", "shell32.lib", "ole32.lib",
        "oleaut32.lib", "uuid.lib", "odbc32.lib", "odbccp32.lib"
    ]
    lst_sources.extend(get_sources(join(base_dir, "win32")))
    env = dict(os.environ, **{
        "LIB": ";".join([
            "C:/Program Files (x86)/Microsoft Visual Studio 14.0/VC/lib/amd64",
            "C:/Program Files (x86)/Microsoft Visual Studio 14.0/VC/atlmfc/lib/amd64",
            "C:/Program Files (x86)/Windows Kits/10/lib/10.0.10240.0/ucrt/x64",
            "C:/Program Files (x86)/Windows Kits/8.1/lib/winv6.3/um/x64",
            "C:/Program Files (x86)/Windows Kits/NETFXSDK/4.6.1/Lib/um/x64",
            "C:/Python27/libs"
        ]),
        "LIBPATH": ";".join([
            "C:/Program Files (x86)/Microsoft Visual Studio 14.0/VC/lib/amd64",
            "C:/Program Files (x86)/Microsoft Visual Studio 14.0/VC/atlmfc/lib/amd64"
        ]),
        "INCLUDE": ";".join([
            "C:/Python27/include",
            "C:/Program Files (x86)/Microsoft Visual Studio 14.0/VC/include",
            "C:/Program Files (x86)/Microsoft Visual Studio 14.0/VC/atlmfc/include",
            "C:/Program Files (x86)/Windows Kits/10/Include/10.0.10240.0/ucrt",
            "C:/Program Files (x86)/Windows Kits/8.1/Include/um",
            "C:/Program Files (x86)/Windows Kits/8.1/Include/shared",
            "C:/Program Files (x86)/Windows Kits/8.1/Include/winrt"
        ])
    })
    env = dict(os.environ)
elif os.name == "posix":
    compiler_args = [
        "gcc", "-fdiagnostics-color=always", "-lstdc++",
        "-std=c++14", "-ldl", "-pthread", "-L.", "-Wall"
    ]
    dylib_args = [
        "-shared", "-fPIC", "-o", join(base_dir, "linux", "lib%s.so" % obj_name)
    ]
    at_end = []
    lst_sources.extend(get_sources(join(base_dir, "linux")))
else:
    raise OSError("OS not recognized")

compiler_args.extend(dylib_args)
compiler_args.extend(lst_sources)
compiler_args.extend(at_end)
call(compiler_args, env=env)