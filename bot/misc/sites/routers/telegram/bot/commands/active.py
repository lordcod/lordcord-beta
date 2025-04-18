import contextlib
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandObject


router = Router()


@router.message(Command('active'))
async def on_active(message: Message, command: CommandObject, storage: dict):
    if not message.chat.is_forum:
        return
    if message.chat.id not in storage:
        return

    _, categories, user_chat = storage[message.chat.id]
    if user_chat.id != message.from_user.id:
        return

    try:
        topic = message.reply_to_message.forum_topic_created
    except AttributeError:
        topic = None
    categories.append(topic.name if topic else None)

    name = 'General' if topic is None else topic.name

    with contextlib.suppress(Exception):
        await message.delete()
    await message.bot.send_message(user_chat.id,
                                   f"✅ <b>Категория «{name}» добавлена</b>\n\n"
                                   "ℹ️ Учтите: если название категории будет изменено, её нужно будет добавить заново!")
