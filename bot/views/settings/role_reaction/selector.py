from typing import List, Optional
import nextcord
from bot.databases import GuildDateBases
from bot.databases.varstructs import ReactionRolePayload
from bot.languages import i18n
from bot.misc import utils
from . import item
from .. import role_reaction
from .._view import DefaultSettingsView


@utils.AsyncSterilization
class RoleReactionSelectorChannelDropDown(nextcord.ui.ChannelSelect):
    async def __init__(self, guild: nextcord.Guild) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        super().__init__(placeholder=i18n.t(locale, 'settings.role-reaction.selector.channel'), channel_types=[
            nextcord.ChannelType.text,
            nextcord.ChannelType.voice,
            nextcord.ChannelType.news,
            nextcord.ChannelType.stage_voice,
            nextcord.ChannelType.guild_directory
        ])

    async def callback(self, interaction: nextcord.Interaction) -> None:
        channel = self.values[0]

        view = await RoleReactionSelectorView(interaction.user.guild, channel)
        await interaction.response.edit_message(embed=view.embed, view=view)


@utils.AsyncSterilization
class RoleReactionSelectorMessageDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild: nextcord.Guild, channel: Optional[nextcord.TextChannel] = None, selected_message_id: Optional[int] = None) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        self.channel = channel
        if channel:
            messages = [msg async for msg in channel.history(limit=15)]
        else:
            messages = []

        options = [
            nextcord.SelectOption(
                label=f'ID: {mes.id}({mes.author.name})',
                value=mes.id,
                description=self.get_content(mes),
                default=mes.id == selected_message_id
            )
            for mes in messages
        ]

        disabled = 0 >= len(options)
        if 0 >= len(options):
            options.append(nextcord.SelectOption(label="SelectOption"))

        super().__init__(placeholder=i18n.t(locale,
                                            'settings.role-reaction.selector.message'), options=options, disabled=disabled)

    @staticmethod
    def get_content(mes: nextcord.Message) -> Optional[str]:
        if mes.content:
            return utils.cut_back(mes.content, 100)
        if mes.embeds:
            return utils.cut_back(f"[EMBEDS] {title if (title := mes.embeds[0].title) else ''}", 100)
        if mes.attachments:
            return '[ATTACHMENTS]'
        return None

    async def callback(self, interaction: nextcord.Interaction) -> None:
        message_id = int(self.values[0])

        view = await RoleReactionSelectorView(
            interaction.user.guild, self.channel, message_id)

        await interaction.response.edit_message(embed=view.embed, view=view)


@utils.AsyncSterilization
class RoleReactionSelectorView(DefaultSettingsView):
    embed: nextcord.Embed = None

    async def __init__(self, guild: nextcord.Guild, channel: Optional[nextcord.TextChannel] = None, message_id: Optional[int] = None) -> None:
        gdb = GuildDateBases(guild.id)
        color = await gdb.get('color')
        locale = await gdb.get('language')

        self.channel = channel
        self.message_id = message_id

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.role-reaction.global.title'),
            description=i18n.t(
                locale, 'settings.role-reaction.global.description'),
            color=color
        )

        super().__init__()

        self.add_item(await RoleReactionSelectorChannelDropDown(guild))
        self.add_item(
            await RoleReactionSelectorMessageDropDown(guild, channel, message_id))
        if message_id:
            self.next.disabled = False

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.next.label = i18n.t(locale, 'settings.button.next')

    @nextcord.ui.button(label="Back", style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction
                   ):
        view = await role_reaction.RoleReactionView(interaction.user)

        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label="Next", style=nextcord.ButtonStyle.blurple, disabled=True)
    async def next(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction
                   ):
        role_reaction = {
            'channel_id': self.channel.id,
            'reactions': {}
        }

        view = await item.RoleReactionItemView(
            interaction.user, self.message_id, self.channel.id, role_reaction)

        await interaction.response.edit_message(embed=view.embed, view=view)
