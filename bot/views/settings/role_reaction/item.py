
import asyncio
from typing import Optional
import nextcord
from bot.databases import GuildDateBases
from bot.databases.varstructs import ReactionRoleItemPayload
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization

from .._view import DefaultSettingsView
from .. import role_reaction
from ..set_reaction import fetch_reaction


@AsyncSterilization
class RoleReactionRegisterItemDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild: nextcord.Guild, message_id: int, channel_id: int, role_reaction: ReactionRoleItemPayload, selected_role: Optional[nextcord.Role] = None) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        self.message_id = message_id
        self.channel_id = channel_id
        self.role_reaction = role_reaction

        options = [
            nextcord.SelectOption(
                label=f"@{role.name}",
                value=role_id,
                emoji=emoji,
                default=selected_role == role
            )
            for emoji, role_id in role_reaction['reactions'].items()
            if (role := guild.get_role(role_id))
        ]

        disabled = 0 >= len(options)
        if 0 >= len(options):
            options.append(nextcord.SelectOption(label="SelectOption"))

        super().__init__(placeholder=i18n.t(locale,
                                            "settings.role-reaction.item.role-set-dropdown"), options=options, disabled=disabled)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        role_id = int(self.values[0])
        role = interaction.guild.get_role(role_id)

        view = await RoleReactionItemView(
            interaction.guild, self.message_id, self.channel_id, self.role_reaction, role)
        await interaction.message.edit(embed=view.embed, view=view)


@AsyncSterilization
class RoleReactionItemDropDown(nextcord.ui.RoleSelect):
    async def __init__(self, guild: nextcord.Guild, message_id: int, channel_id: int, role_reaction: ReactionRoleItemPayload) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        self.message_id = message_id
        self.channel_id = channel_id
        self.role_reaction = role_reaction

        super().__init__(placeholder=i18n.t(locale, "settings.role-reaction.item.role-dropdown"))

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        role: nextcord.Role = self.values[0]

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
            bot_role = interaction.guild.self_role or interaction.client.user
            await interaction.response.send_message(
                content=i18n.t(locale, 'settings.roles.error.assignable',
                               role=role.mention, bot_role=bot_role.mention),
                ephemeral=True
            )
        else:
            view = await RoleReactionItemView(
                interaction.guild, self.message_id, self.channel_id, self.role_reaction, role)
            await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class RoleReactionItemView(DefaultSettingsView):
    embed: nextcord.Embed = None

    async def __init__(self, guild: nextcord.Guild, message_id: int, channel_id: int, role_reaction: ReactionRoleItemPayload, selected_role: Optional[nextcord.Role] = None):
        gdb = GuildDateBases(guild.id)
        color = await gdb.get('color')
        locale = await gdb.get('language')

        self.selected_role = selected_role
        self.role_reaction = role_reaction
        self.message_id = message_id
        self.channel_id = channel_id

        super().__init__()

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.role-reaction.global.title'),
            description=i18n.t(
                locale, 'settings.role-reaction.global.description'),
            color=color
        )
        if role_reaction['reactions']:
            self.embed.add_field(
                name=i18n.t(locale, 'settings.role-reaction.item.field'),
                value='\n'.join([
                    f"・{emoji} - <@&{role_id}>"
                    for emoji, role_id in role_reaction['reactions'].items()
                ])
            )
            self.create.disabled = False
        if selected_role:
            self.update.disabled = False
            self.delete.disabled = False

        self.add_item(await RoleReactionRegisterItemDropDown(
            guild, message_id, channel_id, role_reaction, selected_role))
        self.add_item(await RoleReactionItemDropDown(
            guild, message_id, channel_id, role_reaction))

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.create.label = i18n.t(locale, 'settings.button.create')
        self.update.label = i18n.t(locale, 'settings.button.edit')
        self.delete.label = i18n.t(locale, 'settings.button.delete')

    @nextcord.ui.button(label="Back", style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction
                   ):
        view = await role_reaction.RoleReactionView(interaction.guild)

        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label="Create", style=nextcord.ButtonStyle.blurple, disabled=True)
    async def create(self,
                     button: nextcord.ui.Button,
                     interaction: nextcord.Interaction
                     ):
        channel = interaction.guild.get_channel(self.channel_id)
        message = channel.get_partial_message(self.message_id)

        for react in self.role_reaction['reactions']:
            asyncio.create_task(message.add_reaction(react))

        gdb = GuildDateBases(interaction.guild.id)
        await gdb.set_on_json('role_reactions', self.message_id, self.role_reaction)

        await self.back.callback(interaction)

    @nextcord.ui.button(label="Edit", style=nextcord.ButtonStyle.success, disabled=True)
    async def update(self,
                     button: nextcord.ui.Button,
                     interaction: nextcord.Interaction
                     ):
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        value = await fetch_reaction(interaction, content=i18n.t(locale, 'settings.role-reaction.item.fetch_reaction',
                                                                 role=self.selected_role))

        for _emoji, _role_id in list(self.role_reaction['reactions'].items()):
            if _role_id == self.selected_role.id:
                self.role_reaction['reactions'].pop(_emoji)
        self.role_reaction['reactions'][value] = self.selected_role.id

        view = await RoleReactionItemView(
            interaction.guild, self.message_id, self.channel_id, self.role_reaction, self.selected_role)
        await interaction.message.edit(embed=view.embed, view=view)

    @nextcord.ui.button(label="Delete", style=nextcord.ButtonStyle.red, disabled=True)
    async def delete(self,
                     button: nextcord.ui.Button,
                     interaction: nextcord.Interaction
                     ):
        for _emoji, _role_id in list(self.role_reaction['reactions'].items()):
            if _role_id == self.selected_role.id:
                self.role_reaction['reactions'].pop(_emoji)

        view = RoleReactionItemView(
            interaction.guild, self.message_id, self.channel_id, self.role_reaction)
        await interaction.response.edit_message(embed=view.embed, view=view)
