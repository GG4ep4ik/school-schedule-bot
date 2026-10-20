import gspread
from google.oauth2.service_account import Credentials
from typing import Dict, List, Optional
import hashlib
import json
import re
import config

class SheetsService:
    def __init__(self):
        self.client = None
        self.spreadsheet = None
        self._init_client()

    def _init_client(self):
        """Инициализация клиента Google Sheets"""
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets.readonly',
                'https://www.googleapis.com/auth/drive.readonly'
            ]

            creds = Credentials.from_service_account_file(
                config.CREDENTIALS_FILE,
                scopes=scopes
            )

            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open_by_key(config.SPREADSHEET_ID)
            print(f"✅ Подключение к Google Sheets успешно")
        except Exception as e:
            print(f"❌ Ошибка инициализации Google Sheets: {e}")
            raise

    def reload(self):
        """Перезагрузить данные из таблицы"""
        # Для Google Sheets не требуется явная перезагрузка - данные всегда актуальные
        pass

    def get_all_classes(self) -> List[str]:
        """Получить список всех доступных классов из первой строки"""
        try:
            worksheet = self.spreadsheet.worksheet(config.SHEET_NAME)
            # Классы указаны в первой строке, начиная с третьего столбца (индекс 2)
            first_row = worksheet.row_values(1)

            classes = []
            # Пропускаем первые два столбца (№ и Время)
            for cell_value in first_row[2:]:
                if cell_value and isinstance(cell_value, str):
                    class_name = cell_value.strip()
                    if class_name:
                        classes.append(class_name)

            return classes
        except Exception as e:
            print(f"Ошибка получения списка классов: {e}")
            return []

    def _extract_day_from_cell(self, cell_value) -> Optional[str]:
        """Извлечь название дня недели из ячейки с эмодзи"""
        if not cell_value or not isinstance(cell_value, str):
            return None

        # Удаляем эмодзи и лишние пробелы
        day_mapping = {
            "ПОНЕДЕЛЬНИК": "Понедельник",
            "ВТОРНИК": "Вторник",
            "СРЕДА": "Среда",
            "ЧЕТВЕРГ": "Четверг",
            "ПЯТНИЦА": "Пятница",
            "СУББОТА": "Суббота"
        }

        for key, value in day_mapping.items():
            if key in cell_value.upper():
                return value

        return None

    def _parse_lesson(self, cell_value) -> Dict[str, str]:
        """
        Парсит ячейку с уроком в формате "201 МАТ" или "с/з ФИЗ"
        Возвращает словарь с предметом и кабинетом
        """
        if not cell_value or not isinstance(cell_value, str):
            return {"subject": "", "room": ""}

        cell_value = cell_value.strip()

        # Словарь для расшифровки сокращений
        subjects_map = {
            "МАТ": "Математика",
            "ГЕОМЕ": "Геометрия",
            "АЛГ": "Алгебра",
            "РУС": "Русский язык",
            "ЛИТ": "Литература",
            "АНГЛ": "Английский язык",
            "ФИЗ": "Физкультура",
            "ИНФ": "Информатика",
            "ИСТ": "История",
            "ОБЩ": "Обществознание",
            "ГЕОГР": "География",
            "БИО": "Биология",
            "ХИМ": "Химия",
        }

        # Проверяем формат "с/з" (спортзал)
        if cell_value.startswith("с/з"):
            subject_abbr = cell_value.replace("с/з", "").strip()
            subject = subjects_map.get(subject_abbr, subject_abbr)
            return {"subject": subject, "room": "Спортзал"}

        # Парсим формат "201 МАТ"
        parts = cell_value.split(maxsplit=1)

        if len(parts) == 2:
            room, subject_abbr = parts
            subject = subjects_map.get(subject_abbr, subject_abbr)
            return {"subject": subject, "room": room}
        elif len(parts) == 1:
            # Только предмет без кабинета
            subject = subjects_map.get(parts[0], parts[0])
            return {"subject": subject, "room": ""}

        return {"subject": cell_value, "room": ""}

    def get_schedule_for_day(self, class_name: str, day: str) -> Optional[Dict]:
        """
        Получить расписание для конкретного класса и дня недели

        Возвращает словарь вида:
        {
            'day': 'Понедельник',
            'class': '10 «А»',
            'lessons': [
                {'number': 1, 'time': '08:00 - 08:45', 'subject': 'Математика', 'room': '201'},
                ...
            ]
        }
        """
        try:
            worksheet = self.spreadsheet.worksheet(config.SHEET_NAME)
            all_data = worksheet.get_all_values()

            if len(all_data) < 2:
                return None

            # Находим столбец с нужным классом (первая строка)
            first_row = all_data[0]

            class_col_index = None
            for idx, cell_value in enumerate(first_row):
                if cell_value and cell_value.strip() == class_name:
                    class_col_index = idx
                    break

            if class_col_index is None:
                print(f"❌ Класс {class_name} не найден в таблице")
                return None

            # Ищем строки с расписанием для нужного дня
            lessons = []
            current_day = None
            inside_target_day = False

            for row_idx in range(1, len(all_data)):  # Начинаем со второй строки
                row = all_data[row_idx]

                if len(row) == 0:
                    continue

                first_cell = row[0] if len(row) > 0 else ""

                # Проверяем, не начался ли новый день
                extracted_day = self._extract_day_from_cell(first_cell)

                if extracted_day:
                    current_day = extracted_day
                    inside_target_day = (current_day == day)
                    continue

                # Если мы внутри нужного дня и это строка с уроком
                if inside_target_day and current_day == day:
                    try:
                        lesson_number = row[0] if len(row) > 0 else ""
                        lesson_time = row[1] if len(row) > 1 else ""
                        lesson_cell = row[class_col_index] if class_col_index < len(row) else ""

                        # Проверяем, что это действительно урок (номер - число)
                        if lesson_number and lesson_number.replace('.', '').isdigit():
                            lesson_number = int(float(lesson_number))

                            parsed = self._parse_lesson(lesson_cell)

                            if parsed["subject"]:
                                lessons.append({
                                    'number': lesson_number,
                                    'time': lesson_time.strip() if lesson_time else "",
                                    'subject': parsed['subject'],
                                    'room': parsed['room']
                                })
                    except (ValueError, IndexError) as e:
                        continue

                # Если закончился наш день (встретили следующий день)
                if current_day and current_day != day and extracted_day:
                    break

            if not lessons:
                return None

            return {
                'day': day,
                'class': class_name,
                'lessons': lessons
            }

        except Exception as e:
            print(f"Ошибка получения расписания для {class_name} на {day}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_full_schedule(self, class_name: str) -> Dict[str, Dict]:
        """Получить расписание на всю неделю для класса"""
        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
        week_schedule = {}

        for day in days:
            schedule = self.get_schedule_for_day(class_name, day)
            if schedule:
                week_schedule[day] = schedule

        return week_schedule

    def calculate_schedule_hash(self, class_name: str) -> str:
        """Вычислить хэш расписания для отслеживания изменений"""
        schedule = self.get_full_schedule(class_name)
        schedule_str = json.dumps(schedule, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(schedule_str.encode()).hexdigest()

    def format_schedule_message(self, schedule_data: Dict) -> str:
        """Форматировать расписание в красивое текстовое сообщение"""
        if not schedule_data or not schedule_data.get('lessons'):
            return "📅 На этот день расписания нет"

        day = schedule_data['day']
        class_name = schedule_data['class']
        lessons = schedule_data['lessons']

        # Эмодзи для дней недели
        day_emoji = {
            "Понедельник": "🟦",
            "Вторник": "🟩",
            "Среда": "🟨",
            "Четверг": "🟧",
            "Пятница": "🟪",
            "Суббота": "🟫"
        }

        emoji = day_emoji.get(day, "📅")

        message = f"📚 <b>Расписание для {class_name}</b>\n"
        message += f"{emoji} <b>{day}</b>\n\n"

        for lesson in lessons:
            number = lesson['number']
            time = lesson['time']
            subject = lesson['subject']
            room = lesson['room']

            message += f"<b>{number}.</b> {subject}\n"

            if room:
                if room == "Спортзал":
                    message += f"    🏃 {room}\n"
                else:
                    message += f"    🚪 каб. {room}\n"

            if time:
                message += f"    ⏰ {time}\n"

            message += "\n"

        return message.strip()
