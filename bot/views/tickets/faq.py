import nextcord
from bot.databases import GuildDateBases
from bot.databases.varstructs import CategoryPayload, TicketsButtonsPayload, TicketsItemPayload, TicketsPayload, FaqItemPayload
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization, generate_message, lord_format, get_payload
from typing import List, Optional
from bot.resources.info import DEFAULT_TICKET_FAQ_TYPE


@AsyncSterilization
class FAQDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild_id: Optional[int] = None,
                       faq_items: List[FaqItemPayload] = [],
                       buttons: Optional[TicketsButtonsPayload] = None):
        if guild_id is None:
            super().__init__(custom_id='tickets:faq')
            return
        faq_placeholder = buttons.get('faq_placeholder')
        options = [
            nextcord.SelectOption(
                label=item['label'],
                value=i,
                description=item.get('description'),
                emoji=item.get('emoji'),
            )
            for i, item in enumerate(faq_items)
        ]
        super().__init__(
            custom_id='tickets:faq:dropdown:only',
            placeholder=faq_placeholder,
            options=options
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets', {})
        items = tickets.get(interaction.message.id).get('faq').get('items')
        response = items[int(self.values[0])]
        
        data = generate_message(lord_format(
            response['response'], get_payload(member=interaction.user)))
        await interaction.response.send_message(**data, ephemeral=True)


@AsyncSterilization
class FAQTempDropDown(FAQDropDown.cls):
    async def __init__(self, guild_id: Optional[int] = None, faq_items: List[FaqItemPayload] = [], buttons: Optional[TicketsButtonsPayload] = None):
        await super().__init__(guild_id, faq_items, buttons=buttons)
        if guild_id is None:
            return
        self.faq_items = faq_items

    async def callback(self, interaction: nextcord.Interaction) -> None:
        response = self.faq_items[int(self.values[0])]
        data = generate_message(lord_format(
            response['response'], get_payload(member=interaction.user)))
        await interaction.response.send_message(**data, ephemeral=True)


@AsyncSterilization
class FAQButtonOpen(nextcord.ui.Button):
    async def __init__(self, guild_id: Optional[int] = None, buttons: Optional[TicketsButtonsPayload] = None) -> None:
        if guild_id is None:
            super().__init__(custom_id='tickets:faq:view:faq')
            return
        faq_button = buttons.get('faq_button_open')
        super().__init__(
            style=faq_button.get('style'),
            label=faq_button.get('label'),
            custom_id='tickets:faq:view:faq',
            emoji=faq_button.get('emoji')
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets', {})
        items = tickets.get(interaction.message.id).get('faq').get('items')
        buttons = tickets.get(interaction.message.id)['buttons']

        view = nextcord.ui.View(timeout=300)
        view.add_item(await FAQTempDropDown(interaction.guild_id, items, buttons))
        await interaction.response.send_message(view=view, ephemeral=True)


@AsyncSterilization
class FAQCreateDropDown(FAQDropDown.cls):
    async def __init__(self, guild_id: Optional[int] = None, faq_items: List[FaqItemPayload] = [], buttons: Optional[TicketsButtonsPayload] = None):
        await super().__init__(guild_id, faq_items, buttons)
        self.custom_id = 'tickets:faq:dropdown:create'
        if guild_id is None:
            return
        faq_option = buttons.get('faq_option')
        self.append_option(nextcord.SelectOption(
            label=faq_option['label'],
            value='create_ticket',
            description=faq_option.get('description'),
            emoji=faq_option.get('emoji')
        ))

    async def callback(self, interaction: nextcord.Interaction) -> None:
        from bot.misc.plugins.tickettools import ModuleTicket

        if self.values[0] != 'create_ticket':
            await super().callback(interaction)
            return
        await ModuleTicket(interaction.user, interaction.message.id).create_after_faq(interaction)


@AsyncSterilization
class FAQButtonCreate(nextcord.ui.Button):
    async def __init__(self, guild_id: Optional[int] = None, buttons: Optional[TicketsButtonsPayload] = None) -> None:
        if guild_id is None:
            super().__init__(custom_id='tickets:faq:view:create')
            return
        faq_option = buttons.get('faq_button_create')
        super().__init__(
            style=faq_option.get('style'),
            label=faq_option.get('label'),
            custom_id='tickets:faq:view:create',
            emoji=faq_option.get('emoji')
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        from bot.misc.plugins.tickettools import ModuleTicket

        await ModuleTicket(interaction.user, interaction.message.id).create_after_faq(interaction)


@AsyncSterilization
class ButtonCategoryCreate(nextcord.ui.Button):
    async def __init__(self, index: int, guild_id: Optional[int] = None,  button_data: Optional[CategoryPayload] = None) -> None:
        if guild_id is None:
            super().__init__(
                custom_id=f'tickets:faq:view:create:category:{index}')
            return
        super().__init__(
            style=button_data.get('style', nextcord.ButtonStyle.secondary),
            label=button_data.get('label'),
            custom_id=f'tickets:faq:view:create:category:{index}',
            emoji=button_data.get('emoji')
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        from bot.misc.plugins.tickettools import ModuleTicket

        index = int(interaction.data['custom_id'].removeprefix(
            'tickets:faq:view:create:category:'))
        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets', {})
        categories_data = tickets.get(interaction.message.id).get('categories')
        category = categories_data[index]
        await ModuleTicket(interaction.user, interaction.message.id).create_after_category(interaction, category)


@AsyncSterilization
class FAQView(nextcord.ui.View):
    async def __init__(self, guild_id: Optional[int] = None, ticket_data: TicketsItemPayload = None):
        super().__init__(timeout=None)
        if guild_id is None:
            self.add_item(await FAQCreateDropDown())
            self.add_item(await FAQButtonOpen())
            self.add_item(await FAQButtonCreate())
            for i in range(15):
                self.add_item(await ButtonCategoryCreate(i))
            return

        buttons = ticket_data.get('buttons')
        category_type = ticket_data.get('category_type', 1)

        faq = ticket_data.get('faq', {})
        faq_type = faq.get('type', DEFAULT_TICKET_FAQ_TYPE)
        faq_items = faq.get('items')

        if category_type == 1:
            if faq and faq_items:
                if faq_type == 1:
                    self.add_item(await FAQCreateDropDown(guild_id, faq_items, buttons))
                    return
                else:
                    self.add_item(await FAQButtonOpen(guild_id, buttons))
            self.add_item(await FAQButtonCreate(guild_id, buttons))
        elif category_type == 2:
            if faq and faq_items:
                categories_data = ticket_data.get('categories')

                if faq_type == 1:
                    if categories_data is None or len(categories_data) == 0:
                        self.add_item(await FAQCreateDropDown(guild_id, faq_items, buttons))
                        return
                    self.add_item(await FAQDropDown(guild_id, faq_items, buttons))
                else:
                    self.add_item(await FAQButtonOpen(guild_id, buttons))

            if (categories_data is None or len(categories_data) == 0) and faq_type != 1:
                self.add_item(await FAQButtonCreate(guild_id, buttons))
            for index, category in enumerate(categories_data):
                self.add_item(await ButtonCategoryCreate(index, guild_id, category))

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        tickets: TicketsPayload = await gdb.get('tickets', {})
        ticket_data = tickets.get(interaction.message.id, {})
        enabled = ticket_data.get('enabled')
        if not enabled:
            await interaction.response.send_message(i18n.t(locale, 'tickets.error.disabled'), ephemeral=True)
            return False
        return True
