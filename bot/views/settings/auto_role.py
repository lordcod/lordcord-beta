from typing import Any, Literal, Tuple
import nextcord

from bot.databases.varstructs import AutoRolesPayload
from bot.misc.utils import AsyncSterilization, find_color_emoji

from bot.views.settings._view import DefaultSettingsView

from bot.views import settings_menu
from bot.databases import GuildDateBases
from bot.languages import i18n


RoleMod = Literal['every', 'human', 'bot']
role_modes: Tuple[RoleMod, ...] = ('every', 'human', 'bot')


def parse_roles_data(data: Any) -> AutoRolesPayload:
    if not data:
        return {}
    if not isinstance(data, dict) or not set(role_modes) & set(data.keys()):
        return {'every': data}
    return data


@AsyncSterilization
class RolesModeDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild: nextcord.Guild, mode: RoleMod) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        options = [
            nextcord.SelectOption(
                label=i18n.t(locale, f'settings.auto-role.mods.{cur_mode}.label'),
                description=i18n.t(locale, f'settings.auto-role.mods.{cur_mode}.description'),
                value=cur_mode,
                default=cur_mode == mode
            )
            for cur_mode in role_modes
        ]
        disabled = len(options) == 0
        if disabled:
            options.append(
                nextcord.SelectOption(label='SelectOption')
            )

        super().__init__(options=options)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = self.values[0]

        view = await AutoRoleView(interaction.guild, value)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class RolesDeleteDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild: nextcord.Guild, mode: RoleMod) -> None:
        self.mode = mode

        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        roles_data: AutoRolesPayload = parse_roles_data(await gdb.get('auto_roles'))
        roles_ids = roles_data.get(mode, [])

        options = [
            nextcord.SelectOption(
                label=f'@{role.name}',
                value=role.id,
                emoji=find_color_emoji(role.color.to_rgb())
            )
            for role_id in roles_ids
            if (role := guild.get_role(role_id))
        ]
        disabled = len(options) == 0
        if disabled:
            options.append(
                nextcord.SelectOption(label='SelectOption')
            )

        super().__init__(
            placeholder=i18n.t(locale, 'settings.auto-role.placeholder.remove'),
            options=options[:25],
            max_values=min(25, len(options)),
            disabled=disabled
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)

        roles_data: AutoRolesPayload = parse_roles_data(await gdb.get('auto_roles', {}))
        roles_data[self.mode] = list(
            set(roles_data.get(self.mode, [])) - set(map(int, self.values)))
        await gdb.set('auto_roles', roles_data)

        view = await AutoRoleView(interaction.guild, self.mode)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class RolesDropDown(nextcord.ui.RoleSelect):
    async def __init__(
        self,
        guild: nextcord.Guild,
        mode: str
    ) -> None:
        self.mode = mode
        self.gdb = GuildDateBases(guild.id)
        locale = await self.gdb.get('language')

        super().__init__(
            placeholder=i18n.t(locale, 'settings.auto-role.placeholder.select'),
            min_values=1,
            max_values=25
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        locale = await self.gdb.get('language')

        for role in self.values.roles:
            if role.is_default():
                await interaction.response.send_message(
                    content=i18n.t(locale, 'settings.roles.error.default'),
                    ephemeral=True
                )
            elif role.is_premium_subscriber():
                await interaction.response.send_message(
                    content=i18n.t(locale, 'settings.roles.error.premium', role=role.mention),
                    ephemeral=True
                )
            elif role.is_integration() or role.is_bot_managed():
                await interaction.response.send_message(
                    content=i18n.t(locale, 'settings.roles.error.integration', role=role.mention),
                    ephemeral=True
                )
            elif not role.is_assignable():
                self_role = interaction.guild.self_role
                if self_role is None:
                    self_role = interaction.guild.me.top_role

                await interaction.response.send_message(
                    content=i18n.t(locale, 'settings.roles.error.assignable', role=role.mention, bot_role=self_role.mention),
                    ephemeral=True
                )
            else:
                continue
            break
        else:
            roles_data: AutoRolesPayload = parse_roles_data(await self.gdb.get('auto_roles', {}))
            roles_data[self.mode] = list(
                set(roles_data.get(self.mode, [])) | set(self.values.ids))
            await self.gdb.set('auto_roles', roles_data)

            view = await AutoRoleView(interaction.guild, self.mode)
            await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class AutoRoleView(DefaultSettingsView):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild, mode: str = 'every') -> None:
        self.gdb = GuildDateBases(guild.id)
        self.mode = mode
        color = await self.gdb.get('color')
        locale = await self.gdb.get('language')
        roles_data = parse_roles_data(await self.gdb.get('auto_roles', {}))
        roles_ids = roles_data.get(mode, [])

        super().__init__()

        self.add_item(await RolesModeDropDown(guild, mode))
        self.add_item(await RolesDeleteDropDown(guild, mode))
        self.add_item(await RolesDropDown(guild, mode))

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.auto-role.embed.title'),
            description=i18n.t(locale, 'settings.auto-role.embed.description'),
            color=color
        )
        for mode in role_modes:
            role_ids = roles_data.get(mode, [])
            data = '・'.join([role.mention
                            for role_id in role_ids
                            if (role := guild.get_role(role_id))])
            if not data:
                continue
            self.embed.add_field(
                name=i18n.t(locale, f'settings.auto-role.mods.{mode}.label'),
                value=data,
                inline=False
            )

        if not roles_data:
            self.delete_every.disabled = True
        if not roles_ids:
            self.delete.disabled = True

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.delete.label = i18n.t(locale, 'settings.auto-role.button.delete')
        self.delete_every.label = i18n.t(locale, 'settings.auto-role.button.delete_every')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        view = await settings_menu.SettingsView(interaction.user)

        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Clear roles', style=nextcord.ButtonStyle.red)
    async def delete(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        roles_data: AutoRolesPayload = parse_roles_data(await self.gdb.get('auto_roles'))
        roles_data.pop(self.mode)
        await self.gdb.set('auto_roles', roles_data)

        view = await AutoRoleView(interaction.guild, self.mode)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Clear all roles', style=nextcord.ButtonStyle.red)
    async def delete_every(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.gdb.set('auto_roles', {})

        view = await AutoRoleView(interaction.guild, self.mode)
        await interaction.response.edit_message(embed=view.embed, view=view)
