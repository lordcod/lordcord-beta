import nextcord

from bot.misc.utils import AsyncSterilization


from ... import permisson_command
from bot.views.settings._view import DefaultSettingsView

from bot.databases import GuildDateBases, CommandDB


@AsyncSterilization
class DenyRolesDropDown(nextcord.ui.RoleSelect):
    async def __init__(
        self,
        guild: nextcord.Guild,
        command_name: str
    ) -> None:
        self.command_name = command_name
        self.gdb = GuildDateBases(guild.id)

        super().__init__(
            min_values=1,
            max_values=15,
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        for role in self.values.roles:
            if role.is_integration() or role.is_bot_managed():
                await interaction.response.send_message(
                    content=f"The {role.mention} role cannot be assigned and is used for integration or by a bot.",
                    ephemeral=True
                )
                return

        cdb = CommandDB(interaction.guild_id)
        command_data = await cdb.get(self.command_name, {})
        command_data.setdefault("distribution", {})
        command_data["distribution"]["deny-role"] = self.values.ids
        await cdb.update(self.command_name, command_data)

        view = await DenyRolesView(
            interaction.guild,
            self.command_name
        )
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class DenyRolesView(DefaultSettingsView):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild, command_name: str) -> None:
        self.command_name = command_name

        gdb = GuildDateBases(guild.id)
        color = await gdb.get('color')

        cdb = CommandDB(guild.id)
        command_data = await cdb.get(self.command_name, {})
        command_data.setdefault("distribution", {})
        role_ids = command_data["distribution"].get(
            "deny-role", [])

        self.embed = nextcord.Embed(
            title="Denyed roles",
            description="The selected command will only work in the roles that you select",
            color=color
        )
        if role_ids:
            self.embed.add_field(
                name="Selected roles:",
                value=', '.join([role.mention
                                 for role_id in role_ids
                                 if (role := guild.get_role(role_id))])
            )

        super().__init__()

        cdd = await DenyRolesDropDown(
            guild,
            command_name
        )
        self.add_item(cdd)

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        view = await permisson_command.precise.CommandView(
            interaction.guild,
            self.command_name
        )
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Delete', style=nextcord.ButtonStyle.red)
    async def delete(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        cdb = CommandDB(interaction.guild_id)

        command_data = await cdb.get(self.command_name, {})
        command_data.setdefault("distribution", {})
        command_data["distribution"].pop("deny-role", None)
        await cdb.update(self.command_name, command_data)

        view = await DenyRolesView(interaction.guild, self.command_name)
        await interaction.response.edit_message(embed=view.embed, view=view)
