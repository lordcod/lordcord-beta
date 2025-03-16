import nextcord

from bot.databases.handlers.economyHD import EconomyMemberDB
from bot.misc import logstool
from bot.misc.utils import BlackjackGame


class BlackjackView(nextcord.ui.View):
    embed: nextcord.Embed

    def __init__(self, bjg: BlackjackGame) -> None:
        self.account = EconomyMemberDB(bjg.member.guild.id, bjg.member.id)
        self.bjg = bjg
        super().__init__()

    async def on_timeout(self) -> None:
        self.bjg.complete()

    @nextcord.ui.button(label="Hit", style=nextcord.ButtonStyle.blurple)
    async def hit(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.bjg.add_your_card()

        if self.bjg.is_exceeds_your():
            embed = await self.bjg.completed_embed()
            await interaction.response.edit_message(embed=embed, view=None)
            self.bjg.complete()
        else:
            embed = await self.bjg.embed()
            await interaction.response.edit_message(embed=embed, view=self)

    @nextcord.ui.button(label="Stand", style=nextcord.ButtonStyle.green)
    async def stand(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.bjg.go_dealer()

        embed = await self.bjg.completed_embed()
        await interaction.response.edit_message(embed=embed, view=None)

        match self.bjg.is_winner():
            case 2:
                await self.account.increment("balance", self.bjg.amount)
                await logstool.Logs(self.bjg.member.guild).add_currency(self.bjg.member, self.bjg.amount, reason='draw at blackjack')
            case 1:
                await self.account.increment("balance", 2*self.bjg.amount)
                await logstool.Logs(self.bjg.member.guild).add_currency(self.bjg.member, self.bjg.amount, reason='winning at blackjack')

        self.bjg.complete()
