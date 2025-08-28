#!/usr/bin/env python3
"""
Telegram Bot для сбора лидов с анкетой и Google Sheets интеграцией
Использует aiogram 3.x
"""

import asyncio
import json
import base64
import urllib.parse
import uuid
import logging
import os
import sys
import secrets
import string
import aiosqlite
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Добавляем путь к src для импортов
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode

from config import Config
from google_sheets_manager import GoogleSheetsManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=Config.BOT_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация Google Sheets менеджера
sheets_manager = GoogleSheetsManager()

# Словарь для хранения запланированных напоминаний
reminder_tasks = {}

# Инициализация базы данных
async def init_db():
    """Инициализация базы данных для демо-уведомлений и предзаписей"""
    db_path = "bot.db"
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, event TEXT, payload TEXT, ts TEXT
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS prereg(
            user_id INTEGER PRIMARY KEY,
            code TEXT, tariff TEXT, valid_to TEXT, created_at TEXT
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY, value TEXT
        )""")
        await db.commit()

async def log_event(user_id: int, event: str, payload: str = ""):
    """Логирование событий в базу данных"""
    db_path = "bot.db"
    async with aiosqlite.connect(db_path) as db:
        await db.execute("INSERT INTO events(user_id,event,payload,ts) VALUES(?,?,?,?)",
                         (user_id, event, payload, datetime.utcnow().isoformat()))
        await db.commit()

def gen_code(n=6):
    """Генерация кода предзаписи"""
    alphabet = string.ascii_uppercase + string.digits
    return "LOCK-" + "".join(secrets.choice(alphabet) for _ in range(n))

async def create_prereg(user_id: int, tariff: str = "Pro 2 990 ₽"):
    """Создание предзаписи пользователя"""
    code = gen_code()
    valid_to = (datetime.now().replace(day=1) + timedelta(days=31*6))  # ~6 мес
    db_path = "bot.db"
    async with aiosqlite.connect(db_path) as db:
        # вставляем/обновляем
        await db.execute("""
            INSERT INTO prereg(user_id, code, tariff, valid_to, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET code=excluded.code, tariff=excluded.tariff, valid_to=excluded.valid_to
        """, (user_id, code, tariff, valid_to.isoformat(), datetime.utcnow().isoformat()))
        await db.commit()
        # номер в очереди — по порядку создания
        cur = await db.execute("SELECT COUNT(*) FROM prereg WHERE created_at <= (SELECT created_at FROM prereg WHERE user_id=?)", (user_id,))
        place = (await cur.fetchone())[0]
    return code, valid_to, place

def kb_fbs_demo():
    """Клавиатура для FBS демо-уведомления"""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⏰ Отложить 15 мин", callback_data="demo:fbs:snooze15"),
        InlineKeyboardButton(text="✅ Готово", callback_data="demo:fbs:done")
    ],[
        InlineKeyboardButton(text="📊 Сводка", callback_data="demo:summary")
    ]])

def kb_fbo_demo():
    """Клавиатура для FBO демо-уведомления"""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📅 Изменить слот", callback_data="demo:fbo:slot"),
        InlineKeyboardButton(text="🌅 Напомнить утром", callback_data="demo:fbo:morning")
    ],[
        InlineKeyboardButton(text="📊 Сводка", callback_data="demo:summary")
    ]])

async def send_demo_notifications(msg: Message):
    """Отправка демо-уведомлений"""
    await msg.answer(
        "🔔 Заказ #308132 — дедлайн через 1 ч 20 мин\n"
        "FBS · ПВЗ: Москва, Ленина 10 · приоритет: важно\n\n"
        "Что сделать:\n— Проверьте сборку и маркировку\n— Подтвердите курьера/самовывоз\n— Не откладывайте: после дедлайна рейтинг и отмены",
        reply_markup=kb_fbs_demo()
    )
    await msg.answer(
        "⏰ Поставка FBO — до «красной зоны» 24 ч\n"
        "Риск удержания: min(5 ₽ × ед., 25 000 ₽)\n\n"
        "Что сделать:\n— Уточните слот (переносите не позднее, чем за 72 ч)\n— Проверьте упаковку, габариты и паллеты\n— Назначьте ответственного",
        reply_markup=kb_fbo_demo()
    )

async def send_demo_notifications_with_intro(msg: Message):
    """Отправка демо-уведомлений с вступлением"""
    await msg.answer(
        "🎯 <b>Демо-уведомления приложения «Антипросрочка»</b>\n\n"
        "Ниже вы увидите два типа уведомлений:\n"
        "• <b>FBS</b> — заказы со склада продавца\n"
        "• <b>FBO</b> — поставки на склад маркетплейса\n\n"
        "💡 Попробуйте кнопки — они работают!",
        parse_mode='HTML'
    )
    await send_demo_notifications(msg)

async def remind_later(chat_id: int, minutes: int):
    """Напоминание через указанное количество минут"""
    await asyncio.sleep(minutes * 60)
    await bot.send_message(chat_id, f"🔔 Демо-напоминание: прошло {minutes} мин.")

async def send_checklist(msg: Message):
    """Отправка чек-листа"""
    await msg.answer(
        "📋 Чек-лист «Антипросрочка»\n\n"
        "FBS (со склада продавца):\n"
        "• −4 ч / −2 ч / −60 мин — что делать на каждом шаге\n"
        "• Сборка/маркировка/упаковка — краткий чек-лист\n"
        "• Ответственный + «тихие часы»\n\n"
        "FBO/FBW (на склад МП):\n"
        "• Правило «72 часа» — как избежать удержаний\n"
        "• Формула риска: min(5 ₽ × ед., 25 000 ₽) — с примерами\n"
        "• Перед поставкой: слот, паллеты, габариты, доки"
    )

async def show_pricing(msg: Message):
    """Показать тарифы"""
    pricing_text = """
💰 <b>Тарифы приложения «Антипросрочка»</b>

🚀 <b>Pro</b> — 2 990 ₽/мес
• Уведомления FBS и FBO
• Чек-листы и подсказки
• Аналитика и статистика
• Приоритетная поддержка

⚡ <b>Basic</b> — 1 490 ₽/мес
• Уведомления FBS
• Базовые чек-листы
• Email поддержка

🎯 <b>Enterprise</b> — от 5 990 ₽/мес
• Все функции Pro
• Интеграция с вашими системами
• Персональный менеджер
• Кастомные настройки

💡 <b>Попробуйте бесплатно 15 минут</b>
Без подключений и настроек — сразу увидите результат!
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔒 Закрепить предзапись", callback_data="prereg:lock")],
        [InlineKeyboardButton(text="🎯 Показать демо", callback_data="demo:open")],
        [InlineKeyboardButton(text="💳 Мой код цены", callback_data="my_price")]
    ])
    
    await msg.answer(pricing_text, reply_markup=keyboard, parse_mode='HTML')

