
from typing import List, Optional
import nextcord
import jmespath
from bot.languages import i18n
from bot.resources.info import COUNT_ROLES_PAGE
from bot.misc.utils import AsyncSterilization, parse_fission

from bot.databases import GuildDateBases
from bot.databases import EconomyMemberDB
from bot.views import menus
from bot.databases.varstructs import RoleShopPayload


@AsyncSterilization
class ShopAcceptView(nextcord.ui.View):
    async def __init__(
        self,
        guild_id: int,
        index: int,
        data: RoleShopPayload
    ) -> None:
        super().__init__(timeout=None)

        self.gdb = GuildDateBases(guild_id)
        self.role_index = index
        self.data = data

        locale = await self.gdb.get('language')
        economy_settings = await self.gdb.get('economic_settings')
        shop_info = economy_settings['shop']

        role_description = data.get(
            "description")+"\n\n" if data.get("description") else ""
        role_limit = data.get('limit')-data.get('using_limit',
                                                0) if data.get('limit') else '∞'
        self.embed = nextcord.Embed(
            title=data.get('name') or i18n.t(locale, 'shop.accept.title', number=shop_info.index(data)+1),
            description=i18n.t(locale, 'shop.accept.description',
                               description=role_description,
                               role_id=data.get('role_id'),
                               amount=data.get('amount'),
                               emoji=economy_settings.get('emoji'),
                               limit=role_limit)
        )

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.accept.label = i18n.t(locale, 'settings.button.accept')

    @nextcord.ui.button(label="Back", style=nextcord.ButtonStyle.red)
    async def back(self, button: nextcord.ui.Button, interaction: nextcord.Interaction) -> None:
        view = EconomyShopView(interaction.guild, self.role_index)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label="Accept", style=nextcord.ButtonStyle.green)
    async def accept(self, button: nextcord.ui.Button, interaction: nextcord.Interaction) -> None:
        locale = self.gdb.get('language')
        economy_settings = await self.gdb.get('economic_settings')
        shop_info = economy_settings.get(
            'shop', [])
        emdb = EconomyMemberDB(interaction.guild_id, interaction.user.id)
        balance = await emdb.get('balance')

        if self.data.get('role_id') in interaction.user._roles:
            await interaction.response.send_message(i18n.t(locale, "shop.error.already"),
                                                    ephemeral=True)
            return
        if self.data.get('limit') and self.data.get('using_limit', 0) >= self.data.get('limit'):
            await interaction.response.send_message(
                i18n.t(locale, "shop.error.limit"), ephemeral=True)
            return
        if self.data.get('amount') > balance:
            await interaction.response.send_message(i18n.t(locale, "shop.error.balance", amount=self.data.get('amount'), emoji=economy_settings.get('emoji')),
                                                    ephemeral=True)
            return
        try:
            await interaction.user._state.http.add_role(
                guild_id=interaction.guild_id,
                user_id=interaction.user.id,
                role_id=self.data.get('role_id'),
                reason="Buying a role in the store"
            )
        except nextcord.HTTPException:
            await interaction.user.send(
                f"[**{interaction.guild.name}**] Shop role was not found! Contact the server administrators!")
            return
        for rd in shop_info:
            if rd.get('role_id') == self.data.get('role_id'):
                rd['using_limit'] = rd.get('using_limit', 0) + 1
        economy_settings['shop'] = shop_info
        await self.gdb.set('economic_settings', economy_settings)
        emdb.decline('balance', self.data.get('amount'))

        await interaction.response.send_message(i18n.t(locale, "shop.accept.success"),
                                                ephemeral=True)

        view = await EconomyShopView(interaction.guild, self.role_index)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class EconomyShopDropdown(nextcord.ui.StringSelect):
    async def __init__(
        self,
        guild_id: int,
        index: int,
        data: List[RoleShopPayload]
    ) -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        self.data = data
        self.role_index = index

        options = [
            nextcord.SelectOption(
                label=role.get('name') or i18n.t(locale, "shop.accept.title", number=num),
                value=role.get('role_id'),
                description=role.get('description')
            )
            for num, role in enumerate(data, start=1+index*COUNT_ROLES_PAGE)
        ]

        disabled = 0 >= len(options)
        if 0 >= len(options):
            options.append(label="Option")

        super().__init__(placeholder=i18n.t(locale, "shop.dropdown.placeholder"), options=options, disabled=disabled)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        economy_settings = await gdb.get('economic_settings')
        emdb = EconomyMemberDB(interaction.guild_id, interaction.user.id)
        role_id = int(self.values[0])
        role_data: RoleShopPayload = jmespath.search(
            f'[?role_id==`{role_id}`]|[0]', self.data)
        balance = await emdb.get('balance')

        if role_id in interaction.user._roles:
            await interaction.response.send_message(i18n.t(locale, "shop.error.already"),
                                                    ephemeral=True)
            return
        if role_data.get('limit') and role_data.get('using_limit', 0) >= role_data.get('limit'):
            await interaction.response.send_message(
                i18n.t(locale, "shop.error.limit"), ephemeral=True)
            return
        if role_data.get('amount') > balance:
            await interaction.response.send_message(i18n.t(locale, "shop.error.balance",
                                                           amount=self.data.get('amount'),
                                                           emoji=economy_settings.get('emoji')),
                                                    ephemeral=True)
            return

        view = await ShopAcceptView(interaction.guild_id,
                                    self.role_index, role_data)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class EconomyShopView(menus.Menus):
    value: List[List[RoleShopPayload]]

    async def __init__(
        self,
        guild: nextcord.Guild,
        index: Optional[int] = None
    ):
        self.guild = guild
        self.gdb = GuildDateBases(guild.id)
        self.locale = await self.gdb.get('language')
        self.economy_settings = await self.gdb.get('economic_settings')
        shop_info = self.economy_settings.get('shop', [])
        eft = parse_fission(shop_info, COUNT_ROLES_PAGE)

        super().__init__(eft)

        self.index = index if index else self.index
        self.add_item(await self.get_shop_dropdown())
        self.remove_item(self.button_previous)
        self.remove_item(self.button_next)

        self.handler_disable()

    @property
    def embed(self) -> nextcord.Embed:
        embed = nextcord.Embed(
            title=i18n.t(self.locale, 'shop.embed.title', name=self.guild.name),
            description=i18n.t(self.locale, 'shop.embed.description')
        )
        for num, role in enumerate(self.value[self.index], start=1+COUNT_ROLES_PAGE*self.index):
            role_limit = role.get('limit')-role.get('using_limit',
                                                    0) if role.get('limit') else '∞'
            embed.add_field(
                name=role.get('name') or i18n.t(self.locale, 'shop.accept.title', number=num),
                value=i18n.t(self.locale, 'shop.accept.description',
                             description='',
                             role_id=role.get('role_id'),
                             amount=role.get('amount'),
                             emoji=self.economy_settings.get('emoji'),
                             limit=role_limit),
                inline=False
            )
        embed.set_footer(text=i18n.t(self.locale, 'shop.embed.footer', index=self.index+1, lenght=self.len))
        return embed

    def get_shop_dropdown(self) -> EconomyShopDropdown:
        return EconomyShopDropdown(self.guild.id, self.index, self.value[self.index])

    async def callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        view = await EconomyShopView(interaction.guild, self.index)
        await interaction.response.edit_message(embed=view.embed, view=view)
