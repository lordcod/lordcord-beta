from __future__ import annotations
import contextlib
from typing import Any, List, Literal, Optional, Tuple

import nextcord


from bot.databases.handlers.guildHD import GuildDateBases
from bot.databases.varstructs import ModalItemPayload, TicketsPayload
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization, get_emoji_as_color, get_emoji_wrap
from .base import ViewOptionItem


def get_emoji(system_emoji: int, value: Any) -> str:
    if value:
        return get_emoji_as_color(system_emoji, 'ticon')
    else:
        return get_emoji_as_color(system_emoji, 'ticoff')


def get_style(locale: str, value: Literal[1, 2]) -> str:
    if value == 1:
        return i18n.t(locale, 'settings.tickets.modals.style.short')
    else:
        return i18n.t(locale, 'settings.tickets.modals.style.long')


def join_args(*args: Tuple[str, Optional[Any]]) -> str:
    res = []
    for que, value in args:
        if value is True:
            res.append(que)
            continue
        if not value:
            continue
        res.append(f'{que}{value}')
    return '\n'.join(res)


@AsyncSterilization
class TicketFormsModal(nextcord.ui.Modal):
    async def __init__(self, guild: nextcord.Guild, message_id: int, selected_item: Optional[int] = None):
        self.message_id = message_id
        self.selected_item = selected_item

        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.message_id]
        modals = ticket_data.get('modals')
        item = None

        if selected_item is not None:
            item = modals[selected_item]
            style_num = item.get('style', nextcord.TextInputStyle.short.value)
            style = nextcord.TextInputStyle(style_num)
            super().__init__(i18n.t(locale, 'settings.tickets.modals.modal.title.info',
                                    index=selected_item+1))
        else:
            style = nextcord.TextInputStyle.short
            super().__init__(i18n.t(locale, 'settings.tickets.modals.modal.title.iwoi'))

        def get_data(name):
            if selected_item is not None:
                return item.get(name)

        self.label = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.tickets.modals.modal.label'),
            max_length=45,
            placeholder=get_data('label'),
            required=not get_data('label')
        )
        self.add_item(self.label)

        self.placeholder = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.tickets.modals.modal.placeholder'),
            style=style,
            max_length=100,
            required=False,
            placeholder=get_data('placeholder')
        )
        self.add_item(self.placeholder)

        self.default_value = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.tickets.modals.modal.default'),
            style=style,
            required=False,
            default_value=get_data('default_value')
        )
        self.add_item(self.default_value)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.message_id]
        modals = ticket_data.get('modals', [])
        ticket_data['modals'] = modals

        if self.selected_item is not None:
            item = modals[self.selected_item].copy()
        else:
            item = {}

        data = dict(
            label=self.label.value,
            placeholder=self.placeholder.value,
            default_value=self.default_value.value
        )
        for key, value in data.items():
            if key != 'label' and value.lower().strip() in ('none', '-'):
                item.pop(key, None)
                continue
            if value:
                item[key] = value

        if self.selected_item is not None:
            try:
                modals[self.selected_item] = item
            except IndexError:
                self.selected_item = len(modals)
                modals.append(item)
        else:
            self.selected_item = len(modals)
            modals.append(item)

        await gdb.set_on_json('tickets', self.message_id, ticket_data)

        view = await TicketFormsView(interaction.guild, self.message_id, self.selected_item)
        embed = await view.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)


@AsyncSterilization
class TicketFormsDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild_id: int, modals: Optional[List[ModalItemPayload]] = None, selected_item: Optional[int] = None) -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        get_emoji = await get_emoji_wrap(gdb)

        if modals is None:
            modals = []

        options = [
            nextcord.SelectOption(
                label=item['label'][:100],
                value=i,
                description=item.get('placeholder', '')[:100],
                emoji=get_emoji(f'circle{i+1}'),
                default=selected_item == i
            )
            for i, item in enumerate(modals)
        ]

        disabled = len(options) == 0
        if disabled:
            options.append(
                nextcord.SelectOption(label='SelectOption')
            )

        super().__init__(placeholder=i18n.t(locale, 'settings.tickets.modals.dropdown.forms'),
                         options=options, disabled=disabled)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = int(self.values[0])

        view = await TicketFormsView(interaction.guild, self.view.message_id, value)
        embed = await view.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)


