from typing import Optional
import nextcord

from bot.databases.handlers.guildHD import GuildDateBases
from bot.databases.varstructs import TicketsPayload
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization, find_color_emoji

from .base import ViewOptionItem


@AsyncSterilization
class TicketModRolesDeleteDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild: nextcord.Guild, mod_roles: Optional[list]) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        if mod_roles is None:
            mod_roles = []

        options = [
            nextcord.SelectOption(
                label=f'@{role.name}',
                value=role.id,
                emoji=find_color_emoji(role.color.to_rgb())
            )
            for role_id in mod_roles
            if (role := guild.get_role(role_id))
        ]
        disabled = len(options) == 0
        if disabled:
            options.append(
                nextcord.SelectOption(label='SelectOption')
            )

        super().__init__(placeholder=i18n.t(locale, 'settings.tickets.mod_roles.dropdown.remove'),
                         options=options[:25], max_values=min(25, len(options)), row=0, disabled=disabled)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.view.message_id]
        ticket_data['moderation_roles'] = list(
            set(ticket_data.get('moderation_roles', [])) - set(map(int, self.values)))
        await gdb.set_on_json('tickets', self.view.message_id, ticket_data)

        view = await TicketModRolesView(interaction.guild, self.view.message_id)
        embed = await view.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)


@AsyncSterilization
class TicketModRolesDropDown(nextcord.ui.RoleSelect):
    async def __init__(self, guild: nextcord.Guild) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        super().__init__(placeholder=i18n.t(
            locale, 'settings.tickets.mod_roles.dropdown.add'), max_values=25, row=1)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.view.message_id]
        ticket_data['moderation_roles'] = list(
            set(ticket_data.get('moderation_roles', [])) | set(self.values.ids))
        await gdb.set_on_json('tickets', self.view.message_id, ticket_data)

        view = await TicketModRolesView(interaction.guild, self.view.message_id)
        embed = await view.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)


@AsyncSterilization
class TicketModRolesView(ViewOptionItem):
    label = 'settings.tickets.mod_roles.label'
    description = 'settings.tickets.mod_roles.description'
    emoji = 'ticmodroles'

    async def __init__(self, guild: nextcord.Guild, message_id: int):
        self.message_id = message_id

        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[message_id]
        mod_roles = ticket_data.get('moderation_roles')

        super().__init__()

        if mod_roles:
            self.clear.disabled = False

        self.edit_row_back(2)

        tmrdd = await TicketModRolesDropDown(guild)
        self.add_item(tmrdd)
        tmrdd = await TicketModRolesDeleteDropDown(guild, mod_roles)
        self.add_item(tmrdd)

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.clear.label = i18n.t(locale, 'settings.button.clear')

    @nextcord.ui.button(label='Clear', style=nextcord.ButtonStyle.red, disabled=True, row=2)
    async def clear(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.message_id]
        ticket_data['moderation_roles'] = []
        await gdb.set_on_json('tickets', self.message_id, ticket_data)

        view = await TicketModRolesView(interaction.guild, self.message_id)
        embed = await view.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)
