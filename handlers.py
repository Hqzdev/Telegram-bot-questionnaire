import uuid
import logging
from datetime import datetime
from typing import Dict, Any

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import Config
from states import SurveyStates
from utils import UTMProcessor, GoogleSheetsManager, DataFormatter, logger

router = Router()
sheets_manager = GoogleSheetsManager()

class SurveyHandler:
    """Класс для обработки FSM-анкеты"""
    
    def __init__(self):
        self.survey_config = Config.load_survey()
        self.step_mapping = {
            'name': SurveyStates.name,
            'age': SurveyStates.age,
            'city': SurveyStates.city,
            'interests': SurveyStates.interests,
            'budget': SurveyStates.budget,
            'contact': SurveyStates.contact,
            'phone': SurveyStates.phone
        }
    
    def get_step_keyboard(self, step_config: Dict[str, Any]) -> InlineKeyboardMarkup:
        """Создает клавиатуру для шага с кнопками"""
        if step_config['type'] != 'buttons':
            return None
            
        keyboard = []
        for option in step_config['options']:
            keyboard.append([InlineKeyboardButton(text=option, callback_data=f"answer:{step_config['id']}:{option}")])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    async def start_survey(self, message: Message, state: FSMContext, utm_data: Dict[str, str] = None):
        """Начинает анкету"""
        # Сохраняем начальные данные
        await state.update_data(
            lead_id=str(uuid.uuid4()),
            user_id=message.from_user.id,
            username=message.from_user.username,
            tg_start=datetime.now().isoformat(),
            utm_data=utm_data or {},
            answers={}
        )
        
        # Переходим к первому шагу
        first_step = self.survey_config['steps'][0]
        await state.set_state(self.step_mapping[first_step['id']])
        
        keyboard = self.get_step_keyboard(first_step)
        await message.answer(first_step['question'], reply_markup=keyboard)
    
    async def handle_text_answer(self, message: Message, state: FSMContext):
        """Обрабатывает текстовый ответ"""
        current_state = await state.get_state()
        step_id = current_state.split(':')[-1]
        
        # Сохраняем ответ
        data = await state.get_data()
        if 'answers' not in data:
            data['answers'] = {}
        data['answers'][step_id] = message.text
        await state.set_data(data)
        
        # Переходим к следующему шагу
        await self.next_step(message, state)
    
    async def handle_button_answer(self, callback: CallbackQuery, state: FSMContext):
        """Обрабатывает ответ через кнопку"""
        _, step_id, answer = callback.data.split(':', 2)
        
        # Сохраняем ответ
        data = await state.get_data()
        if 'answers' not in data:
            data['answers'] = {}
        data['answers'][step_id] = answer
        await state.set_data(data)
        
        await callback.answer()
        await self.next_step(callback.message, state)
    
    async def next_step(self, message: Message, state: FSMContext):
        """Переходит к следующему шагу анкеты"""
        data = await state.get_data()
        current_answers = data.get('answers', {})
        
        # Находим следующий шаг
        next_step = None
        for step in self.survey_config['steps']:
            if step['id'] not in current_answers:
                next_step = step
                break
        
        if next_step:
            # Переходим к следующему шагу
            await state.set_state(self.step_mapping[next_step['id']])
            keyboard = self.get_step_keyboard(next_step)
            await message.answer(next_step['question'], reply_markup=keyboard)
        else:
            # Анкета завершена
            await self.complete_survey(message, state)
    
    async def complete_survey(self, message: Message, state: FSMContext):
        """Завершает анкету и сохраняет данные"""
        logger.info(f"Начинаем завершение анкеты для пользователя {message.from_user.id}")
        
        data = await state.get_data()
        
        # Проверяем, что все необходимые данные есть
        required_keys = ['lead_id', 'user_id', 'username', 'answers', 'utm_data', 'tg_start']
        missing_keys = [key for key in required_keys if key not in data]
        
        if missing_keys:
            logger.error(f"Отсутствуют необходимые данные: {missing_keys}")
            await message.answer("❌ Произошла ошибка при обработке данных. Попробуйте начать анкету заново.")
            await state.clear()
            return
        
        data['tg_complete'] = datetime.now().isoformat()
        
        logger.info(f"Данные анкеты: {data}")
        
        # Форматируем данные для Google Sheets
        try:
            row_data = DataFormatter.format_lead_data(
                lead_id=data['lead_id'],
                user_id=data['user_id'],
                username=data['username'],
                answers=data['answers'],
                utm_data=data['utm_data'],
                tg_start=data['tg_start'],
                tg_complete=data['tg_complete']
            )
            logger.info(f"Данные отформатированы для Google Sheets: {row_data}")
        except Exception as e:
            logger.error(f"Ошибка форматирования данных: {e}")
            await message.answer("❌ Произошла ошибка при обработке данных. Попробуйте позже.")
            await state.clear()
            return
        
        # Сохраняем в Google Sheets (если доступен)
        sheets_success = False
        if sheets_manager.enabled:
            logger.info("Пытаемся сохранить данные в Google Sheets...")
            sheets_success = await sheets_manager.append_row(row_data)
            logger.info(f"Результат сохранения в Google Sheets: {sheets_success}")
        else:
            logger.info("Google Sheets отключен, сохраняем только в чат")
        
        # Формируем уведомление для приватного чата
        notification_text = f"""
🎉 Новый лид заполнил анкету!

📋 Lead ID: {data['lead_id']}
👤 Пользователь: @{data['username']} (ID: {data['user_id']})
📅 Время заполнения: {data['tg_complete']}
💾 Google Sheets: {'✅ Сохранено' if sheets_success else '❌ Отключен'}

📊 Ответы:
"""
        for step in self.survey_config['steps']:
            answer = data['answers'].get(step['id'], 'Не указано')
            notification_text += f"• {step['question']}: {answer}\n"
        
        if data['utm_data']:
            notification_text += "\n🏷 UTM-параметры:\n"
            for key, value in data['utm_data'].items():
                notification_text += f"• {key}: {value}\n"
        
        # Отправляем уведомление в приватный чат
        try:
            await message.bot.send_message(Config.PRIVATE_CHAT_ID, notification_text)
            logger.info(f"Уведомление отправлено в приватный чат {Config.PRIVATE_CHAT_ID}")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {e}")
        
        # Отправляем ответ пользователю
        if sheets_success:
            await message.answer("✅ Спасибо! Ваша анкета успешно заполнена и отправлена.")
            logger.info(f"Анкета успешно завершена для пользователя {message.from_user.id}")
        else:
            await message.answer("✅ Спасибо! Ваша анкета заполнена. Данные отправлены администратору.")
            logger.info(f"Анкета завершена (только в чат) для пользователя {message.from_user.id}")
        
        # Очищаем состояние
        await state.clear()
        logger.info(f"Состояние очищено для пользователя {message.from_user.id}")

