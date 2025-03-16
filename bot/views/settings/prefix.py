import nextcord

from bot.misc.utils import AsyncSterilization
from bot.views.information_dd import get_info_dd


from ._view import DefaultSettingsView

from bot.databases import GuildDateBases
from bot.views import settings_menu
from bot.resources.info import DEFAULT_PREFIX
from bot.languages import i18n


@AsyncSterilization
class Modal(nextcord.ui.Modal):
    async def __init__(self, guild_id) -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        prefix = await gdb.get('prefix')

        super().__init__(title=i18n.t(locale, 'settings.prefix.title'))

        self.prefix = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.prefix.title'),
            placeholder=prefix,
            max_length=3
        )
        self.add_item(self.prefix)

    async def callback(self, interaction: nextcord.Interaction):
        prefix = self.prefix.value
        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set('prefix', prefix)

        view = await PrefixView(interaction.guild)

        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class PrefixView(DefaultSettingsView):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild) -> None:
        gdb = GuildDateBases(guild.id)
        prefix = await gdb.get('prefix')
        color = await gdb.get('color')
        locale = await gdb.get('language')

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.prefix.title'),
            description=i18n.t(locale, 'settings.prefix.description'),
            color=color
        )

        super().__init__()

        self.add_item(
            get_info_dd(placeholder=i18n.t(locale, 'settings.prefix.current',
                                           prefix=prefix))
        )

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.edit.label = i18n.t(locale, 'settings.button.edit')
        self.reset.label = i18n.t(locale, 'settings.button.reset')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        view = await settings_menu.SettingsView(interaction.user)

        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Edit', style=nextcord.ButtonStyle.blurple)
    async def edit(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        modal = await Modal(interaction.guild_id)

        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label='Reset', style=nextcord.ButtonStyle.success)
    async def reset(self,
                    button: nextcord.ui.Button,
                    interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set('prefix', DEFAULT_PREFIX)

        view = await PrefixView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
