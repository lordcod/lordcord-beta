import asyncio
from typing import List
import nextcord

from bot.databases.varstructs import TicketsPayload
from bot.misc.utils import AsyncSterilization, get_emoji_wrap
from bot.resources.info import DEFAULT_TICKET_PAYLOAD, DEFAULT_TICKET_PAYLOAD_RU
from bot.views.settings.tickets.item.view import TicketsItemView
from .selector import TicketsSelectorView


from bot.misc.tickettools import ModuleTicket
from .._view import DefaultSettingsView

from bot.databases import GuildDateBases
from bot.views import settings_menu
from bot.languages import i18n


def get_category_name(channel: nextcord.TextChannel):
    if channel.category is None:
        return ''
    return f' ({channel.category.name})'


@AsyncSterilization
class TicketsDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild: nextcord.Guild):
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        get_emoji = await get_emoji_wrap(gdb)
        tickets: TicketsPayload = await gdb.get('tickets', {})

        options = []
        deleted_tickets = []

        for message_id, item in tickets.items():
            channel = guild.get_channel(item.get('channel_id'))

            if channel is None:
                deleted_tickets.append(message_id)
                continue

            index = len(options)+1
            options.append(nextcord.SelectOption(
                label=i18n.t(locale, 'settings.tickets.init.ticket',
                             index=index),
                value=message_id,
                description=f"#{channel}{get_category_name(channel)}",
                emoji=get_emoji(f'circle{index}')
            ))

        disabled = len(options) == 0
        if disabled:
            options.append(nextcord.SelectOption(label='SelectOption'))

        super().__init__(placeholder=i18n.t(locale, 'settings.tickets.init.dropdown'),
                         options=options, disabled=disabled)

        if len(deleted_tickets) > 0:
            self.process_delete_tickets(gdb, tickets, deleted_tickets)

    def process_delete_tickets(
        self,
        gdb: GuildDateBases,
        tickets: TicketsPayload,
        deleted_tickets: List[int]
    ) -> None:
        async def wrapped():
            for message_id in deleted_tickets:
                tickets.pop(message_id, None)
            await gdb.set('tickets', tickets)

        asyncio.create_task(wrapped())

    async def callback(self, interaction: nextcord.Interaction) -> None:
        message_id = int(self.values[0])

        view = await TicketsItemView(interaction.guild, message_id)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class TicketsView(DefaultSettingsView):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild) -> None:
        gdb = GuildDateBases(guild.id)
        color = await gdb.get('color')
        locale = await gdb.get('language')

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.tickets.init.title'),
            color=color,
            description=i18n.t(locale, 'settings.tickets.init.description'),
        )

        super().__init__()

        self.add_item(await TicketsDropDown(guild))

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.create.label = i18n.t(locale, 'settings.button.create')
        self.select.label = i18n.t(locale, 'settings.button.select')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        view = await settings_menu.SettingsView(interaction.user)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Create', style=nextcord.ButtonStyle.blurple)
    async def create(self,
                     button: nextcord.ui.Button,
                     interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')

        category = await interaction.guild.create_category(name='TICKET CATEGORY')
        channel = await interaction.guild.create_text_channel(
            name='ticket',
            category=category,
            overwrites={
                interaction.guild.default_role: nextcord.PermissionOverwrite(view_channel=True,
                                                                             read_message_history=True,
                                                                             send_messages=False,
                                                                             send_messages_in_threads=True)
            }
        )

        data = (DEFAULT_TICKET_PAYLOAD_RU if locale == 'ru'
                else DEFAULT_TICKET_PAYLOAD).copy()

        if category is not None:
            data.update({'category_id': category.id})

        await ModuleTicket.create_ticket_panel(channel, data)

        view = await TicketsView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Select', style=nextcord.ButtonStyle.success)
    async def select(self,
                     button: nextcord.ui.Button,
                     interaction: nextcord.Interaction):
        view = await TicketsSelectorView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
