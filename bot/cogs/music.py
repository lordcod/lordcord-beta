from os import environ
import logging
import re
import time
from nextcord.ext import commands
from yandex_music_api import Client as YaClient
from yandex_music_api.exceptions import NotFound as YandexNotFound
from bot.databases.handlers.guildHD import GuildDateBases
from bot.languages import i18n
from bot.misc.lordbot import LordBot

from bot.views.selector_music import SelectMusicView
from bot.misc.music import queue, MusicPlayer, current_players


_log = logging.getLogger(__name__)

YANDEX_MUSIC_API_REGEX = r'https:\/\/music.yandex.ru'
YANDEX_MUSIC_SEARCH_TRACK = re.compile(
    YANDEX_MUSIC_API_REGEX+r'\/album\/(\d+)\/track\/(\d+)(.*)')
YANDEX_MUSIC_SEARCH_ALBUM = re.compile(
    YANDEX_MUSIC_API_REGEX+r'\/album\/(\d+)(.*)')
YANDEX_MUSIC_SEARCH_PLAYLIST = re.compile(
    YANDEX_MUSIC_API_REGEX+r'\/users\/([a-zA-Z0-9-_\.]+)\/playlists\/(\d+)(.*)')
YANDEX_MUSIC_SEARCH_ARTIST = re.compile(
    YANDEX_MUSIC_API_REGEX+r'\/artist\/(\d+)(.*)')


class Voice(commands.Cog):
    def __init__(self, bot: LordBot) -> None:
        self.bot = bot
        self.yandex_client = YaClient(environ.get(
            'yandex_api_token'))

    @commands.command()
    async def play(self, ctx: commands.Context, *, request: str):
        gdb = GuildDateBases(ctx.guild.id)
        locale = await gdb.get('language')
        voice = ctx.guild.voice_client

        if not ctx.author.voice:
            await ctx.send(i18n.t(locale, 'music.error.not_in_channel'))
            return
        if voice and ctx.author.voice.channel != voice.channel:
            await ctx.send(i18n.t(locale, 'music.error.already'))
            return
        if voice is None:
            channel = ctx.message.author.voice.channel
            permission = channel.permissions_for(ctx.guild.me)
            if not (permission.connect and permission.speak and permission.priority_speaker):
                raise commands.MissingPermissions(['connect', 'speak', 'priority_speaker'])
            voice = await channel.connect()
            if voice.channel in ctx.guild.stage_channels:
                await ctx.guild.me.edit(suppress=False)

        await ctx.message.delete(delay=0.5)
        mes = await ctx.send(i18n.t(locale, 'music.player.loading'))

        player = MusicPlayer(ctx.guild, mes)

        if finder := YANDEX_MUSIC_SEARCH_TRACK.fullmatch(request):
            found = finder.group(2)
            track = await self.yandex_client.get_track(found, with_only_result=True)
            queue.add(
                ctx.guild.id,
                track
            )
        elif finder := YANDEX_MUSIC_SEARCH_ALBUM.fullmatch(request):
            found = finder.group(1)
            album = await self.yandex_client.get_album(found, with_only_result=True)
            tracks = await album.get_tracks()
            for track in tracks:
                queue.add(
                    ctx.guild.id,
                    track
                )
        elif finder := YANDEX_MUSIC_SEARCH_PLAYLIST.fullmatch(request):
            uid = finder.group(1)
            pid = finder.group(2)
            playlist = await self.yandex_client.get_playlist_from_userid(uid, pid)
            tracks = playlist.tracks[:10]
            for track in tracks:
                queue.add(
                    ctx.guild.id,
                    track
                )
        elif finder := YANDEX_MUSIC_SEARCH_ARTIST.fullmatch(request):
            artist_id = finder.group(1)
            playlist = await self.yandex_client.get_artists(artist_id, with_only_result=True)
            tracks = await playlist.get_rating_tracks(page_size=10)
            for track in tracks:
                queue.add(
                    ctx.guild.id,
                    track
                )
        else:
            try:
                tracks = await self.yandex_client.search(request)
            except YandexNotFound:
                await mes.edit(content=i18n.t(locale, 'music.error.search'))
                return

            view = await SelectMusicView(ctx.guild.id, queue, player, tracks[:25], ctx.author)
            await mes.edit(content=i18n.t(locale, 'music.player.select', lenght=len(tracks[:25])),
                           view=view)
            return

        await player.process()

    @commands.command(name="move-to")
    async def move_to(self, ctx: commands.Context, index: int):
        gdb = GuildDateBases(ctx.guild.id)
        locale = await gdb.get('language')
        player = current_players.get(ctx.guild.id)

        if not ctx.author.voice:
            await ctx.send(i18n.t(locale, 'music.error.not_in_channel'))
        elif player is None:
            await ctx.send(i18n.t(locale, 'music.error.bot_not_in_channel'))
        elif ctx.author.voice.channel != player.voice.channel:
            await ctx.send(i18n.t(locale, 'music.error.already'))
        elif not queue.has(ctx.guild.id, index-1):
            await ctx.send(i18n.t(locale, 'music.error.track_not_found', index=index))
        elif player.index == index-1:
            await ctx.send(i18n.t(locale, 'music.error.current_track'))
        else:
            await player.move_to(index-1)

    @commands.command(name="seek")
    async def seek(self, ctx: commands.Context, seconds: int):
        gdb = GuildDateBases(ctx.guild.id)
        locale = await gdb.get('language')
        player = current_players.get(ctx.guild.id)

        if not ctx.author.voice:
            await ctx.send(i18n.t(locale, 'music.error.not_in_channel'))
        elif player is None:
            await ctx.send(i18n.t(locale, 'music.error.bot_not_in_channel'))
        elif ctx.author.voice.channel != player.voice.channel:
            await ctx.send(i18n.t(locale, 'music.error.already'))

        player.played_coro = player.play(seconds)
        player.voice.stop()


def setup(bot):
    bot.add_cog(Voice(bot))
