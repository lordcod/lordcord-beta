
import nextcord
from nextcord.ext import commands
import nextcord.types
import nextcord.types.raw_models

from bot.databases import GuildDateBases

from bot.misc.lordbot import LordBot


class ReactionsEvent(commands.Cog):
    def __init__(self, bot: LordBot) -> None:
        self.bot = bot
        super().__init__()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: nextcord.RawReactionActionEvent):
        if payload.guild_id is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        gdb = GuildDateBases(payload.guild_id)
        role_reaction = await gdb.get('role_reactions')

        if role_reaction is None:
            return

        try:
            role_id = role_reaction[payload.message_id]['reactions'][str(
                payload.emoji)]
        except KeyError:
            return

        role = guild.get_role(role_id)
        if not (role and role.is_assignable()):
            await guild._state.http.remove_reaction(
                channel_id=payload.channel_id,
                message_id=payload.message_id,
                emoji=str(payload.emoji).strip('<>'),
                member_id=payload.member.id
            )
            return
        try:
            await guild._state.http.add_role(
                guild_id=payload.guild_id,
                user_id=payload.user_id,
                role_id=role_id
            )
        except nextcord.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: nextcord.RawReactionActionEvent):
        if payload.guild_id is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        gdb = GuildDateBases(payload.guild_id)
        role_reaction = await gdb.get('role_reactions')

        try:
            if payload.emoji.id is not None:
                emoji = self.bot._connection._emojis[payload.emoji.id]
                role_id = role_reaction[payload.message_id]['reactions'][str(
                    emoji)]
            else:
                role_id = role_reaction[payload.message_id]['reactions'][str(
                    payload.emoji)]
        except KeyError:
            return

        role = guild.get_role(role_id)
        if not (role and role.is_assignable()):
            return
        try:
            await guild._state.http.remove_role(
                guild_id=payload.guild_id,
                user_id=payload.user_id,
                role_id=role_id
            )
        except nextcord.HTTPException:
            return


def setup(bot):
    bot.add_cog(ReactionsEvent(bot))
