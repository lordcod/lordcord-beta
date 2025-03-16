import nextcord

from bot.databases.handlers.guildHD import GuildDateBases
from bot.languages import i18n


class DefaultSettingsView(nextcord.ui.View):
    def __init__(self, *, timeout: float | None = 180, auto_defer: bool = True, prevent_update: bool = True) -> None:
        super().__init__(timeout=timeout, auto_defer=auto_defer, prevent_update=prevent_update)

    async def interaction_check(
        self,
        interaction: nextcord.Interaction
    ) -> bool:
        if not interaction.user.guild_permissions.manage_guild:
            gdb = GuildDateBases(interaction.guild_id)
            locale = await gdb.get('language')
            await interaction.response.send_message(
                i18n.t(locale, 'settings.permission.denied'),
                ephemeral=True
            )
            return False
        return True
