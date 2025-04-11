from aiogram import Router
from aiogram.types import (
    Message, ChatAdministratorRights,
    KeyboardButton, KeyboardButtonRequestChat,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.filters import CommandStart, CommandObject
from aiogram.utils.deep_linking import create_startgroup_link

router = Router()

bot_rights = ChatAdministratorRights(
    is_anonymous=False,
    can_manage_chat=True,
    can_delete_messages=False,
    can_manage_video_chats=False,
    can_restrict_members=False,
    can_promote_members=False,
    can_change_info=False,
    can_invite_users=False,
    can_post_stories=False,
    can_edit_stories=False,
    can_delete_stories=False,
    can_pin_messages=False,
    can_manage_topics=False
)

user_rights = ChatAdministratorRights(
    is_anonymous=False,
    can_manage_chat=True,
    can_delete_messages=False,
    can_manage_video_chats=False,
    can_restrict_members=False,
    can_promote_members=True,
    can_change_info=False,
    can_invite_users=False,
    can_post_stories=False,
    can_edit_stories=False,
    can_delete_stories=False,
    can_pin_messages=False,
    can_manage_topics=False
)


@router.message(CommandStart(deep_link=True, deep_link_encoded=True))
async def start(message: Message, command: CommandObject) -> None:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(
        text="Выбрать канал!",
        request_chat=KeyboardButtonRequestChat(
                request_id=int(command.args),
                chat_is_channel=True,
                bot_is_member=True,
                user_administrator_rights=user_rights,
                bot_administrator_rights=bot_rights,
                request_photo=True,
                request_username=True,
                request_title=True,
                )
    ))
    url = await create_startgroup_link(message.bot, 'true')

    await message.answer('Добро пожаловать!\n'
                         'Назначьте бота администратором в нужном канале или группе, '
                         '<b>после чего выберите этот чат с помощью инлайн-кнопок ниже.</b>\n'
                         f'<a href="{url}">Назначить бота администратором! (клик)</a>',
                         reply_markup=builder.as_markup(resize_keyboard=True),)


@router.message(CommandStart())
async def start_welcome(message: Message, command: CommandObject) -> None:
    await message.answer("Привет!\n"
                         "Этот бот предназначен для синхронизации <b>Telegram и Discord ботов</b>, "
                         "обеспечивая обмен сообщениями и получение уведомлений.")