@AsyncSterilization
class TicketFormsRequiredDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild_id: int, modal: Optional[ModalItemPayload], selected_item: Optional[int] = None) -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        get_emoji = await get_emoji_wrap(gdb)

        self.selected_item = selected_item

        if selected_item is None:
            options = [nextcord.SelectOption(label='SelectOption')]
            super().__init__(placeholder=i18n.t(locale, 'settings.tickets.modals.dropdown.required.placeholder'),
                             options=options, disabled=True)
            return

        required = modal.get('required', True)

        options = [
            nextcord.SelectOption(
                label=i18n.t(
                    locale, 'settings.tickets.modals.dropdown.required.required.label'),
                value=1,
                description=i18n.t(
                    locale, 'settings.tickets.modals.dropdown.required.required.description'),
                emoji=get_emoji('ticon'),
                default=required
            ),
            nextcord.SelectOption(
                label=i18n.t(
                    locale, 'settings.tickets.modals.dropdown.required.optional.label'),
                value=0,
                description=i18n.t(
                    locale, 'settings.tickets.modals.dropdown.required.optional.description'),
                emoji=get_emoji('ticoff'),
                default=not required
            ),
        ]

        super().__init__(placeholder=i18n.t(locale,
                                            'settings.tickets.modals.dropdown.required.placeholder'), options=options)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = bool(int(self.values[0]))

        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.view.message_id]

        modals = ticket_data['modals']
        modal = modals[self.selected_item]
        modal['required'] = value

        await gdb.set_on_json('tickets', self.view.message_id, ticket_data)

        view = await TicketFormsView(interaction.guild, self.view.message_id, self.selected_item)
        embed = await view.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)


@AsyncSterilization
class TicketFormsStyleDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild_id: int, modal: Optional[ModalItemPayload], selected_item: Optional[int] = None) -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        get_emoji = await get_emoji_wrap(gdb)

        self.selected_item = selected_item

        if selected_item is None:
            options = [nextcord.SelectOption(label='SelectOption')]
            super().__init__(placeholder=i18n.t(
                locale, 'settings.tickets.modals.dropdown.style.placeholder'),
                options=options, disabled=True)
            return

        style = modal.get('style', 1)

        options = [
            nextcord.SelectOption(
                label=i18n.t(
                    locale, 'settings.tickets.modals.dropdown.style.short.label'),
                value=1,
                description=i18n.t(
                    locale, 'settings.tickets.modals.dropdown.style.short.description'),
                emoji=get_emoji('textsmall'),
                default=style == 1
            ),
            nextcord.SelectOption(
                label=i18n.t(
                    locale, 'settings.tickets.modals.dropdown.style.paragraph.label'),
                value=2,
                description=i18n.t(
                    locale, 'settings.tickets.modals.dropdown.style.paragraph.description'),
                emoji=get_emoji('textbig'),
                default=style == 2
            ),
        ]

        super().__init__(placeholder=i18n.t(
            locale, 'settings.tickets.modals.dropdown.style.placeholder'), options=options)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = int(self.values[0])

        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.view.message_id]

        modals = ticket_data['modals']
        modal = modals[self.selected_item]
        modal['style'] = value

        await gdb.set_on_json('tickets', self.view.message_id, ticket_data)

        view = await TicketFormsView(interaction.guild, self.view.message_id, self.selected_item)
        embed = await view.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)


