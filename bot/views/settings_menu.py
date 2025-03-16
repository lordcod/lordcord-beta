import nextcord
from bot.misc.utils import AsyncSterilization, get_emoji_wrap

from bot.databases import GuildDateBases
from bot.views.settings import moduls
from bot.views.settings._view import DefaultSettingsView
from bot.languages import i18n


@AsyncSterilization
class SetDropdown(nextcord.ui.StringSelect):
    async def __init__(self, guild_id: int):
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        get_emoji = await get_emoji_wrap(gdb)

        options = [
            nextcord.SelectOption(
                label=i18n.t(locale, 'settings.module-name.economy'),
                emoji=get_emoji('economy'),
                value='Economy'
            ),
            nextcord.SelectOption(
                label=i18n.t(locale, 'settings.module-name.languages'),
                emoji=get_emoji('lang'),
                value='Languages'
            ),
            nextcord.SelectOption(
                label=i18n.t(locale, 'settings.module-name.prefix'),
                emoji=get_emoji('prefix'),
                value='Prefix'
            ),
            nextcord.SelectOption(
                label=i18n.t(locale, 'settings.module-name.color'),
                emoji=get_emoji('colors'),
                value='Color'
            ),
            nextcord.SelectOption(
                label=i18n.t(locale, 'settings.module-name.music'),
                emoji=get_emoji('music'),
                value='Music'
            ),
            nextcord.SelectOption(
                label=i18n.t(locale, 'settings.module-name.tickets'),
                emoji=get_emoji('tickets'),
                value='Tickets'
            ),
            nextcord.SelectOption(
                label=i18n.t(locale, 'settings.module-name.auto-roles'),
                emoji=get_emoji('autoroles'),
                value='AutoRoles'
            ),
            nextcord.SelectOption(
                label=i18n.t(locale, 'settings.module-name.role-reactions'),
                emoji=get_emoji('reacroles'),
                value='RoleReactions'
            ),
            nextcord.SelectOption(
                label=i18n.t(locale, 'settings.module-name.notification'),
                emoji=get_emoji('notifi'),
                value='Notification'
            ),
            nextcord.SelectOption(
                label=i18n.t(locale, 'settings.module-name.tempvoice'),
                emoji=get_emoji('timechannels'),
                value='TempVoice'
            ),
            nextcord.SelectOption(
                label=i18n.t(locale, 'settings.module-name.reactions'),
                emoji=get_emoji('autoreac'),
                value='Reactions'
            ),
            nextcord.SelectOption(
                label=i18n.t(locale, 'settings.module-name.thread'),
                emoji=get_emoji('automes'),
                value='ThreadMessage'
            ),
            nextcord.SelectOption(
                label=i18n.t(locale, 'settings.module-name.logs'),
                emoji=get_emoji('changelog'),
                value='Logs'
            ),
            nextcord.SelectOption(
                label=i18n.t(locale, 'settings.module-name.ideas'),
                emoji=get_emoji('ideas'),
                value='Ideas'
            ),
            nextcord.SelectOption(
                label=i18n.t(
                    locale, 'settings.module-name.command-permission'),
                emoji=get_emoji('settings'),
                value='CommandPermission'
            ),
        ]

        super().__init__(
            placeholder=i18n.t(locale, 'settings.start.choose'),
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: nextcord.Interaction):
        value = self.values[0]
        view = await moduls[value](interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class SettingsView(DefaultSettingsView):
    embed: nextcord.Embed

    async def __init__(self, member: nextcord.Member) -> None:
        gdb = GuildDateBases(member.guild.id)
        color = await gdb.get('color')
        locale = await gdb.get('language')

        self.embed = nextcord.Embed(
            description=i18n.t(locale, 'settings.start.description'),
            color=color
        )
        self.embed.set_author(name=i18n.t(
            locale, 'settings.start.title'), icon_url=member.guild.icon)
        self.embed.set_footer(
            text=i18n.t(locale, 'settings.start.request',
                        name=member.display_name),
            icon_url=member.display_avatar)

        super().__init__()

        sd = await SetDropdown(member.guild.id)
        self.add_item(sd)
