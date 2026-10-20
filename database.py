import aiosqlite
from typing import Optional
import config

class Database:
    def __init__(self, db_path: str = config.DATABASE_PATH):
        self.db_path = db_path

    async def init_db(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    class_name TEXT NOT NULL,
                    notifications_enabled INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS schedule_cache (
                    class_name TEXT PRIMARY KEY,
                    data_hash TEXT NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await db.commit()

    async def set_user_class(self, user_id: int, class_name: str):
        """Сохранить класс пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO users (user_id, class_name)
                VALUES (?, ?)
                ON CONFLICT(user_id)
                DO UPDATE SET class_name = ?
            """, (user_id, class_name, class_name))
            await db.commit()

    async def get_user_class(self, user_id: int) -> Optional[str]:
        """Получить класс пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT class_name FROM users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def set_notifications(self, user_id: int, enabled: bool):
        """Включить/выключить уведомления"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users
                SET notifications_enabled = ?
                WHERE user_id = ?
            """, (1 if enabled else 0, user_id))
            await db.commit()

    async def get_users_by_class(self, class_name: str) -> list[int]:
        """Получить всех пользователей определенного класса с включенными уведомлениями"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT user_id FROM users
                WHERE class_name = ? AND notifications_enabled = 1
            """, (class_name,)) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    async def update_schedule_hash(self, class_name: str, data_hash: str):
        """Обновить хэш расписания для класса"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO schedule_cache (class_name, data_hash)
                VALUES (?, ?)
                ON CONFLICT(class_name)
                DO UPDATE SET data_hash = ?, last_updated = CURRENT_TIMESTAMP
            """, (class_name, data_hash, data_hash))
            await db.commit()

    async def get_schedule_hash(self, class_name: str) -> Optional[str]:
        """Получить сохраненный хэш расписания"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT data_hash FROM schedule_cache WHERE class_name = ?",
                (class_name,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def get_all_classes(self) -> list[str]:
        """Получить список всех классов с подписчиками"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT DISTINCT class_name FROM users WHERE notifications_enabled = 1"
            ) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