@AsyncSterilization
class TicketFormsView(ViewOptionItem):
    label = 'settings.tickets.modals.label'
    description = 'settings.tickets.modals.description'
    emoji = 'ticforms'

    async def __init__(self, guild: nextcord.Guild, message_id: int, selected_item: Optional[int] = None):
        self.message_id = message_id
        self.selected_item = selected_item

        gdb = GuildDateBases(guild.id)
        color = await gdb.get('color')
        locale = await gdb.get('language')
        system_emoji = await gdb.get('system_emoji')
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.message_id]
        ticket_index = list(tickets.keys()).index(message_id)+1
        created_embed = ticket_data.get('creating_embed_inputs', True)
        modals = ticket_data.get('modals')
        item = None

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.tickets.modals.embed.title',
                         index=ticket_index),
            color=color,
            description=i18n.t(
                locale, 'settings.tickets.modals.embed.description')
        )

        if selected_item is not None:
            item = modals[selected_item]
            self.embed.add_field(
                name='',
                value=join_args(
                    (i18n.t(locale, 'settings.tickets.modals.info.embed'),
                     get_emoji(system_emoji,
                               created_embed)),
                    (i18n.t(locale, 'settings.tickets.modals.info.label'),
                     item.get('label')),
                    (i18n.t(locale, 'settings.tickets.modals.info.placeholder'),
                     item.get('placeholder')),
                    (i18n.t(locale, 'settings.tickets.modals.info.default'),
                     item.get('default_value')[:250]),
                    (i18n.t(locale, 'settings.tickets.modals.info.style'),
                     get_style(locale, item.get('style', 1))),
                    (i18n.t(locale, 'settings.tickets.modals.info.required'),
                     get_emoji(system_emoji,
                               item.get('required', True)))
                )
            )

        super().__init__()

        if modals is not None:
            if len(modals) >= 5:
                self.add.disabled = True
            self.clear.disabled = False
        if selected_item is not None:
            self.edit.disabled = False
            self.remove.disabled = False
        if created_embed:
            self.switch_creating_embed_inputs.label = i18n.t(
                locale, 'settings.tickets.modals.button.create_embeds.disable')
            self.switch_creating_embed_inputs.style = nextcord.ButtonStyle.red
        else:
            self.switch_creating_embed_inputs.label = i18n.t(
                locale, 'settings.tickets.modals.button.create_embeds.enable')
            self.switch_creating_embed_inputs.style = nextcord.ButtonStyle.green

        tfrdd = await TicketFormsRequiredDropDown(guild.id, item, selected_item)
        self.add_item(tfrdd)

        tfsdd = await TicketFormsStyleDropDown(guild.id, item, selected_item)
        self.add_item(tfsdd)

        tfdd = await TicketFormsDropDown(guild.id, modals, selected_item)
        self.add_item(tfdd)

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.add.label = i18n.t(locale, 'settings.button.add')
        self.edit.label = i18n.t(locale, 'settings.button.edit')
        self.remove.label = i18n.t(locale, 'settings.button.remove')
        self.clear.label = i18n.t(locale, 'settings.button.clear')

    @nextcord.ui.button(label='Add', style=nextcord.ButtonStyle.green, row=0)
    async def add(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        modal = await TicketFormsModal(interaction.guild, self.message_id)
        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label='Edit', style=nextcord.ButtonStyle.blurple, disabled=True, row=0)
    async def edit(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        modal = await TicketFormsModal(interaction.guild, self.message_id, self.selected_item)
        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label='Remove', style=nextcord.ButtonStyle.red, disabled=True, row=0)
    async def remove(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.message_id]
        with contextlib.suppress(IndexError):
            ticket_data['modals'].pop(self.selected_item)
        await gdb.set_on_json('tickets', self.message_id, ticket_data)

        view = await TicketFormsView(interaction.guild, self.message_id)
        embed = await view.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)

    @nextcord.ui.button(label='Enable creating embed inputs', style=nextcord.ButtonStyle.grey, row=1)
    async def switch_creating_embed_inputs(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.message_id]
        ticket_data['creating_embed_inputs'] = not ticket_data.get(
            'creating_embed_inputs')
        await gdb.set_on_json('tickets', self.message_id, ticket_data)

        view = await TicketFormsView(interaction.guild, self.message_id, self.selected_item)
        embed = await view.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)

    @nextcord.ui.button(label='Clear', style=nextcord.ButtonStyle.grey, disabled=True, row=1)
    async def clear(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.message_id]
        ticket_data['modals'] = []
        await gdb.set_on_json('tickets', self.message_id, ticket_data)

        view = await TicketFormsView(interaction.guild, self.message_id)
        embed = await view.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)
