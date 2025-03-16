
import nextcord
from bot.databases import GuildDateBases

alphabet = ['🇦', '🇧', '🇨', '🇩', '🇪', '🇫', '🇬', '🇭', '🇮', '🇯',
            '🇰', '🇱', '🇲', '🇳', '🇴', '🇵', '🇶', '🇷', '🇸', '🇹',
            '🇺', '🇻', '🇼', '🇽', '🇾', '🇿']


class CreatePoll(nextcord.ui.Modal):
    def __init__(self) -> None:
        super().__init__("Create pool", timeout=300)

        self.question = nextcord.ui.TextInput(
            label='Question',
            placeholder='Write a question',
            max_length=100
        )
        self.choices = nextcord.ui.TextInput(
            label='Choices',
            placeholder='Write the options of choice through the line each',
            style=nextcord.TextInputStyle.paragraph
        )
        self.description = nextcord.ui.TextInput(
            label='Description',
            style=nextcord.TextInputStyle.paragraph,
            required=False,
            max_length=1500
        )

        self.add_item(self.question)
        self.add_item(self.choices)
        self.add_item(self.description)

    async def callback(self, interaction: nextcord.Interaction):
        await interaction.response.defer()

        gdb = GuildDateBases(interaction.guild_id)
        color = await gdb.get('color')
        polls = await gdb.get('polls')

        question = self.question.value
        choices = self.choices.value.split('\n')[:len(alphabet)]
        sketch = self.description.value

        if 1 >= len(choices):
            await interaction.followup.send(content=(
                "There must be more than 1 choice option\n"
                "To specify more options, move the line"
            ), ephemeral=True)
            return

        description = '\n'.join(
            [f'* {alphabet[num]} `{choice}`' for num, choice in enumerate(choices)])

        embed = nextcord.Embed(
            title=question,
            description=description,
            color=color
        )
        if sketch:
            embed.add_field(name='Description:', value=sketch)

        message = await interaction.channel.send(embed=embed)

        for serial, _ in enumerate(choices):
            interaction._state.loop.create_task(
                message.add_reaction(alphabet[serial]))

        poll_data = {
            'title': question,
            'sketch': sketch,
            'user_id': interaction.user.id,
            'options': choices,
        }
        polls[message.id] = poll_data

        await gdb.set('polls', polls)
