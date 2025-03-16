import nextcord

from bot.databases.handlers.guildHD import GuildDateBases
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization, get_emoji_wrap
from bot.views.settings.tempvoice.optns.base import ViewOptionItem


@AsyncSterilization
class TypePanelDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild_id: int, type_panel: int) -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        get_emoji = await get_emoji_wrap(gdb)

        options = [
            nextcord.SelectOption(
                label=i18n.t(
                    locale, 'settings.tempvoice.panel.type.none.label'),
                description=i18n.t(
                    locale, 'settings.tempvoice.panel.type.none.description'),
                value=0,
                default=type_panel == 0,
                emoji=get_emoji('buttonnone')
            ),
            nextcord.SelectOption(
                label=i18n.t(
                    locale, 'settings.tempvoice.panel.type.button.label'),
                description=i18n.t(
                    locale, 'settings.tempvoice.panel.type.button.description'),
                value=1,
                default=type_panel == 1,
                emoji=get_emoji('buttonbutton')
            ),
            nextcord.SelectOption(
                label=i18n.t(
                    locale,
                    'settings.tempvoice.panel.type.dropdown.label'
                ),
                description=i18n.t(
                    locale, 'settings.tempvoice.panel.type.dropdown.description'),
                value=2,
                default=type_panel == 2,
                emoji=get_emoji('buttondropdown')
            ),
        ]
        super().__init__(options=options)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = int(self.values[0])
        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set_on_json('tempvoice', 'type_panel', value)

        await self.view.edit_panel(interaction)

        view = await TypePanelView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class TypeMessagePanelDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild_id: int, type_message_panel: int) -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        get_emoji = await get_emoji_wrap(gdb)

        options = [
            nextcord.SelectOption(
                label=i18n.t(
                    locale, 'settings.tempvoice.panel.type_message.panel.label'),
                description=i18n.t(
                    locale, 'settings.tempvoice.panel.type_message.panel.description'),
                emoji=get_emoji('advanced'),
                value=1,
                default=type_message_panel == 1
            ),
            nextcord.SelectOption(
                label=i18n.t(
                    locale, 'settings.tempvoice.panel.type_message.voice.label'),
                description=i18n.t(
                    locale, 'settings.tempvoice.panel.type_message.voice.description'),
                emoji=get_emoji('micon'),
                value=2,
                default=type_message_panel == 2
            ),
            nextcord.SelectOption(
                label=i18n.t(
                    locale, 'settings.tempvoice.panel.type_message.every.label'),
                description=i18n.t(
                    locale, 'settings.tempvoice.panel.type_message.every.description'),
                emoji=get_emoji('ticforms'),
                value=3,
                default=type_message_panel == 3
            ),
        ]
        super().__init__(options=options)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = int(self.values[0])
        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set_on_json('tempvoice', 'type_message_panel', value)

        await self.view.edit_panel(interaction)

        view = await TypePanelView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class TypePanelView(ViewOptionItem):
    label = 'settings.tempvoice.panel.label'
    description = 'settings.tempvoice.panel.description'
    emoji = 'advanced'

    async def __init__(self, guild: nextcord.Guild):
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        data = await gdb.get('tempvoice')
        type_panel = data.get('type_panel', 1)
        type_message_panel = data.get('type_message_panel', 1)

        get_emoji = await get_emoji_wrap(gdb)

        enabled_panel = True
        if type_panel == 0:
            enabled_panel = False
            default_advance_panel = False
        if type_panel == 1:
            default_advance_panel = False
        elif type_panel == 2:
            default_advance_panel = True

        self.advance_panel = data.get('advance_panel', default_advance_panel)

        super().__init__()

        tpdd = await TypePanelDropDown(guild.id, type_panel)
        tmpdd = await TypeMessagePanelDropDown(guild.id, type_message_panel)
        self.add_item(tpdd)
        self.add_item(tmpdd)

        if not enabled_panel:
            tmpdd.disabled = True
            self.edit.disabled = True

        self.edit.style = nextcord.ButtonStyle.blurple
        if self.advance_panel:
            self.edit.emoji = get_emoji('simple')
            self.edit.label = i18n.t(locale, 'settings.tempvoice.panel.simple')
        else:
            self.edit.emoji = get_emoji('advanced')
            self.edit.label = i18n.t(
                locale, 'settings.tempvoice.panel.extend')

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.edit.label = i18n.t(locale, 'settings.button.edit')

    @nextcord.ui.button()
    async def edit(self, button: nextcord.ui.Button, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set_on_json('tempvoice', 'advance_panel', not self.advance_panel)

        await self.edit_panel(interaction)

        view = await TypePanelView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
