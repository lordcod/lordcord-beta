
from typing import List, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Channel:
    id: str
    name: str
    description: str
    created_at: datetime
    custom_url: str
    thumbnail: str

    @property
    def url(self) -> str:
        return f'https://www.youtube.com/channel/{self.id}'


@dataclass
class ShortChannel:
    id: str
    name: str
    created_at: datetime
    url: str


@dataclass
class Thumbnail:
    url: str
    width: int
    height: int


@dataclass
class Stats:
    likes: int
    views: int


@dataclass
class Timestamp:
    published: datetime
    updated: datetime


@dataclass
class Video:
    id: str
    title: str
    description: str
    url: str
    thumbnail: Thumbnail
    stats: Stats | None
    timestamp: Timestamp
    channel: ShortChannel

    def __eq__(self, value: object) -> bool:
        return isinstance(value, Video) and self.id == value.id


class VideoHistory:
    def __init__(self) -> None:
        self.videos: list[Video] = []

    def add(self, video: Video):
        self.videos.append(video)

    def has(self, video: Video):
        for v in self.videos:
            if v.id == video.id:
                return True
        return False

    def get_diff(self, videos: List[Video]) -> Tuple[List[Video], List[Video]]:
        ret = []
        diff = []

        include = True
        for video in videos:
            if video not in self.videos:
                diff.append(video)
                if include:
                    ret.append(video)
            else:
                include = False

        return ret, diff

    def extend(self, videos: List[Video]):
        return self.videos.extend(videos)
