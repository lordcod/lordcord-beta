import nextcord

from ... import permisson_command
from bot.views.settings._view import DefaultSettingsView

from bot.misc.utils import TimeCalculator, AsyncSterilization

from bot.misc.time_transformer import display_time
from bot.misc.ratelimit import BucketType
from bot.databases import GuildDateBases, CommandDB

cd_types = {
    0: 'Member',
    1: 'Server(global)'
}


@AsyncSterilization
class CoolModal(nextcord.ui.Modal):
    async def __init__(
        self,
        cooltype: int,
        command_name: str,
        *,
        rate: int = None,
        per: float = None
    ) -> None:
        self.type = cooltype
        self.command_name = command_name

        super().__init__("Cooldown")

        self.rate = nextcord.ui.TextInput(
            label="Rate (Example: 2)",
            placeholder=rate,
            min_length=1,
            max_length=4,
        )
        self.per = nextcord.ui.TextInput(
            label="Per (Example: 1h10m)",
            placeholder=per,
            min_length=1,
            max_length=10
        )

        self.add_item(self.rate)
        self.add_item(self.per)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        srate = self.rate.value
        per = TimeCalculator().convert(self.per.value)
        rate = srate.isdigit() and int(srate)

        if not (per and rate):
            raise TypeError

        cdb = CommandDB(interaction.guild.id)
        command_data = await cdb.get(self.command_name, {})
        command_data.setdefault("distribution", {})
        command_data["distribution"]["cooldown"] = {
            "type": self.type,
            "rate": rate,
            "per": per
        }
        await cdb.update(self.command_name, command_data)

        view = await CooldownsView(
            interaction.guild,
            self.command_name
        )
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class CooltypeDropDown(nextcord.ui.StringSelect):
    async def __init__(
        self,
        guild_id: int,
        command_name: str
    ) -> None:
        self.command_name = command_name

        options = [
            nextcord.SelectOption(
                label="Member",
                value=BucketType.MEMBER.value
            ),
            nextcord.SelectOption(
                label="Server",
                value=BucketType.SERVER.value
            )
        ]

        super().__init__(options=options)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        cooltype = int(self.values[0])

        cdb = CommandDB(interaction.guild.id)
        command_data = await cdb.get(self.command_name, {})
        command_data.setdefault("distribution", {})
        command_data["distribution"].setdefault("cooldown", {})
        cooldata = command_data["distribution"]["cooldown"]

        if cooldata.get('rate') and cooldata.get('per'):
            cooldata.update({'type': cooltype})
            await cdb.update(self.command_name, command_data)

            view = await CooldownsView(
                interaction.guild,
                self.command_name
            )
            await interaction.response.edit_message(embed=view.embed, view=view)
            return

        modal = await CoolModal(cooltype, self.command_name)
        await interaction.response.send_modal(modal)


@AsyncSterilization
class CooldownsView(DefaultSettingsView):
    embed: nextcord.Embed = None

    async def __init__(self, guild: nextcord.Guild, command_name: str) -> None:
        self.command_name = command_name

        gdb = GuildDateBases(guild.id)
        lang = await gdb.get('language')
        color = await gdb.get('color')

        cdb = CommandDB(guild.id)
        command_data = await cdb.get(command_name, {})
        distribution = command_data.get("distribution", {})
        self.cooldate = cooldate = distribution.get("cooldown", None)

        super().__init__()

        if cooldate:
            description = (
                "The current delay for the command\n"
                f"Type: **{cd_types.get(cooldate.get('type'))}**\n"
                f"Frequency of use: **{cooldate.get('rate')}** → **{display_time(cooldate.get('per'), lang)}**\n"
            )
        else:
            self.remove_item(self.edit)
            self.remove_item(self.delete)
            description = "The delay is not set"

        self.embed = nextcord.Embed(
            title=f"Command: {command_name}",
            description=description,
            color=color
        )

        cdd = await CooltypeDropDown(
            guild.id,
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

    @nextcord.ui.button(label='Edit', style=nextcord.ButtonStyle.blurple)
    async def edit(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        cooltype = self.cooldate.get('type')

        modal = await CoolModal(cooltype, self.command_name)
        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label='Delete', style=nextcord.ButtonStyle.red)
    async def delete(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        cdb = CommandDB(interaction.guild.id)
        command_data = await cdb.get(self.command_name, {})
        command_data.setdefault("distribution", {})
        command_data["distribution"].pop("cooldown", None)
        await cdb.update(self.command_name, command_data)

        view = await CooldownsView(
            interaction.guild,
            self.command_name
        )
        await interaction.response.edit_message(embed=view.embed, view=view)
