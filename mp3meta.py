from typing import BinaryIO, Dict, Tuple, Optional, Union


def byt_2_int(byts: bytes, sync_safe=True):
    rtn = 0
    power = 1
    mul = 128
    if sync_safe:
        mul *= 2
    for byt in byts[::-1]:
        rtn += power * byt
        power *= mul
    return rtn


def byt_2_bin(byts: bytes):
    byts = byts[::-1]
    bits = list()
    for val in byts:
        tmp = [0] * 8
        for c in range(8):
            tmp[c] = val % 2
            val >>= 1
        bits.extend(tmp)
    return bits


def align_byts_long(num: int, align: int) -> bytes:
    return num.to_bytes(align, "little", signed=False)


def get_long_byts(byts: bytes) -> int:
    return int.from_bytes(byts, "little", signed=False)


def pack_bytes(byts: bytes, head_len: int) -> bytes:
    return align_byts_long(len(byts), head_len) + byts


def is_valid_header(header: int) -> bool:
    sync = header >> 16
    if sync & 0xFFE0 != 0xFFE0:
        return False
    ver = (header >> 19) & 0x3
    if ver == 1:
        return False
    layer = (header >> 17) & 0x3
    if layer == 0:
        return False
    bit_rate = (header >> 12) & 0xF
    if bit_rate in (0, 0xF):
        return False
    sample_rate = (header >> 10) & 0x3
    if sample_rate == 0x3:
        return False
    return True


find_sz = 8192


def find_header(fl: BinaryIO, start_pos: int) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    fl.seek(start_pos)
    data = fl.read(find_sz)
    while len(data) > 0:
        pos = data.find(b"\xff", 0)
        while pos >= 0:
            header = data[pos:pos + 4]
            head_num = byt_2_int(header)
            if len(header) == 4 and is_valid_header(head_num):
                return start_pos + pos, head_num, header
            pos = data.find(b"\xff", pos + 1)
        data = fl.read(find_sz)
        start_pos += find_sz
    return None, None, None


BIT_RATE_TABLE = ((0, 0, 0, 0, 0),
                  (32, 32, 32, 32, 8),
                  (64, 48, 40, 48, 16),
                  (96, 56, 48, 56, 24),
                  (128, 64, 56, 64, 32),
                  (160, 80, 64, 80, 40),
                  (192, 96, 80, 96, 48),
                  (224, 112, 96, 112, 56),
                  (256, 128, 112, 128, 64),
                  (288, 160, 128, 144, 80),
                  (320, 192, 160, 160, 96),
                  (352, 224, 192, 176, 112),
                  (384, 256, 224, 192, 128),
                  (416, 320, 256, 224, 144),
                  (448, 384, 320, 256, 160),
                  (None, None, None, None, None))


lst_ver = [2.5, None, 2.0, 1.0]

SAMPLE_RATE_TABLE = (
    (11025, 12000, 8000),
    (None, None, None),
    (22050, 24000, 16000),
    (44100, 48000, 32000)
)


def read_from(fl: BinaryIO, pos: int, length: int) -> bytes:
    prev_pos = fl.tell()
    fl.seek(pos)
    rtn = fl.read(length)
    fl.seek(prev_pos)
    return rtn


def decode_txt(b: bytes):
    if b[0] == '\0':
        return str(b[1:], "utf-8")
    elif b[0:2] == "\xff\xfe":
        return str(b[2:], "UTF-16-LE")
    elif b[0:2] == "\xfe\xff":
        return str(b[2:], "UTF-16-BE")
    else:
        return str(b[1:], "latin1")


class SimpleFrame:
    special = ["TALB", "TPE1", "TIT2"]

    def __init__(self, all_frames: Dict[str, "SimpleFrame"], fl_obj: BinaryIO,
                 name: str, sync_safe: bool = False, read_file_limit: int = 256):
        self.name = name
        all_frames[self.name] = self
        self.length = byt_2_int(fl_obj.read(4), sync_safe)
        self.flags = byt_2_bin(fl_obj.read(2))
        self.data_is_str: bool = True
        if self.length < read_file_limit or name in SimpleFrame.special:
            self.data: Union[bytes, int] = fl_obj.read(self.length)
        else:
            self.data_is_str = False
            self.data: Union[bytes, int] = fl_obj.tell()
            fl_obj.seek(self.length, 1)