async def send_reminder(user_id: int):
    """Отправляет напоминание о прохождении анкеты"""
    try:
        await bot.send_message(
            user_id,
            "🔔 Напоминание! Не забудьте пройти анкету для получения персонального предложения.\n\n"
            "Нажмите /start чтобы начать заполнение анкеты.",
            parse_mode='HTML'
        )
        logger.info(f"Отправлено напоминание пользователю {user_id}")
    except Exception as e:
        logger.error(f"Ошибка отправки напоминания пользователю {user_id}: {e}")

async def schedule_reminder(user_id: int, delay_hours: int = 24):
    """Планирует отправку напоминания через указанное количество часов"""
    delay_seconds = delay_hours * 3600
    
    async def reminder_task():
        await asyncio.sleep(delay_seconds)
        await send_reminder(user_id)
        # Удаляем задачу из словаря после выполнения
        if user_id in reminder_tasks:
            del reminder_tasks[user_id]
    
    # Отменяем предыдущее напоминание, если оно есть
    if user_id in reminder_tasks:
        reminder_tasks[user_id].cancel()
    
    # Создаем новую задачу
    task = asyncio.create_task(reminder_task())
    reminder_tasks[user_id] = task
    logger.info(f"Запланировано напоминание для пользователя {user_id} через {delay_hours} часов")

