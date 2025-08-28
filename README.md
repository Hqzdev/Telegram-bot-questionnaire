# Telegram Bot для сбора лидов

Telegram бот на Python с использованием **aiogram 3.x** для сбора лидов через анкету с интеграцией Google Sheets.

## 🚀 Быстрый старт

1. **Клонируйте репозиторий**
2. **Установите зависимости**: `pip install -r requirements.txt`
3. **Настройте .env файл** (см. раздел "Конфигурация")
4. **Настройте Google Sheets**: `python setup_sheets.py`
5. **Запустите бота**: `python bot.py`

## 📋 Функционал

- ✅ **Анкета с inline-кнопками** (одиночный и множественный выбор)
- ✅ **Парсинг UTM-параметров** из start payload
- ✅ **Сохранение в Google Sheets** с автоматическим форматированием
- ✅ **Уведомления в приватный канал** о новых лидах
- ✅ **Отслеживание времени** начала и завершения анкеты
- ✅ **Уникальные Lead ID** для каждого пользователя
- ✅ **Подробное логирование** всех действий

## ⚙️ Конфигурация

### 1. Создайте файл `.env` в корне проекта:

```env
# Telegram Bot Configuration
BOT_TOKEN=your_telegram_bot_token_here
PRIVATE_CHANNEL_ID=your_private_channel_id_here

# Google Sheets Configuration
SHEET_ID=your_google_sheet_id_here
GOOGLE_CREDENTIALS_JSON=your_google_credentials_json_here

# Optional Settings
LOG_LEVEL=INFO
LOG_FILE=bot.log
```

### 2. Получение BOT_TOKEN

