import random
import nextcord

from typing import Dict, List, Optional, Tuple
from collections import deque

from bot.resources.ether import Emoji


class TicTacToeButton(nextcord.ui.Button['TicTacToe']):
    def __init__(self, x: int, y: int):
        super().__init__(style=nextcord.ButtonStyle.secondary, label="\u200b", row=y)
        self.x = x
        self.y = y

    def go_comp(self) -> str:
        view: TicTacToe = self.view

        empty_pos = []
        for x in range(3):
            for y in range(3):
                state = view.board[y][x]
                if state in (view.X, view.O):
                    continue
                empty_pos.append((x, y))

        if len(view.motion_board[view.O]) == 3:
            x, y = view.motion_board[view.O][0]
            view.board[y][x] = view.DEFAULT

            but = view.button_board[(x, y)]
            but.style = nextcord.ButtonStyle.secondary
            but.label = "\u200b"
            but.emoji = None
            but.disabled = False

        x, y = random.choice(empty_pos)

        but = view.button_board[(x, y)]
        but.style = nextcord.ButtonStyle.success
        but.emoji = Emoji.tic_tac_o
        but.disabled = True

        view.board[y][x] = view.O
        view.motion_board[view.O].append((x, y))
        view.current_player = view.X

        return "It is now X's turn"

    async def callback(self, interaction: nextcord.Interaction):
        view: TicTacToe = self.view
        state = view.board[self.y][self.x]
        if state in (view.X, view.O):
            return

        if view.current_player == view.X:
            if len(view.motion_board[view.X]) == 3:
                x, y = view.motion_board[view.X][0]
                view.board[y][x] = view.DEFAULT
                but = view.button_board[(x, y)]

                but.style = nextcord.ButtonStyle.secondary
                but.label = "\u200b"
                but.emoji = None
                but.disabled = False

            self.style = nextcord.ButtonStyle.danger
            self.emoji = Emoji.tic_tac_x
            self.disabled = True

            view.board[self.y][self.x] = view.X
            view.motion_board[view.X].append((self.x, self.y))
            view.current_player = view.O

            content = "It is now O's turn"
        else:
            if len(view.motion_board[view.O]) == 3:
                x, y = view.motion_board[view.O][0]
                view.board[y][x] = view.DEFAULT
                but = view.button_board[(x, y)]

                but.style = nextcord.ButtonStyle.secondary
                but.label = "\u200b"
                but.emoji = None
                but.disabled = False

            self.style = nextcord.ButtonStyle.success
            self.emoji = Emoji.tic_tac_o
            self.disabled = True

            view.board[self.y][self.x] = view.O
            view.motion_board[view.O].append((self.x, self.y))
            view.current_player = view.X

            content = "It is now X's turn"

        winner = view.check_board_winner()
        if winner is None and view.o_user is None:
            content = self.go_comp()
            winner = view.check_board_winner()
        if winner is not None:
            if winner == view.X:
                content = "X won!"
            elif winner == view.O:
                content = "O won!"

            for child in view.children:
                child.disabled = True

            view.stop()

        await interaction.response.edit_message(content=content, view=view)


class TicTacToe(nextcord.ui.View):
    children: List[TicTacToeButton]
    button_board: Dict[Tuple[int, int], TicTacToeButton]
    motion_board: Dict[int, Tuple[int, int]]

    DEFAULT = 0
    X = -1
    O = 1

    def __init__(self, x_user: nextcord.Member, o_user: Optional[nextcord.Member] = None):
        self.x_user = x_user
        self.o_user = o_user

        super().__init__()

        self.current_player = self.X
        self.board = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ]
        self.motion_board = {
            self.X: deque(maxlen=3),
            self.O: deque(maxlen=3)
        }
        self.button_board = {}

        for x in range(3):
            for y in range(3):
                button = TicTacToeButton(x, y)
                self.button_board[(x, y)] = button
                self.add_item(button)

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        if (self.current_player == self.X and interaction.user == self.x_user
                or self.current_player == self.O and interaction.user == self.o_user):
            return True
        await interaction.send(f"{Emoji.cross} It's not your turn now!", ephemeral=True)
        return False

    def check_board_winner(self):
        for across in self.board:
            value = sum(across)
            if value == 3:
                return self.O
            if value == -3:
                return self.X

        for line in range(3):
            value = self.board[0][line] + self.board[1][line] + self.board[2][line]
            if value == 3:
                return self.O
            if value == -3:
                return self.X

        diag = self.board[0][2] + self.board[1][1] + self.board[2][0]
        if diag == 3:
            return self.O
        if diag == -3:
            return self.X

        diag = self.board[0][0] + self.board[1][1] + self.board[2][2]
        if diag == 3:
            return self.O
        if diag == -3:
            return self.X

        return None