# Состояния FSM для анкеты
class SurveyStates(StatesGroup):
    waiting_for_start = State()
    question_1 = State()
    question_2 = State()
    question_3 = State()
    question_4 = State()
    question_5 = State()
    question_6 = State()
    question_7 = State()

# Конфигурация анкеты - легко изменить вопросы и варианты ответов
SURVEY_CONFIG = {
    "welcome": {
        "title": "**Добро пожаловать! Давайте заполним анкету за 1 минуту и 8 простых кликов для получения персонального предложения.**",
        "buttons": [
            "Начать анкету",
            "Позже"
        ]
    },
    "questions": [
        {
            "id": "platforms",
            "question": "Где вы продаёте?",
            "type": "single",
            "options": [
                "Wildberries",
                "Ozon",
                "На обеих"
            ]
        },
        {
            "id": "work_type",
            "question": "Как вы работаете чаще всего?",
            "type": "single",
            "options": [
                "Со склада продавца (FBS)",
                "На склад МП (FBO/FBW)",
                "И так, и так"
            ]
        },
        {
            "id": "volume_fbs",
            "question": "FBS заказы в месяц (примерно):",
            "type": "single",
            "options": [
                "0-50",
                "50-200",
                "200-500",
                "500+",
                "Не работаю FBS"
            ]
        },
        {
            "id": "volume_fbo",
            "question": "FBO/FBW поставки в месяц (примерно):",
            "type": "single",
            "options": [
                "0-2",
                "3-6",
                "7-15",
                "16+",
                "Не работаю FBO"
            ]
        },
        {
            "id": "main_concern",
            "question": "Что сильнее всего беспокоило за последние 30 дней?",
            "type": "single",
            "options": [
                "Не успели доставить по FBS за 24/120 часов",
                "Перенос/отмена поставки < 3 дней (FBO/FBW, штраф)",
                "Недовоз/проблемы на приёмке",
                "Неверные габариты/маркировка (штрафы)",
                "Другое"
            ]
        },
        {
            "id": "frequency",
            "question": "Как часто это случалось за 30 дней?",
            "type": "single",
            "options": [
                "Ни разу",
                "1-3 раза",
                "4-10 раз",
                "Больше 10 раз"
            ]
        },
        {
            "id": "losses",
            "question": "Примерно сколько денег потеряли на этом за 30 дней?",
            "type": "single",
            "options": [
                "0 ₽",
                "до 5 000 ₽",
                "5-25 тыс ₽",
                "25-100 тыс ₽",
                "100 тыс+ ₽"
            ]
        },
        {
            "id": "reasons",
            "question": "Почему это чаще всего происходило?",
            "type": "multi",
            "options": [
                "Не успеваем собрать/упаковать",
                "Слот/логистика сорвалась (поставка)",
                "Нет остатков / ошибка планирования",
                "Человеческий фактор (смена/ошибка)",
                "Другое"
            ]
        },
        {
            "id": "urgency",
            "question": "Хотели бы Вы приложение, которое поможет избежать штрафы?",
            "type": "single",
            "options": [
                "Да, как можно скорее",
                "Да, но могу и без него",
                "Нет, я сам справлюсь"
            ]
        },
        {
            "id": "price",
            "question": "Какой ценник Вам был бы комфортен за такое приложение?",
            "type": "single",
            "options": [
                "до 990 ₽",
                "1-3 тыс ₽",
                "3-5 тыс ₽",
                "5 тыс+ ₽",
                "Хочу бесплатно/сам"
            ]
        }
    ],
    "final": {
        "title": "Спасибо! Отправляю чек-лист «Антипросрочка» (2 страницы) и закрепляю за вами минимальную цену на 6 месяцев.",
        "description": "Как двигаемся дальше?",
        "buttons": [
            "Закрепить предзапись в приоритет и быть первым кто испробует",
            "Показать демо-уведомления",
            "Готово"
        ]
    }
}

