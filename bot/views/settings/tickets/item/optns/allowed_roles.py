from typing import Optional
import nextcord

from bot.databases.handlers.guildHD import GuildDateBases
from bot.databases.varstructs import TicketsPayload
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization,  find_color_emoji

from .base import ViewOptionItem


@AsyncSterilization
class TicketAllowedRolesDeleteDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild: nextcord.Guild, approved_roles: Optional[list]) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        if approved_roles is None:
            approved_roles = []

        options = [
            nextcord.SelectOption(
                label=f'@{role.name}',
                value=role.id,
                emoji=find_color_emoji(role.color.to_rgb())
            )
            for role_id in approved_roles
            if (role := guild.get_role(role_id))
        ]
        disabled = len(options) == 0
        if disabled:
            options.append(
                nextcord.SelectOption(label='SelectOption')
            )

        super().__init__(placeholder=i18n.t(locale, 'settings.tickets.allow_roles.dropdown.remove'),
                         options=options[:25], max_values=min(25, len(options)), row=0, disabled=disabled)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.view.message_id]
        ticket_data['approved_roles'] = list(
            set(ticket_data.get('approved_roles', [])) - set(map(int, self.values)))
        await gdb.set_on_json('tickets', self.view.message_id, ticket_data)

        await self.view.update(interaction)


@AsyncSterilization
class TicketAllowedRolesDropDown(nextcord.ui.RoleSelect):
    async def __init__(self, guild: nextcord.Guild) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        super().__init__(placeholder=i18n.t(
            locale, 'settings.tickets.allow_roles.dropdown.add'), max_values=25, row=1)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.view.message_id]

        for role in self.values.roles:
            if role.is_default():
                await interaction.response.send_message(
                    content=i18n.t(locale, 'settings.roles.error.default'),
                    ephemeral=True
                )
            elif role.is_premium_subscriber():
                await interaction.response.send_message(
                    content=i18n.t(
                        locale, 'settings.roles.error.premium', role=role.mention),
                    ephemeral=True
                )
            elif role.is_integration() or role.is_bot_managed():
                await interaction.response.send_message(
                    content=i18n.t(
                        locale, 'settings.roles.error.integration', role=role.mention),
                    ephemeral=True
                )
            elif not role.is_assignable():
                await interaction.response.send_message(
                    content=i18n.t(locale, 'settings.roles.error.assignable',
                                   role=role.mention, bot_role=interaction.guild.self_role.mention),
                    ephemeral=True
                )
            else:
                continue
            break
        else:
            ticket_data['approved_roles'] = list(
                set(ticket_data.get('approved_roles', [])) | set(self.values.ids))
            await gdb.set_on_json('tickets', self.view.message_id, ticket_data)

            await self.view.update(interaction)


@AsyncSterilization
class TicketAllowedRolesView(ViewOptionItem):
    label = 'settings.tickets.allow_roles.label'
    description = 'settings.tickets.allow_roles.description'
    emoji = 'ticallowedroles'

    async def __init__(self, guild: nextcord.Guild, message_id: int):
        self.message_id = message_id

        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[message_id]
        approved_roles = ticket_data.get('approved_roles')

        super().__init__()

        self.edit_row_back(2)

        if 'approved_roles' in ticket_data:
            self.clear.disabled = False
            self.delete.disabled = False

        tmrddd = await TicketAllowedRolesDeleteDropDown(guild, approved_roles)
        self.add_item(tmrddd)
        tmrdd = await TicketAllowedRolesDropDown(guild)
        self.add_item(tmrdd)

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.clear.label = i18n.t(locale, 'settings.button.clear')
        self.delete.label = i18n.t(locale, 'settings.button.delete')

    @nextcord.ui.button(label='Clear', style=nextcord.ButtonStyle.red, disabled=True, row=2)
    async def clear(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.message_id]
        ticket_data['approved_roles'] = []
        await gdb.set_on_json('tickets', self.message_id, ticket_data)

        view = await TicketAllowedRolesView(interaction.guild, self.message_id)
        embed = await view.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)

    @nextcord.ui.button(label='Delete', style=nextcord.ButtonStyle.red, disabled=True, row=2)
    async def delete(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.message_id]
        ticket_data['approved_roles'] = None
        await gdb.set_on_json('tickets', self.message_id, ticket_data)

        view = await TicketAllowedRolesView(interaction.guild, self.message_id)
        embed = await view.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)
