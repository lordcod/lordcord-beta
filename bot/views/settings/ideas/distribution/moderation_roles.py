import nextcord

from bot.languages import i18n
from bot.misc.utils import AsyncSterilization

from bot.databases import GuildDateBases
from bot.databases.varstructs import IdeasPayload
from .base import ViewOptionItem


@AsyncSterilization
class RolesDropDown(nextcord.ui.RoleSelect):
    async def __init__(
        self,
        guild: nextcord.Guild
    ) -> None:
        self.gdb = GuildDateBases(guild.id)
        locale = await self.gdb.get('language')

        super().__init__(
            placeholder=i18n.t(locale, 'settings.ideas.mod_role.dropdown'),
            min_values=1,
            max_values=15
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        locale = await self.gdb.get('language')

        for role in self.values.roles:
            if role.is_integration() or role.is_bot_managed():
                await interaction.response.send_message(
                    content=i18n.t(
                        locale, 'settings.roles.error.integration', role=role.mention),
                    ephemeral=True
                )
                return
        else:
            await self.gdb.set_on_json('ideas', 'moderation_role_ids', self.values.ids)

            view = await ModerationRolesView(interaction.guild)
            await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class ModerationRolesView(ViewOptionItem):
    label: str = 'settings.ideas.dropdown.mod_roles.title'
    description: str = 'settings.ideas.dropdown.mod_roles.description'
    emoji: str = 'ideamod'

    async def __init__(self, guild: nextcord.Guild) -> None:
        self.gdb = GuildDateBases(guild.id)
        self.idea_data: IdeasPayload = await self.gdb.get('ideas')
        mod_role_ids = self.idea_data.get('moderation_role_ids')
        color = await self.gdb.get('color')
        locale = await self.gdb.get('language')

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.ideas.init.title'),
            description=i18n.t(locale, 'settings.ideas.init.description'),
            color=color
        )

        field_roles = None
        if mod_role_ids:
            moderation_roles = filter(lambda item: item is not None,
                                      map(guild.get_role,
                                          mod_role_ids))
            if moderation_roles:
                field_roles = '・'.join([role.mention for role in moderation_roles])

        if field_roles:
            self.embed.add_field(
                name='',
                value=i18n.t(locale, 'settings.ideas.mod_role.field')+field_roles
            )

        super().__init__()

        if mod_role_ids:
            self.delete.disabled = False

        self.edit_row_back(1)

        cdd = await RolesDropDown(guild)
        self.add_item(cdd)

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.delete.label = i18n.t(locale, 'settings.button.delete')

    @nextcord.ui.button(label='Delete', style=nextcord.ButtonStyle.red, row=1, disabled=True)
    async def delete(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.gdb.set_on_json('ideas', 'moderation_role_ids', [])

        view = await ModerationRolesView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