class UTMParser:
    """Класс для парсинга UTM-параметров из start payload"""
    
    @staticmethod
    def parse_start_payload(payload: str) -> Dict[str, str]:
        """Парсит UTM-параметры из start payload"""
        utm_data = {}
        
        if not payload:
            return utm_data
            
        try:
            # Пробуем декодировать как base64 JSON
            try:
                decoded = base64.b64decode(payload).decode('utf-8')
                data = json.loads(decoded)
                if isinstance(data, dict):
                    utm_data = {k: v for k, v in data.items() if k.startswith('utm_')}
            except (base64.binascii.Error, json.JSONDecodeError, UnicodeDecodeError):
                pass
            
            # Если base64 не сработал, пробуем URL-encoded
            if not utm_data:
                parsed = urllib.parse.parse_qs(payload)
                utm_data = {k: v[0] for k, v in parsed.items() if k.startswith('utm_')}
                
        except Exception as e:
            logger.error(f"Ошибка при парсинге start payload: {e}")
            
        return utm_data

class SurveyHandler:
    """Класс для обработки анкеты"""
    
    def __init__(self):
        self.config = SURVEY_CONFIG
    
    def create_keyboard(self, question: Dict[str, Any], user_answers: Dict[str, Any] = None) -> InlineKeyboardMarkup:
        """Создает клавиатуру для вопроса"""
        keyboard = []
        
        for i, option in enumerate(question['options']):
            # Для множественного выбора показываем статус выбора
            if question['type'] == 'multi':
                is_selected = user_answers and option in user_answers.get(question['id'], [])
                text = f"{'✅' if is_selected else '⬜'} {option}"
            else:
                text = option
            
            # Используем индекс вместо полного текста для избежания проблем с символами
            callback_data = f"answer:{question['id']}:{i}"
            keyboard.append([InlineKeyboardButton(text=text, callback_data=callback_data)])
        
        # Кнопка "Далее" для множественного выбора
        if question['type'] == 'multi':
            keyboard.append([InlineKeyboardButton(text="➡️ Далее", callback_data=f"next:{question['id']}")])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    async def start_survey(self, message: Message, state: FSMContext, utm_data: Dict[str, str] = None):
        """Начинает анкету"""
        # Сохраняем начальные данные
        await state.update_data(
            lead_id=str(uuid.uuid4()),
            user_id=message.from_user.id,
            username=message.from_user.username or "Не указан",
            tg_start=datetime.now().isoformat(),
            utm_data=utm_data or {},
            answers={}
        )
        
        # Показываем приветственное сообщение
        welcome_text = f"{self.config['welcome']['title']}"
        keyboard = [[InlineKeyboardButton(text=btn, callback_data=f"welcome:{i}")] for i, btn in enumerate(self.config['welcome']['buttons'])]
        await message.answer(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode='Markdown'
        )
    
    async def show_question(self, message: Message, state: FSMContext, question_index: int = 0):
        """Показывает вопрос анкеты"""
        if question_index >= len(self.config['questions']):
            # Анкета завершена
            await self.complete_survey(message, state)
            return
        
        question = self.config['questions'][question_index]
        data = await state.get_data()
        user_answers = data.get('answers', {})
        
        keyboard = self.create_keyboard(question, user_answers)
        await message.answer(question['question'], reply_markup=keyboard)
    
    async def handle_answer(self, callback: CallbackQuery, state: FSMContext):
        """Обрабатывает ответ на вопрос"""
        _, question_id, option_index = callback.data.split(':', 2)
        option_index = int(option_index)
        
        data = await state.get_data()
        answers = data.get('answers', {})
        
        # Обрабатываем ответ в зависимости от типа вопроса
        question = next((q for q in self.config['questions'] if q['id'] == question_id), None)
        if not question:
            await callback.answer("Ошибка: вопрос не найден")
            return
        
        # Получаем текст ответа по индексу
        if 0 <= option_index < len(question['options']):
            answer_text = question['options'][option_index]
        else:
            await callback.answer("Ошибка: неверный индекс ответа")
            return
        
        if question['type'] == 'multi':
            # Множественный выбор
            if question_id not in answers:
                answers[question_id] = []
            
            if answer_text in answers[question_id]:
                answers[question_id].remove(answer_text)
            else:
                answers[question_id].append(answer_text)
            
            # Обновляем клавиатуру
            keyboard = self.create_keyboard(question, answers)
            await callback.message.edit_reply_markup(reply_markup=keyboard)
            await callback.answer()
            
        else:
            # Одиночный выбор
            answers[question_id] = answer_text
            data['answers'] = answers
            await state.set_data(data)
            
            await callback.answer()
            await self.show_next_question(callback.message, state, question_id)
    
    async def handle_next(self, callback: CallbackQuery, state: FSMContext):
        """Обрабатывает кнопку 'Далее' для множественного выбора"""
        _, question_id = callback.data.split(':', 1)
        
        data = await state.get_data()
        answers = data.get('answers', {})
        
        # Проверяем, что выбран хотя бы один вариант
        if question_id not in answers or not answers[question_id]:
            await callback.answer("Пожалуйста, выберите хотя бы один вариант")
            return
        
        await callback.answer()
        await self.show_next_question(callback.message, state, question_id)
    
    async def show_next_question(self, message: Message, state: FSMContext, current_question_id: str):
        """Показывает следующий вопрос"""
        current_index = next((i for i, q in enumerate(self.config['questions']) if q['id'] == current_question_id), -1)
        next_index = current_index + 1
        
        if next_index < len(self.config['questions']):
            await self.show_question(message, state, next_index)
        else:
            # Анкета завершена
            await self.complete_survey(message, state)
    
    async def complete_survey(self, message: Message, state: FSMContext):
        """Завершает анкету и сохраняет данные"""
        data = await state.get_data()
        data['tg_complete'] = datetime.now().isoformat()
        
        logger.info(f"Завершение анкеты для пользователя {data['user_id']}")
        
        # Сохраняем в Google Sheets
        success = await sheets_manager.save_lead(data)
        
        # Отправляем уведомление в приватный канал
        await self.send_notification(data, success)
        
        # Отправляем демо-уведомления
        await send_demo_notifications_with_intro(message)
        
        # Отправляем чек-лист
        await send_checklist(message)
        
        # Отправляем финальное сообщение с кнопками
        final_text = f"**{self.config['final']['title']}**\n\n{self.config['final']['description']}"
        keyboard = [[InlineKeyboardButton(text=btn, callback_data=f"final:{i}")] for i, btn in enumerate(self.config['final']['buttons'])]
        await message.answer(
            final_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode='Markdown'
        )
        
        # Очищаем состояние
        await state.clear()
    
    async def send_notification(self, data: Dict[str, Any], sheets_success: bool):
        """Отправляет уведомление в приватный канал"""
        try:
            # Проверяем, что PRIVATE_CHANNEL_ID настроен
            if not Config.PRIVATE_CHANNEL_ID:
                logger.warning("PRIVATE_CHANNEL_ID не настроен. Уведомление не отправлено.")
                return
                
            # Форматируем время для читаемости
            try:
                complete_time = datetime.fromisoformat(data['tg_complete']).strftime('%d.%m.%Y %H:%M:%S')
            except:
                complete_time = data['tg_complete']
                
            notification_text = f"""
🎉 <b>Новый лид заполнил анкету!</b>

📋 <b>Lead ID:</b> <code>{data['lead_id']}</code>
👤 <b>Пользователь:</b> @{data['username']} (ID: {data['user_id']})
📅 <b>Время заполнения:</b> {complete_time}
💾 <b>Google Sheets:</b> {'✅ Сохранено' if sheets_success else '❌ Ошибка'}

📊 <b>Ответы:</b>
"""
            
            for question in self.config['questions']:
                question_id = question['id']
                answer = data['answers'].get(question_id, 'Не указано')
                
                if isinstance(answer, list):
                    answer = ', '.join(answer) if answer else 'Не указано'
                
                notification_text += f"• <b>{question['question']}</b>: {answer}\n"
            
            # Добавляем UTM-параметры
            utm_data = data.get('utm_data', {})
            if utm_data:
                notification_text += "\n🏷 <b>UTM-параметры:</b>\n"
                for key, value in utm_data.items():
                    notification_text += f"• <b>{key}:</b> {value}\n"
            
            # Добавляем подробную информацию о статусе Google Sheets
            if sheets_success:
                notification_text += "\n✅ <b>Данные успешно загружены в Google Sheets!</b>"
            else:
                notification_text += "\n❌ <b>Ошибка при загрузке в Google Sheets!</b>"
            
            await bot.send_message(Config.PRIVATE_CHANNEL_ID, notification_text, parse_mode='HTML')
            logger.info(f"Уведомление отправлено в канал {Config.PRIVATE_CHANNEL_ID}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {e}")
            logger.error(f"Детали ошибки: {type(e).__name__}")