1. Найдите [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте полученный токен в `BOT_TOKEN`

### 3. Получение PRIVATE_CHANNEL_ID

1. Создайте приватный канал в Telegram
2. Добавьте вашего бота в канал как администратора
3. Отправьте любое сообщение в канал
4. Перейдите по ссылке: `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates`
5. Найдите `"chat":{"id":-1001234567890}` - это и есть ваш `PRIVATE_CHANNEL_ID`

### 4. Настройка Google Sheets

#### Шаг 1: Создание Google Cloud Project

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Включите **Google Sheets API** в разделе "APIs & Services" > "Library"

#### Шаг 2: Создание Service Account

1. Перейдите в "APIs & Services" > "Credentials"
2. Нажмите "Create Credentials" > "Service Account"
3. Заполните форму:
   - **Name**: `telegram-bot-sheets`
   - **Description**: `Service account for Telegram bot Google Sheets integration`
4. Нажмите "Create and Continue"
5. Пропустите шаги 2 и 3, нажмите "Done"

#### Шаг 3: Создание ключа

1. Найдите созданный service account в списке
2. Нажмите на email service account
3. Перейдите на вкладку "Keys"
4. Нажмите "Add Key" > "Create new key"
5. Выберите "JSON" и нажмите "Create"
6. Файл автоматически скачается

#### Шаг 4: Настройка Google Sheets

1. Создайте новую Google таблицу
2. Скопируйте ID таблицы из URL: `https://docs.google.com/spreadsheets/d/`**`1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms`**`/edit`
3. Добавьте email service account как редактора таблицы
4. Скопируйте содержимое скачанного JSON файла в переменную `GOOGLE_CREDENTIALS_JSON`

## 📊 Структура данных в Google Sheets

После настройки таблица будет содержать следующие колонки:

| Колонка | Описание |
|---------|----------|
| Lead ID | Уникальный идентификатор лида |
| User ID | ID пользователя в Telegram |
| Username | Username пользователя |
| TG Start | Время начала анкеты |
| TG Complete | Время завершения анкеты |
| Возраст | Ответ на вопрос о возрасте |
| Интересы | Выбранные интересы |
| Бюджет | Бюджет на обучение |
| Опыт | Опыт в выбранной области |
| Способ связи | Предпочитаемый способ связи |
| Время | Удобное время для занятий |
| UTM Source | Источник трафика |
| UTM Medium | Канал трафика |
| UTM Campaign | Название кампании |
| UTM Term | Ключевые слова |
| UTM Content | Контент |

## 🔧 Настройка анкеты

Анкета настраивается в файле `bot.py` в переменной `SURVEY_CONFIG`. Вы можете легко изменить:

### Структура вопроса:

```python
{
    "id": "unique_question_id",
    "question": "Текст вопроса",
    "type": "single",  # "single" или "multi"
    "options": [
        "Вариант 1",
        "Вариант 2",
        "Вариант 3"
    ]
}
```

### Типы вопросов:

- **`single`** - Одиночный выбор (одна кнопка)
- **`multi`** - Множественный выбор (несколько кнопок + кнопка "Далее")

### Примеры вопросов:

#### Одиночный выбор:
```python
{
    "id": "age",
    "question": "Выберите ваш возраст:",
    "type": "single",
    "options": ["18-25 лет", "26-35 лет", "36-45 лет", "46+ лет"]
}
```

#### Множественный выбор:
```python
{
    "id": "interests",
    "question": "Какие направления вас интересуют?",
    "type": "multi",
    "options": ["Программирование", "Дизайн", "Маркетинг", "Продажи"]
}
```

## 🔗 UTM-параметры

Бот автоматически парсит UTM-параметры из start payload. Поддерживаются форматы:

### Base64 JSON:
```
https://t.me/your_bot?start=eyJ1dG1fc291cmNlIjoiZ29vZ2xlIiwidXRtX21lZGl1bSI6ImNwYyJ9
```

### URL-encoded:
```
https://t.me/your_bot?start=utm_source%3Dgoogle%26utm_medium%3Dcpc
```

## 🚀 Развертывание

### Локальный запуск:
```bash
python bot.py
```

### На хостинге (Railway, Heroku, DigitalOcean):

1. **Создайте файл `Procfile`:**
```
worker: python bot.py
```

2. **Создайте файл `runtime.txt`:**
```
python-3.9.18
```

3. **Настройте переменные окружения** на хостинге
4. **Запустите деплой**

## 📝 Команды бота

- `/start` - Начать анкету (с поддержкой UTM-параметров)
- `/restart` - Перезапустить анкету

## 🔍 Логирование

Бот ведет подробные логи в файл `bot.log`:

- Все действия пользователей
- Ошибки Google Sheets API
- UTM-параметры
- Время выполнения операций

## 🛠️ Устранение неполадок

### Ошибка "Google Sheets отключен"
- Проверьте правильность `GOOGLE_CREDENTIALS_JSON`
- Убедитесь, что service account добавлен как редактор таблицы
- Проверьте, что Google Sheets API включен

### Ошибка "PRIVATE_CHANNEL_ID не найден"
- Убедитесь, что бот добавлен в канал как администратор
- Проверьте правильность ID канала (должен начинаться с `-100`)

### Ошибка "BOT_TOKEN недействителен"
- Проверьте правильность токена бота
- Убедитесь, что бот не заблокирован

## 📁 Структура проекта

```
telegram-bot/
├── bot.py                 # Основной файл бота
├── config.py              # Конфигурация
├── google_sheets_manager.py # Менеджер Google Sheets
├── setup_sheets.py        # Скрипт настройки Google Sheets
├── requirements.txt       # Зависимости Python
├── .env                   # Переменные окружения (создать)
├── env_example.txt        # Пример .env файла
├── bot.log               # Логи (создается автоматически)
└── README_NEW.md         # Документация
```

## 🤝 Поддержка

При возникновении проблем:

1. Проверьте логи в файле `bot.log`
2. Убедитесь, что все переменные окружения настроены правильно
3. Проверьте права доступа service account к Google Sheets

## 📄 Лицензия

MIT License - используйте свободно для своих проектов!
