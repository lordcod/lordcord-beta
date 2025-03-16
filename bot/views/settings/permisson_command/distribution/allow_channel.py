from typing import List
import nextcord

from bot.misc.utils import AsyncSterilization


from ... import permisson_command
from bot.views.settings._view import DefaultSettingsView

from bot.databases import GuildDateBases, CommandDB


@AsyncSterilization
class AllowChannelsDropDown(nextcord.ui.ChannelSelect):
    async def __init__(
        self,
        guild: nextcord.Guild,
        command_name: str
    ) -> None:

        self.command_name = command_name
        super().__init__(
            placeholder="Select the channels in which the command will work",
            min_values=1,
            max_values=15,
            channel_types=[
                nextcord.ChannelType.text,
                nextcord.ChannelType.voice,
                nextcord.ChannelType.category,
                nextcord.ChannelType.news,
                nextcord.ChannelType.stage_voice,
                nextcord.ChannelType.guild_directory,
                nextcord.ChannelType.forum
            ]
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        channels: List[int] = []
        categories: List[int] = []

        for channel in self.values.channels:
            if channel.type == nextcord.ChannelType.category:
                categories.append(channel.id)
            else:
                channels.append(channel.id)

        cdb = CommandDB(interaction.guild_id)
        command_data = await cdb.get(self.command_name, {})
        command_data.setdefault("distribution", {})
        command_data["distribution"]["allow-channel"] = {
            'channels': channels,
            'categories': categories
        }
        await cdb.update(self.command_name, command_data)

        view = await AllowChannelsView(
            interaction.guild,
            self.command_name
        )
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class AllowChannelsView(DefaultSettingsView):
    embed: nextcord.Embed = None

    async def __init__(self, guild: nextcord.Guild, command_name: str) -> None:
        self.command_name = command_name

        gdb = GuildDateBases(guild.id)
        color = await gdb.get('color')

        cdb = CommandDB(guild.id)
        command_data = await cdb.get(self.command_name, {})
        command_data.setdefault("distribution", {})

        allow_data = command_data["distribution"].get(
            "allow-channel", {})

        channel_ids = allow_data.get('channels')
        category_ids = allow_data.get('categories')

        self.embed = nextcord.Embed(
            title="Allowed channels",
            description="The selected command will only work in the channels that you select",
            color=color
        )
        if category_ids:
            self.embed.add_field(
                name="Selected categories:",
                value=', '.join([channel.mention
                                 for category_id in category_ids
                                 if (channel := guild.get_channel(category_id))])
            )
        if channel_ids:
            self.embed.add_field(
                name="Selected channels:",
                value=', '.join([channel.mention
                                 for channel_id in channel_ids
                                 if (channel := guild.get_channel(channel_id))])
            )

        super().__init__()

        cdd = await AllowChannelsDropDown(
            guild,
            command_name
        )
        self.add_item(cdd)

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        view = await permisson_command.precise.CommandView(
            interaction.guild,
            self.command_name
        )
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Delete', style=nextcord.ButtonStyle.red)
    async def delete(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        cdb = CommandDB(interaction.guild_id)
        command_data = await cdb.get(self.command_name, {})
        command_data.setdefault("distribution", {})
        command_data["distribution"].pop("allow-channel", None)
        await cdb.update(self.command_name, command_data)

        view = await AllowChannelsView(interaction.guild, self.command_name)
        await interaction.response.edit_message(embed=view.embed, view=view)
