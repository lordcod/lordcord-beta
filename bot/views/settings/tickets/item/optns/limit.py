import nextcord

from bot.databases.handlers.guildHD import GuildDateBases
from bot.databases.varstructs import TicketsPayload
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization
from .base import OptionItem


@AsyncSterilization
class UserLimitModal(nextcord.ui.Modal, OptionItem):
    label = 'settings.tickets.limit.label'
    description = 'settings.tickets.limit.description'
    emoji = 'ticlimit'

    async def __init__(self, guild: nextcord.Guild, message_id: int):
        self.message_id = message_id

        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[message_id]
        user_limit = ticket_data.get('user_tickets_limit')
        global_user_limit = ticket_data.get('global_user_tickets_limit')

        super().__init__(i18n.t(locale, 'settings.tickets.limit.title'))

        self.global_limit = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.tickets.limit.global_limit.label'),
            placeholder=i18n.t(
                locale, 'settings.tickets.limit.global_limit.placeholder'),
            default_value=global_user_limit,
            required=False,
            max_length=2
        )
        self.add_item(self.global_limit)

        self.limit = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.tickets.limit.user_limit.label'),
            placeholder=i18n.t(
                locale, 'settings.tickets.limit.user_limit.placeholder'),
            default_value=user_limit,
            required=False,
            max_length=2
        )
        self.add_item(self.limit)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.message_id]

        global_user_limit = self.global_limit.value
        user_limit = self.limit.value

        if (ticket_data.get('global_user_tickets_limit') == global_user_limit
                and ticket_data.get('user_tickets_limit') == user_limit
                or not global_user_limit
                and not user_limit):
            await self.update(interaction)
            return

        if (
            (global_user_limit and not global_user_limit.isdigit())
            or (user_limit and not user_limit.isdigit())
        ):
            await interaction.response.send_message(i18n.t(locale, 'settings.tickets.limit.invalid'),
                                                    ephemeral=True)
            await self.update(interaction)
            return

        if global_user_limit:
            ticket_data['global_user_tickets_limit'] = int(global_user_limit)
        if user_limit:
            ticket_data['user_tickets_limit'] = int(user_limit)

        await gdb.set_on_json('tickets', self.message_id, ticket_data)

        await self.update(interaction)
