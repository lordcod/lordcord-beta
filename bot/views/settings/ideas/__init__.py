import nextcord

from bot.misc.utils import AsyncSterilization, generate_message, get_payload, lord_format

from bot.resources.info import DEFAULT_IDEAS_MESSAGES
from bot.views.settings._view import DefaultSettingsView
from bot.views.settings.ideas.distribution.base import FunctionOptionItem, ViewOptionItem
from bot.views.settings.ideas.embeds import get_embed
from .distribution import distrubuters

from bot.databases.varstructs import IdeasPayload
from bot.databases import GuildDateBases
from bot.views import settings_menu
from bot.views.ideas import IdeaView, get_default_payload
from bot.languages import i18n


@AsyncSterilization
class IdeasDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild: nextcord.Guild):
        self.gdb = GuildDateBases(guild.id)
        locale = await self.gdb.get('language')
        system_emoji = await self.gdb.get('system_emoji')

        self.distrubuters = {
            k: await v(guild)
            for k, v in distrubuters.items()
        }

        options = [
            nextcord.SelectOption(
                label=i18n.t(locale, value.label),
                value=key,
                description=i18n.t(locale, value.description),
                emoji=value.get_emoji(system_emoji)
            )
            for key, value in self.distrubuters.items()
        ]

        super().__init__(
            placeholder=i18n.t(
                locale, 'settings.ideas.dropdown.placeholder'),
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        catalog = self.values[0]
        item = self.distrubuters[catalog]
        if isinstance(item, ViewOptionItem):
            await interaction.response.edit_message(embed=item.embed, view=item)
        elif isinstance(item, FunctionOptionItem):
            await item.callback(interaction)


@AsyncSterilization
class IdeasView(DefaultSettingsView):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild) -> None:
        gdb = GuildDateBases(guild.id)
        locale: str = await gdb.get('language')
        ideas: IdeasPayload = await gdb.get('ideas', {})
        enabled = ideas.get('enabled')

        self.embed = await get_embed(guild)

        super().__init__()

        idd = await IdeasDropDown(guild)
        self.add_item(idd)

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.enable.label = i18n.t(locale, 'settings.button.enable')
        self.disable.label = i18n.t(locale, 'settings.button.disable')

        if enabled:
            self.remove_item(self.enable)
        else:
            self.remove_item(self.disable)

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        view = await settings_menu.SettingsView(interaction.user)

        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Enable', style=nextcord.ButtonStyle.blurple)
    async def enable(self,
                     button: nextcord.ui.Button,
                     interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        ideas: IdeasPayload = await gdb.get('ideas')

        channel_suggest_id = ideas.get("channel_suggest_id")
        channel_offers_id = ideas.get("channel_offers_id")

        channel_suggest = interaction.guild.get_channel(channel_suggest_id)
        channel_offers = interaction.guild.get_channel(channel_offers_id)

        if not (channel_suggest and channel_offers):
            await interaction.response.send_message(
                i18n.t(locale, 'settings.ideas.init.error.enable'),
                ephemeral=True
            )
            return

        suggestion_message_data = ideas.get('messages', get_default_payload(locale)[
                                            'messages']).get('suggestion')
        suggestion_message = generate_message(lord_format(suggestion_message_data,
                                                          get_payload(guild=interaction.guild)))

        view = await IdeaView(interaction.guild)
        message_suggest = await channel_suggest.send(**suggestion_message, view=view)

        ideas['message_suggest_id'] = message_suggest.id
        ideas['enabled'] = True
        await gdb.set('ideas', ideas)

        view = await IdeasView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Disable', style=nextcord.ButtonStyle.red)
    async def disable(self,
                      button: nextcord.ui.Button,
                      interaction: nextcord.Interaction):
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

        ideas['enabled'] = False

        await gdb.set('ideas', ideas)

        view = await IdeasView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
