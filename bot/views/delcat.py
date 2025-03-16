import asyncio
import nextcord

from bot.languages import i18n
from bot.databases import GuildDateBases
from bot.misc.utils import AsyncSterilization

from bot.resources.ether import Emoji


@AsyncSterilization
class DelCatView(nextcord.ui.View):
    async def __init__(
        self,
        member: nextcord.Member,
        category: nextcord.CategoryChannel
    ) -> None:
        gdb = GuildDateBases(member.guild.id)
        self.locale = await gdb.get('language')
        emoji = nextcord.PartialEmoji.from_str(Emoji.warn)

        self.member = member
        self.category = category
        self.embed = nextcord.Embed(
            description=i18n.t(self.locale, "delcat.issue.description",
                               category=self.category.name),
            color=0xED390D
        )
        self.embed.set_author(
            name=i18n.t(self.locale, "delcat.issue.title"),
            icon_url=emoji.url
        )
        super().__init__(timeout=60)

    @nextcord.ui.button(label="Accept", style=nextcord.ButtonStyle.blurple)
    async def accept(
        self,
        button: nextcord.ui.Button,
        interaction: nextcord.Interaction
    ) -> None:
        tasks = [self.category.delete()] + [channel.delete()
                                            for channel in self.category.channels]
        await asyncio.gather(*tasks)

        emoji = nextcord.PartialEmoji.from_str(Emoji.success)
        embed = nextcord.Embed(
            description=i18n.t(
                self.locale, "delcat.accept.description", count=len(tasks)-1),
            color=0x57F287
        )
        self.embed.set_author(
            name=i18n.t(self.locale, "delcat.accept.title",
                        category=self.category.name),
            icon_url=emoji.url
        )

        await interaction.response.edit_message(embed=embed, view=None)

    @ nextcord.ui.button(label="Cancel", style=nextcord.ButtonStyle.red)
    async def cancel(
        self,
        button: nextcord.ui.Button,
        interaction: nextcord.Interaction
    ) -> None:
        emoji = nextcord.PartialEmoji.from_str(Emoji.success)
        embed = nextcord.Embed(color=0x57F287)
        self.embed.set_author(
            name=i18n.t(self.locale, "delcat.accept.title",
                        category=self.category.name),
            icon_url=emoji.url
        )

        await interaction.response.edit_message(embed=embed, view=None)

    async def interaction_check(
        self,
        interaction: nextcord.Interaction
    ) -> bool:
        return interaction.user == self.member
