import nextcord
from bot.databases import GuildDateBases
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization

from .. import music
from .._view import DefaultSettingsView


@AsyncSterilization
class MaxSizeModal(nextcord.ui.Modal):
    async def __init__(self, guild_id, value: int) -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')

        super().__init__(i18n.t(locale, 'settings.music.max-queue-size.description'))
        self.size = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.music.max-queue-size.name'),
            placeholder=value,
            max_length=3
        )
        self.add_item(self.size)

    async def callback(self, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        max_size = self.size.value

        if not max_size.isdigit():
            return

        await gdb.set_on_json('music_settings', 'queue-max-size', int(max_size))

        view = await MaxSizeView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class MaxSizeView(DefaultSettingsView):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild) -> None:
        self.gdb = GuildDateBases(guild.id)
        locale = await self.gdb.get('language')
        color = await self.gdb.get('color')

        self.embed = nextcord.Embed(
            title=i18n.t(locale,
                         'settings.music.title'),
            description=i18n.t(locale,
                               'settings.music.description'),
            color=color
        )
        self.embed.add_field(
            name='',
            value=i18n.t(locale, 'settings.music.max_size.select')
        )

        super().__init__()

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.edit.label = i18n.t(locale, 'settings.button.edit')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        view = await music.MusicView(interaction.guild)

        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Edit', style=nextcord.ButtonStyle.blurple)
    async def edit(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        music_settings = await self.gdb.get("music_settings")
        max_size = music_settings.get("queue-max-size", 150)

        modal = await MaxSizeModal(interaction.guild_id, max_size)
        await interaction.response.send_modal(modal)
