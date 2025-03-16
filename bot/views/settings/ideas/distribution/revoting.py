from .base import FunctionOptionItem
from bot.resources.info import DEFAULT_IDEAS_REVOTING
from bot.misc.utils import AsyncSterilization
import nextcord


@AsyncSterilization
class RevotingFunc(FunctionOptionItem):
    async def __init__(self, guild: nextcord.Guild):
        await super().__init__(guild)

        ideas = await self.get_ideas_data()
        self.allow_image = ideas.get('revoting', DEFAULT_IDEAS_REVOTING)

        if self.allow_image:
            self.label = 'settings.ideas.dropdown.revoting.disable.label'
            self.description = 'settings.ideas.dropdown.revoting.disable.description'
            self.emoji = 'ticoff'
        else:
            self.label = "settings.ideas.dropdown.revoting.enable.label"
            self.description = 'settings.ideas.dropdown.revoting.enable.description'
            self.emoji = 'ticon'

    async def callback(self, interaction: nextcord.Interaction) -> None:
        ideas = await self.get_ideas_data()
        ideas['revoting'] = not ideas.get('revoting', DEFAULT_IDEAS_REVOTING)
        await self.set_ideas_data(ideas)

        await super().callback(interaction)