class Mp3Info(object):
    def __init__(self, fl_obj: BinaryIO):
        self.all_frames: Dict[str, SimpleFrame] = {}
        self.fl_obj = fl_obj
        prev_pos = fl_obj.tell()
        fl_obj.seek(0)
        start_pos = 0
        has_frames = False
        if fl_obj.read(3) == "ID3":
            has_frames = True
            fl_obj.seek(6)
            start_pos = byt_2_int(fl_obj.read(4), False) + 10
        pos_head, header, head_bytes = find_header(fl_obj, start_pos)
        self.head_int = header
        if pos_head is None:
            raise Exception("Could not find mp3 Header " + str(fl_obj.name))
        ver_idx = (header >> 19) & 0x3
        self.sample_rate = SAMPLE_RATE_TABLE[ver_idx][(header >> 10) & 0x3]
        self.ver = lst_ver[ver_idx]
        self.layer = 4 - ((header >> 17) & 0x3)
        if self.layer == 4:
            raise Exception("Invalid MPEG Layer")
        self.copyright = (header >> 3) & 0x1
        self.original = (header >> 2) & 0x1
        bit_rate_row = (header >> 12) & 0xF
        bit_rate_col = None
        i_ver = int(self.ver)
        if i_ver == 1:
            if self.layer == 1:
                bit_rate_col = 0
            elif self.layer == 2:
                bit_rate_col = 1
            elif self.layer == 3:
                bit_rate_col = 2
        elif i_ver == 2:
            if self.layer == 1:
                bit_rate_col = 3
            elif self.layer == 2 or self.layer == 3:
                bit_rate_col = 4
        if bit_rate_col is None:
            raise Exception("Mp3 version and layer combination is invalid")
        self.bit_rate = BIT_RATE_TABLE[bit_rate_row][bit_rate_col]
        self.head_size = 0
        if has_frames:
            self.read_frames(fl_obj)
            self.fill_frame_dat()
        else:
            self.album = None
            self.artist = None
            self.song_name = None
        self.end_meta_pos = fl_obj.tell()
        self.head_size += 4
        fl_obj.seek(0, 2)
        self.f_len = fl_obj.tell()
        fl_obj.seek(prev_pos)

    @property
    def duration(self) -> float:  # get the duration in seconds
        return (self.f_len - self.end_meta_pos) / (self.bit_rate * 1000 / 8)

    # noinspection PyBroadException
    def fill_frame_dat(self):
        try:
            alb_frame = self.all_frames["TALB"]
            if alb_frame.data_is_str:
                self.album = alb_frame.data
            else:
                self.album = read_from(self.fl_obj, alb_frame.data, alb_frame.length)
            self.album = decode_txt(self.album)
        except Exception:
            self.album = None
        try:
            art_frame = self.all_frames["TPE1"]
            if art_frame.data_is_str:
                self.artist = art_frame.data
            else:
                self.artist = read_from(self.fl_obj, art_frame.data, art_frame.length)
            self.artist = decode_txt(self.artist)
        except Exception:
            self.artist = None
        try:
            song_frame = self.all_frames["TIT2"]
            if song_frame.data_is_str:
                self.song_name = song_frame.data
            else:
                self.song_name = read_from(self.fl_obj, song_frame.data, song_frame.length)
            self.song_name = decode_txt(self.song_name)
        except Exception:
            self.song_name = None

    def read_frames(self, fl_obj: BinaryIO):
        fl_obj.seek(6)
        len_header = byt_2_int(fl_obj.read(4), False)
        self.head_size = len_header + 10
        self.all_frames = {}
        data = fl_obj.read(4)
        while fl_obj.tell() - 10 < len_header and len(data) > 0 and data[0] != '\0':
            SimpleFrame(self.all_frames, fl_obj, data.decode("utf-8"), False)
            data = fl_obj.read(4)

    def serialize(self):
        rtn = align_byts_long(self.head_int, 4)
        rtn += align_byts_long(self.head_size, 4)
        rtn += align_byts_long(self.f_len, 8)
        null = "\0" * 4
        if self.album is not None:
            album = self.all_frames["TALB"].data
            if isinstance(album, bytes):
                rtn += pack_bytes(album, 4)
            else:
                rtn += null
        else:
            rtn += null
        if self.artist is not None:
            artist = self.all_frames["TPE1"].data
            if isinstance(artist, bytes):
                rtn += pack_bytes(artist, 4)
            else:
                rtn += null
        else:
            rtn += null
        if self.song_name is not None:
            song_name = self.all_frames["TIT2"].data
            if isinstance(song_name, bytes):
                rtn += pack_bytes(song_name, 4)
            else:
                rtn += null
        else:
            rtn += null
        return rtn
