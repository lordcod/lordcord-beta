from typing import Optional
import nextcord
from bot import languages
from bot.languages import i18n
from bot.languages import data as lang_data
from bot.databases import GuildDateBases
import googletrans
import jmespath

from bot.misc.utils import AsyncSterilization

translator = googletrans.Translator()


@AsyncSterilization
class TranslateDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild_id: int, dest: Optional[str] = None) -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')

        super().__init__(
            placeholder=i18n.t(locale, 'translate.placeholder'),
            options=[
                nextcord.SelectOption(
                    label=lang.get('native_name'),
                    value=lang.get('google_language'),
                    description=lang.get('language_name'),
                    emoji=lang.get('flag'),
                    default=lang.get('google_language') == dest
                )
                for lang in languages.data[:24]
            ]
        )

    async def callback(self, interaction: nextcord.Interaction):
        await interaction.response.defer()

        dest = self.values[0]
        result = translator.translate(
            text=interaction.message.content, dest=dest)

        view = TranslateView(interaction.guild_id, dest)
        await interaction.edit_original_message(content=result.text, view=view)


@AsyncSterilization
class TranslateView(nextcord.ui.View):
    async def __init__(self, guild_id: int, dest: Optional[str] = None) -> None:
        super().__init__(timeout=None)
        tdd = await TranslateDropDown(guild_id, dest)
        self.add_item(tdd)


class AutoTranslateView(nextcord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @nextcord.ui.button(label="Translate", style=nextcord.ButtonStyle.blurple)
    async def translate(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        data = jmespath.search(
            f"[?discord_language=='{interaction.locale}']|[0]", lang_data)

        result = translator.translate(
            text=interaction.message.content, dest=data.get('google_language'))

        view = await TranslateView(interaction.guild_id, data.get('google_language'))

        await interaction.response.send_message(content=result.text,
                                                view=view,
                                                ephemeral=True)
