import nextcord
import jmespath
from bot.databases import GuildDateBases
from bot.databases.varstructs import RoleShopPayload
from typing import List, Optional
from copy import deepcopy

from bot.languages import i18n
from bot.misc.utils import AsyncSterilization

from .. import economy
from .._view import DefaultSettingsView


def get_role_data(role_id: int, roles: List[RoleShopPayload]) -> RoleShopPayload:
    return jmespath.search(
        f'[?role_id==`{role_id}`]|[0]', roles)


def update_role_data(
    role_data: RoleShopPayload,
    roles: List[RoleShopPayload]
) -> List[RoleShopPayload]:
    roles = roles or []
    new_roles = deepcopy(roles)
    for index, rd in enumerate(roles):
        if rd.get('role_id') != role_data.get('role_id'):
            continue
        new_roles[index] = role_data
        break
    else:
        new_roles.append(role_data)
    return new_roles


@AsyncSterilization
class ShopModal(nextcord.ui.Modal):
    async def __init__(self, guild_id: int, role_id: int) -> None:
        self.role_id = role_id
        self.gdb = GuildDateBases(guild_id)
        locale = await self.gdb.get('language')
        economy_settings = await self.gdb.get('economic_settings', {})
        shop_info = economy_settings.get('shop')
        self.role_data = role_data = get_role_data(role_id, shop_info) or {}

        super().__init__(i18n.t(locale, 'settings.economy.shop.title'))

        self.amount = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.economy.shop.amount'),
            custom_id="shop:amount",
            max_length=6,
            placeholder=role_data.get('amount')
        )
        if role_data.get('amount'):
            self.amount.required = False
        self.add_item(self.amount)

        self.limit = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.economy.shop.limit'),
            custom_id="shop:limit",
            max_length=3,
            placeholder=role_data.get('limit'),
            required=False
        )
        self.add_item(self.limit)

        self.name = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.economy.shop.name'),
            custom_id="shop:name",
            max_length=100,
            placeholder=role_data.get('name'),
            required=False
        )
        self.add_item(self.name)

        self.description = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.economy.shop.description'),
            custom_id="shop:description",
            style=nextcord.TextInputStyle.paragraph,
            placeholder=role_data.get('description'),
            required=False
        )
        self.add_item(self.description)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        self.gdb = GuildDateBases(interaction.guild_id)
        locale = await self.gdb.get('language')

        if not self.amount.value.isdigit():
            await interaction.response.send_message(i18n.t(locale, 'settings.economy.shop.error.type.amount'), ephemeral=True)
            return
        if self.limit.value and not self.limit.value.isdigit():
            await interaction.response.send_message(i18n.t(locale, 'settings.economy.shop.error.type.limit'), ephemeral=True)
            return

        economy_settings = await self.gdb.get('economic_settings', {})
        shop_info = economy_settings.get('shop')

        if not self.role_data:
            self.role_data = {
                "role_id": self.role_id,
                "amount": int(self.amount.value),
                "limit": self.limit.value and int(self.limit.value),
                "name": self.name.value,
                "description": self.description.value
            }
        else:
            self.role_data = {
                "role_id": self.role_id,
                "amount": int(self.amount.value) or self.role_data.get('amount'),
                "limit": self.limit.value and int(self.limit.value) or self.role_data.get('limit'),
                "name": self.name.value or self.role_data.get('name'),
                "description": self.description.value or self.role_data.get('description'),
                "using_limit":  self.role_data.get('using_limit')
            }
        shop_info = update_role_data(self.role_data, shop_info)
        economy_settings['shop'] = shop_info
        await self.gdb.set('economic_settings', economy_settings)

        view = await ShopView(interaction.guild,
                              interaction.guild.get_role(self.role_id))
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class ShopDropDown(nextcord.ui.RoleSelect):
    async def __init__(self, guild_id):
        self.gdb = GuildDateBases(guild_id)
        locale = await self.gdb.get('language')

        super().__init__(
            placeholder=i18n.t(locale, 'settings.economy.shop.placeholder'),
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')

        role = self.values[0]

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
            view = await ShopView(interaction.guild, role)
            await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class ShopView(DefaultSettingsView):
    embed: nextcord.Embed = None

    async def __init__(self, guild: nextcord.Guild, selected_role: Optional[nextcord.Role] = None) -> None:
        self.selected_role = selected_role
        self.gdb = GuildDateBases(guild.id)
        locale = await self.gdb.get('language')
        economy_settings = await self.gdb.get('economic_settings')
        shop_info = economy_settings.get('shop', [])
        super().__init__()

        dd = await ShopDropDown(guild.id)
        self.add_item(dd)

        if selected_role and (data := get_role_data(selected_role.id, shop_info)):
            role_description = data.get(
                "description")+"\n\n" if data.get("description") else ""
            role_limit = data.get('limit')-data.get('using_limit',
                                                    0) if data.get('limit') else '∞'
            self.embed = nextcord.Embed(
                title=data.get('name') or i18n.t(
                    locale, 'settings.economy.shop.title')+f" #{shop_info.index(data)+1}",
                description=i18n.t(locale, 'settings.economy.shop.role_description',
                                   description=role_description,
                                   role_id=data.get('role_id'),
                                   emoji=economy_settings.get('emoji'),
                                   limit=role_limit)
            )
            self.edit.disabled = False
            self.delete.disabled = False
        if selected_role and not get_role_data(selected_role.id, shop_info):
            self.create.disabled = False

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.create.label = i18n.t(locale, 'settings.button.create')
        self.edit.label = i18n.t(locale, 'settings.button.edit')
        self.delete.label = i18n.t(locale, 'settings.button.delete')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        view = await economy.Economy(interaction.guild)

        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label="Create", style=nextcord.ButtonStyle.success, disabled=True)
    async def create(self,
                     button: nextcord.ui.Button,
                     interaction: nextcord.Interaction):
        modal = await ShopModal(interaction.guild_id, self.selected_role.id)
        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label="Edit", style=nextcord.ButtonStyle.blurple, disabled=True)
    async def edit(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        modal = await ShopModal(interaction.guild_id, self.selected_role.id)
        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label="Delete", style=nextcord.ButtonStyle.red, disabled=True)
    async def delete(self,
                     button: nextcord.ui.Button,
                     interaction: nextcord.Interaction):
        economy_settings = await self.gdb.get('economic_settings')
        shop_info: list = economy_settings.get('shop', [])
        role_data = get_role_data(self.selected_role.id, shop_info)
        shop_info.remove(role_data)
        economy_settings['shop'] = shop_info
        await self.gdb.set('economic_settings', economy_settings)

        view = await ShopView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
