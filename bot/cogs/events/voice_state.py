import asyncio
import time
import math
import nextcord
from nextcord.ext import commands

from bot.databases.datastore import DataStore
from bot.databases.handlers.guildHD import GuildDateBases
from bot.misc.plugins import logstool
from bot.misc.lordbot import LordBot
from bot.misc.music import current_players
from bot.misc.plugins.tempvoice import TempVoiceModule


class VoiceStateEvent(commands.Cog):
    def __init__(self, bot: LordBot) -> None:
        self.bot = bot
        super().__init__()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: nextcord.Member, before: nextcord.VoiceState, after: nextcord.VoiceState) -> None:
        # add connect, disconnect, mute, unmmute, etc. log
        tasks = []
        if before.channel is None and after.channel is not None:
            tasks.extend((
                self.connect_to_voice(member),
                self.check_bot_player_conn(after.channel),
                logstool.Logs(member.guild).connect_voice(
                    member, after.channel)
            ))
        if before.channel is not None and after.channel is None:
            tasks.extend((
                self.disconnect_from_voice(member),
                self.check_bot_player(member, before.channel),
                logstool.Logs(member.guild).disconnect_voice(
                    member, before.channel)
            ))
        if before.channel != after.channel:
            tasks.append(TempVoiceModule(member).process(
                before.channel, after.channel))
        if (
            before.channel is not None
            and after.channel is not None
            and before.channel != after.channel
        ):
            tasks.append(logstool.Logs(member.guild).move_voice(
                member, before.channel, after.channel))

        await asyncio.gather(*tasks)

    async def check_bot_player(self, member: nextcord.Member, channel: nextcord.VoiceChannel):
        if channel.guild.id in current_players and self.bot.user.id == member.id:
            await current_players[channel.guild.id].stop()
        if (1 == len(channel.members)
            and self.bot.user == channel.members[0]
                and channel.guild.id in current_players):
            await current_players[channel.guild.id].point_not_user()

    async def check_bot_player_conn(self, channel: nextcord.VoiceChannel):
        if (2 == len(channel.members)
            and self.bot.user in channel.members
                and channel.guild.id in current_players):
            await current_players[channel.guild.id].point_user()

    async def connect_to_voice(self, member: nextcord.Member) -> None:
        state = DataStore('temp_voice_state')
        await state.set(member.id, time.time())

    async def disconnect_from_voice(self, member: nextcord.Member) -> None:
        gdb = GuildDateBases(member.guild.id)
        state = DataStore('voice_state')
        temp_state = DataStore('temp_voice_state')
        member_started_at = await temp_state.get(member.id)
        await temp_state.delete(member.id)

        if member_started_at is None:
            return

        voice_time = time.time()-member_started_at

        guild_state = await gdb.get('voice_time_state', {})
        guild_state[member.id] = guild_state.get(member.id, 0) + voice_time
        await gdb.set('voice_time_state', guild_state)

        await state.increment(member.id, voice_time)

        await self.give_score(member, voice_time)

    async def give_score(self, member: nextcord.Member, voice_time: float) -> None:
        state = DataStore('score')
        gdb = GuildDateBases(member.guild.id)

        multiplier = 1
        user_level = 1
        score = voice_time * 0.5 \
            * multiplier / math.sqrt(user_level)

        guild_state = await gdb.get('score_state', {})
        guild_state[member.id] = guild_state.get(member.id, 0) + score
        await gdb.set('score_state', guild_state)

        await state.increment(member.id, score)


def setup(bot: LordBot):
    bot.add_cog(VoiceStateEvent(bot))
