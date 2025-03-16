import nextcord

from bot.misc.utils import AsyncSterilization


from .. import permisson_command
from .distribution.allow_channel import AllowChannelsView
from .distribution.allow_role import AllowRolesView
from .distribution.deny_channel import DenyChannelsView
from .distribution.deny_role import DenyRolesView
from .distribution.cooldown import CooldownsView
from bot.views.settings._view import DefaultSettingsView

from bot.resources.ether import Emoji
from bot.databases import GuildDateBases, CommandDB
from bot.languages import help as help_info, i18n
from bot.languages.help import get_command


@AsyncSterilization
class DistrubDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild_id, command_name) -> None:
        self.command_name = command_name

        options = [
            nextcord.SelectOption(
                label='Cooldown',
                emoji=Emoji.cooldown,
                value='cooldown'
            ),
            nextcord.SelectOption(
                label='Allow Channel',
                emoji=Emoji.channel_text,
                value='allow_channel'
            ),
            nextcord.SelectOption(
                label='Allow Role',
                emoji=Emoji.auto_role,
                value='allow_role'
            ),
            nextcord.SelectOption(
                label='Deny Channel',
                emoji=Emoji.channel_text,
                value='deny_channel'
            ),
            nextcord.SelectOption(
                label='Deny Role',
                emoji=Emoji.auto_role,
                value='deny_role'
            ),
        ]

        super().__init__(options=options)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = self.values[0]

        objections = {
            'deny_channel': DenyChannelsView,
            'deny_role': DenyRolesView,
            'allow_channel': AllowChannelsView,
            'allow_role': AllowRolesView,
            'cooldown': CooldownsView
        }
        classification = objections.get(value)
        view = await classification(
            interaction.guild,
            self.command_name
        )

        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class CommandView(DefaultSettingsView):
    embed: nextcord.Embed = None

    async def __init__(self, guild: nextcord.Guild, command_name: str) -> None:
        self.command_name = command_name

        self.gdb = GuildDateBases(guild.id)
        color: int = await self.gdb.get('color')
        locale: str = await self.gdb.get('language')

        self.cdb = CommandDB(guild.id)
        self.command_info: dict = await self.cdb.get(command_name, {})
        self.command_data = get_command(command_name)

        self.operate = self.command_info.get("operate", 1)

        cat_emoji = help_info.categories_emoji[self.command_data.get(
            'category')]
        self.embed = nextcord.Embed(
            title=(
                f"{cat_emoji}"
                f"{self.command_data.get('name')}"
            ),
            description=self.command_data.get(
                'brief_descriptrion').get(locale),
            color=color
        )

        super().__init__()

        DDD = await DistrubDropDown(guild.id, command_name)
        self.add_item(DDD)

        if self.command_data.get("allowed_disabled") is False:
            self.switcher.label = "Forbidden"
            self.switcher.style = nextcord.ButtonStyle.grey
            self.switcher.disabled = True
            DDD.disabled = True
        elif self.operate == 1:
            self.switcher.label = "Disable"
            self.switcher.style = nextcord.ButtonStyle.red
        elif self.operate == 0:
            self.switcher.label = "Enable"
            self.switcher.style = nextcord.ButtonStyle.green

        self.back.label = i18n.t(locale, 'settings.button.back')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        cat_name = self.command_data.get('category')
        index = list(help_info.categories).index(cat_name)

        view = await permisson_command.CommandsDataView(interaction.guild, index)

        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Switcher')
    async def switcher(self,
                       button: nextcord.ui.Button,
                       interaction: nextcord.Interaction):
        command_info = self.command_info
        desperate = 0 if self.operate else 1
        command_info['operate'] = desperate
        await self.cdb.update(self.command_name, command_info)

        view = await CommandView(interaction.guild, self.command_name)
        await interaction.response.edit_message(embed=view.embed, view=view)
