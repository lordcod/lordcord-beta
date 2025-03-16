from __future__ import annotations
import nextcord
from nextcord import utils

from bot.databases import GuildDateBases
from yandex_music_api.track import Track
from bot.languages import i18n

from typing import List, TYPE_CHECKING

from bot.misc.utils import AsyncSterilization

from bot.resources.ether import Emoji

if TYPE_CHECKING:
    from bot.misc.music import Queue, MusicPlayer


@AsyncSterilization
class SelectMusicDropDown(nextcord.ui.Select):
    async def __init__(self, guild_id: int, queue: Queue, player: MusicPlayer, tracks: List[Track]) -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        self.tracks = tracks
        self.queue = queue
        self.player = player

        super().__init__(
            placeholder=i18n.t(locale, 'music.selector.placeholder'),
            min_values=1,
            max_values=1,
            options=[
                nextcord.SelectOption(
                    label=track.title,
                    value=track.id,
                    description=', '.join(track.artist_names),
                    emoji=Emoji.yandex_music
                )
                for track in tracks[-25:]
            ]
        )

    async def callback(self, interaction: nextcord.Interaction):
        track_id = int(self.values[0])
        track = utils.get(self.tracks, id=track_id)

        self.queue.add(
            interaction.guild_id,
            track
        )
        await self.player.process()


@AsyncSterilization
class SelectMusicView(nextcord.ui.View):
    embed: nextcord.Embed

    async def __init__(self, guild_id: int, queue: Queue, player: MusicPlayer, tracks: List[Track], member: nextcord.Member) -> None:
        self.member = member
        super().__init__(timeout=300)
        TDD = await SelectMusicDropDown(guild_id, queue, player, tracks)
        self.add_item(TDD)

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        return interaction.user == self.member

    @nextcord.ui.button(label='Cancal', style=nextcord.ButtonStyle.red)
    async def cancel(self, button: nextcord.ui.Button, interaction: nextcord.Interaction) -> None:
        await interaction.message.delete()
