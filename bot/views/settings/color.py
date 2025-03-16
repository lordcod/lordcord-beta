import nextcord
from bot.databases import GuildDateBases
import re
from bot.misc.utils import AsyncSterilization

from bot.resources.ether import ColorType
from bot.views import settings_menu
from ._view import DefaultSettingsView
from bot.resources.info import DEFAULT_COLOR
from bot.resources.ether import every_emojis
from bot.languages import i18n

HEX_REGEX = re.compile(r'#?([0-9a-fA-F]{6})')

system_emoji_colors = [{'value': item, 'label': name.capitalize()} for name, item in ColorType.__dict__.items() if isinstance(item, ColorType)]


@AsyncSterilization
class ColorModal(nextcord.ui.Modal):
    async def __init__(self, guild_id) -> None:
        self.gdb = GuildDateBases(guild_id)
        color = await self.gdb.get("color")
        hex_color = f"#{color:0>6x}".upper()

        super().__init__("Color")

        self.color = nextcord.ui.TextInput(
            label="Color", placeholder=hex_color)

        self.add_item(self.color)

    async def callback(self, interaction: nextcord.Interaction):
        locale = await self.gdb.get('language')

        hex_color = self.color.value
        result = HEX_REGEX.fullmatch(hex_color)

        if not result:
            await interaction.response.send_message(i18n.t(locale, 'settings.color.not-valid'),
                                                    ephemeral=True)
            return

        color = int(result.group(1), 16)
        await self.gdb.set("color", color)

        view = await ColorView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class EmojiDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild_id: int) -> None:
        gdb = GuildDateBases(guild_id)
        system_emoji = await gdb.get("system_emoji")

        options = [
            nextcord.SelectOption(
                label=data['label'],
                value=data['value'],
                description=None,
                emoji=every_emojis['settings'][data['value']],
                default=data['value'] == system_emoji
            )
            for data in system_emoji_colors
        ]
        super().__init__(options=options)

    async def callback(self, interaction: nextcord.Interaction):
        value = int(self.values[0])

        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set("system_emoji", value)

        view = await ColorView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class ColorView(DefaultSettingsView):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get("language")
        color = await gdb.get("color")
        hex_color = f"#{color:0>6x}".upper()

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.color.title'),
            description=i18n.t(locale, 'settings.color.description'),
            color=color,
        )
        self.embed.add_field(
            name=i18n.t(locale, 'settings.color.current', hex_color=hex_color),
            value=''
        )

        super().__init__()

        self.add_item(await EmojiDropDown(guild.id))

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.edit.label = i18n.t(locale, 'settings.button.edit')
        self.reset.label = i18n.t(locale, 'settings.button.reset')

    @nextcord.ui.button(label="Back", style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction
                   ):
        view = await settings_menu.SettingsView(interaction.user)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label="Edit", style=nextcord.ButtonStyle.blurple)
    async def edit(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction
                   ):
        modal = await ColorModal(interaction.guild_id)
        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label="Reset", style=nextcord.ButtonStyle.success)
    async def reset(
        self, button: nextcord.ui.Button, interaction: nextcord.Interaction
    ):
        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set("color", DEFAULT_COLOR)

        view = await ColorView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
