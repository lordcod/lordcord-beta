
import nextcord
from bot import languages
from bot.misc.utils import AsyncSterilization

from bot.views import settings_menu
from ._view import DefaultSettingsView
from bot.databases import GuildDateBases
from bot.languages import i18n


@AsyncSterilization
class DropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild_id):
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')

        options = [
            nextcord.SelectOption(
                label=(f"{data.get('english_name')} "
                       f"({data.get('native_name')})"),
                value=data.get('locale'),
                emoji=data.get('flag', None),
                default=locale == data.get('locale')
            )
            for data in languages.current
        ]

        super().__init__(
            placeholder=i18n.t(locale, 'settings.languages.choose'),
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = self.values[0]

        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set('language', value)

        view = await Languages(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class Languages(DefaultSettingsView):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild) -> None:
        gdb = GuildDateBases(guild.id)
        color = await gdb.get('color')
        locale = await gdb.get('language')

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.languages.title'),
            description=i18n.t(locale, 'settings.languages.description'),
            color=color
        )

        super().__init__()

        self.back.label = i18n.t(locale, 'settings.button.back')

        lang = await DropDown(guild.id)
        self.add_item(lang)

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        view = await settings_menu.SettingsView(interaction.user)

        await interaction.response.edit_message(embed=view.embed, view=view)
