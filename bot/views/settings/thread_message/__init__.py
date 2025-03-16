import nextcord

from bot.languages import i18n
from bot.misc.utils import AsyncSterilization


from .additional import InstallThreadView
from .precise import ThreadData
from .._view import DefaultSettingsView

from bot.views import settings_menu
from bot.databases import GuildDateBases
from bot.resources.ether import channel_types_emoji


@AsyncSterilization
class DropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild: nextcord.Guild):
        self.gdb = GuildDateBases(guild.id)
        locale = await self.gdb.get('language')
        self.forum_message = await self.gdb.get('thread_messages')
        channels = [guild.get_channel(key) for key in self.forum_message]

        options = [
            nextcord.SelectOption(
                label=chnl.name,
                emoji=channel_types_emoji[chnl.type.value],
                value=chnl.id
            )
            for chnl in channels
            if chnl is not None
        ]

        disabled = 0 >= len(options)
        if disabled:
            options.append(nextcord.SelectOption(label="SelectOption"))

        super().__init__(
            placeholder=i18n.t(
                locale, 'settings.thread.init.placeholder'),
            min_values=1,
            max_values=1,
            options=options,
            disabled=disabled
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = self.values[0]
        value = int(value)
        channel = await interaction.guild.fetch_channel(value)
        channel_data = self.forum_message.get(value)
        locale = await self.gdb.get('language')
        color = await self.gdb.get('color')

        embed = nextcord.Embed(
            title=i18n.t(
                locale, 'settings.thread.init.brief'),
            description=i18n.t(
                locale, 'settings.thread.init.channel', channel=channel.mention),
            color=color
        )
        view = await ThreadData(channel, channel_data)
        await interaction.response.edit_message(embed=embed,
                                                view=view)


@AsyncSterilization
class AutoThreadMessage(DefaultSettingsView):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        color = await gdb.get('color')

        self.embed = nextcord.Embed(
            title=i18n.t(
                locale, 'settings.thread.init.title'),
            description=i18n.t(
                locale, 'settings.thread.init.description'),
            color=color
        )

        super().__init__()

        self.back.label = i18n.t(
            locale, 'settings.button.back')
        self.addtion.label = i18n.t(
            locale, 'settings.button.add')

        dd = await DropDown(guild)
        self.add_item(dd)

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        view = await settings_menu.SettingsView(interaction.user)

        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Add', style=nextcord.ButtonStyle.green)
    async def addtion(self,
                      button: nextcord.ui.Button,
                      interaction: nextcord.Interaction):
        view = await InstallThreadView(interaction.guild_id)

        await interaction.response.edit_message(embed=None, view=view)
