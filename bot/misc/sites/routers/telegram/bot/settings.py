from aiogram import F, Router
from aiogram.types import (
    Message, ReplyKeyboardRemove,
    ChatMemberAdministrator, ChatMemberMember, ChatMemberOwner,
    InlineKeyboardButton, CallbackQuery
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

response = "<b>Канал успешно подключён. Вы можете вернуться к настройке в Discord!</b>"


def get_keyboard(chat_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text='Завершить',
        callback_data=f'end:{chat_id}'
    ))
    return builder.as_markup()


@router.callback_query(F.data.startswith("end:"))
async def on_inline(query: CallbackQuery, storage: dict, dispatch):
    chat_id = int(query.data.removeprefix("end:"))
    if chat_id not in storage:
        return
    chat_shared, categories, _ = storage.pop(chat_id)

    await query.message.answer(response,
                               reply_markup=ReplyKeyboardRemove())
    await query.answer()

    dispatch('tg_channel_joined',
             chat_shared.request_id//10,
             chat_shared,
             categories)


@router.message(F.chat_shared)
async def on_chat_shared(message: Message, storage: dict, dispatch):
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

    chat = await message.bot.get_chat(message.chat_shared.chat_id)
    if not chat.is_forum:
        await message.answer(response,
                             reply_markup=ReplyKeyboardRemove())
        dispatch('tg_channel_joined',
                 message.chat_shared.request_id//10,
                 message.chat_shared,
                 None)
    else:
        storage[chat.id] = (message.chat_shared, [], message.from_user)
        await message.answer(
            ("<b>🔔 Настройка уведомлений</b>\n\n"
             "📩 Вы можете получать уведомления только от тех категорий форума, которые вам интересны.\n"
             "👉 Чтобы включить уведомления по нужной категории — перейдите в неё и отправьте команду: <code>/active</code>\n"
             "✅ Когда закончите выбор или хотите включить уведомления сразу по всем категориям — нажмите кнопку <b>Завершить</b> ниже."),
            reply_markup=get_keyboard(
                chat.id)
        )
