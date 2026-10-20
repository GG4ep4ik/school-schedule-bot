# 📦 Деплой бота на BotHost

Эта папка содержит все необходимое для размещения вашего бота на хостинге.

## 📁 Структура папки

```
deploy_bothost/
├── bot.py                    # Главный файл бота
├── config.py                 # Конфигурация
├── database.py               # Работа с базой данных
├── scheduler.py              # Мониторинг изменений
├── sheets_service.py         # Работа с Google Sheets
├── local_sheets_service.py   # Работа с локальным Excel
├── handlers/                 # Обработчики команд
│   ├── __init__.py
│   └── common.py
├── data/                     # База данных (создается автоматически)
├── requirements.txt          # Зависимости Python
├── .env.example              # Пример настроек
├── Procfile                  # Команда запуска для хостинга
├── runtime.txt               # Версия Python
└── .gitignore                # Игнорируемые файлы
```

## 🚀 Что нужно для деплоя

1. **Токен бота** от @BotFather
2. **Google Sheets API** (credentials.json) - если используете Google Таблицы
3. **ID таблицы** - если используете Google Таблицы
4. Или **Excel файл** - если используете локальное расписание

## 📋 Следуйте инструкции

Откройте файл **DEPLOY_INSTRUCTION.md** для подробной пошаговой инструкции.
