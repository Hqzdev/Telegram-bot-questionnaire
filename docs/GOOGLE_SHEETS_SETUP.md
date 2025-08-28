# Настройка Google Sheets для Telegram бота

Пошаговая инструкция по настройке Google Sheets API для работы с ботом.

## 📋 Что нужно сделать

1. Создать Google Cloud Project
2. Включить Google Sheets API
3. Создать Service Account
4. Скачать ключ доступа
5. Настроить Google таблицу
6. Добавить учетные данные в бота

## 🚀 Пошаговая инструкция

### Шаг 1: Создание Google Cloud Project

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Нажмите на выпадающий список проектов вверху страницы
3. Нажмите "New Project"
4. Введите название проекта (например: `telegram-bot-sheets`)
5. Нажмите "Create"

### Шаг 2: Включение Google Sheets API

1. В меню слева выберите "APIs & Services" > "Library"
2. Найдите "Google Sheets API" в поиске
3. Нажмите на "Google Sheets API"
4. Нажмите "Enable"

### Шаг 3: Создание Service Account

1. В меню слева выберите "APIs & Services" > "Credentials"
2. Нажмите "Create Credentials" > "Service Account"
3. Заполните форму:
   - **Service account name**: `telegram-bot-sheets`
   - **Service account ID**: заполнится автоматически
   - **Description**: `Service account for Telegram bot Google Sheets integration`
4. Нажмите "Create and Continue"
5. На шаге "Grant this service account access to project":
   - Выберите роль "Editor" (или "Viewer" если нужен только доступ на чтение)
   - Нажмите "Continue"
6. На шаге "Grant users access to this service account":
   - Оставьте пустым
   - Нажмите "Done"

### Шаг 4: Создание ключа доступа

1. В списке Service Accounts найдите созданный аккаунт
2. Нажмите на email service account (например: `telegram-bot-sheets@project-id.iam.gserviceaccount.com`)
3. Перейдите на вкладку "Keys"
4. Нажмите "Add Key" > "Create new key"
5. Выберите "JSON"
6. Нажмите "Create"
7. Файл автоматически скачается на ваш компьютер

### Шаг 5: Настройка Google таблицы

1. Перейдите в [Google Sheets](https://sheets.google.com/)
2. Создайте новую таблицу или откройте существующую
3. Скопируйте ID таблицы из URL:
   ```
   https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit
   ```
   ID: `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms`
4. Нажмите "Share" (кнопка "Настройки доступа") в правом верхнем углу
5. В поле "Добавить пользователей и группы" введите email service account
6. Выберите роль "Editor"
7. Снимите галочку "Уведомить пользователей"
8. Нажмите "Готово"

### Шаг 6: Настройка бота

1. Откройте скачанный JSON файл в текстовом редакторе
2. Скопируйте все содержимое файла
3. В файле `.env` добавьте переменную:
   ```env
   GOOGLE_CREDENTIALS_JSON={"type":"service_account","project_id":"...","private_key_id":"...",...}
   ```
4. Также добавьте ID таблицы:
   ```env
   SHEET_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
   ```

### Шаг 7: Инициализация таблицы

1. Запустите скрипт настройки:
   ```bash
   python setup_sheets.py
   ```
2. Если все настроено правильно, вы увидите:
   ```
   ✅ Google Sheets успешно настроена!
   📊 Таблица: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
   📝 Заголовки добавлены и отформатированы
   ```

## 🔧 Альтернативный способ (через файл)

Если вы предпочитаете использовать файл вместо переменной окружения:

1. Переименуйте скачанный JSON файл в `service-account-key.json`
2. Поместите файл в корень проекта
3. В файле `.env` оставьте `GOOGLE_CREDENTIALS_JSON` пустым или удалите эту строку

## 🛠️ Устранение неполадок

### Ошибка "Google Sheets отключен"

**Причина**: Неправильные учетные данные или отсутствие доступа.

**Решение**:
1. Проверьте правильность JSON в `GOOGLE_CREDENTIALS_JSON`
2. Убедитесь, что service account добавлен как редактор таблицы
3. Проверьте, что Google Sheets API включен в проекте

### Ошибка "Requested entity was not found"

**Причина**: Неправильный ID таблицы или отсутствие доступа.

**Решение**:
1. Проверьте правильность `SHEET_ID`
2. Убедитесь, что service account имеет доступ к таблице
3. Проверьте, что таблица существует и не удалена

### Ошибка "Unable to parse range"

**Причина**: Проблемы с форматом данных или правами доступа.

**Решение**:
1. Запустите `python setup_sheets.py` для инициализации таблицы
2. Проверьте права доступа service account
3. Убедитесь, что таблица не заблокирована

## 📊 Структура таблицы

После успешной инициализации таблица будет содержать:

| Колонка | Описание |
|---------|----------|
| A | Lead ID |
| B | User ID |
| C | Username |
| D | TG Start |
| E | TG Complete |
| F | Возраст |
| G | Интересы |
| H | Бюджет |
| I | Опыт |
| J | Способ связи |
| K | Время |
| L | UTM Source |
| M | UTM Medium |
| N | UTM Campaign |
| O | UTM Term |
| P | UTM Content |

## 🔒 Безопасность

⚠️ **Важно**: 
- Никогда не публикуйте JSON файл с ключами в публичных репозиториях
- Добавьте `service-account-key.json` в `.gitignore`
- Используйте переменные окружения на продакшене
- Регулярно ротируйте ключи доступа

## 📞 Поддержка

Если у вас возникли проблемы:

1. Проверьте логи в `bot.log`
2. Убедитесь, что все шаги выполнены правильно
3. Проверьте права доступа service account
4. Убедитесь, что Google Sheets API включен

