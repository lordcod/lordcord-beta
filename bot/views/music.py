from __future__ import annotations
import contextlib
from functools import partial
import logging
import time
import nextcord
from typing import TYPE_CHECKING

from bot.databases.handlers.guildHD import GuildDateBases
from bot.languages import i18n
from bot.misc.utils import get_emoji_wrap
from bot.resources.ether import Emoji

if TYPE_CHECKING:
    from bot.misc.music import Queue, MusicPlayer

_log = logging.getLogger(__name__)


def attach_button(emoji: str, row: int) -> None:
    def decorator(func):
        func.__button_data__ = {
            "url": None,
            "emoji": emoji,
            "row": row,
        }
        return func
    return decorator


class MusicQueueDropDown(nextcord.ui.StringSelect):
    def __init__(self, guild_id: int, queue: Queue, player: MusicPlayer) -> None:
        gdb = GuildDateBases(guild_id)
        locale = gdb.get_cache('language')

        self.guild_id = guild_id
        self.queue = queue
        self.player = player

        super().__init__(placeholder=i18n.t(locale, 'music.player.placeholder'))

    def update_queue(self):
        guild_queue = self.queue[self.guild_id]
        if len(guild_queue) > 25 and self.player.index >= 4:
            iterator = list(
                enumerate(guild_queue[self.player.index-4:self.player.index+21]))[::-1]
        else:
            iterator = list(enumerate(guild_queue[:25]))

        options = [
            nextcord.SelectOption(
                label=f'{i+1}. ' + track.title,
                value=i,
                description=', '.join(track.artist_names),
                emoji=Emoji.yandex_music,
                default=i == self.player.index
            )
            for i, track in iterator
        ]

        disabled = 0 == len(options)
        if 0 == len(options):
            options.append(nextcord.SelectOption(label='SelectOption'))

        self.options = options
        self.disabled = disabled

    async def callback(self, interaction: nextcord.Interaction) -> None:
        index = int(self.values[0])
        await self.player.move_to(index)


class MusicView(nextcord.ui.View):
    embed: nextcord.Embed

    def __init__(self, guild_id: int, queue: Queue, player: MusicPlayer) -> None:
        self.guild_id = guild_id
        self.player = player
        self.queue = queue

        super().__init__(timeout=1800)

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')

        if not interaction.user.voice:
            await interaction.response.send_message(i18n.t(locale, 'music.error.not_in_channel'), ephemeral=True)
            return False
        if interaction.user.voice.channel != self.player.voice.channel:
            await interaction.response.send_message(i18n.t(locale, 'music.error.already'), ephemeral=True)
            return False
        return True

    async def create_buttons(self):
        get_emoji = await get_emoji_wrap(self.guild_id)

        self.clear_items()

        self.mqdd = MusicQueueDropDown(self.guild_id, self.queue, self.player)
        self.add_item(self.mqdd)

        for name, but in self.__class__.__dict__.items():
            if isinstance(but, nextcord.ui.Button):
                but = button.callback.func
            if not hasattr(but, '__button_data__'):
                continue

            data = but.__button_data__.copy()
            try:
                data['emoji'] = get_emoji(data['emoji'])
            except KeyError:
                data['label'] = 'ㅤ'
                data['emoji'] = None
            button = nextcord.ui.Button(**data)
            button.callback = partial(but, self)
            self.add_item(button)

            setattr(self, name, button)

    async def parse_buttons(self):
        await self.create_buttons()
        get_emoji = await get_emoji_wrap(self.guild_id)
        with_empty = not (self.player.voice.is_playing()
                          or self.player.voice.is_paused())

        if self.player.voice.is_playing():
            self.pause_play.emoji = get_emoji('pause')
        if self.player.voice.is_paused():
            self.pause_play.emoji = get_emoji('play')
        if with_empty:
            self.pause_play.disabled = True
            self.repeat.disabled = True
        else:
            self.pause_play.disabled = False
            self.repeat.disabled = False

        if with_empty or 15 > time.time()-self.player.started_at:
            self.undo.disabled = True
        else:
            self.undo.disabled = False

        if with_empty or time.time()-self.player.started_at+15 > self.player.data.diration:
            self.redo.disabled = True
        else:
            self.redo.disabled = False

        if self.player.voice.source.volume+0.1 > 1:
            self.volume_up.disabled = True
        else:
            self.volume_up.disabled = False

        if 0 > self.player.voice.source.volume-0.1:
            self.volume_down.disabled = True
        else:
            self.volume_down.disabled = False

        if with_empty or not self.queue.has(self.guild_id, self.player.index-1):
            self.backward.disabled = True
        else:
            self.backward.disabled = False

        if with_empty or not self.queue.has(self.guild_id, self.player.index+1):
            self.forward.disabled = True
        else:
            self.forward.disabled = False

    @attach_button(emoji='undo', row=1)
    async def undo(self, interaction: nextcord.Interaction):
        self.player.played_coro = self.player.play(
            time.time()-self.player.started_at-15)
        self.player.voice.stop()

    @attach_button(emoji='previous', row=1)
    async def backward(self, interaction: nextcord.Interaction):
        await self.player.move_to(self.player.index-1)

    @attach_button(emoji='pause', row=1)
    async def pause_play(self, interaction: nextcord.Interaction):
        if self.player.voice.is_playing():
            self.player.voice.pause()
            self.player.updated_task.cancel()
            self.player.stopped_at = time.time()-self.player.started_at
        elif self.player.voice.is_paused():
            self.player.voice.resume()
            self.player.started_at = time.time()-self.player.stopped_at
            self.player.updated_task = self.player.get_updated_task()
        await self.player.update_message()

    @attach_button(emoji='next', row=1)
    async def forward(self, interaction: nextcord.Interaction):
        await self.player.move_to(self.player.index+1)

    @attach_button(emoji='redo', row=1)
    async def redo(self, interaction: nextcord.Interaction):
        self.player.played_coro = self.player.play(
            time.time()-self.player.started_at+15)
        self.player.voice.stop()

    @attach_button(emoji='stop', row=2)
    async def stop(self, interaction: nextcord.Interaction):
        await self.player.stop()

    @attach_button(emoji='repeat', row=2)
    async def repeat(self, interaction: nextcord.Interaction):
        self.player.played_coro = self.player.play()
        self.player.voice.stop()

    @attach_button(emoji='vol2', row=2)
    async def volume_down(self, interaction: nextcord.Interaction):
        self.player.voice.source.volume -= 0.1
        await self.player.update_message()

    @attach_button(emoji='vol3', row=2)
    async def volume_up(self, interaction: nextcord.Interaction):
        self.player.voice.source.volume += 0.1
        await self.player.update_message()

    @attach_button(emoji='playlist', row=2)
    async def playlist(self, interaction: nextcord.Interaction):
        pass
