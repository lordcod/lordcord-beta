import time
from typing import Optional
import nextcord
import jmespath
from nextcord.ext import commands
from bot.databases import GuildDateBases
from bot.databases.varstructs import IdeasPayload
from bot.languages import i18n
from bot.misc.lordbot import LordBot
from bot.misc.time_transformer import display_time
from bot.misc.utils import TimeCalculator
from bot.views.ideas import BanData, MuteData


class IdeasModeration(commands.Cog):
    def __init__(self, bot: LordBot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        gdb = GuildDateBases(ctx.guild.id)
        ideas: IdeasPayload = await gdb.get('ideas')
        mod_roles = ideas.get('moderation_role_ids')

        if not set(ctx.author._roles) & set(mod_roles) or ctx.author.guild_permissions.administrator:
            raise commands.MissingPermissions('manage_roles')

        return True

    @commands.group(invoke_without_command=True)
    async def ideas(self, ctx: commands.Context) -> None:
        pass

    @ideas.command()
    async def ban(self, ctx: commands.Context, member: nextcord.Member, *, reason: Optional[str] = None) -> None:
        gdb = GuildDateBases(ctx.guild.id)
        color = await gdb.get('color')
        locale = await gdb.get('language')
        ideas: IdeasPayload = await gdb.get('ideas')
        ban_users = ideas.get('ban_users', [])

        if data_ban := BanData.get(ideas, member.id):
            moderator = ctx.guild.get_member(data_ban.moderator_id)
            embed = nextcord.Embed(
                title=i18n.t(locale, 'ideas.mod.ban.title'),
                description=i18n.t(
                    locale,
                    'ideas.mod.ban.already.description',
                    member=member,
                    moderator=moderator,
                    reason=data_ban.reason or i18n.t(locale, 'ideas.mod.permission.unspecified')
                ),
                color=color
            )
            await ctx.send(embed=embed)
            return

        ban_users.append([member.id, ctx.author.id, reason])
        await gdb.set_on_json('ideas', 'ban_users', ban_users)

        embed = nextcord.Embed(
            title=i18n.t(locale, 'ideas.mod.ban.title'),
            description=i18n.t(
                locale,
                'ideas.mod.ban.success.description',
                member=member,
                moderator=ctx.author,
                reason=reason or 'unspecified'
            ),
            color=color
        )
        await ctx.send(embed=embed)

    @ideas.command()
    async def unban(self, ctx: commands.Context, member: nextcord.Member, *, reason: Optional[str] = None) -> None:
        gdb = GuildDateBases(ctx.guild.id)
        color = await gdb.get('color')
        locale = await gdb.get('language')
        ideas: IdeasPayload = await gdb.get('ideas')
        ban_users = ideas.get('ban_users', [])
        data_ban = BanData.get(ideas, member.id)

        if not data_ban:
            embed = nextcord.Embed(
                title=i18n.t(locale, 'ideas.mod.unban.title'),
                description=i18n.t(locale, 'ideas.mod.unban.already.description', member=member.mention),
                color=color
            )
            await ctx.send(embed=embed)
            return

        ban_users.remove(data_ban)
        await gdb.set_on_json('ideas', 'ban_users', ban_users)

        embed = nextcord.Embed(
            title=i18n.t(locale, 'ideas.mod.unban.title'),
            description=i18n.t(locale, 'ideas.mod.unban.success.description',
                               member=member,
                               moderator=ctx.author,
                               reason=reason or i18n.t(locale, 'ideas.mod.permission.unspecified')),
            color=color
        )
        await ctx.send(embed=embed)

    @ideas.command()
    async def mute(self, ctx: commands.Context, member: nextcord.Member, timestamp: TimeCalculator, *, reason: Optional[str] = None) -> None:
        gdb = GuildDateBases(ctx.guild.id)
        color = await gdb.get('color')
        locale = await gdb.get('language')
        ideas: IdeasPayload = await gdb.get('ideas')
        muted_users = ideas.get('muted_users', [])

        if data_mute := MuteData.get(ideas, member.id):
            moderator = ctx.guild.get_member(data_mute.moderator_id)
            embed = nextcord.Embed(
                title=i18n.t(locale, 'ideas.mod.ban.title'),
                description=i18n.t(
                    locale,
                    'ideas.mod.mute.already.description',
                    member=member,
                    timestamp=data_mute.timestamp,
                    display_time=display_time(data_mute.timestamp-time.time(), locale),
                    moderator=moderator,
                    reason=data_mute.reason or i18n.t(locale, 'ideas.mod.permission.unspecified')
                ),
                color=color
            )
            await ctx.send(embed=embed)
            return

        muted_users.append(
            [member.id, ctx.author.id, timestamp + time.time(), reason])
        await gdb.set_on_json('ideas', 'muted_users', muted_users)

        embed = nextcord.Embed(
            title=i18n.t(locale, 'ideas.mod.mute.title'),
            description=i18n.t(
                locale,
                'ideas.mod.mute.success.description',
                member=member,
                timestamp=timestamp,
                display_time=display_time(timestamp, locale),
                moderator=ctx.author,
                reason=reason or i18n.t(locale, 'ideas.mod.permission.unspecified')
            ),
            color=color
        )
        await ctx.send(embed=embed)

    @ideas.command()
    async def unmute(self, ctx: commands.Context, member: nextcord.Member, *, reason: Optional[str] = None) -> None:
        gdb = GuildDateBases(ctx.guild.id)
        color = await gdb.get('color')
        locale = await gdb.get('language')
        ideas: IdeasPayload = await gdb.get('ideas')
        muted_users = ideas.get('muted_users', [])
        data_mute = MuteData.get(ideas, member.id)

        if not data_mute:
            embed = nextcord.Embed(
                title=i18n.t(locale, 'ideas.mod.unmute.title'),
                description=i18n.t(locale, 'ideas.mod.unmute.already.description',
                                   member=member.mention),
                color=color
            )
            await ctx.send(embed=embed)
            return

        muted_users.remove(data_mute)
        await gdb.set_on_json('ideas', 'muted_users', muted_users)

        embed = nextcord.Embed(
            title=i18n.t(locale, 'ideas.mod.unmute.title'),
            description=i18n.t(locale, 'ideas.mod.unmute.success.description',
                               member=member,
                               moderator=ctx.author,
                               reason=reason or i18n.t(locale, 'ideas.mod.permission.unspecified')),
            color=color
        )
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(IdeasModeration(bot))