# Создаем экземпляр обработчика анкеты
survey_handler = SurveyHandler()

# Обработчики команд
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start с парсингом UTM-параметров"""
    # Парсим UTM-параметры из start payload
    utm_data = UTMProcessor.parse_start_payload(message.text.split()[1] if len(message.text.split()) > 1 else None)
    
    if utm_data:
        logger.info(f"Получены UTM-параметры для пользователя {message.from_user.id}: {utm_data}")
    
    await survey_handler.start_survey(message, state, utm_data)

@router.message(Command("restart"))
async def cmd_restart(message: Message, state: FSMContext):
    """Перезапуск анкеты"""
    await state.clear()
    await survey_handler.start_survey(message, state)

# Обработчики FSM состояний
@router.callback_query(F.data.startswith("answer:"))
async def handle_button_states(callback: CallbackQuery, state: FSMContext):
    """Обработчик состояний с кнопками"""
    await survey_handler.handle_button_answer(callback, state)

# Админские команды
@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Показывает статистику лидов (только для админов)"""
    if message.from_user.id not in Config.ADMIN_USER_IDS:
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    
    try:
        stats = await sheets_manager.get_stats()
        stats_text = f"""
📊 Статистика лидов:

📈 Всего лидов: {stats['total_leads']}
📅 Лидов за сегодня: {stats['today_leads']}
        """
        await message.answer(stats_text)
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        await message.answer("❌ Ошибка при получении статистики.")

