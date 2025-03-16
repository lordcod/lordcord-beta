
import asyncio
from typing import Optional
import nextcord
from bot.databases import GuildDateBases
from bot.languages import i18n
from bot.misc.lordbot import LordBot
from bot.misc.utils import is_custom_emoji, is_emoji, AsyncSterilization

from nextcord.utils import MISSING


@AsyncSterilization
class RoleReactionItemModal(nextcord.ui.Modal):
    async def __init__(self, guild: nextcord.Guild, future: asyncio.Future) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        self.future = future

        super().__init__(i18n.t(locale, 'settings.set-reaction.modal.emoji'), timeout=60)

        self.emoji = nextcord.ui.TextInput(i18n.t(locale, 'settings.set-reaction.modal.emoji'))
        self.add_item(self.emoji)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        value = self.emoji.value

        if not is_emoji(value):
            await interaction.response.send_message(i18n.t(locale, 'settings.set-reaction.modal.error'), ephemeral=True)
            return

        self.future.set_result(value)


@AsyncSterilization
class ReactionUsingModal(nextcord.ui.View):
    async def __init__(self, guild_id: int, future: asyncio.Future) -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        self.future = future
        super().__init__(timeout=60)
        self.use_modal.label = i18n.t(locale, 'settings.set-reaction.button.use-modal')

    @nextcord.ui.button(label="Use modal", style=nextcord.ButtonStyle.blurple)
    async def use_modal(self,
                        button: nextcord.ui.Button,
                        interaction: nextcord.Interaction
                        ):
        await interaction.response.send_modal(await RoleReactionItemModal(interaction.guild, self.future))


async def fetch_reaction(
    interaction: nextcord.Interaction[LordBot],
    message: Optional[nextcord.Message] = None,
    content: Optional[str] = MISSING,
    content_i18n: Optional[str] = MISSING,
) -> str:
    if content is not MISSING and content_i18n is not MISSING:
        raise TypeError("Content and i18n no join")

    gdb = GuildDateBases(interaction.guild_id)
    locale = await gdb.get('language')
    future = interaction._state.loop.create_future()
    view = await ReactionUsingModal(interaction.guild_id, future)

    if message is None:
        if content_i18n is MISSING and content is MISSING:
            content = i18n.t(locale, 'settings.set-reaction.content')
        if content_i18n is not MISSING:
            content = i18n.t(locale, content_i18n)
        message = await interaction.response.send_message(content, view=view, ephemeral=True)

    def check(message: nextcord.Message):
        return message.author == interaction.user and message.channel == interaction.channel and is_emoji(message.content)

    try:
        listeners = interaction.client._listeners['message']
    except KeyError:
        listeners = []
        interaction.client._listeners['message'] = listeners
    finally:
        listeners.append((future, check))

    try:
        done = await asyncio.wait_for(future, timeout=60)
    except asyncio.TimeoutError:
        await message.edit(i18n.t(locale, 'settings.set-reaction.error.timeout'), view=None)
        return

    if isinstance(done, nextcord.Message):
        value = done.content
        await done.delete()
    else:
        value = done
    await message.delete()

    allowed_emoji = list(map(str, interaction._state.emojis))
    if is_custom_emoji(value) and value not in allowed_emoji:
        await message.edit(i18n.t(locale, 'settings.set-reaction.error.located'), view=None)
        return

    return value
