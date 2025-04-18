from ..enums.rights import user_rights, bot_rights
from aiogram.utils.deep_linking import create_startgroup_link
from aiogram.filters import CommandStart, CommandObject
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import (
    Message,
    KeyboardButton,
    KeyboardButtonRequestChat,
)
from aiogram import Router

router = Router()


def get_keyboard(request_id: int):
    base_request = dict(
        bot_is_member=True,
        user_administrator_rights=user_rights,
        bot_administrator_rights=bot_rights,
        request_photo=True,
        request_username=True,
        request_title=True,
    )

    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(
            text="Выбрать канал!",
            request_chat=KeyboardButtonRequestChat(
                **base_request,
                request_id=request_id*10+1,
                chat_is_channel=True
            )
        ),
        KeyboardButton(
            text="Выбрать группу!",
            request_chat=KeyboardButtonRequestChat(
                **base_request,
                request_id=request_id*10+2,
                chat_is_channel=False,
            )
        ),
    )

    return builder.as_markup(resize_keyboard=True)


@router.message(CommandStart(deep_link=True, deep_link_encoded=True))
async def start(message: Message, command: CommandObject) -> None:
    url = await create_startgroup_link(message.bot, 'true')

    await message.answer('<b>👋 Добро пожаловать!</b>\n'
                         'Выберите чат с помощью инлайн-кнопок ниже.\n'
                         f'<b>Назначьте бота администратором вручную:</b> <a href="{url}">(нажмите здесь)</a>',
                         reply_markup=get_keyboard(int(command.args)),)


@router.message(CommandStart())
async def start_welcome(message: Message, command: CommandObject) -> None:
    await message.answer("Привет!\n"
                         "Этот бот предназначен для синхронизации <b>Telegram и Discord ботов</b>, обеспечивая обмен сообщениями и получение уведомлений.")
