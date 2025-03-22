import contextlib
import nextcord

from bot.misc.utils import AsyncSterilization

from bot.resources.info import DEFAULT_IDEAS_NAMES, DEFAULT_IDEAS_NAMES_RU, DEFAULT_IDEAS_PAYLOAD, DEFAULT_IDEAS_PAYLOAD_RU
from bot.views.settings._view import DefaultSettingsView
from bot.views.settings.ideas.distribution.base import FunctionOptionItem, ViewOptionItem
from bot.views.settings.ideas.embeds import get_embed
from bot.misc.utils import AsyncSterilization, generate_message, get_payload, lord_format
from bot.views.ideas import IdeaView, get_default_payload
from .distribution import distrubuters

from bot.databases.varstructs import IdeasPayload
from bot.databases import GuildDateBases
from bot.views import settings_menu
from bot.languages import i18n
from .selector import IdeasSelectorView


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
        color = await gdb.get('color')
        ideas: IdeasPayload = await gdb.get('ideas', {})
        enabled = ideas.get('enabled')

        super().__init__()

        if ideas.get('channel_offers_id'):
            self.embed = await get_embed(guild)

            self.remove_item(self.create)
            self.remove_item(self.select)

            idd = await IdeasDropDown(guild)
            self.add_item(idd)

            if enabled:
                self.switch.style = nextcord.ButtonStyle.red
                self.switch.label = i18n.t(locale, 'settings.button.disable')
            else:
                self.switch.style = nextcord.ButtonStyle.green
                self.switch.label = i18n.t(locale, 'settings.button.enable')
        else:
            self.embed = nextcord.Embed(
                title=i18n.t(locale, 'settings.ideas.init.title'),
                description=i18n.t(locale, 'settings.ideas.init.description'),
                color=color
            )

            self.remove_item(self.delete)
            self.remove_item(self.switch)

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

    @nextcord.ui.button(label='Delete', style=nextcord.ButtonStyle.red)
    async def delete(self,
                     button: nextcord.ui.Button,
                     interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        ideas: IdeasPayload = await gdb.get('ideas', {})

        channels = ['channel_suggest_id', 'channel_approved_id',
                    'channel_denied_id', 'channel_offers_id']
        for chnl in channels:
            channel = interaction.guild.get_channel(ideas.get(chnl))
            if channel is None:
                continue

            with contextlib.suppress(nextcord.HTTPException):
                await channel.delete()

        await gdb.set('ideas', {})

        view = await IdeasView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Switch')
    async def switch(self,
                     button: nextcord.ui.Button,
                     interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set_on_json('ideas', 'enabled', not await gdb.get('enabled'))

        view = await IdeasView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Create', style=nextcord.ButtonStyle.blurple)
    async def create(self,
                     button: nextcord.ui.Button,
                     interaction: nextcord.Interaction):
        await interaction.response.defer()

        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        ideas = DEFAULT_IDEAS_PAYLOAD_RU if locale == 'ru' else DEFAULT_IDEAS_PAYLOAD
        names = ideas.get('names')

        category = await interaction.guild.create_category(names.get('category'))

        suggestion_channel = await interaction.guild.create_text_channel(
            name=names.get('suggest'),
            category=category,
            overwrites={
                interaction.guild.default_role: nextcord.PermissionOverwrite(view_channel=True,
                                                                             read_message_history=True,
                                                                             send_messages=False)
            }
        )

        view = await IdeaView(interaction.guild)
        suggestion_message_data = ideas.get('messages').get('suggestion')
        suggestion_message = generate_message(lord_format(suggestion_message_data,
                                                          get_payload(guild=interaction.guild)))
        message_suggest = await suggestion_channel.send(**suggestion_message, view=view)
        message_suggest_id = message_suggest.id

        offers_channel = await interaction.guild.create_text_channel(
            name=names.get('offers'),
            category=category,
            overwrites={
                interaction.guild.default_role: nextcord.PermissionOverwrite(view_channel=True,
                                                                             read_message_history=True,
                                                                             send_messages=False)
            }
        )

        approved_channel = await interaction.guild.create_text_channel(
            name=names.get('approved'),
            category=category,
            overwrites={
                interaction.guild.default_role: nextcord.PermissionOverwrite(view_channel=True,
                                                                             read_message_history=True,
                                                                             send_messages=False)
            }
        )

        ideas.update({
            'enabled': True,
            'channel_offers_id': offers_channel.id,
            'channel_approved_id': approved_channel.id,
            'channel_suggest_id': suggestion_channel.id,
            'message_suggest_id': message_suggest_id
        })
        await gdb.set('ideas', ideas)

        view = await IdeasView(interaction.guild)
        await interaction.message.edit(embed=view.embed, view=view)

    @nextcord.ui.button(label='Select', style=nextcord.ButtonStyle.success)
    async def select(self,
                     button: nextcord.ui.Button,
                     interaction: nextcord.Interaction):
        view = await IdeasSelectorView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
