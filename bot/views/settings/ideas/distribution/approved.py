import nextcord

from bot.languages import i18n
from bot.misc.utils import AsyncSterilization
from bot.views.information_dd import get_info_dd
from .base import ViewOptionItem


from bot.databases import GuildDateBases
from bot.databases.varstructs import IdeasPayload

from typing import Optional


@AsyncSterilization
class ApprovedDropDown(nextcord.ui.ChannelSelect):
    async def __init__(
        self,
        guild_id: int
    ) -> None:
        self.gdb = GuildDateBases(guild_id)
        self.idea_data = await self.gdb.get('ideas')
        locale = await self.gdb.get('language')

        super().__init__(placeholder=i18n.t(locale, 'settings.ideas.channel.dropdown'),
                         channel_types=[nextcord.ChannelType.text])

    async def callback(self, interaction: nextcord.Interaction) -> None:
        channel = self.values[0]
        await self.gdb.set_on_json('ideas', 'channel_approved_id', channel.id)

        view = await ApprovedView(interaction.guild, channel)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class ApprovedView(ViewOptionItem):
    label: str = 'settings.ideas.dropdown.approved.title'
    description: str = 'settings.ideas.dropdown.approved.description'
    emoji: str = 'ideaapproved'

    async def __init__(self, guild: nextcord.Guild, channel: Optional[nextcord.TextChannel] = None) -> None:
        self.gdb = GuildDateBases(guild.id)
        self.idea_data: IdeasPayload = await self.gdb.get('ideas')
        channel_approved_id = self.idea_data.get('channel_approved_id')
        color = await self.gdb.get('color')
        locale = await self.gdb.get('language')

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.ideas.init.title'),
            description=i18n.t(locale, 'settings.ideas.init.description'),
            color=color
        )
        super().__init__()

        self.edit_row_back(1)

        if channel is not None:
            self.channel = channel
        if channel_approved_id is not None:
            self.delete.disabled = False

        if channel or (channel := guild.get_channel(channel_approved_id)):
            self.embed.add_field(
                name='',
                value=i18n.t(locale, 'settings.ideas.value.approved')+channel.mention
            )

        cdd = await ApprovedDropDown(guild.id)
        self.add_item(cdd)

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.delete.label = i18n.t(locale, 'settings.button.delete')

    @nextcord.ui.button(label='Delete', style=nextcord.ButtonStyle.red, row=1, disabled=True)
    async def delete(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        idea_data = self.idea_data
        idea_data.pop('channel_approved_id', None)
        await self.gdb.set('ideas', idea_data)

        view = await ApprovedView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
