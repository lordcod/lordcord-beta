import nextcord

from bot.databases.handlers.guildHD import GuildDateBases
from bot.databases.varstructs import IdeasPayload, IdeasReactionSystem, IdeasSuggestSystem
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization, get_emoji_wrap
from .base import ViewOptionItem
from ..embeds import join_args


@AsyncSterilization
class TypesReactionsDropdown(nextcord.ui.StringSelect):
    async def __init__(self, guild_id: int) -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        ideas: IdeasPayload = await gdb.get('ideas')
        reaction_system: IdeasReactionSystem = ideas.get('reaction_system', IdeasReactionSystem.REACTIONS)
        get_emoji = await get_emoji_wrap(gdb)

        options = [
            nextcord.SelectOption(
                label=i18n.t(
                    locale, 'settings.ideas.types.react.reactions.label'),
                value=IdeasReactionSystem.REACTIONS,
                description=i18n.t(
                    locale, 'settings.ideas.types.react.reactions.description'),
                emoji=get_emoji('ticon'),
                default=IdeasReactionSystem.REACTIONS == reaction_system
            ),
            nextcord.SelectOption(
                label=i18n.t(
                    locale, 'settings.ideas.types.react.buttons.label'),
                value=IdeasReactionSystem.BUTTONS,
                description=i18n.t(
                    locale, 'settings.ideas.types.react.buttons.description'),
                emoji=get_emoji('buttonbutton'),
                default=IdeasReactionSystem.BUTTONS == reaction_system
            ),
        ]

        super().__init__(options=options)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = int(self.values[0])

        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set_on_json('ideas', 'reaction_system', value)

        view = await TypesView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class TypesSuggestionDropdown(nextcord.ui.StringSelect):
    async def __init__(self, guild_id: int) -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        ideas: IdeasPayload = await gdb.get('ideas')
        suggest_system: IdeasSuggestSystem = ideas.get('suggest_system', IdeasSuggestSystem.BUTTONS)
        get_emoji = await get_emoji_wrap(gdb)

        options = [
            nextcord.SelectOption(
                label=i18n.t(
                    locale, 'settings.ideas.types.suggs.but.label'),
                value=IdeasSuggestSystem.BUTTONS,
                description=i18n.t(
                    locale, 'settings.ideas.types.suggs.but.description'),
                emoji=get_emoji('buttonbutton'),
                default=IdeasSuggestSystem.BUTTONS == suggest_system
            ),
            nextcord.SelectOption(
                label=i18n.t(
                    locale, 'settings.ideas.types.suggs.cmd.label'),
                value=IdeasSuggestSystem.COMMANDS,
                description=i18n.t(
                    locale, 'settings.ideas.types.suggs.cmd.description'),
                emoji=get_emoji('ticon'),
                default=IdeasSuggestSystem.COMMANDS == suggest_system
            ),
            nextcord.SelectOption(
                label=i18n.t(
                    locale, 'settings.ideas.types.suggs.every.label'),
                value=IdeasSuggestSystem.EVERYTHING,
                description=i18n.t(
                    locale, 'settings.ideas.types.suggs.every.description'),
                emoji=get_emoji('ticoff'),
                default=IdeasSuggestSystem.EVERYTHING == suggest_system
            ),
        ]

        super().__init__(options=options)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = int(self.values[0])

        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set_on_json('ideas', 'suggest_system', value)

        view = await TypesView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class TypesView(ViewOptionItem):
    label: str = 'settings.ideas.dropdown.types.title'
    description: str = 'settings.ideas.dropdown.types.description'
    emoji: str = 'ticpanelmes'

    async def __init__(self, guild: nextcord.Guild) -> None:
        self.guild = guild

        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        system_emoji = await gdb.get('system_emoji')
        color = await gdb.get('color')
        ideas = await self.get_ideas_data()
        reaction_system: IdeasReactionSystem = ideas.get('reaction_system', IdeasReactionSystem.REACTIONS)
        suggest_system: IdeasSuggestSystem = ideas.get('suggest_system', IdeasSuggestSystem.BUTTONS)

        if reaction_system == IdeasReactionSystem.REACTIONS:
            reaction_system_name = i18n.t(locale, 'settings.ideas.types.react.reactions.label')
        elif reaction_system == IdeasReactionSystem.BUTTONS:
            reaction_system_name = i18n.t(locale, 'settings.ideas.types.react.buttons.label')

        if suggest_system == IdeasSuggestSystem.BUTTONS:
            suggest_system_name = i18n.t(locale, 'settings.ideas.types.suggs.but.label')
        elif suggest_system == IdeasSuggestSystem.COMMANDS:
            suggest_system_name = i18n.t(locale, 'settings.ideas.types.suggs.cmd.label')
        elif suggest_system == IdeasSuggestSystem.EVERYTHING:
            suggest_system_name = i18n.t(locale, 'settings.ideas.types.suggs.every.label')

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.ideas.init.title'),
            description=i18n.t(locale, 'settings.ideas.init.description'),
            color=color
        )

        description = join_args(
            (i18n.t(locale, 'settings.ideas.value.reactions_system'), reaction_system_name),
            (i18n.t(locale, 'settings.ideas.value.suggest_system'), suggest_system_name)
        )
        self.embed.description += '\n\n'+description

        super().__init__()

        self.edit_row_back(2)

        self.add_item(await TypesReactionsDropdown(guild.id))
        self.add_item(await TypesSuggestionDropdown(guild.id))

        self.back.label = i18n.t(locale, 'settings.button.back')
