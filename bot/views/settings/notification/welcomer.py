from httpx import delete
import nextcord

from bot.misc.utils.image_utils import WelcomeImageGenerator
from bot.views.settings import notification
from bot.views.settings._view import DefaultSettingsView

from bot.misc import utils
from bot.languages import i18n
from bot.databases import GuildDateBases
from bot.resources.info import DEFAULT_WELCOMER_IMAGE_CONFIG, DEFAULT_WELCOMER_CONTENT


@utils.AsyncSterilization
class MessageModal(nextcord.ui.Modal):
    async def __init__(self, guild: nextcord.Guild) -> None:
        self.gdb = GuildDateBases(guild.id)
        locale = await self.gdb.get('language')
        greeting_message = await self.gdb.get('greeting_message')

        super().__init__(i18n.t(locale, 'settings.welcomer.modal.title'))

        self.message = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.welcomer.modal.label'),
            placeholder=i18n.t(locale, 'settings.welcomer.modal.placeholder'),
            style=nextcord.TextInputStyle.paragraph,
            default_value=greeting_message.get('message')
        )
        self.add_item(self.message)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        message = self.message.value
        greeting_message: dict = await self.gdb.get('greeting_message')
        greeting_message['message'] = message
        await self.gdb.set('greeting_message', greeting_message)

        view = await WelcomerView(interaction.guild)

        await interaction.response.edit_message(embed=view.embed, view=view)


@utils.AsyncSterilization
class ChannelsDropDown(nextcord.ui.ChannelSelect):
    async def __init__(self, guild_id) -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        super().__init__(
            placeholder=i18n.t(
                locale, 'settings.welcomer.dropdown-placeholder'),
            channel_types=[nextcord.ChannelType.news,
                           nextcord.ChannelType.text]
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        channel = self.values[0]

        gdb = GuildDateBases(interaction.guild_id)
        greeting_message = await gdb.get('greeting_message')
        greeting_message['channel_id'] = channel.id
        if greeting_message.get('enabled') is None:
            greeting_message['enabled'] = True
        if 'content' not in greeting_message:
            greeting_message['message'] = DEFAULT_WELCOMER_CONTENT
        await gdb.set('greeting_message', greeting_message)

        view = await WelcomerView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)


@utils.AsyncSterilization
class WelcomerView(DefaultSettingsView):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild) -> None:
        self.gdb = GuildDateBases(guild.id)

        locale = await self.gdb.get('language')
        color = await self.gdb.get('color')
        greeting_message: dict = await self.gdb.get('greeting_message')
        enabled = greeting_message.get('enabled')
        message = greeting_message.get('message')
        image_config = greeting_message.get('image')
        channel_id = greeting_message.get('channel_id')

        super().__init__()

        self.add_item(await ChannelsDropDown(guild.id))

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.welcomer.embed.title'),
            description=i18n.t(locale, 'settings.welcomer.embed.description'),
            color=color
        )

        if channel := guild.get_channel(channel_id):
            self.channel = channel

            self.embed.add_field(
                name=i18n.t(locale, 'settings.welcomer.embed.field.selected',
                            channel=channel.mention),
                value='',
                inline=False)

        if (message or image_config) and enabled:
            self.preview.disabled = False

        if enabled:
            self.set_message.disabled = False
            self.switch_image.disabled = False

        if not (message or image_config) or not channel_id or not enabled:
            self.embed.add_field(
                name=i18n.t(locale, 'settings.welcomer.embed.field.failure'),
                value='',
                inline=False
            )

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.set_message.label = i18n.t(
            locale, 'settings.welcomer.button.install')
        self.preview.label = i18n.t(locale, 'settings.welcomer.button.view')
        self.delete.label = i18n.t(locale, 'settings.welcomer.button.delete')

        if image_config:
            self.switch_image.label = i18n.t(
                locale, 'settings.welcomer.button.disable_image')
            self.switch_image.style = nextcord.ButtonStyle.danger
        else:
            self.switch_image.label = i18n.t(
                locale, 'settings.welcomer.button.enable_image')
            self.switch_image.style = nextcord.ButtonStyle.success

        if enabled:
            self.switch.label = i18n.t(locale, 'settings.button.disable')
            self.switch.style = nextcord.ButtonStyle.danger
        else:
            self.switch.label = i18n.t(locale, 'settings.button.enable')
            self.switch.style = nextcord.ButtonStyle.success

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red, row=1)
    async def back(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        view = await notification.NotificationView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Switch', style=nextcord.ButtonStyle.red, row=1)
    async def switch(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        greeting_message: dict = await self.gdb.get('greeting_message')
        enabled = greeting_message.get('enabled')
        if not enabled:
            greeting_message['enabled'] = True
            greeting_message['content'] = DEFAULT_WELCOMER_CONTENT
            await self.gdb.set('greeting_message', greeting_message)
        else:
            await self.gdb.set_on_json('greeting_message', 'enabled', False)

        view = await WelcomerView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Clear', style=nextcord.ButtonStyle.red, row=1)
    async def delete(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.gdb.set('greeting_message', {'enabled': False})

        view = await WelcomerView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Set message', style=nextcord.ButtonStyle.success, disabled=True, row=2)
    async def set_message(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        modal = await MessageModal(interaction.guild)

        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label='View', style=nextcord.ButtonStyle.blurple, disabled=True, row=2)
    async def preview(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.defer(with_message=True, ephemeral=True)

        greeting_message: dict = await self.gdb.get('greeting_message')
        content: str = greeting_message.get('message')
        payload = utils.get_payload(member=interaction.user)
        message_format = utils.lord_format(content, payload)
        message_data = utils.generate_message(message_format)

        content: str = greeting_message.get('message')

        message_format = utils.lord_format(content, payload)
        message_data = utils.generate_message(message_format)

        if (image_config := greeting_message.get('image')) and isinstance(image_config, dict):
            wig = WelcomeImageGenerator(
                interaction.user, interaction.client.session, image_config)
            image_bytes = await wig.generate()
            file = nextcord.File(image_bytes, "welcome-image.png")
            message_data["file"] = file

        await interaction.followup.send(**message_data)

    @nextcord.ui.button(label='Switch image', style=nextcord.ButtonStyle.red, disabled=True, row=2)
    async def switch_image(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        greeting_message: dict = await self.gdb.get('greeting_message')
        image_config = greeting_message.get('image')
        if image_config and isinstance(image_config, dict):
            await self.gdb.set_on_json('greeting_message', 'image', {})
        else:
            await self.gdb.set_on_json('greeting_message', 'image', DEFAULT_WELCOMER_IMAGE_CONFIG)

        view = await WelcomerView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
