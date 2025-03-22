from typing import Optional
import nextcord

from bot.misc.utils import AsyncSterilization, generate_message, get_payload, lord_format
from bot.views.ideas import IdeaView, get_default_payload
from bot.resources.info import DEFAULT_IDEAS_PAYLOAD, DEFAULT_IDEAS_PAYLOAD_RU

from .. import ideas
from .._view import DefaultSettingsView

from bot.databases import GuildDateBases
from bot.languages import i18n


@AsyncSterilization
class IdeasSelectorDropDown(nextcord.ui.ChannelSelect):
    async def __init__(
        self,
        placeholder: str,
        guild: nextcord.Guild,
        selected_offers: Optional[nextcord.TextChannel] = None,
        selected_suggest: Optional[nextcord.TextChannel] = None,
        selected_approved: Optional[nextcord.TextChannel] = None,
    ) -> None:
        self.guild = guild
        self.selected_offers = selected_offers
        self.selected_suggest = selected_suggest
        self.selected_approved = selected_approved

        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        super().__init__(placeholder=placeholder,
                         channel_types=[nextcord.ChannelType.text])

    async def callback(self, interaction: nextcord.Interaction) -> None:
        view = await IdeasSelectorView(
            interaction.guild,
            self.selected_offers,
            self.selected_suggest,
            self.selected_approved
        )
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class OffersChannelDropDown(IdeasSelectorDropDown.cls):
    async def __init__(self, *args) -> None:
        await super().__init__('Select a channel for all the ideas', *args)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        channel = self.values[0]
        self.selected_offers = channel
        await super().callback(interaction)


@AsyncSterilization
class SuggestChannelDropDown(IdeasSelectorDropDown.cls):
    async def __init__(self, *args) -> None:
        await super().__init__('[OPTIONAL] Select the suggested channel', *args)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        channel = self.values[0]
        self.selected_suggest = channel
        await super().callback(interaction)


@AsyncSterilization
class ApprovedChannelDropDown(IdeasSelectorDropDown.cls):
    async def __init__(self, *args) -> None:
        await super().__init__('[OPTIONAL] Select an approved channel', *args)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        channel = self.values[0]
        self.selected_approved = channel
        await super().callback(interaction)


@AsyncSterilization
class IdeasSelectorView(DefaultSettingsView):
    embed: nextcord.Embed = None

    async def __init__(
        self,
        guild: nextcord.Guild,
        selected_offers: Optional[nextcord.TextChannel] = None,
        selected_suggest: Optional[nextcord.TextChannel] = None,
        selected_approved: Optional[nextcord.TextChannel] = None,
    ) -> None:
        self.selected_offers = selected_offers
        self.selected_suggest = selected_suggest
        self.selected_approved = selected_approved

        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        super().__init__()

        args = [guild, selected_offers, selected_suggest, selected_approved]
        self.add_item(await OffersChannelDropDown(*args))
        self.add_item(await SuggestChannelDropDown(*args))
        self.add_item(await ApprovedChannelDropDown(*args))

        if selected_offers is not None:
            self.create.disabled = False

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.create.label = i18n.t(locale, 'settings.button.create')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        view = await ideas.IdeasView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Create', style=nextcord.ButtonStyle.blurple, disabled=True)
    async def create(self,
                     button: nextcord.ui.Button,
                     interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')

        data = get_default_payload(locale)

        if self.selected_suggest is not None:
            view = await IdeaView(interaction.guild)

            suggestion_message_data = data.get('messages').get('suggestion')
            suggestion_message = generate_message(lord_format(suggestion_message_data,
                                                              get_payload(guild=interaction.guild)))
            message_suggest = await self.selected_suggest.send(**suggestion_message, view=view)
            message_suggest_id = message_suggest.id
        else:
            message_suggest_id = None

        data.update({
            'enabled': True,
            'channel_offers_id': self.selected_suggest.id,
            'channel_approved_id': self.selected_approved and self.selected_approved.id,
            'channel_suggest_id': self.selected_suggest and self.selected_suggest.id,
            'message_suggest_id': message_suggest_id
        })

        view = await ideas.IdeasView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
