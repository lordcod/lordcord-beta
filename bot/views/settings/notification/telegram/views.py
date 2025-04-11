import random
import string
import nextcord

from bot.databases.handlers.guildHD import GuildDateBases
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization
from bot.views.settings._view import DefaultSettingsView
from bot.views.settings import notification

from .dropdowns import TelegramItemsDropDown
from .items import TelegramItemView
from .waiting import TelegramWaitingView


def generate_hex() -> str:
    return ''.join(random.choices(string.hexdigits, k=18))


@AsyncSterilization
class TelegramView(DefaultSettingsView):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild):
        gdb = GuildDateBases(guild.id)
        color = await gdb.get('color')
        locale = await gdb.get('language')

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.notifi.telegram.title'),
            color=color,
            description=i18n.t(locale, 'settings.notifi.telegram.description')
        )

        super().__init__()

        self.add_item(await TelegramItemsDropDown(guild))

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.add.label = i18n.t(locale, 'settings.button.add')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        modal = await notification.NotificationView(interaction.guild)
        await interaction.response.edit_message(modal)

    @nextcord.ui.button(label='Add', style=nextcord.ButtonStyle.green)
    async def add(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        request_id = random.randint(1_000_000, 1_000_000_000)

        def check_registration(id: str, chat):
            return int(id) == request_id

        view = await TelegramWaitingView(interaction.guild, request_id)
        await interaction.response.edit_message(embed=view.embed, view=view)

        _, chat = await interaction.client.wait_for('tg_channel_joined', check=check_registration)

        id = generate_hex()
        data = {
            'id': id,
            'chat_id': chat.chat_id,
            'title': chat.title,
            'username': chat.username
        }

        view = await TelegramItemView(interaction.guild, id, data)
        await interaction.message.edit(embed=view.embed, view=view)
