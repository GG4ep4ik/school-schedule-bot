import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

import config
from database import Database
from scheduler import ScheduleMonitor
from handlers import router

# Выбираем сервис в зависимости от настроек
if config.USE_LOCAL_FILE:
    from local_sheets_service import LocalSheetsService
    sheets = LocalSheetsService(config.LOCAL_SCHEDULE_FILE)
else:
    from sheets_service import SheetsService
    sheets = SheetsService()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Глобальные объекты
db = Database()

async def setup_bot_commands(bot: Bot):
    """Установить команды бота для меню"""
    commands = [
        BotCommand(command="start", description="🚀 Начать работу с ботом"),
        BotCommand(command="menu", description="📱 Главное меню"),
        BotCommand(command="setclass", description="🎓 Выбрать/изменить класс"),
        BotCommand(command="help", description="❓ Справка по командам"),
    ]
    await bot.set_my_commands(commands)

async def on_startup(bot: Bot):
    """Действия при запуске бота"""
    logger.info("Инициализация бота...")

    import os

    # Проверяем источник данных
    if config.USE_LOCAL_FILE:
        logger.info(f"Режим работы: локальный файл ({config.LOCAL_SCHEDULE_FILE})")

        # Проверяем наличие файла расписания
        if not os.path.exists(config.LOCAL_SCHEDULE_FILE):
            logger.error(f"❌ Файл {config.LOCAL_SCHEDULE_FILE} не найден!")
            logger.error(f"Положите файл Excel с расписанием в папку проекта")
            sys.exit(1)
    else:
        logger.info("Режим работы: Google Sheets")

        # Проверяем наличие credentials.json
        if not os.path.exists(config.CREDENTIALS_FILE):
            logger.error(f"Файл {config.CREDENTIALS_FILE} не найден!")
            logger.error("Скачайте credentials.json из Google Cloud Console")
            sys.exit(1)

        # Проверяем SPREADSHEET_ID
        if not config.SPREADSHEET_ID:
            logger.error("SPREADSHEET_ID не указан в .env файле!")
            sys.exit(1)

    # Создаем папку для данных если её нет
    os.makedirs("data", exist_ok=True)

    # Инициализируем базу данных
    await db.init_db()
    logger.info("База данных инициализирована")

    # Проверяем подключение к источнику данных
    try:
        classes = sheets.get_all_classes()
        source = "локального файла" if config.USE_LOCAL_FILE else "Google Sheets"
        logger.info(f"✅ Подключение к {source} успешно. Найдено классов: {len(classes)}")
        logger.info(f"📚 Доступные классы: {', '.join(classes)}")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к источнику данных: {e}")
        sys.exit(1)

    # Устанавливаем команды бота
    await setup_bot_commands(bot)

    logger.info("Бот успешно запущен!")

async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("Остановка бота...")

async def main():
    """Главная функция запуска бота"""
    # Создаем бота
    bot = Bot(
        token=config.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Создаем диспетчер
    dp = Dispatcher()

    # Регистрируем роутер
    dp.include_router(router)

    # Передаем зависимости в хэндлеры через middleware
    @dp.update.outer_middleware()
    async def db_sheets_middleware(handler, event, data):
        data['db'] = db
        data['sheets'] = sheets
        return await handler(event, data)

    # Запускаем мониторинг расписания
    monitor = ScheduleMonitor(bot, db, sheets)
    monitor.start()

    # Выполняем действия при запуске
    await on_startup(bot)

    try:
        # Запускаем polling
        logger.info("Начинаем получение обновлений...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        # Останавливаем мониторинг
        monitor.stop()
        await on_shutdown()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