# Создаем экземпляр обработчика анкеты
survey_handler = SurveyHandler()

# Обработчики команд
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start с парсингом UTM-параметров"""
    # Парсим UTM-параметры из start payload
    utm_data = UTMParser.parse_start_payload(message.text.split()[1] if len(message.text.split()) > 1 else None)
    
    if utm_data:
        logger.info(f"Получены UTM-параметры для пользователя {message.from_user.id}: {utm_data}")
    
    await survey_handler.start_survey(message, state, utm_data)

@dp.message(Command("restart"))
async def cmd_restart(message: Message, state: FSMContext):
    """Перезапуск анкеты"""
    await state.clear()
    await survey_handler.start_survey(message, state)

@dp.message(Command("my_price"))
async def my_price(msg: Message):
    """Показать код цены пользователя"""
    try:
        db_path = "bot.db"
        async with aiosqlite.connect(db_path) as db:
            cur = await db.execute("SELECT code, tariff, valid_to FROM prereg WHERE user_id=?", (msg.from_user.id,))
            row = await cur.fetchone()
        
        if not row:
            await msg.answer("❌ Предзапись не найдена\n💡 Используйте /prereg для создания предзаписи")
            return
        
        code, tariff, valid_to = row
        d = datetime.fromisoformat(valid_to)
        await msg.answer(
            f"💳 <b>Ваш код цены</b>\n\n"
            f"Код: <code>{code}</code>\n"
            f"Тариф: {tariff}\n"
            f"Действует до: {d.strftime('%d.%m.%Y')}",
            parse_mode='HTML'
        )
    except Exception as e:
        await msg.answer("❌ Ошибка получения кода цены")
        logger.error(f"Ошибка получения кода цены: {e}")

@dp.message(Command("demo"))
async def cmd_demo(msg: Message):
    """Отправка демо-уведомлений"""
    await send_demo_notifications_with_intro(msg)

@dp.message(Command("pricing"))
async def cmd_pricing(msg: Message):
    """Показать тарифы"""
    await show_pricing(msg)

@dp.message(Command("demo_notifications"))
async def cmd_demo_notifications(msg: Message):
    """Отправка демо-уведомлений (альтернативная команда)"""
    await send_demo_notifications_with_intro(msg)

@dp.message(Command("checklist"))
async def cmd_checklist(msg: Message):
    """Показать чек-лист"""
    await send_checklist(msg)

@dp.message(Command("summary"))
async def cmd_summary(msg: Message):
    """Показать сводку"""
    await msg.answer("📈 Сводка за сегодня:\n• Спасено заказов: 7\n• Избегнуто удержаний: 1\n• Экономия: 25 000 ₽")

@dp.message(Command("prereg"))
async def cmd_prereg(msg: Message):
    """Создать предзапись"""
    try:
        code, valid_to, place = await create_prereg(msg.from_user.id)
        await log_event(msg.from_user.id, "prereg_lock", code)
        await msg.answer(
            f"✅ Предзапись закреплена!\n"
            f"Код цены: <b>{code}</b>\n"
            f"Тариф: Pro 2 990 ₽\n"
            f"Действует до: {valid_to.strftime('%d.%m.%Y')}\n"
            f"Ваш номер в очереди: №{place}",
            parse_mode='HTML'
        )
    except Exception as e:
        await msg.answer("❌ Ошибка создания предзаписи. Попробуйте позже.")
        logger.error(f"Ошибка создания предзаписи: {e}")

@dp.message(Command("help"))
async def cmd_help(msg: Message):
    """Показать справку по командам"""
    help_text = """
