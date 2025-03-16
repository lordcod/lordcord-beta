import logging
import nextcord
from nextcord.ext import commands

from bot.databases import GuildDateBases
from bot.languages import i18n
from bot.misc.lordbot import LordBot
from string import hexdigits

from bot.resources.info import DISCORD_SUPPORT_SERVER

_log = logging.getLogger(__name__)


class InteractionsEvent(commands.Cog):
    def __init__(self, bot: LordBot) -> None:
        self.bot = bot
        bot.set_event(self.on_item_not_found, name='on_view_not_found')
        bot.set_event(self.on_item_not_found, name='on_modal_not_found')
        super().__init__()

    async def on_item_not_found(self, interaction: nextcord.Interaction):
        if interaction.is_expired() or interaction.response.is_done():
            return

        gdb = GuildDateBases(interaction.guild_id)
        color = await gdb.get('color')
        locale = await gdb.get('language')

        embed = nextcord.Embed(
            title=i18n.t(locale, 'interaction.error.expired.title'),
            description=i18n.t(locale, 'interaction.error.expired.description'),
            color=color
        )
        if set(interaction.data['custom_id']) - set(hexdigits):
            embed.add_field(
                '',
                i18n.t(locale, 'interaction.error.expired.support',  DISCORD_SUPPORT_SERVER=DISCORD_SUPPORT_SERVER)
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


def setup(bot):
    bot.add_cog(InteractionsEvent(bot))
