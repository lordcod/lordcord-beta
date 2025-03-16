from asyncio import Task
import asyncio
from collections import defaultdict
import contextlib
import logging
import time
import nextcord

from yandex_music_api.track import Track

import random
from typing import Any, Coroutine, List,  Optional, Dict

from bot.databases.handlers.guildHD import GuildDateBases
from bot.languages import i18n
from bot.misc.utils import get_emoji_wrap
from bot.views.music import MusicView

_log = logging.getLogger(__name__)

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
ffmpeg_path = "ffmpeg"
initally_num = 10
DEFAULT_VOLUME = 0.5


def convert_time(timestamp: Any):
    timestamp = int(timestamp)

    seconds = timestamp % 60
    minutes = timestamp // 60

    if minutes < 60:
        return f"{minutes:0>2}:{seconds:0>2}"
    else:
        seconds = timestamp % 60
        minutes = timestamp / 60 % 60
        hours = timestamp // (60 * 60)
        return f"{hours:0>2.0f}:{minutes:0>2.0f}:{seconds:0>2.0f}"


async def get_emoji(gdb: GuildDateBases, volume: int):
    _get_emoji = await get_emoji_wrap(gdb)
    if 66 < volume <= 100:
        return _get_emoji('vol3')
    if 33 < volume <= 66:
        return _get_emoji('vol2')
    if 0 < volume <= 33:
        return _get_emoji('vol1')
    return _get_emoji('vol0')


class Queue:
    def __init__(self) -> None:
        self.data: defaultdict[int, List[Track]] = defaultdict(list)

    def token_generate(self) -> int:
        val = random.randint(1000000, 9999999)
        return val

    def add(self, guild_id: int, track: Track) -> int:
        self.data[guild_id].append(track)
        return track.id

    def remove(self, guild_id: int, index: int = 0) -> None:
        data = self.get(guild_id, index)

        if data is not None:
            self.data[guild_id].pop(index)

    def clear(self, guild_id: int) -> None:
        self.data[guild_id] = []

    def get(self, guild_id: int, index: int) -> Optional[Track]:
        try:
            return self.data[guild_id][index]
        except IndexError:
            return None

    def has(self, guild_id: int, index: int) -> bool:
        if 0 > index:
            return False
        try:
            self.data[guild_id][index]
        except IndexError:
            return False
        else:
            return True

    def get_next(self, guild_id: int) -> Optional[Track]:
        try:
            return self.data[guild_id][0]
        except IndexError:
            return None

    def set(self, guild_id: int, tracks: List[Track]) -> None:
        self.data[guild_id] = tracks

    def __getitem__(self, __key: int) -> List[Track]:
        return self.data[__key]


