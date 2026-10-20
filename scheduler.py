import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from aiogram import Bot
from database import Database
from sheets_service import SheetsService
import config
import logging

logger = logging.getLogger(__name__)

class ScheduleMonitor:
    def __init__(self, bot: Bot, db: Database, sheets: SheetsService):
        self.bot = bot
        self.db = db
        self.sheets = sheets
        self.scheduler = AsyncIOScheduler()

    async def check_schedule_changes(self):
        """Проверить изменения в расписании для всех классов"""
        try:
            # Получаем все классы с подписчиками
            classes = await self.db.get_all_classes()

            for class_name in classes:
                # Вычисляем текущий хэш расписания
                current_hash = self.sheets.calculate_schedule_hash(class_name)

                # Получаем сохраненный хэш
                saved_hash = await self.db.get_schedule_hash(class_name)

                # Если хэши не совпадают - расписание изменилось
                if saved_hash and current_hash != saved_hash:
                    logger.info(f"Обнаружены изменения в расписании для класса {class_name}")

                    # Получаем всех пользователей этого класса
                    users = await self.db.get_users_by_class(class_name)

                    # Отправляем уведомления
                    for user_id in users:
                        try:
                            await self.bot.send_message(
                                user_id,
                                f"🔔 <b>Внимание!</b>\n\n"
                                f"Расписание для класса <b>{class_name}</b> изменилось!\n\n"
                                f"Используй /menu чтобы посмотреть актуальное расписание.",
                                parse_mode="HTML"
                            )
                        except Exception as e:
                            logger.error(f"Ошибка отправки уведомления пользователю {user_id}: {e}")

                # Обновляем хэш в базе
                await self.db.update_schedule_hash(class_name, current_hash)

        except Exception as e:
            logger.error(f"Ошибка проверки изменений расписания: {e}")

    def start(self):
        """Запустить мониторинг расписания"""
        # Добавляем задачу на проверку изменений
        self.scheduler.add_job(
            self.check_schedule_changes,
            trigger=IntervalTrigger(minutes=config.CHECK_INTERVAL_MINUTES),
            id='schedule_monitor',
            name='Мониторинг изменений расписания',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info(f"Мониторинг расписания запущен (интервал: {config.CHECK_INTERVAL_MINUTES} мин)")

    def stop(self):
        """Остановить мониторинг"""
        self.scheduler.shutdown()
        logger.info("Мониторинг расписания остановлен")
