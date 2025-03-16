from __future__ import annotations

import asyncio
import nextcord
import time
from typing import TYPE_CHECKING, Optional
from bot.databases.handlers.guildHD import GuildDateBases
from bot.languages import i18n
from bot.misc import giveaway as misc_giveaway
from bot.misc.utils import AsyncSterilization, translate_to_timestamp

if TYPE_CHECKING:
    from bot.misc.lordbot import LordBot
    from bot.misc.giveaway import GiveawayConfig, Giveaway


@AsyncSterilization
class GiveawaySettingsSponsorDropDown(nextcord.ui.UserSelect):
    async def __init__(self, member: nextcord.Member, guild_id: int, giveaway_config: GiveawayConfig) -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        self.member = member
        self.giveaway_config = giveaway_config
        super().__init__(placeholder=i18n.t(locale, 'giveaway.settings.sponsor'))

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        return interaction.user == self.member

    async def callback(self, interaction: nextcord.Interaction) -> None:
        self.giveaway_config.sponsor = self.values[0]

        view = await GiveawaySettingsView(
            self.member, interaction.guild_id, self.giveaway_config)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class GiveawaySettingsChannelDropDown(nextcord.ui.ChannelSelect):
    async def __init__(self, member: nextcord.Member, guild_id: int, giveaway_config: 'GiveawayConfig') -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        self.member = member
        self.giveaway_config = giveaway_config
        super().__init__(placeholder=i18n.t(locale, 'giveaway.settings.channel'), channel_types=[
            nextcord.ChannelType.news, nextcord.ChannelType.text])

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        return interaction.user == self.member

    async def callback(self, interaction: nextcord.Interaction) -> None:
        channel: nextcord.TextChannel = self.values[0]

        if not channel.permissions_for(interaction.client).send_messages:
            await interaction.response.send_message("У бота недостаточно прав")
            return

        self.giveaway_config.channel = channel

        view = await GiveawaySettingsView(
            self.member, interaction.guild_id, self.giveaway_config)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class GiveawaySettingsPrizeModal(nextcord.ui.Modal):
    async def __init__(self, guild_id: int, giveaway_config: 'GiveawayConfig') -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')

        self.giveaway_config = giveaway_config

        super().__init__("giveaway.settings.prize.placeholder")

        self.prize = nextcord.ui.TextInput(
            label=i18n.t(locale, "giveaway.settings.prize.label"),
            max_length=200
        )
        self.add_item(self.prize)

        self.quantity = nextcord.ui.TextInput(
            label=i18n.t(locale, "giveaway.settings.prize.quantity"),
            max_length=2,
            default_value="1"
        )
        self.add_item(self.quantity)

    async def callback(self, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')

        if not self.quantity.value.isdigit():
            await interaction.response.send_message(i18n.t(locale, "giveaway.settings.prize.error"), ephemeral=True)
            return

        self.giveaway_config.prize = self.prize.value
        self.giveaway_config.quantity = int(self.quantity.value)

        view = await GiveawaySettingsView(
            interaction.user, interaction.guild_id, self.giveaway_config)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class GiveawaySettingsDescriptionModal(nextcord.ui.Modal):
    async def __init__(self, guild_id: int, giveaway_config: 'GiveawayConfig') -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')

        self.giveaway_config = giveaway_config

        super().__init__(i18n.t(locale, "giveaway.settings.description.placeholder"))

        self.description = nextcord.ui.TextInput(
            label=i18n.t(locale, "giveaway.settings.description.title"),
            style=nextcord.TextInputStyle.paragraph
        )
        self.add_item(self.description)

    async def callback(self, interaction: nextcord.Interaction):
        self.giveaway_config.description = self.description.value

        view = await GiveawaySettingsView(
            interaction.user, interaction.guild_id, self.giveaway_config)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class GiveawaySettingsDateendModal(nextcord.ui.Modal):
    async def __init__(self, guild_id: int, giveaway_config: 'GiveawayConfig') -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        self.giveaway_config = giveaway_config

        super().__init__(i18n.t(locale, "giveaway.settings.dateend.placeholder"))

        self.date_end = nextcord.ui.TextInput(
            label=i18n.t(locale, "giveaway.settings.dateend.title"),
            style=nextcord.TextInputStyle.paragraph,
            placeholder=(
                "01.01.2023\n"
                "01.01.2023 12:30\n"
                "01.01.2023 12:30:45\n"
                "12:30\n"
                "1d2m3h4m5s"
            )
        )
        self.add_item(self.date_end)

    async def callback(self, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')

        date_end = translate_to_timestamp(self.date_end.value)

        if not date_end:
            await interaction.response.send_message(i18n.t(locale, "giveaway.settings.dateend.error"))
            return

        self.giveaway_config.date_end = date_end

        view = await GiveawaySettingsView(
            interaction.user, interaction.guild_id, self.giveaway_config)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class GiveawaySettingsView(nextcord.ui.View):
    embed: nextcord.Embed

    async def __init__(self, member: nextcord.Member, guild_id: int, giveaway_config: Optional[GiveawayConfig] = None) -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        if giveaway_config is None:
            giveaway_config = misc_giveaway.GiveawayConfig()
        self.giveaway_config = giveaway_config
        self.member = member
        super().__init__()
        self.add_item(await GiveawaySettingsChannelDropDown(
            member, guild_id, self.giveaway_config))
        self.add_item(await GiveawaySettingsSponsorDropDown(
            member, guild_id, self.giveaway_config))

        self.embed = nextcord.Embed(
            title=i18n.t(locale, "giveaway.settings.init.title"))

        self.embed.description = self.giveaway_config.description
        self.embed.add_field(
            name=i18n.t(locale, "giveaway.settings.init.info.title"),
            value=i18n.t(locale, "giveaway.settings.init.info.decription",
                         prize=self.giveaway_config.prize if self.giveaway_config.prize else i18n.t(locale, 'giveaway.settings.init.info.dnr'),
                         quantity=self.giveaway_config.quantity if self.giveaway_config.quantity else 1,
                         channel=self.giveaway_config.channel.mention if self.giveaway_config.channel else i18n.t(locale, 'giveaway.settings.init.info.dnr'),
                         sponsor=self.giveaway_config.sponsor.mention if self.giveaway_config.sponsor else member.mention,
                         date_end=f'<t:{self.giveaway_config.date_end :.0f}:f>' if self.giveaway_config.date_end else i18n.t(locale, 'giveaway.settings.init.info.dnr')
                         ),
        )

        if self.giveaway_config.prize:
            self.prize.style = nextcord.ButtonStyle.blurple
        if self.giveaway_config.description:
            self.description.style = nextcord.ButtonStyle.blurple
        if self.giveaway_config.date_end:
            self.date_end.style = nextcord.ButtonStyle.blurple

        self.create.label = i18n.t(locale, "giveaway.settings.init.create.title")
        self.prize.label = i18n.t(locale, "giveaway.settings.prize.label")
        self.description.label = i18n.t(locale, "giveaway.settings.description.title")
        self.date_end.label = i18n.t(locale, "giveaway.settings.dateend.title")

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        return interaction.user == self.member

    @nextcord.ui.button(label="Create giveaway", style=nextcord.ButtonStyle.success)
    async def create(self, button: nextcord.ui.Button, interaction: nextcord.Interaction[LordBot]):
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        if not (self.giveaway_config.prize
                and self.giveaway_config.date_end
                and self.giveaway_config.channel):
            await interaction.response.send_message(i18n.t(locale, "giveaway.settings.init.create.error"),
                                                    ephemeral=True)
            return
        if not self.giveaway_config.sponsor:
            self.giveaway_config.sponsor = interaction.user
        asyncio.create_task(interaction.delete_original_message(), name=f'giveaway:delete:{interaction.message.id}')
        giveaway = await misc_giveaway.Giveaway.create_as_config(interaction.guild, self.giveaway_config)
        await giveaway.fetch_giveaway_data()
        interaction.client.lord_handler_timer.create(
            giveaway.giveaway_data.get('date_end')-time.time(),
            giveaway.complete(),
            f'giveaway:{giveaway.message_id}'
        )

    @nextcord.ui.button(label="Prize", style=nextcord.ButtonStyle.grey)
    async def prize(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(await GiveawaySettingsPrizeModal(interaction.guild_id, self.giveaway_config))

    @nextcord.ui.button(label="Description", style=nextcord.ButtonStyle.grey)
    async def description(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(await GiveawaySettingsDescriptionModal(interaction.guild_id, self.giveaway_config))

    @nextcord.ui.button(label="Date end", style=nextcord.ButtonStyle.grey)
    async def date_end(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(await GiveawaySettingsDateendModal(interaction.guild_id, self.giveaway_config))


@AsyncSterilization
class GiveawayConfirmView(nextcord.ui.View):
    async def __init__(self, giveaway: 'Giveaway') -> None:
        gdb = GuildDateBases(giveaway.guild.id)
        locale = await gdb.get('language')
        self.giveaway = giveaway
        super().__init__()
        self.confirm.label = i18n.t(locale, "giveaway.confirm.leave")

    @nextcord.ui.button(label="Leave giveaway", style=nextcord.ButtonStyle.red)
    async def confirm(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        asyncio.create_task(interaction.delete_original_message())

        if not await self.giveaway.check_participation(interaction.user.id):
            return

        await self.giveaway.demote_participant(interaction.user.id)
        await self.giveaway.update_message()


class GiveawayView(nextcord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @nextcord.ui.button(emoji="🎉", custom_id="giveaway:participate", style=nextcord.ButtonStyle.blurple)
    async def participate(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        giveaway = misc_giveaway.Giveaway(
            interaction.guild, interaction.message.id)

        if await giveaway.check_participation(interaction.user.id):
            await interaction.response.send_message(content=i18n.t(locale, "giveaway.confirm.issue"),
                                                    view=await GiveawayConfirmView(
                                                        giveaway),
                                                    ephemeral=True)
            return

        await giveaway.promote_participant(interaction.user.id)

        await giveaway.update_message()
