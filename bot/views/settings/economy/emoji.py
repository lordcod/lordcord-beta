
import nextcord

from bot.databases import GuildDateBases
from bot.languages import i18n
from bot.resources.info import DEFAULT_EMOJI
from bot.misc.utils import AsyncSterilization

from bot.views.information_dd import get_info_dd
from bot.views.settings.set_reaction import fetch_reaction

from .. import economy
from .._view import DefaultSettingsView


@AsyncSterilization
class EmojiView(DefaultSettingsView):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild) -> None:
        gdb = GuildDateBases(guild.id)
        color = await gdb.get('color', 1974050)
        locale = await gdb.get('language')
        economy_settings: dict = await gdb.get('economic_settings')
        emoji = economy_settings.get("emoji")

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.economy.emoji.title'),
            description=i18n.t(locale, 'settings.economy.emoji.description'),
            color=color
        )

        super().__init__()

        if emoji != DEFAULT_EMOJI:
            self.reset.disabled = False

        self.add_item(get_info_dd(label=i18n.t(locale, 'settings.economy.emoji.dropdown'), emoji=emoji))

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.install.label = i18n.t(locale, 'settings.button.set')
        self.reset.label = i18n.t(locale, 'settings.button.reset')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        view = await economy.Economy(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Install', style=nextcord.ButtonStyle.blurple)
    async def install(self,
                      button: nextcord.ui.Button,
                      interaction: nextcord.Interaction):
        value = await fetch_reaction(interaction)

        if value is None:
            return

        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set_on_json('economic_settings', 'emoji', value)

        view = await EmojiView(interaction.guild)
        await interaction.message.edit(embed=view.embed, view=view)

    @nextcord.ui.button(label='Reset', style=nextcord.ButtonStyle.success, disabled=True)
    async def reset(self,
                    button: nextcord.ui.Button,
                    interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set_on_json('economic_settings', 'emoji', DEFAULT_EMOJI)

        view = await EmojiView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
