import nextcord


class Menus(nextcord.ui.View):
    def __init__(self, value: list, timeout: float | None = None):
        super().__init__(timeout=timeout)
        self.len = len(value)
        self.index = 0
        self.value = value
        self.handler_disable()

    def custom_emoji(self, **kwargs):
        for key, value in kwargs.items():
            atr = getattr(self, f'button_{key}')
            setattr(atr, 'emoji', value)

    def handler_disable(self):
        if self.index > 0:
            self.button_previous.disabled = False
            self.button_backward.disabled = False

        if self.index <= 0:
            self.button_previous.disabled = True
            self.button_backward.disabled = True

        if self.index < self.len-1:
            self.button_forward.disabled = False
            self.button_next.disabled = False

        if self.index >= self.len-1:
            self.button_forward.disabled = True
            self.button_next.disabled = True

    async def callback(self,
                       button: nextcord.ui.Button,
                       interaction: nextcord.Interaction):
        pass

    async def previous(self,
                       button: nextcord.ui.Button,
                       interaction: nextcord.Interaction):
        pass

    async def backward(self,
                       button: nextcord.ui.Button,
                       interaction: nextcord.Interaction):
        pass

    async def forward(self,
                      button: nextcord.ui.Button,
                      interaction: nextcord.Interaction):
        pass

    async def next(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        pass

    def add_element(self, val):
        self.value.append(val)
        self.len += 1

    def renove_element(self, val):
        self.value.remove(val)
        self.len -= 1

    @nextcord.ui.button(emoji='⏮', style=nextcord.ButtonStyle.grey, disabled=True)
    async def button_previous(self,
                              button: nextcord.ui.Button, interaction:
                                  nextcord.Interaction):
        self.index = 0
        self.handler_disable()
        await self.previous(button, interaction)
        await self.callback(button, interaction)

    @nextcord.ui.button(emoji='◀️', style=nextcord.ButtonStyle.grey, disabled=True)
    async def button_backward(self,
                              button: nextcord.ui.Button,
                              interaction: nextcord.Interaction):
        self.index -= 1
        self.handler_disable()
        await self.backward(button, interaction)
        await self.callback(button, interaction)

    @nextcord.ui.button(emoji='▶', style=nextcord.ButtonStyle.grey)
    async def button_forward(self,
                             button: nextcord.ui.Button,
                             interaction: nextcord.Interaction):
        self.index += 1
        self.handler_disable()
        await self.forward(button, interaction)
        await self.callback(button, interaction)

    @nextcord.ui.button(emoji='⏭', style=nextcord.ButtonStyle.grey)
    async def button_next(self,
                          button: nextcord.ui.Button,
                          interaction: nextcord.Interaction):
        self.index = self.len-1
        await self.handler_disable()
        await self.next(button, interaction)
        await self.callback(button, interaction)
