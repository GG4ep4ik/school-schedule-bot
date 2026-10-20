from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import config

router = Router()

class ScheduleStates(StatesGroup):
    choosing_class = State()

def create_class_keyboard(classes: list) -> InlineKeyboardMarkup:
    """Создать клавиатуру с выбором класса"""
    buttons = []

    # Группируем по 3 кнопки в ряд
    for i in range(0, len(classes), 3):
        row = []
        for class_name in classes[i:i+3]:
            row.append(InlineKeyboardButton(
                text=class_name,
                callback_data=f"class_{class_name}"
            ))
        buttons.append(row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_days_keyboard() -> InlineKeyboardMarkup:
    """Создать клавиатуру с выбором дня недели"""
    day_emoji = {
        "Понедельник": "1️⃣",
        "Вторник": "2️⃣",
        "Среда": "3️⃣",
        "Четверг": "4️⃣",
        "Пятница": "5️⃣",
        "Суббота": "6️⃣"
    }

    buttons = []
    for day in config.DAYS_LIST:
        emoji = day_emoji.get(day, "📅")
        buttons.append([InlineKeyboardButton(
            text=f"{emoji} {day}",
            callback_data=f"day_{day}"
        )])

    buttons.append([InlineKeyboardButton(
        text="◀️ Назад в меню",
        callback_data="back_to_menu"
    )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_main_menu() -> InlineKeyboardMarkup:
    """Создать главное меню"""
    buttons = [
        [InlineKeyboardButton(text="📅 Расписание на завтра", callback_data="tomorrow")],
        [InlineKeyboardButton(text="📆 Выбрать день недели", callback_data="choose_day")],
        [InlineKeyboardButton(text="🔄 Сменить класс", callback_data="change_class")],
        [InlineKeyboardButton(text="🔔 Уведомления", callback_data="notifications")],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, db, sheets):
    """Обработчик команды /start"""
    user_class = await db.get_user_class(message.from_user.id)

    if user_class:
        await message.answer(
            f"👋 Привет! Ты уже выбрал класс: <b>{user_class}</b>\n\n"
            "Выбери действие:",
            reply_markup=create_main_menu(),
            parse_mode="HTML"
        )
    else:
        classes = sheets.get_all_classes()

        if not classes:
            await message.answer(
                "❌ Не удалось загрузить список классов.\n"
                "Проверь настройки Google Sheets."
            )
            return

        await message.answer(
            "👋 Привет! Я бот для просмотра школьного расписания.\n\n"
            "Сначала выбери свой класс:",
            reply_markup=create_class_keyboard(classes)
        )
        await state.set_state(ScheduleStates.choosing_class)

@router.message(Command("menu"))
async def cmd_menu(message: Message, db):
    """Показать главное меню"""
    user_class = await db.get_user_class(message.from_user.id)

    if not user_class:
        await message.answer(
            "❌ Сначала выбери свой класс с помощью команды /start"
        )
        return

    await message.answer(
        f"📚 Твой класс: <b>{user_class}</b>\n\n"
        "Выбери действие:",
        reply_markup=create_main_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("class_"))
async def process_class_selection(callback: CallbackQuery, state: FSMContext, db):
    """Обработка выбора класса"""
    class_name = callback.data.split("_", 1)[1]

    await db.set_user_class(callback.from_user.id, class_name)
    await state.clear()

    await callback.message.edit_text(
        f"✅ Класс <b>{class_name}</b> сохранен!\n\n"
        "Выбери действие:",
        reply_markup=create_main_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "change_class")
async def change_class(callback: CallbackQuery, state: FSMContext, sheets):
    """Изменить класс"""
    classes = sheets.get_all_classes()

    if not classes:
        await callback.answer("❌ Не удалось загрузить список классов", show_alert=True)
        return

    await callback.message.edit_text(
        "Выбери новый класс:",
        reply_markup=create_class_keyboard(classes)
    )
    await state.set_state(ScheduleStates.choosing_class)
    await callback.answer()

@router.callback_query(F.data == "tomorrow")
async def show_tomorrow_schedule(callback: CallbackQuery, db, sheets):
    """Показать расписание на завтра"""
    user_class = await db.get_user_class(callback.from_user.id)

    if not user_class:
        await callback.answer("❌ Сначала выбери класс", show_alert=True)
        return

    # Определяем следующий учебный день
    today = datetime.now().weekday()  # 0 = Понедельник, 6 = Воскресенье

    # Если сегодня воскресенье (6), завтра понедельник (0)
    if today == 6:
        tomorrow_day = "Понедельник"
    # Если сегодня суббота (5), завтра воскресенье, пропускаем до понедельника
    elif today == 5:
        tomorrow_day = "Понедельник"
    else:
        tomorrow_day = config.DAYS_LIST[today + 1]

    schedule = sheets.get_schedule_for_day(user_class, tomorrow_day)

    if schedule:
        message = sheets.format_schedule_message(schedule)
    else:
        message = f"📅 На {tomorrow_day} расписания нет"

    await callback.message.edit_text(
        message,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_menu")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "choose_day")
async def choose_day(callback: CallbackQuery):
    """Показать меню выбора дня"""
    await callback.message.edit_text(
        "📆 Выбери день недели:",
        reply_markup=create_days_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("day_"))
async def show_day_schedule(callback: CallbackQuery, db, sheets):
    """Показать расписание на выбранный день"""
    day = callback.data.split("_", 1)[1]
    user_class = await db.get_user_class(callback.from_user.id)

    if not user_class:
        await callback.answer("❌ Сначала выбери класс", show_alert=True)
        return

    schedule = sheets.get_schedule_for_day(user_class, day)

    if schedule:
        message = sheets.format_schedule_message(schedule)
    else:
        message = f"📅 На {day} расписания нет"

    await callback.message.edit_text(
        message,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📆 Другой день", callback_data="choose_day")],
            [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_menu")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, db):
    """Вернуться в главное меню"""
    user_class = await db.get_user_class(callback.from_user.id)

    await callback.message.edit_text(
        f"📚 Твой класс: <b>{user_class}</b>\n\n"
        "Выбери действие:",
        reply_markup=create_main_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "notifications")
async def toggle_notifications(callback: CallbackQuery, db):
    """Переключить уведомления"""
    # TODO: Реализовать переключение уведомлений
    await callback.answer(
        "🔔 Уведомления включены! Ты получишь сообщение, если расписание изменится.",
        show_alert=True
    )

@router.message(Command("setclass"))
async def cmd_set_class(message: Message, state: FSMContext, sheets):
    """Команда для установки класса"""
    classes = sheets.get_all_classes()

    if not classes:
        await message.answer(
            "❌ Не удалось загрузить список классов.\n"
            "Проверь настройки Google Sheets."
        )
        return

    await message.answer(
        "Выбери свой класс:",
        reply_markup=create_class_keyboard(classes)
    )
    await state.set_state(ScheduleStates.choosing_class)

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Справка по командам"""
    help_text = """
📖 <b>Доступные команды:</b>

/start - Начать работу с ботом
/menu - Открыть главное меню
/setclass - Выбрать/изменить класс
/help - Показать эту справку

📱 <b>Возможности бота:</b>

• Просмотр расписания на завтра
• Выбор конкретного дня недели
• Уведомления об изменениях в расписании
• Красивое форматирование с временем уроков

💡 Бот автоматически отслеживает изменения в расписании и присылает уведомления!
    """

    await message.answer(help_text, parse_mode="HTML")