@router.message(Command("resend"))
async def cmd_resend(message: Message):
    """Переотправляет последние данные в приватный чат (только для админов)"""
    if message.from_user.id not in Config.ADMIN_USER_IDS:
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    
    try:
        # Получаем последние данные из Google Sheets
        result = sheets_manager.service.spreadsheets().values().get(
            spreadsheetId=Config.SPREADSHEET_ID,
            range=f"{Config.SHEET_NAME}!A:Z"
        ).execute()
        
        values = result.get('values', [])
        if len(values) <= 1:
            await message.answer("📋 Данных для переотправки нет.")
            return
        
        # Берем последнюю строку
        last_row = values[-1]
        headers = DataFormatter.get_sheet_headers()
        
        # Формируем сообщение
        resend_text = "🔄 Переотправка последнего лида:\n\n"
        for i, header in enumerate(headers):
            if i < len(last_row):
                resend_text += f"• {header}: {last_row[i]}\n"
        
        await message.bot.send_message(Config.PRIVATE_CHAT_ID, resend_text)
        await message.answer("✅ Данные переотправлены в приватный чат.")
        
    except Exception as e:
        logger.error(f"Ошибка переотправки данных: {e}")
        await message.answer("❌ Ошибка при переотправке данных.")

@router.message(Command("leads"))
async def cmd_leads(message: Message):
    """Показывает последние лиды в чате (только для админов)"""
    if message.from_user.id not in Config.ADMIN_USER_IDS:
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    
    try:
        # Получаем данные из Google Sheets
        if not sheets_manager.enabled:
            await message.answer("❌ Google Sheets отключен. Данные недоступны.")
            return
            
        result = sheets_manager.service.spreadsheets().values().get(
            spreadsheetId=Config.SPREADSHEET_ID,
            range=f"{Config.SHEET_NAME}!A:Z"
        ).execute()
        
        values = result.get('values', [])
        if len(values) <= 1:
            await message.answer("📋 Лидов пока нет.")
            return
        
        # Показываем последние 5 лидов
        recent_leads = values[-5:] if len(values) > 5 else values[1:]
        headers = DataFormatter.get_sheet_headers()
        
        leads_text = f"📋 Последние {len(recent_leads)} лидов:\n\n"
        
        for i, lead in enumerate(recent_leads, 1):
            leads_text += f"🔸 Лид #{len(values) - len(recent_leads) + i - 1}\n"
            
            # Показываем основные поля
            if len(lead) > 0:
                leads_text += f"   ID: {lead[0]}\n"
            if len(lead) > 2:
                leads_text += f"   Пользователь: {lead[2]}\n"
            if len(lead) > 3:
                leads_text += f"   Время: {lead[3]}\n"
            
            # Показываем ответы на вопросы
            survey_config = Config.load_survey()
            for j, step in enumerate(survey_config['steps']):
                if len(lead) > 5 + j:
                    answer = lead[5 + j] if lead[5 + j] else "Не указано"
                    leads_text += f"   {step['question']}: {answer}\n"
            
            leads_text += "\n"
        
        await message.answer(leads_text)
        
    except Exception as e:
        logger.error(f"Ошибка получения лидов: {e}")
        await message.answer("❌ Ошибка при получении данных.")

# Обработчик неизвестных сообщений
@router.message()
async def handle_unknown(message: Message, state: FSMContext):
    """Обработчик неизвестных сообщений"""
    current_state = await state.get_state()
    if current_state:
        # Если пользователь в процессе заполнения анкеты, напоминаем использовать кнопки
        await message.answer("📝 Пожалуйста, используйте кнопки для ответа на вопросы анкеты.")
    else:
        await message.answer("👋 Привет! Нажмите /start чтобы начать заполнение анкеты.")

