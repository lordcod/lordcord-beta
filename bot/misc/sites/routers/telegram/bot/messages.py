
from aiogram import F, Router
from aiogram.types import Message

router = Router()


@router.channel_post()
async def channel_message(message: Message, dispatch):
    dispatch('tg_post', message)


@router.message()
async def group_message(message: Message, dispatch):
    if message.chat.type == 'private':
        return
    dispatch('tg_post', message)
