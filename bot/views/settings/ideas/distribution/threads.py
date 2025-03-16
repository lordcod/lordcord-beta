import nextcord

from bot.databases.handlers.guildHD import GuildDateBases
from bot.databases.varstructs import IdeasPayload
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization, get_emoji_wrap
from bot.resources.info import DEFAULT_THREAD_NAME, DEFAULT_THREAD_NAME_RU
from .base import ViewOptionItem
from ..embeds import join_args, get_emoji


@AsyncSterilization
class ThreadsOpenDropdown(nextcord.ui.StringSelect):
    async def __init__(self, guild_id: int) -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        ideas: IdeasPayload = await gdb.get('ideas')
        thread_open = ideas.get('thread_open')
        get_emoji = await get_emoji_wrap(gdb)

        options = [
            nextcord.SelectOption(
                label=i18n.t(
                    locale, 'settings.ideas.threads.open.enable.label'),
                value=1,
                description=i18n.t(
                    locale, 'settings.ideas.threads.open.enable.description'),
                emoji=get_emoji('ticon'),
                default=thread_open
            ),
            nextcord.SelectOption(
                label=i18n.t(
                    locale, 'settings.ideas.threads.open.disable.label'),
                value=0,
                description=i18n.t(
                    locale, 'settings.ideas.threads.open.disable.description'),
                emoji=get_emoji('ticoff'),
                default=not thread_open
            ),
        ]

        super().__init__(options=options)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = bool(int(self.values[0]))

        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set_on_json('ideas', 'thread_open', value)

        view = await ThreadsView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class ThreadsDeleteDropdown(nextcord.ui.StringSelect):
    async def __init__(self, guild_id: int) -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        ideas: IdeasPayload = await gdb.get('ideas')
        thread_delete = ideas.get('thread_delete')
        get_emoji = await get_emoji_wrap(gdb)

        options = [
            nextcord.SelectOption(
                label=i18n.t(
                    locale, 'settings.ideas.threads.delete.enable.label'),
                value=1,
                description=i18n.t(
                    locale, 'settings.ideas.threads.delete.enable.description'),
                emoji=get_emoji('ticon'),
                default=thread_delete
            ),
            nextcord.SelectOption(
                label=i18n.t(
                    locale, 'settings.ideas.threads.delete.disable.label'),
                value=0,
                description=i18n.t(
                    locale, 'settings.ideas.threads.delete.disable.description'),
                emoji=get_emoji('ticoff'),
                default=not thread_delete
            ),
        ]

        super().__init__(placeholder=i18n.t(locale,
                                            'settings.tickets.modals.dropdown.required.placeholder'), options=options)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = bool(int(self.values[0]))

        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set_on_json('ideas', 'thread_delete', value)

        view = await ThreadsView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class ThreadsNameModal(nextcord.ui.Modal):
    async def __init__(self, guild_id: int) -> None:
        gdb = GuildDateBases(guild_id)
        ideas: IdeasPayload = await gdb.get('ideas')
        locale = await gdb.get('language')
        default_thread_name = DEFAULT_THREAD_NAME_RU if locale == 'ru' else DEFAULT_THREAD_NAME
        thread_name = ideas.get('thread_name', default_thread_name)

        super().__init__(i18n.t(locale, 'settings.ideas.threads.name.title'))

        self.name = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.ideas.threads.name.label'),
            max_length=100,
            placeholder=thread_name
        )
        self.add_item(self.name)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = self.name.value

        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set_on_json('ideas', 'thread_name', value)

        view = await ThreadsView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class ThreadsView(ViewOptionItem):
    label: str = 'settings.ideas.dropdown.threads.title'
    description: str = 'settings.ideas.dropdown.threads.description'
    emoji: str = 'ticpanelmes'

    async def __init__(self, guild: nextcord.Guild) -> None:
        self.guild = guild

        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        system_emoji = await gdb.get('system_emoji')
        color = await gdb.get('color')
        ideas = await self.get_ideas_data()
        thread_open = ideas.get('thread_open')
        thread_delete = ideas.get('thread_delete')
        default_thread_name = DEFAULT_THREAD_NAME_RU if locale == 'ru' else DEFAULT_THREAD_NAME
        thread_name = ideas.get('thread_name', default_thread_name)

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.ideas.init.title'),
            description=i18n.t(locale, 'settings.ideas.init.description'),
            color=color
        )

        description = join_args(
            (i18n.t(locale, 'settings.ideas.value.thread_delete'), get_emoji(system_emoji, thread_delete)),
            (i18n.t(locale, 'settings.ideas.value.thread_open'), get_emoji(system_emoji, thread_open)),
            (i18n.t(locale, 'settings.ideas.value.thread_name'), thread_open and thread_name and '`'+thread_name+'`'),
        )
        self.embed.description += '\n\n'+description

        super().__init__()

        self.add_item(await ThreadsOpenDropdown(guild.id))
        self.add_item(await ThreadsDeleteDropdown(guild.id))

        if thread_open:
            self.edit.disabled = False
            self.reset.disabled = False

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.edit.label = i18n.t(locale, 'settings.ideas.button.edit_thread')
        self.reset.label = i18n.t(locale, 'settings.ideas.button.reset_thread')

    @nextcord.ui.button(label='Edit thread name', style=nextcord.ButtonStyle.green, disabled=True)
    async def edit(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        modal = await ThreadsNameModal(interaction.guild_id)
        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label='Reset thread name', style=nextcord.ButtonStyle.blurple, disabled=True)
    async def reset(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        thread_name = DEFAULT_THREAD_NAME_RU if locale == 'ru' else DEFAULT_THREAD_NAME
        await gdb.set_on_json('ideas', 'thread_name', thread_name)

        view = await ThreadsView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
