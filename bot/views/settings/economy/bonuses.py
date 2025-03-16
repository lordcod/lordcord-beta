from typing import Optional
import nextcord
from bot.databases import GuildDateBases
from bot.languages import i18n
from bot.misc.utils import TimeCalculator, AsyncSterilization

from bot.resources.info import DEFAULT_ECONOMY_SETTINGS
from .. import economy
from .._view import DefaultSettingsView


reward_names = [
    'daily',
    'weekly',
    'monthly'
]


@AsyncSterilization
class RewardBonusModal(nextcord.ui.Modal):
    async def __init__(self, guild: nextcord.Guild, value: str) -> None:
        self.gdb = GuildDateBases(guild.id)
        locale = await self.gdb.get('language')
        self.economy_settings = await self.gdb.get('economic_settings', {})
        self.value = value
        previous = self.economy_settings.get(value)

        label = i18n.t(locale, 'settings.economy.bonus.'+value)
        super().__init__(label, timeout=300)
        self.bonus = nextcord.ui.TextInput(
            label=label,
            placeholder=previous,
            max_length=6
        )
        self.add_item(self.bonus)

    async def callback(self, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        bonus = self.bonus.value

        if not bonus.isdigit():
            return

        await gdb.set_on_json('economic_settings', self.value, int(bonus))

        view = await BonusView(interaction.guild)
        await interaction.message.edit(embed=view.embed, view=view)


@AsyncSterilization
class WorkBonusModal(nextcord.ui.Modal):
    async def __init__(self, guild: nextcord.Guild) -> None:
        super().__init__('Work', timeout=300)
        self.gdb = GuildDateBases(guild.id)
        locale = await self.gdb.get('language')
        self.economy_settings = await self.gdb.get('economic_settings', {})
        work_data = self.economy_settings.get('work')
        _min_work_previous = work_data.get('min')
        _max_work_previous = work_data.get('max')
        _cooldwon_previous = work_data.get('cooldown')

        self.min_work = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.economy.bonus.min_work'),
            placeholder=_min_work_previous,
            required=False,
            max_length=6
        )
        self.add_item(self.min_work)

        self.max_work = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.economy.bonus.max_work'),
            placeholder=_max_work_previous,
            required=False,
            max_length=6
        )
        self.add_item(self.max_work)

        self.cooldown = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.economy.bonus.cooldown'),
            placeholder=_cooldwon_previous,
            required=False,
            max_length=20
        )
        self.add_item(self.cooldown)

    async def callback(self, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        cooldown = None

        if not (self.min_work.value or self.min_work.value or self.cooldown.value):
            await interaction.response.send_message(i18n.t(locale, 'settings.economy.error.no_selected'), ephemeral=True)
            return
        if (self.min_work.value and not self.min_work.value.isdigit()) or (self.max_work.value and not self.max_work.value.isdigit()):
            await interaction.response.send_message(i18n.t(locale, 'settings.economy.error.type'), ephemeral=True)
            return
        if self.cooldown.value:
            try:
                cooldown = TimeCalculator().convert(self.cooldown.value)
            except TypeError:
                await interaction.response.send_message(i18n.t(locale, 'settings.economy.error.type_time'), ephemeral=True)
                return

        economy_settings = await gdb.get('economic_settings')
        work_data = self.economy_settings.get('work')

        if self.min_work.value:
            work_data['min'] = int(self.min_work.value)
        if self.max_work.value:
            work_data['max'] = int(self.max_work.value)
        if cooldown:
            work_data['cooldown'] = cooldown

        economy_settings['work'] = work_data
        await gdb.set('economic_settings', economy_settings)

        view = BonusView(interaction.guild)
        await interaction.message.edit(embed=view.embed, view=view)


@AsyncSterilization
class BetBonusModal(nextcord.ui.Modal):
    async def __init__(self, guild: nextcord.Guild) -> None:
        super().__init__('Bet', timeout=300)
        self.gdb = GuildDateBases(guild.id)
        locale = await self.gdb.get('language')
        self.economy_settings = await self.gdb.get('economic_settings', {})
        work_data = self.economy_settings.get('bet')
        _min_bet_previous = work_data.get('min')
        _max_bet_previous = work_data.get('max')

        self.min_bet = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.economy.bonus.min_bet'),
            placeholder=_min_bet_previous,
            required=False,
            max_length=6
        )
        self.add_item(self.min_bet)

        self.max_bet = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.economy.bonus.max_bet'),
            placeholder=_max_bet_previous,
            required=False,
            max_length=6
        )
        self.add_item(self.max_bet)

    async def callback(self, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')

        if not (self.min_bet.value or self.min_bet.value):
            await interaction.response.send_message(i18n.t(locale, 'settings.economy.error.no_selected'), ephemeral=True)
            return
        if (self.min_bet.value and not self.min_bet.value.isdigit()) or (self.max_bet.value and not self.max_bet.value.isdigit()):
            await interaction.response.send_message(i18n.t(locale, 'settings.economy.error.type'), ephemeral=True)
            return

        economy_settings = await gdb.get('economic_settings')
        bet_data = self.economy_settings.get('bet')
        if self.min_bet.value:
            bet_data['min'] = int(self.min_bet.value)
        if self.max_bet.value:
            bet_data['max'] = int(self.max_bet.value)
        economy_settings['bet'] = bet_data

        await gdb.set('economic_settings', economy_settings)

        view = BonusView(interaction.guild)
        await interaction.message.edit(embed=view.embed, view=view)


@AsyncSterilization
class BonusDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild_id: int, selected_value: Optional[str] = None):
        self.gdb = GuildDateBases(guild_id)
        locale = await self.gdb.get('language')
        self.economy_settings = await self.gdb.get('economic_settings', {})
        options = [
            nextcord.SelectOption(
                label=i18n.t(locale, 'settings.economy.bonus.daily'),
                value='daily',
                default='daily' == selected_value
            ),
            nextcord.SelectOption(
                label=i18n.t(locale, 'settings.economy.bonus.weekly'),
                value='weekly',
                default='weekly' == selected_value
            ),
            nextcord.SelectOption(
                label=i18n.t(locale, 'settings.economy.bonus.monthly'),
                value='monthly',
                default='monthly' == selected_value
            ),
            nextcord.SelectOption(
                label=i18n.t(locale, 'settings.economy.bonus.work'),
                value='work',
                default='work' == selected_value
            ),
            nextcord.SelectOption(
                label=i18n.t(locale, 'settings.economy.bonus.bet'),
                value='bet',
                default='bet' == selected_value
            )
        ]

        super().__init__(
            placeholder=i18n.t(locale, 'settings.economy.bonus.dropdown.placeholder'),
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = self.values[0]
        view = await BonusView(interaction.guild, value)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class BonusView(DefaultSettingsView):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild, value: Optional[str] = None) -> None:
        self.value = value
        self.embed = (await economy.Economy(guild)).embed
        self.gdb = GuildDateBases(guild.id)
        locale = await self.gdb.get('language')

        super().__init__()

        if value:
            self.edit.disabled = False
            self.reset.disabled = False
        self.add_item(await BonusDropDown(guild.id, value))

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.edit.label = i18n.t(locale, 'settings.button.edit')
        self.reset.label = i18n.t(locale, 'settings.button.reset')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        view = await economy.Economy(interaction.guild)
        await interaction.message.edit(embed=view.embed, view=view)

    @nextcord.ui.button(label='Edit', style=nextcord.ButtonStyle.success, disabled=True)
    async def edit(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        if self.value in reward_names:
            modal = await RewardBonusModal(interaction.guild, self.value)
        if self.value == 'work':
            modal = await WorkBonusModal(interaction.guild)
        if self.value == 'bet':
            modal = await BetBonusModal(interaction.guild)
        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label='Reset', style=nextcord.ButtonStyle.blurple, disabled=True)
    async def reset(self,
                    button: nextcord.ui.Button,
                    interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set_on_json('economic_settings', self.value, DEFAULT_ECONOMY_SETTINGS[self.value])

        view = await BonusView(interaction.guild, self.value)
        await interaction.message.edit(embed=view.embed, view=view)
