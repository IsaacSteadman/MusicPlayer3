from typing import List, Set, Union
import os


def get_files_exts(d: str, exts: Union[List[str], Set[str]], out_full: bool = True) -> List[str]:
    ls = os.listdir
    isf = os.path.isfile
    isd = os.path.isdir
    spe = os.path.splitext
    nxt = ["/"]
    rtn = []
    while len(nxt):
        cur = nxt
        nxt = []
        for d1 in cur:
            full_par = d + d1
            for f in ls(full_par):
                full = full_par + f
                if isf(full):
                    base, ext = spe(f)
                    if ext in exts:
                        rtn.append(full if out_full else (d1 + f))
                elif isd(full):
                    nxt.append(d1 + f + "/")
    return rtn
