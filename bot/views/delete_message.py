from typing import Optional
import nextcord
from bot.languages import i18n


class DeleteMessageView(nextcord.ui.View):
    def __init__(self, locale: Optional[str] = None):
        super().__init__(timeout=None)

        # self.delete_message.label = ''

    @nextcord.ui.button(label='Delete', custom_id='delete:message:view', style=nextcord.ButtonStyle.red)
    async def delete_message(self,
                             button: nextcord.ui.Button,
                             interaction: nextcord.Interaction):
        await interaction.response.defer()
        await interaction.message.delete()
