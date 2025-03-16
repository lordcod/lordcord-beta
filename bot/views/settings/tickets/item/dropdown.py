from typing import Dict, List
import nextcord

from bot.databases import GuildDateBases
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization
from bot.views.settings.tickets.item.optns.components import TicketComponentsView
from .optns.categories import TicketCategoriesView
from .optns.channels import TicketChannelsView
from .optns.messages import TicketMessagesView
from .optns.name import TicketNameModal
from .optns.limit import UserLimitModal
from .optns.closed_user import ClosedUserFunction
from .optns.allowed_roles import TicketAllowedRolesView
from .optns.faq import TicketFAQView
from .optns.modals import TicketFormsView
from .optns.moderation_roles import TicketModRolesView
from .optns.base import OptionItem,  FunctionOptionItem, ViewOptionItem
from .optns.ticket_type import TicketTypeView

#
# TODO: Add Settings
# Categories (Advanced settings)
# Saving history
# Auto archived
# Channel id, category id, closed category id
#

distribution: List[AsyncSterilization[OptionItem]] = [
    TicketTypeView,
    ClosedUserFunction,
    TicketMessagesView,
    TicketNameModal,
    TicketChannelsView,
    TicketFAQView,
    TicketCategoriesView,
    TicketFormsView,
    UserLimitModal,
    TicketModRolesView,
    TicketAllowedRolesView,
    TicketComponentsView
]
distribution_keys: Dict[str, AsyncSterilization[OptionItem]] = {
    item.cls.__name__.lower(): item for item in distribution}


@AsyncSterilization
class TicketsItemDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild: nextcord.Guild, message_id: int):
        self.message_id = message_id

        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        system_emoji = await gdb.get('system_emoji')

        self.items: Dict[str, OptionItem] = {}
        for key, item in distribution_keys.items():
            self.items[key] = await item(guild, message_id)

        super().__init__(options=[
            nextcord.SelectOption(
                label=i18n.t(locale, item.label),
                value=key,
                description=i18n.t(locale, item.description),
                emoji=item.get_emoji(system_emoji)
            )
            for key, item in self.items.items()
        ])

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = self.values[0]
        item = self.items[value]

        if isinstance(item, nextcord.ui.Modal):
            await interaction.response.send_modal(item)
        elif isinstance(item, ViewOptionItem):
            embed = await item.get_embed(interaction.guild)
            await interaction.response.edit_message(embed=embed, view=item)
        elif isinstance(item, FunctionOptionItem):
            await item.callback(interaction)
