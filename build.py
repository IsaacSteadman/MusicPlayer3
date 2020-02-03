import os
from subprocess import call
import sys
from sys import argv
import json
from os.path import join, dirname, splitext, abspath
from typing import List


def p_call(args, **kwargs):
    print(args, dict(kwargs))
    call(args, **kwargs)


base_dir = abspath(dirname(__file__))
obj_name = "FastMusicPlayer"


def get_sources(d: str) -> List[str]:
    print("get_sources(%r)" % d)
    res = []
    for f in os.listdir(d):
        print("  " + f)
        base, ext = splitext(f)
        if ext in [".c", ".cpp"]:
            res.append(join(d, f))
    return res


lst_sources = get_sources(join(base_dir, "common"))


class Config(object):
    def __init__(self, json: dict):
        self.json = json
    
    def resolve(self, k: str) -> str:
        s = self.json[k]
        return self.resolve_internal(s)
    
    def resolve_internal(self, s: str) -> str:
        pos1 = s.find("<")
        pos2 = s.find(">", pos1)
        while pos1 >= 0 and pos2 >= 0:
            s = s[:pos1] + self.resolve(s[pos1 + 1:pos2]) + s[pos2 + 1:]
            pos1 = s.find("<")
            pos2 = s.find(">", pos1 + 1)
        return s
    
    def resolve_dict_list_str_reduce(self, k: str, reduce_fn):
        dct: dict = self.json[k]
        assert isinstance(dct, dict)
        return {k1: reduce_fn([self.resolve_internal(v1) for v1 in v]) for k1, v in dct.items()}


if os.name == "nt":
    with open(join(base_dir, "win32", "build_config.json"), "r") as fl:
        config = Config(json.load(fl))
    msvc_dir = config.resolve("msvc_dir")
    win_kit_dir = config.resolve("win_kit_dir")
    compiler_args = [
        config.resolve("cl.exe"), "/Wall",
        "/D", "NDEBUG", "/D", "_WINDOWS", "/D", "_USRDLL",
        "/D", "_WINDLL", "/D", "_UNICODE", "/D", "UNICODE"
    ]
    dylib_args = [
        "/LD",
    ]
    at_end = [
        "/link", "/MACHINE:X64",
        "/OUT:%s" % join(base_dir, "win32", "./%s.dll" % obj_name),
        "/SUBSYSTEM:WINDOWS",
        "/DYNAMICBASE", "kernel32.lib", "user32.lib",
        "gdi32.lib", "winspool.lib", "comdlg32.lib",
        "advapi32.lib", "shell32.lib", "ole32.lib",
        "oleaut32.lib", "uuid.lib", "odbc32.lib", "odbccp32.lib"
    ]
    lst_sources.extend(get_sources(join(base_dir, "win32")))
    env = dict(os.environ, **config.resolve_dict_list_str_reduce("cl_env", lambda x: ";".join(x)))
    # env = dict(os.environ, **{
    #     "LIB": ";".join([
    #         "%s/VC/lib/amd64" % msvc_dir,
    #         "%s/VC/atlmfc/lib/amd64" % msvc_dir,
    #         "%s/10/lib/10.0.10240.0/ucrt/x64" % win_kit_dir,
    #         "%s/8.1/lib/winv6.3/um/x64" % win_kit_dir,
    #         "%s/NETFXSDK/4.6.1/Lib/um/x64" % win_kit_dir,
    #         # "C:/Python27/libs"
    #     ]),
    #     "LIBPATH": ";".join([
    #         "%s/VC/lib/amd64" % msvc_dir,
    #         "%s/VC/atlmfc/lib/amd64" % msvc_dir
    #     ]),
    #     "INCLUDE": ";".join([
    #         # "C:/Python27/include",
    #         "%s/VC/include" % msvc_dir,
    #         "%s/VC/atlmfc/include" % msvc_dir,
    #         "%s/10/Include/10.0.10240.0/ucrt" % win_kit_dir,
    #         "%s/8.1/Include/um" % win_kit_dir,
    #         "%s/8.1/Include/shared" % win_kit_dir,
    #         "%s/8.1/Include/winrt" % win_kit_dir
    #     ])
    # })
    # env = dict(os.environ)
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

if len(lst_sources) == 0:
    print("No sources found")
    raise SystemExit(-1)

compiler_args.extend(dylib_args)
compiler_args.extend(lst_sources)
compiler_args.extend(at_end)
if __name__ == "__main__":
    if len(argv) > 1:
        if len(argv) == 2 and argv[1].lower() == "clean":
            if os.name == "nt":
                path = join(base_dir, "win32")
                for f in os.listdir(path):
                    base, ext = splitext(f)
                    if ext in [".exp", ".lib", ".obj", ".dll"]:
                        os.remove(join(path, f))
                        print("removing " + f)
            else:
                print("Unsupported operating system: '%s'" % os.name)
        else:
            print("bad args, only supports no args or 'clean'")
    else:
        call(compiler_args, cwd=join(base_dir, "win32"), env=env)