import nextcord

from bot.languages import i18n
from bot.misc.time_transformer import display_time
from bot.views.information_dd import get_info_dd

from bot.databases import GuildDateBases
from bot.databases.varstructs import IdeasPayload
from bot.misc.utils import TimeCalculator, AsyncSterilization
from .base import ViewOptionItem


@AsyncSterilization
class CooldownModal(nextcord.ui.Modal):
    async def __init__(self, guild_id: int):
        self.gdb = GuildDateBases(guild_id)
        locale = await self.gdb.get('language')

        super().__init__("Cooldown")

        self.coldtime = nextcord.ui.TextInput(
            i18n.t(locale, 'settings.ideas.cooldown.modal.title'),
            max_length=100
        )
        self.add_item(self.coldtime)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        locale = await self.gdb.get('language')
        try:
            cooltime = TimeCalculator(operatable_time=False).convert(self.coldtime.value)
        except ValueError:
            await interaction.response.send_message(i18n.t(locale, 'settings.ideas.cooldown.modal.error'))
            return
        await self.gdb.set_on_json('ideas', 'cooldown', cooltime)

        view = await CooldownView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class CooldownView(ViewOptionItem):
    label: str = 'settings.ideas.dropdown.cooldown.title'
    description: str = 'settings.ideas.dropdown.cooldown.description'
    emoji: str = 'ideacd'

    async def __init__(self, guild: nextcord.Guild) -> None:
        self.gdb = GuildDateBases(guild.id)
        self.idea_data: IdeasPayload = await self.gdb.get('ideas')
        color = await self.gdb.get('color')
        locale = await self.gdb.get('language')
        cooldown = self.idea_data.get('cooldown')

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.ideas.init.title'),
            description=i18n.t(locale, 'settings.ideas.init.description'),
            color=color
        )

        super().__init__()

        if cooldown is not None:
            self.embed.add_field(
                name='',
                value=i18n.t(locale, 'settings.ideas.value.cooldown')+display_time(cooldown, locale, max_items=2)
            )
        self.back.label = i18n.t(locale, 'settings.button.back')
        self.edit.label = i18n.t(locale, 'settings.button.edit')
        self.reset.label = i18n.t(locale, 'settings.button.reset')

    @nextcord.ui.button(label='Edit',  style=nextcord.ButtonStyle.success)
    async def edit(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        modal = await CooldownModal(interaction.guild_id)
        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label='Reset', style=nextcord.ButtonStyle.blurple)
    async def reset(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.gdb.set_on_json('ideas', 'cooldown', None)
        self.update(interaction)
