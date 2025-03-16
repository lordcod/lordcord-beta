import nextcord

from bot.languages import i18n
from bot.misc.time_transformer import display_time
from bot.misc.utils import AsyncSterilization, get_emoji_wrap

from bot.resources.info import DEFAULT_ECONOMY_SETTINGS
from bot.views.information_dd import get_info_dd
from bot.views.settings.economy.theft import TheftView

from .emoji import EmojiView
from .bonuses import BonusView
from .shop import ShopView
from .._view import DefaultSettingsView

from bot.resources.ether import Emoji
from bot.databases import GuildDateBases
from bot.views import settings_menu


@AsyncSterilization
class ChooseDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild_id: int):
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        get_emoji = await get_emoji_wrap(guild_id)

        options = [
            nextcord.SelectOption(
                label=i18n.t(locale, 'settings.economy.init.dropdown.bonus'),
                emoji=Emoji.bagmoney,
                value='bonus'
            ),
            nextcord.SelectOption(
                label=i18n.t(locale, 'settings.economy.init.dropdown.emoji'),
                emoji=Emoji.emoji,
                value='emoji'
            ),
            nextcord.SelectOption(
                label=i18n.t(locale, 'settings.economy.init.dropdown.shop'),
                emoji=Emoji.auto_role,
                value='shop'
            ),
            nextcord.SelectOption(
                label=i18n.t(locale, 'settings.economy.init.dropdown.theft'),
                emoji=Emoji.theft,
                value='theft'
            ),
        ]

        super().__init__(
            placeholder=i18n.t(locale, 'settings.economy.init.dropdown.placeholder'),
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = self.values[0]
        distrubutes = {
            'bonus': BonusView,
            'emoji': EmojiView,
            'shop': ShopView,
            'theft': TheftView
        }
        view = await distrubutes[value](interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class Economy(DefaultSettingsView):
    async def __init__(self, guild: nextcord.Guild) -> None:
        self.gdb = GuildDateBases(guild.id)
        color: int = await self.gdb.get('color')
        locale: str = await self.gdb.get('language')
        self.es: dict = await self.gdb.get('economic_settings')
        operate: bool = self.es.get('operate')

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.economy.init.embed.title'),
            description=i18n.t(locale, 'settings.economy.init.embed.description'),
            color=color
        )
        self.embed.add_field(
            name=i18n.t(locale, 'settings.economy.init.info.name'),
            value=i18n.t(
                locale, 'settings.economy.init.info.value',
                daily=self.es.get('daily'),
                weekly=self.es.get('weekly'),
                monthly=self.es.get('monthly'),
                bet_min=self.es.get('bet', DEFAULT_ECONOMY_SETTINGS['bet']).get('min'),
                bet_max=self.es.get('bet', DEFAULT_ECONOMY_SETTINGS['bet']).get('max'),
                work_min=self.es.get('work', DEFAULT_ECONOMY_SETTINGS['work']).get('min'),
                work_max=self.es.get('work', DEFAULT_ECONOMY_SETTINGS['work']).get('max'),
                cooldown=display_time(self.es.get('work', DEFAULT_ECONOMY_SETTINGS['work']).get('cooldown'), locale),
            )
        )

        super().__init__()

        self.add_item(get_info_dd(
            label=i18n.t(locale, 'settings.economy.init.emoji'),
            emoji=self.es.get('emoji')
        ))
        economy_dd = await ChooseDropDown(guild.id)
        self.add_item(economy_dd)

        self.back.label = i18n.t(locale, 'settings.button.back')

        if operate:
            self.economy_switcher.label = i18n.t(locale, 'settings.button.disable')
            self.economy_switcher.style = nextcord.ButtonStyle.red
            self.economy_switcher_value = False
        else:
            self.economy_switcher.label = i18n.t(locale, 'settings.button.enable')
            self.economy_switcher.style = nextcord.ButtonStyle.green
            self.economy_switcher_value = True

            economy_dd.disabled = True

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        view = await settings_menu.SettingsView(interaction.user)

        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Switch', style=nextcord.ButtonStyle.green)
    async def economy_switcher(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.gdb.set_on_json('economic_settings', 'operate',
                                   self.economy_switcher_value)

        view = await Economy(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
