import nextcord

from bot.misc.plugins.tempvoice import TempVoiceModule
from bot.misc.utils import AsyncSterilization
from bot.views.settings.tempvoice import options_voice
from bot.views.settings.tempvoice.select_voice import TempVoiceSelectorView


from .._view import DefaultSettingsView

from bot.databases import GuildDateBases
from bot.views import settings_menu
from bot.languages import i18n


@AsyncSterilization
class TempVoiceView(DefaultSettingsView):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild) -> None:
        gdb = GuildDateBases(guild.id)
        color = await gdb.get('color')
        locale = await gdb.get('language')
        data = await gdb.get('tempvoice')

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.tempvoice.init.title'),
            color=color,
            description=i18n.t(locale, 'settings.tempvoice.init.description')
        )

        super().__init__()

        if data:
            self.remove_item(self.create)
            self.remove_item(self.select)

            optns = await options_voice.TempVoiceDropDown(guild)
            self.add_item(optns)

            if data.get('enabled'):
                self.switch.label = i18n.t(locale, 'settings.button.disable')
                self.switch.style = nextcord.ButtonStyle.red
            else:
                optns.disabled = True
                self.switch.label = i18n.t(locale, 'settings.button.enable')
                self.switch.style = nextcord.ButtonStyle.green
        else:
            self.remove_item(self.switch)
            self.remove_item(self.delete)

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.delete.label = i18n.t(locale, 'settings.button.delete')
        self.create.label = i18n.t(locale, 'settings.button.create')
        self.select.label = i18n.t(locale, 'settings.button.select')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        view = await settings_menu.SettingsView(interaction.user)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Switch', style=nextcord.ButtonStyle.red)
    async def switch(self,
                     button: nextcord.ui.Button,
                     interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        data = await gdb.get('tempvoice')
        enabled = data.get('enabled')
        await gdb.set_on_json('tempvoice', 'enabled', not enabled)

        view = await TempVoiceView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Delete', style=nextcord.ButtonStyle.red)
    async def delete(self,
                     button: nextcord.ui.Button,
                     interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set('tempvoice', {})

        view = await TempVoiceView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Create', style=nextcord.ButtonStyle.blurple)
    async def create(self,
                     button: nextcord.ui.Button,
                     interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')

        category = await interaction.guild.create_category(name=i18n.t(locale, 'settings.tempvoice.init.create.category'))
        panel_channel = await interaction.guild.create_text_channel(
            name=i18n.t(locale, 'settings.tempvoice.init.create.panel'),
            category=category,
            overwrites={
                interaction.guild.default_role: nextcord.PermissionOverwrite(view_channel=True,
                                                                             read_message_history=True,
                                                                             send_messages=False)
            }
        )
        channel = await interaction.guild.create_voice_channel(
            name=i18n.t(locale, 'settings.tempvoice.init.create.name'),
            category=category,
            user_limit=2,
            overwrites={
                interaction.guild.default_role: nextcord.PermissionOverwrite(view_channel=True,
                                                                             read_message_history=True,
                                                                             connect=True)
            }
        )

        data = {
            'enabled': True,
            'channel_id': channel.id,
            'category_id': category.id,
            'panel_channel_id': panel_channel.id,
            'type_message_panel': 1
        }

        await gdb.set('tempvoice', data)
        await TempVoiceModule.create_panel(interaction.guild)

        view = await TempVoiceView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Select', style=nextcord.ButtonStyle.success)
    async def select(self,
                     button: nextcord.ui.Button,
                     interaction: nextcord.Interaction):
        view = await TempVoiceSelectorView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
