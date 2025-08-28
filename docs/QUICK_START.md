# 🚀 Быстрый запуск Telegram бота

## 📋 Что у вас есть

✅ **Полностью готовый Telegram бот** с анкетой и Google Sheets интеграцией

## ⚡ Быстрый запуск (5 минут)

### 1. Установите зависимости
```bash
pip install -r requirements.txt
```

### 2. Создайте файл .env
Скопируйте содержимое `env_example.txt` в новый файл `.env` и заполните:

```env
BOT_TOKEN=ваш_токен_бота
PRIVATE_CHANNEL_ID=ваш_id_канала
SHEET_ID=ваш_id_таблицы
GOOGLE_CREDENTIALS_JSON=ваш_json_ключ
```

### 3. Настройте Google Sheets
```bash
python setup_sheets.py
```

### 4. Запустите бота
```bash
python bot.py
```

## 🔧 Как получить необходимые данные

### BOT_TOKEN
1. Найдите [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте полученный токен

### PRIVATE_CHANNEL_ID
1. Создайте приватный канал
2. Добавьте бота как администратора
3. Отправьте сообщение в канал
4. Перейдите: `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates`
5. Найдите `"chat":{"id":-1001234567890}`

### Google Sheets
Следуйте подробной инструкции в `GOOGLE_SHEETS_SETUP.md`

## 📊 Функционал бота

- ✅ Анкета с кнопками (6 вопросов)
- ✅ Множественный выбор для интересов и времени
- ✅ Парсинг UTM-параметров
- ✅ Сохранение в Google Sheets
- ✅ Уведомления в канал
- ✅ Уникальные Lead ID

## 🎯 Команды бота

- `/start` - Начать анкету
- `/restart` - Перезапустить анкету

## 📝 Настройка анкеты

Измените вопросы в файле `bot.py` в переменной `SURVEY_CONFIG`:

```python
SURVEY_CONFIG = {
    "welcome_message": "Ваше приветствие",
    "questions": [
        {
            "id": "age",
            "question": "Ваш вопрос",
            "type": "single",  # или "multi"
            "options": ["Вариант 1", "Вариант 2"]
        }
    ]
}
```

## 🚀 Развертывание на хостинге

1. Создайте аккаунт на [Railway](https://railway.app/) или [Heroku](https://heroku.com/)
2. Подключите GitHub репозиторий
3. Настройте переменные окружения
4. Запустите деплой

## 📞 Поддержка

- 📖 Подробная документация: `README_NEW.md`
- 🔧 Настройка Google Sheets: `GOOGLE_SHEETS_SETUP.md`
- 📋 Логи: `bot.log`

## 🎉 Готово!

Ваш бот готов к работе! Пользователи смогут заполнять анкету, а данные будут автоматически сохраняться в Google Sheets и отправляться в ваш канал.