🤖 <b>Доступные команды:</b>

📝 <b>Анкета:</b>
/start — Начать заполнение анкеты
/restart — Перезапустить анкету

🎯 <b>Демо и функции:</b>
/demo — Показать демо-уведомления
/demo_notifications — Альтернативная команда для демо
/checklist — Показать чек-лист «Антипросрочка»
/summary — Показать сводку

💰 <b>Тарифы и предзапись:</b>
/pricing — Показать тарифы
/prereg — Создать предзапись
/my_price — Показать ваш код цены

❓ <b>Справка:</b>
/help — Показать эту справку
"""
    await msg.answer(help_text, parse_mode='HTML')

# Обработчики callback-запросов
@dp.callback_query(F.data.startswith("welcome:"))
async def handle_welcome_buttons(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопок вступления"""
    _, button_index = callback.data.split(':', 1)
    button_index = int(button_index)
    
    if button_index == 0:  # "Начать анкету"
        await callback.answer()
        await survey_handler.show_question(callback.message, state, 0)
    else:  # "Позже"
        await callback.answer("Хорошо, возвращайтесь когда будете готовы! 👋")
        await callback.message.edit_text("Хорошо, возвращайтесь когда будете готовы! 👋")
        
        # Планируем напоминание через 24 часа
        user_id = callback.from_user.id
        await schedule_reminder(user_id, 24)

