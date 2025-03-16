import nextcord

from bot.languages import help as help_info, i18n
from bot.databases import GuildDateBases
from bot.misc.utils import AsyncSterilization, get_emoji_wrap


@AsyncSterilization
class HelpDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild_id: int) -> None:
        self.gdb = GuildDateBases(guild_id)
        locale = await self.gdb.get('language')
        get_emoji = await get_emoji_wrap(self.gdb)

        options = [
            nextcord.SelectOption(
                label=i18n.t(locale, f'commands.category.{category}'),
                value=category,
                emoji=get_emoji(help_info.categories_emoji.get(category)),
            )
            for category in help_info.categories.keys()
        ]

        super().__init__(options=options)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        color = await self.gdb.get('color')
        locale = await self.gdb.get('language')

        category = self.values[0]
        category_data = help_info.categories.get(category)
        get_emoji = await get_emoji_wrap(self.gdb)
        emoji = get_emoji(help_info.categories_emoji.get(category))
        category_name = i18n.t(locale, f'commands.category.{category}')

        texts = []
        for command in category_data:
            cmd_name = command.get('name')
            texts.append(f"`{cmd_name}` - {i18n.t(locale, f'commands.command.{cmd_name}.brief')}")

        embed = nextcord.Embed(
            description='\n'.join(texts),
            color=color
        )
        embed.set_author(icon_url=nextcord.PartialEmoji.from_str(emoji).url,
                         name=category_name)
        await interaction.response.send_message(embed=embed, ephemeral=True)


@AsyncSterilization
class HelpView(nextcord.ui.View):
    async def __init__(self, guild_id) -> None:
        super().__init__()

        HDD = await HelpDropDown(guild_id)
        self.add_item(HDD)
