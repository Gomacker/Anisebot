import io
from pathlib import Path

from PIL import Image, ImageSequence

from anise_core import RES_PATH
from anise_core.worldflipper import Unit


def save_gif(frames: list[Image.Image], durations: list[int], path: Path) -> None:
    frames[0].save(path, format='GIF', save_all=True, loop=0, duration=durations, disposal=2, append_images=frames[1:])


def make_gif(frames: list[Image.Image], durations: list[int]) -> Image.Image:
    buf = io.BytesIO()
    frames[0].save(buf, format='GIF', save_all=True, loop=0, duration=durations, disposal=2, append_images=frames[1:])
    return Image.open(buf)


def make_gif_to_buf(frames: list[Image.Image], durations: list[int]) -> io.BytesIO:
    buf = io.BytesIO()
    frames[0].save(buf, format='GIF', save_all=True, loop=0, duration=durations, disposal=2, append_images=frames[1:])
    return buf


class GifSynchronizer:
    def __init__(self, image_gif: Image.Image):
        self.gif = image_gif
        self._all_frames: list[Image.Image] = ImageSequence.all_frames(self.gif)

    @property
    def all_frames(self) -> list[Image.Image]:
        return self._all_frames

    def time_count(self):
        return sum([i.info['duration'] for i in self.all_frames])

    def get_frame_and_next_dur(self, index_time, loop=False) -> tuple[Image.Image, int]:
        dur_count = 0
        time_count = self.time_count()
        if index_time >= time_count:
            if loop:
                index_time = index_time % time_count
            else:
                return self.all_frames[-1], -1
        for i in self.all_frames:
            dur_count += i.info['duration']
            if index_time < dur_count:
                return i, dur_count - index_time


def select_max(l):
    return max(l, key=lambda x: x[1])


def select_min_but_positive(l):
    return min(filter(lambda x: x[1] >= 0, l), key=lambda x: x[1])


def make_union_gif(units: list[Unit], bg: Image.Image = Image.new('RGBA', (480, 270), (240, 240, 240))):
    path = RES_PATH / 'unit' / 'pixelart/walk_front'
    gif_images = [GifSynchronizer(Image.open(path / f'{u.extractor_id}.gif')) for u in units]

    index_time = 0
    frames = list()
    durations = list()
    first_frame = True
    frame_and_next_dur: list[tuple[Image.Image, int]]
    nextf: tuple[Image.Image, int]
    while (select_max(frame_and_next_dur := [i.get_frame_and_next_dur(index_time) for i in gif_images]))[1] > 0:
        print(index_time)
        frame_canvas = Image.new('RGBA', bg.size)
        frame_canvas.paste(bg)
        nextf = select_min_but_positive(frame_and_next_dur)
        i = 0
        for frame, next_dur in frame_and_next_dur:
            temp = Image.new('RGBA', (frame.width, frame.height))
            temp.paste(frame, (0, 0))
            # temp = temp.resize((temp.width // 2, temp.height // 2), Resampling.NEAREST)
            # left_ = 25 + ((i//3) % 2)*42 + (i % 3)*128 - frame.width // 2
            # top_ = 72 + (i//3)*16 - frame.height // 2
            left_ = (bg.width - 2*128 - 42) // 2 + ((i//3) % 2)*42 + (i % 3)*128 - frame.width // 2
            top_ = bg.height // 2 + (i//3)*16 - frame.height // 2
            frame_canvas.paste(temp, (left_, top_), mask=temp)
            i += 1
        frames.append(frame_canvas)
        durations.append(80 if first_frame else 100)
        # durations.append(nextf[1])
        first_frame = False
        index_time += nextf[1]
    return frames, durations