@dp.callback_query(F.data.startswith("answer:"))
async def handle_answer(callback: CallbackQuery, state: FSMContext):
    """Обработчик ответов на вопросы"""
    await survey_handler.handle_answer(callback, state)

@dp.callback_query(F.data.startswith("next:"))
async def handle_next(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Далее'"""
    await survey_handler.handle_next(callback, state)

@dp.callback_query(F.data.startswith("final:"))
async def handle_final_buttons(callback: CallbackQuery, state: FSMContext):
    """Обработчик финальных кнопок"""
    _, button_index = callback.data.split(':', 1)
    button_index = int(button_index)
    
    if button_index == 0:  # "Закрепить предзапись в приоритет и быть первым кто испробует"
        code, valid_to, place = await create_prereg(callback.from_user.id)
        await log_event(callback.from_user.id, "prereg_lock", code)
        await callback.message.answer(
            f"✅ Готово! Вы в приоритете.\n"
            f"Код цены: <b>{code}</b>\n"
            f"Цена фиксирована на 6 месяцев (до {valid_to.strftime('%d.%m.%Y')}).\n"
            f"Ваш номер в очереди: №{place}.\n\n"
            f"Далее: 15-минутный пилот без подключений — когда удобно?"
        )
        await callback.answer("Предзапись закреплена.")
    elif button_index == 1:  # "Показать демо-уведомления"
        await callback.answer("Показываем демо-уведомления...")
        await send_demo_notifications_with_intro(callback.message)
    else:  # "Готово"
        await callback.answer("Спасибо за участие!")
        await callback.message.edit_text("👋 Спасибо за участие в опросе!")

@dp.callback_query(F.data.startswith("demo:"))
async def handle_demo_buttons(callback: CallbackQuery):
    """Обработчик демо-кнопок"""
    await log_event(callback.from_user.id, "demo_click", callback.data)
    
    if callback.data == "demo:fbs:snooze15":
        await callback.answer("⏰ Напомню через 15 минут")
        await callback.message.answer("🔔 Напоминание запланировано на 15 минут")
    elif callback.data == "demo:fbs:done":
        await callback.answer("✅ Выполнено!")
        await callback.message.answer("🎉 Заказ отмечен как выполненный")
    elif callback.data == "demo:fbo:slot":
        await callback.answer("📅 Открываю календарь слотов")
        await callback.message.answer("📋 Подсказки по переносу слота:\n• Переносить не позднее 72 часов\n• Уведомить менеджера\n• Проверить новый слот")
    elif callback.data == "demo:fbo:morning":
        await callback.answer("🌅 Напомню утром")
        await callback.message.answer("⏰ Напоминание установлено на утро (9:00)")
    elif callback.data == "demo:summary":
        await callback.answer("📊 Показываю сводку")
        await callback.message.answer("📈 Сводка за сегодня:\n• Спасено заказов: 7\n• Избегнуто удержаний: 1\n• Экономия: 25 000 ₽")
    elif callback.data == "demo:open":
        await callback.answer("🎯 Показываю демо")
        await send_demo_notifications_with_intro(callback.message)

@dp.callback_query(F.data.startswith("nav:"))
async def handle_nav_buttons(callback: CallbackQuery):
    """Обработчик навигационных кнопок"""
    await log_event(callback.from_user.id, "nav_click", callback.data)
    
    if callback.data == "nav:pricing":
        await callback.answer("💰 Показываю тарифы")
        await show_pricing(callback.message)

@dp.callback_query(F.data.startswith("prereg:"))
async def handle_prereg_buttons(callback: CallbackQuery):
    """Обработчик кнопок предзаписи"""
    await log_event(callback.from_user.id, "prereg_click", callback.data)
    
    if callback.data == "prereg:lock":
        await callback.answer("🔒 Создаю предзапись...")
        try:
            code, valid_to, place = await create_prereg(callback.from_user.id)
            await callback.message.answer(
                f"✅ Предзапись закреплена!\n"
                f"Код цены: <b>{code}</b>\n"
                f"Тариф: Pro 2 990 ₽\n"
                f"Действует до: {valid_to.strftime('%d.%m.%Y')}\n"
                f"Ваш номер в очереди: №{place}",
                parse_mode='HTML'
            )
        except Exception as e:
            await callback.message.answer("❌ Ошибка создания предзаписи. Попробуйте позже.")
            logger.error(f"Ошибка создания предзаписи: {e}")

@dp.callback_query(F.data == "my_price")
async def handle_my_price_button(callback: CallbackQuery):
    """Обработчик кнопки 'Мой код цены'"""
    await log_event(callback.from_user.id, "my_price_click", "button")
    
    try:
        db_path = "bot.db"
        async with aiosqlite.connect(db_path) as db:
            cur = await db.execute("SELECT code, tariff, valid_to FROM prereg WHERE user_id=?", (callback.from_user.id,))
            row = await cur.fetchone()
        
        if not row:
            await callback.answer("❌ Предзапись не найдена")
            await callback.message.answer("💡 Сначала создайте предзапись через кнопку «Закрепить предзапись»")
            return
        
        code, tariff, valid_to = row
        d = datetime.fromisoformat(valid_to)
        
        await callback.answer("💳 Показываю код цены")
        await callback.message.answer(
            f"💳 <b>Ваш код цены</b>\n\n"
            f"Код: <code>{code}</code>\n"
            f"Тариф: {tariff}\n"
            f"Действует до: {d.strftime('%d.%m.%Y')}",
            parse_mode='HTML'
        )
    except Exception as e:
        await callback.answer("❌ Ошибка получения кода")
        logger.error(f"Ошибка получения кода цены: {e}")

# Обработчик неизвестных сообщений
@dp.message()
async def handle_unknown(message: Message):
    """Обработчик неизвестных сообщений"""
    await message.answer("👋 Привет! Нажмите /start чтобы начать заполнение анкеты или /help для справки по командам.")

async def main():
    """Основная функция запуска бота"""
    logger.info("Бот запускается...")
    
    try:
        # Инициализируем базу данных
        await init_db()
        logger.info("База данных инициализирована")
        
        # Проверяем конфигурацию
        Config.validate()
        logger.info("Конфигурация проверена успешно")
        
        # Запускаем бота
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())





