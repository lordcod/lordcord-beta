from typing import Optional
import nextcord
from nextcord.ext import commands
from bot.databases import GuildDateBases
from bot.languages import i18n
from bot.misc.lordbot import LordBot
from bot.resources.ether import Emoji


class GreedyUser(str):
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}['{self}']"

    def __class_getitem__(cls, param: str):
        return cls(param)


reaction_models = [
    GreedyUser['airkiss'],
    'angrystare',
    GreedyUser['bite'],
    'clap',
    GreedyUser['cuddle'],
    'bleh',
    'blush',
    'brofist',
    'celebrate',
    'cheers',
    'confused',
    GreedyUser['cool'],
    'cry',
    'dance',
    'drool',
    'evillaugh',
    'facepalm',
    GreedyUser['handhold'],
    GreedyUser['kiss'],
    'happy',
    'headbang',
    GreedyUser['hug'],
    'laugh',
    GreedyUser['lick'],
    GreedyUser['love'],
    'nervous',
    'no',
    'nom',
    'nosebleed',
    'mad',
    GreedyUser['nuzzle'],
    'nyah',
    GreedyUser['pat'],
    GreedyUser['pinch'],
    GreedyUser['poke'],
    'pout',
    GreedyUser['punch'],
    'roll',
    'run',
    'sad',
    'peek',
    'scared',
    'shout',
    'shrug',
    'shy',
    'sigh',
    'sip',
    'slap',
    'sleep',
    'slowclap',
    GreedyUser['smack'],
    'smug',
    'sneeze',
    GreedyUser['sorry'],
    'stare',
    'surprised',
    'sweat',
    'thumbsup',
    GreedyUser['tickle'],
    'tired',
    GreedyUser['wave'],
    GreedyUser['wink'],
    'yawn',
    'yay',
    'yes',
    'smile',
    'woah'
]


class InteractionsCommand(commands.Cog):
    def __init__(self, bot: LordBot) -> None:
        self.bot = bot

        for react_type in reaction_models:
            self.register_command(react_type)

    def register_command(self, react_type: str) -> None:
        @commands.command(name=react_type)
        async def _react_type_callback(ctx: commands.Context, user: Optional[nextcord.Member] = None, *, comment: Optional[str] = None):
            await self.reactions(ctx, react_type, user, comment=comment)
        self.bot.add_command(_react_type_callback)

    async def get_gif_with_react(self, react_type: str) -> str:
        params = {
            'reaction': react_type,
            'format': 'gif'
        }
        async with self.bot.session.get('https://api.otakugifs.xyz/gif', params=params) as responce:
            responce.raise_for_status()
            json = await responce.json()
            return json['url']

    @commands.command(name='interactions', aliases=['reactions', 'reacts'])
    async def reactions(self, ctx: commands.Context, react_type: str, user: Optional[nextcord.Member] = None, *, comment: Optional[str] = None) -> None:
        gdb = GuildDateBases(ctx.guild.id)
        color = await gdb.get('color')
        locale = await gdb.get('language')
        try:
            model = reaction_models[reaction_models.index(react_type)]
        except ValueError:
            await ctx.send(f"{Emoji.cross} The `{react_type}` interaction was not found")
            return

        if user is None and isinstance(model, GreedyUser):
            await ctx.send(f"{Emoji.cross} You must specify the user")
            return

        if user is None:
            text = i18n.t(locale, f"commands.reactions.{model}.not_user", author=ctx.author.mention)
        else:
            text = i18n.t(locale, f"commands.reactions.{model}.user", author=ctx.author.mention, user=user.mention)

        embed = nextcord.Embed(
            description=text,
            color=color
        )
        if comment:
            embed.add_field(
                name='Comment',
                value=comment
            )
        embed.set_image(await self.get_gif_with_react(react_type))

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(InteractionsCommand(bot))
