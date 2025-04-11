from PIL import UnidentifiedImageError
from aiohttp import ClientConnectorError
import nextcord
from easy_pil import load_image_async

from bot.views.settings import notification
from bot.views.settings._view import DefaultSettingsView

from bot.misc import utils
from bot.languages import i18n
from bot.databases import GuildDateBases


@utils.AsyncSterilization
class MyIWMModal(nextcord.ui.Modal):
    async def __init__(self, guild_id: int) -> None:
        self.gdb = GuildDateBases(guild_id)
        locale = self.gdb.get('language')

        super().__init__("image")

        self.link = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.welcomer.image.link'),
            placeholder=i18n.t(locale, 'settings.welcomer.image.placeholder'),
            min_length=10,
            max_length=1000
        )

        self.add_item(self.link)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        locale = self.gdb.get('language')
        link = self.link.value

        try:
            await load_image_async(link)
        except (ClientConnectorError, UnidentifiedImageError):
            await interaction.response.send_message(i18n.t(locale, 'settings.welcomer.image.error'), ephemeral=True)
            return

        await self.gdb.set_on_json('greeting_message', 'image', link)

        view = await WelcomerView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)


@utils.AsyncSterilization
class IWMDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild_id: int) -> None:
        self.gdb = GuildDateBases(guild_id)
        greeting_message: dict = await self.gdb.get('greeting_message')
        image = greeting_message.get('image')

        options = []
        for name, wel_mes in utils.welcome_message_items.items():
            options.append(nextcord.SelectOption(
                label=wel_mes[0],
                value=name,
                description=wel_mes[2],
                default=wel_mes[1] == image
            ))
        super().__init__(options=options)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = self.values[0]
        if value == "my-image":
            modal = await MyIWMModal(interaction.guild_id)
            await interaction.response.send_modal(modal)
            return

        image = utils.welcome_message_items[value][1]
        await self.gdb.set_on_json('greeting_message', 'image', image)

        view = await WelcomerView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)


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

        self.gdb = GuildDateBases(interaction.guild_id)
        greeting_message: dict = await self.gdb.get('greeting_message')
        greeting_message['channel_id'] = channel.id
        await self.gdb.set('greeting_message', greeting_message)

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

        super().__init__()

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.install.label = i18n.t(locale, 'settings.welcomer.button.install')
        self.preview.label = i18n.t(locale, 'settings.welcomer.button.view')
        self.delete.label = i18n.t(locale, 'settings.welcomer.button.delete')

        self.add_item(await ChannelsDropDown(guild.id))
        self.add_item(await IWMDropDown(guild.id))

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.welcomer.embed.title'),
            description=i18n.t(locale, 'settings.welcomer.embed.description'),
            color=color
        )

        if channel := guild.get_channel(
                greeting_message.get('channel_id')):
            self.delete.disabled = False
            self.channel = channel

            self.embed.add_field(
                name=i18n.t(locale, 'settings.welcomer.embed.field.selected',
                            channel=channel.mention),
                value='',
                inline=False)
        else:
            self.install.disabled = True

        if greeting_message.get('message'):
            self.delete.disabled = False
        else:
            self.preview.disabled = True

        if not (greeting_message.get('message') and greeting_message.get('channel_id')):
            self.embed.add_field(
                name=i18n.t(locale, 'settings.welcomer.embed.field.failure'),
                value='',
                inline=False
            )

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        view = await notification.NotificationView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Install', style=nextcord.ButtonStyle.success)
    async def install(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        modal = await MessageModal(interaction.guild)

        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label='View', style=nextcord.ButtonStyle.blurple)
    async def preview(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.defer()

        greeting_message: dict = await self.gdb.get('greeting_message')
        content: str = greeting_message.get('message')
        payload = utils.get_payload(member=interaction.user)
        message_format = utils.lord_format(content, payload)
        message_data = utils.generate_message(message_format)

        if image_link := greeting_message.get('image'):
            image_bytes = await utils.generate_welcome_image(interaction.user, image_link)
            file = nextcord.File(image_bytes, "welcome-image.png")
            message_data["file"] = file

        await interaction.followup.send(**message_data, ephemeral=True)

    @nextcord.ui.button(label='Delete', style=nextcord.ButtonStyle.red, disabled=True)
    async def delete(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.gdb.set('greeting_message', {})

        view = await WelcomerView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
