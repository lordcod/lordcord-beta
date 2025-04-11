from aiogram import F, Router
from aiogram.types import (
    Message, ReplyKeyboardRemove,
    ChatMemberAdministrator, ChatMemberMember, ChatMemberOwner
)

router = Router()


@router.channel_post()
async def channel_message(message: Message, dispatch):
    dispatch('tg_post', message)


@router.message(F.chat_shared)
async def on_chat_shared(message: Message, dispatch):
    try:
        me = await message.bot.me()
        status = await message.bot.get_chat_member(message.chat_shared.chat_id,
                                                   me.id)
    except Exception:
        status = False
    else:
        status = isinstance(
            status, (ChatMemberMember, ChatMemberAdministrator))

    if not status:
        await message.answer("Бот отсутствует в этом канале.")
        return

    status = await message.bot.get_chat_member(message.chat_shared.chat_id, message.from_user.id)

    if not isinstance(status, (ChatMemberAdministrator, ChatMemberOwner)):
        await message.answer("У вас нет прав администратора в этом канале.")
        return

    await message.answer("<b>→ Канал успешно подключён — можно продолжить настройку!</b>",
                         reply_markup=ReplyKeyboardRemove())

    dispatch('tg_channel_joined',
             message.chat_shared.request_id, message.chat_shared)
