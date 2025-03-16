import contextlib
import logging
import nextcord
from nextcord.ext import commands
from bot.misc.lordbot import LordBot

_log = logging.getLogger(__name__)

reaction_data = {
    1153047978769133568: 1210941887108743218,
    1153051615121649896: 1210945846296846346,
    1211220580670373919: 1211220639634034699,
    1212086116031660072: 1212086745479520386
}


class CMCReactionEvent(commands.Cog):
    def __init__(self, bot: LordBot) -> None:
        self.bot = bot
        super().__init__()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: nextcord.RawReactionActionEvent):
        if (payload.channel_id not in reaction_data
                or str(payload.emoji) != "✅"):
            return

        guild = self.bot.get_guild(payload.guild_id)
        channel = guild.get_channel(payload.channel_id)

        try:
            message = await channel.fetch_message(payload.message_id)
        except nextcord.HTTPException:
            return

        reaction = nextcord.utils.get(message.reactions, emoji=payload.emoji.name)

        if not reaction or reaction.count > 1:
            return

        channel = reaction.message.guild.get_channel(
            reaction_data[reaction.message.channel.id])

        with contextlib.suppress(Exception):
            content = (
                f'Ник: **{message.embeds[0].fields[0].value}**\n'
                f'Дс: **{message.embeds[0].fields[1].value}**'
            )
            await channel.send(content)


def setup(bot):
    bot.add_cog(CMCReactionEvent(bot))
