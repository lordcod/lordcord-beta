import nextcord

from bot.languages import i18n
from bot.misc.utils import AsyncSterilization
from bot.views.information_dd import get_info_dd


from bot.databases import GuildDateBases
from bot.databases.varstructs import IdeasPayload
from .base import ViewOptionItem

from typing import Optional


@AsyncSterilization
class ChannelsDropDown(nextcord.ui.ChannelSelect):
    async def __init__(
        self,
        guild_id: int
    ) -> None:
        self.gdb = gdb = GuildDateBases(guild_id)
        self.idea_data = await gdb.get('ideas')
        locale = await gdb.get('language')

        super().__init__(placeholder=i18n.t(locale, 'settings.ideas.channel.dropdown'), channel_types=[nextcord.ChannelType.text])

    async def callback(self, interaction: nextcord.Interaction) -> None:
        channel = self.values[0]
        await self.gdb.set_on_json('ideas', 'channel_suggest_id', channel.id)

        view = await SuggestView(interaction.guild, channel)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class SuggestView(ViewOptionItem):
    label: str = 'settings.ideas.dropdown.suggest.title'
    description: str = 'settings.ideas.dropdown.suggest.description'
    emoji: str = 'ideacreate'

    async def __init__(self, guild: nextcord.Guild, channel: Optional[nextcord.TextChannel] = None) -> None:
        self.gdb = GuildDateBases(guild.id)
        self.idea_data: IdeasPayload = await self.gdb.get('ideas')
        channel_suggest_id = self.idea_data.get('channel_suggest_id')
        color = await self.gdb.get('color')
        locale = await self.gdb.get('language')

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.ideas.init.title'),
            description=i18n.t(locale, 'settings.ideas.init.description'),
            color=color
        )
        if channel or (channel := guild.get_channel(channel_suggest_id)):
            self.channel = channel
            self.embed.add_field(
                name='',
                value=i18n.t(locale, 'settings.ideas.value.suggest')+channel.mention
            )

        super().__init__()
        self.edit_row_back(1)

        cdd = await ChannelsDropDown(guild.id)
        self.add_item(cdd)

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.delete.label = i18n.t(locale, 'settings.button.delete')

    @nextcord.ui.button(label='Delete', row=1, style=nextcord.ButtonStyle.red, disabled=True)
    async def delete(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        ideas: IdeasPayload = await gdb.get('ideas')

        channel_suggest_id = ideas.get("channel_suggest_id")
        channel_suggest = interaction.guild.get_channel(channel_suggest_id)
        message_suggest_id = ideas.get("message_suggest_id")

        if channel_suggest and message_suggest_id:
            message_suggest = channel_suggest.get_partial_message(
                message_suggest_id)
            try:
                await message_suggest.delete()
            except nextcord.errors.HTTPException:
                pass

        ideas['channel_suggest_id'] = None
        ideas['message_suggest_id'] = None

        await gdb.set('ideas', ideas)

        view = await SuggestView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
