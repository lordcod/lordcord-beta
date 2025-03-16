from __future__ import annotations

import asyncio
import logging
import time
from typing import List,  TYPE_CHECKING,  Dict
import os
import xmltodict
from datetime import datetime

from bot.databases.handlers.guildHD import GuildDateBases
from bot.misc.utils import get_payload, generate_message, lord_format
from bot.resources.info import DEFAULT_YOUTUBE_MESSAGE

try:
    from .ytypes import Channel, Thumbnail, Stats, Timestamp, Video, ShortChannel, VideoHistory
except ImportError:
    from ytypes import Channel, Thumbnail, Stats, Timestamp, Video, ShortChannel, VideoHistory

if TYPE_CHECKING:
    from bot.misc.lordbot import LordBot

_log = logging.getLogger(__name__)


class YtNoti:
    def __init__(
        self,
        bot: LordBot,
        apikey: str = os.getenv('YOUTUBE_API_KEY')
    ) -> None:
        self.bot = bot
        self.apikey = apikey

        self.__running = False
        self.channel_ids = set()
        self.video_history = VideoHistory()
        self.directed_data = {}
        self.user_info: Dict[int, Channel] = {}

        self.heartbeat_timeout = 180
        self.last_heartbeat = time.time()

    @property
    def running(self) -> bool:
        return self.__running and self.last_heartbeat > time.time() - self.heartbeat_timeout

    @running.setter
    def running(self, __value: bool) -> None:
        if not isinstance(__value, bool):
            raise TypeError('The %s type is not supported' %
                            (type(__value).__name__,))
        self.__running = __value

    async def callback(self, video: Video) -> None:
        _log.debug('%s publish new video: %s (%s)',
                   video.channel.name, video.title, video.url)

        for gid in self.directed_data[video.channel.id]:
            guild = self.bot.get_guild(gid)
            gdb = GuildDateBases(gid)
            yt_data = await gdb.get('youtube_notification')
            for id, data in yt_data.items():
                if data['yt_id'] == video.channel.id:
                    channel = self.bot.get_channel(data['channel_id'])
                    payload = get_payload(guild=guild, video=video)
                    mes_data = generate_message(lord_format(
                        data.get('message', DEFAULT_YOUTUBE_MESSAGE), payload))
                    await channel.send(**mes_data)

    async def request(self, method: str, url: str, **kwargs):
        try:
            async with self.bot.session.request(method, url, **kwargs) as response:
                content_type = response.headers.get('Content-Type')
                if content_type == 'application/json' or 'application/json' in content_type:
                    data = await response.json()
                else:
                    data = await response.read()
        except Exception as exc:
            _log.error(
                'It was not possible to get data from the api', exc_info=exc)
            return None

        if not response.ok:
            _log.error(
                'It was not possible to get data from the api, status: %s, data: %s', response.status, data)
            return None

        return data

    def parse_channel(self, data: dict) -> Channel:
        channel_id = data['id']
        if isinstance(channel_id, dict):
            channel_id = channel_id['channelId']

        channel = Channel(
            id=channel_id,
            name=data['snippet']['title'],
            description=data['snippet']['description'],
            thumbnail=data['snippet']['thumbnails']['default']['url'],
            created_at=datetime.fromisoformat(data['snippet']['publishedAt']),
            custom_url=data['snippet'].get('customUrl', None),
        )
        self.user_info[channel.id] = channel
        return channel

    def get_videos_from_body(self, body: dict) -> List[Video]:
        videos = []
        entries = body["feed"]["entry"] if isinstance(
            body["feed"]["entry"], list) else [body["feed"]["entry"]]

        for entry in entries:
            channel = ShortChannel(
                id=entry["yt:channelId"],
                name=entry["author"]["name"],
                url=entry["author"]["uri"],
                created_at=datetime.fromisoformat(body["feed"]["published"])
            )

            thumbnail = Thumbnail(
                url=entry["media:group"]["media:thumbnail"]["@url"],
                width=int(entry["media:group"]["media:thumbnail"]["@width"]),
                height=int(entry["media:group"]["media:thumbnail"]["@height"]),
            )

            stats = None
            if "media:community" in entry["media:group"]:
                stats = Stats(
                    likes=int(entry["media:group"]["media:community"]
                              ["media:starRating"]["@count"]),
                    views=int(entry["media:group"]["media:community"]
                              ["media:statistics"]["@views"]),
                )

            timestamp = Timestamp(
                published=datetime.strptime(
                    entry["published"], "%Y-%m-%dT%H:%M:%S%z"),
                updated=datetime.strptime(
                    entry["updated"], "%Y-%m-%dT%H:%M:%S%z")
            )

            videos.append(Video(
                id=entry["yt:videoId"],
                title=entry["title"],
                description=entry["media:group"]["media:description"] or "",
                url=entry["link"]["@href"],
                thumbnail=thumbnail,
                stats=stats,
                timestamp=timestamp,
                channel=channel
            ))

        return videos

    async def add_channel(self, guild_id: int, channel_id: str) -> None:
        if channel_id not in self.channel_ids:
            videos = await self.get_video_history(channel_id)
            _, diff = self.video_history.get_diff(videos)
            self.video_history.extend(diff)
            self.channel_ids.add(channel_id)
        self.directed_data.setdefault(channel_id, set())
        self.directed_data[channel_id].add(guild_id)

    async def get_video_history(self, channel_id: str) -> List[Video]:
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        body = await self.request('GET', url)

        if body is None:
            return []

        json = xmltodict.parse(body.decode())
        return self.get_videos_from_body(json)

    async def search(self, query: str) -> List[Channel]:
        ret = []

        url = 'https://youtube.googleapis.com/youtube/v3/search'
        params = {
            'part': 'snippet,id',
            'type': 'channel',
            'maxResults': 15,
            'q': query,
            'key': self.apikey
        }

        json = await self.request('GET', url, params=params)

        if json is None:
            return []

        for data in json['items']:
            ret.append(self.parse_channel(data))

        return ret

    async def get_channel_ids(self, ids: List[str]) -> List[Channel]:
        ret = []

        url = 'https://www.googleapis.com/youtube/v3/channels'
        params = [
            ('part', 'snippet,id'),
            ('type', 'channel'),
            ('maxResults', 15),
            ('key', self.apikey)
        ]

        for id in ids:
            params.append(('id', id))

        json = await self.request('GET', url, params=params)

        if json is None:
            return []

        for data in json['items']:
            ret.append(self.parse_channel(data))

        return ret

    async def get_channel_ids_additionally(self, query: str) -> List[Channel]:
        search_result = await self.search(query)
        geted_result = await self.get_channel_ids([data.id for data in search_result])
        return geted_result

    async def parse_youtube(self) -> None:
        if self.__running:
            return

        if self.apikey is None:
            _log.error(
                "[YouTube Notification] It was not possible to get tokens for authorization")
            return

        _log.debug('Started youtube parsing')

        for cid in self.channel_ids:
            videos = await self.get_video_history(cid)
            _, diff = self.video_history.get_diff(videos)
            self.video_history.extend(diff)

        self.__running = True
        while True:
            await asyncio.sleep(self.heartbeat_timeout)
            if not self.__running:
                break
            self.last_heartbeat = time.time()

            gvhd = []
            for cid in self.channel_ids:
                try:
                    videos = await self.get_video_history(cid)
                except Exception as exp:
                    _log.error('An error was received when executing the request (%s)',
                               cid,
                               exc_info=exp)
                    videos = []

                vhd, diff = self.video_history.get_diff(videos)
                self.video_history.extend(diff)
                gvhd.extend(vhd)

            await asyncio.gather(*[self.callback(v) for v in gvhd])

        _log.debug('Parsing %s ending', type(self).__name__)