class MusicPlayer:
    started_at: int
    stopped_at: int
    updated_task: Task
    leaved_task: Optional[Task] = None
    played_coro: Optional[Coroutine[Any, Any, Any]] = None
    with_stopped: bool = False
    index: int

    def __init__(self,
                 guild: nextcord.Guild,
                 message: nextcord.Message
                 ) -> None:
        self.guild = guild
        self.guild_id = guild.id
        self.message = message

    @property
    def voice(self) -> Optional[nextcord.VoiceClient]:
        return self.guild.voice_client

    async def process(self, index: Optional[int] = None):
        if index is None:
            if self.guild_id in current_players:
                index = current_players[self.guild_id].index+1
            else:
                index = 0

        self.index = index
        self.data = queue.get(self.guild_id, index)
        self.view = MusicView(self.guild_id, queue, self)

        if self.guild_id in current_players:
            player = current_players[self.guild_id]
            if player.leaved_task is not None:
                player.index = self.index
                player.data = self.data
                player.leaved_task.cancel()
                await player.play()
            else:
                await player.update_message()

            gdb = GuildDateBases(self.guild_id)
            locale = await gdb.get('language')
            await self.message.edit(
                i18n.t(locale,  "music.player.added"),
                delete_after=15,
                embeds=[],
                view=None
            )
            return

        sessions_volume[self.guild_id] = DEFAULT_VOLUME
        current_players[self.guild_id] = self
        await self.play()

    async def move_to(self, index: int) -> None:
        track = queue.get(self.guild_id, index)

        if track is None:
            raise IndexError("Track at index %s was not found." % index)

        if not self.updated_task.done():
            self.updated_task.cancel()

        self.index = index
        self.data = track
        self.played_coro = self.play()
        self.voice.stop()

    async def stop(self):
        self.with_stopped = True

        if self.voice and self.voice.is_playing():
            self.voice.stop()
        queue.clear(self.guild_id)
        current_players.pop(self.guild_id, None)
        sessions_volume.pop(self.guild_id, None)

        if self.voice:
            await self.voice.disconnect()

        gdb = GuildDateBases(self.guild_id)
        locale = await gdb.get('language')
        with contextlib.suppress(Exception):
            await self.message.edit(i18n.t(locale, 'music.player.out.last'),
                                    embeds=[],
                                    view=None)

    def get_leaved_task(self) -> Task:
        async def inner():
            await asyncio.sleep(180)
            await self.stop()
        return asyncio.create_task(inner(), name=f'voice-leave-task:{self.guild_id}')

    def get_updated_task(self) -> Task:
        async def inner():
            if 10 > self.data.diration:
                for _ in range(int(self.data.diration)-1):
                    await asyncio.sleep(1)
                    await self.update_message()
                return

            retry = self.data.diration // 10
            for _ in range(9):
                await asyncio.sleep(retry)
                await self.update_message()
        return asyncio.create_task(inner(), name=f'voice-update-message-task:{self.guild_id}')

    async def point_not_user(self) -> None:
        if self.voice.is_playing():
            gdb = GuildDateBases(self.guild_id)
            locale = await gdb.get('language')

            self.voice.pause()
            self.updated_task.cancel()
            self.stopped_at = time.time()-self.started_at
            self.leaved_task = self.get_leaved_task()
            await self.message.edit(
                content=i18n.t(locale, 'music.player.out.not_user', time=time.time()+180),
                embeds=[],
                view=None
            )

    async def point_user(self) -> None:
        if self.voice.is_paused() and self.leaved_task is not None and queue.has(self.guild_id, self.index):
            self.leaved_task.cancel()
            self.voice.resume()
            self.started_at = time.time()-self.stopped_at
            self.updated_task = self.get_updated_task()
            await self.update_message()

    async def update_message(self):
        gdb = GuildDateBases(self.guild_id)
        locale = await gdb.get('language')

        embed = nextcord.Embed(
            title=self.data.title,
            url=self.data.get_url()
        )
        embed.set_author(
            name=', '.join(self.data.artist_names),
            icon_url=self.data.get_image('480x480')
        )
        if self.voice.is_playing():
            embed.set_thumbnail("https://i.postimg.cc/NfhqmcP9/GIF-20240709-000613-764-ezgif-com-gif-maker.gif")
            embed.add_field(
                name=i18n.t(locale, 'music.player.message.status'),
                value=i18n.t(locale, 'music.player.message.listen',
                             passtime=convert_time(time.time()-self.started_at),
                             fulltime=convert_time(self.data.diration))
            )
        if self.voice.is_paused():
            embed.set_thumbnail("https://i.postimg.cc/0Q5b0SWQ/cf937614db244f5f8728623910d7a7aas-AWmsn-Zwjf-R1-R9ll-0.png")
            embed.add_field(
                name=i18n.t(locale, 'music.player.message.status'),
                value=i18n.t(locale, 'music.player.message.pause',
                             passtime=convert_time(time.time()-self.started_at),
                             fulltime=convert_time(self.data.diration))
            )

        if self.voice.source:
            volume = self.voice.source.volume * 100
        else:
            volume = 0
        embed.add_field(
            name=i18n.t(locale, 'music.player.message.volume'),
            value=f'{await get_emoji(gdb, volume)} {volume:.0f}%'
        )

        await self.view.parse_buttons()
        self.view.mqdd.update_queue()

        await self.message.edit(
            content=None,
            embed=embed,
            view=self.view
        )

    async def callback(self, err):
        with contextlib.suppress(AttributeError):
            sessions_volume[self.guild_id] = self.voice.source.volume
        if self.updated_task and not self.updated_task.done():
            self.updated_task.cancel()
        if self.with_stopped:
            return
        if self.played_coro:
            asyncio.create_task(self.played_coro)
            self.played_coro = None
            return

        gdb = GuildDateBases(self.guild_id)
        locale = await gdb.get('language')

        if not queue.has(self.guild_id, self.index+1):
            await self.message.edit(
                content=i18n.t(locale, 'music.player.out.previous', time=time.time()+180),
                embeds=[],
                view=None
            )
            self.leaved_task = self.get_leaved_task()
            return

        self.index += 1
        self.data = queue.get(self.guild_id, self.index)
        await self.play()

    async def play(self, indent_song: Optional[float] = None):
        options = FFMPEG_OPTIONS.copy()
        if indent_song:
            options['options'] += f" -ss {indent_song}"

        try:
            music_url = await self.data.download_link()
        except Exception as exc:
            await self.callback(exc)
            return

        source = nextcord.FFmpegPCMAudio(
            music_url, pipe=False, executable=ffmpeg_path, **options)
        source = nextcord.PCMVolumeTransformer(source, volume=sessions_volume[self.guild_id])
        self.voice.play(source, after=self.callback)

        if indent_song is not None:
            self.started_at = time.time()-indent_song
        else:
            self.started_at = time.time()

        self.updated_task = self.get_updated_task()
        await self.update_message()


sessions_volume: Dict[int, int] = {}
current_players: Dict[int, MusicPlayer] = {}
queue: Queue = Queue()
