#!/usr/bin/env python3
"""
Тестовый скрипт для проверки отправки уведомлений
"""

import asyncio
import sys
import os
from datetime import datetime

# Добавляем путь к src для импортов
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from aiogram import Bot
from aiogram.enums import ParseMode
from config import Config

async def test_notification():
    """Тестирует отправку уведомления в канал"""
    print("📢 Тестирование отправки уведомления...")
    
    try:
        # Создаем бота
        bot = Bot(token=Config.BOT_TOKEN, parse_mode=ParseMode.HTML)
        
        # Тестовые данные
        test_data = {
            'lead_id': 'test-notification-123',
            'user_id': 123456789,
            'username': 'test_user',
            'tg_complete': datetime.now().isoformat(),
            'answers': {
                'platforms': 'Wildberries',
                'work_type': 'Со склада продавца (FBS)',
                'volume_fbs': '50-200',
                'volume_fbo': '3-6',
                'main_concern': 'Просрочки по заказам (FBS, не успели к дедлайну)',
                'frequency': '1-3 раза',
                'losses': '5-25 тыс ₽',
                'reasons': ['Не успеваем собрать/упаковать', 'Слот/логистика сорвалась (поставка)'],
                'urgency': 'Срочно',
                'price': '1-3 тыс ₽'
            },
            'utm_data': {
                'utm_source': 'test',
                'utm_medium': 'test'
            }
        }
        
        # Формируем уведомление
        complete_time = datetime.fromisoformat(test_data['tg_complete']).strftime('%d.%m.%Y %H:%M:%S')
        
        notification_text = f"""
🎉 <b>ТЕСТ: Новый лид заполнил анкету!</b>

📋 <b>Lead ID:</b> <code>{test_data['lead_id']}</code>
👤 <b>Пользователь:</b> @{test_data['username']} (ID: {test_data['user_id']})
📅 <b>Время заполнения:</b> {complete_time}
💾 <b>Google Sheets:</b> ✅ Сохранено

📊 <b>Ответы:</b>
• <b>Где вы продаёте:</b> {test_data['answers']['platforms']}
• <b>Как вы работаете:</b> {test_data['answers']['work_type']}
• <b>FBS заказы в месяц:</b> {test_data['answers']['volume_fbs']}
• <b>FBO/FBW поставки в месяц:</b> {test_data['answers']['volume_fbo']}
• <b>Главная проблема:</b> {test_data['answers']['main_concern']}
• <b>Частота проблем:</b> {test_data['answers']['frequency']}
• <b>Потери за 30 дней:</b> {test_data['answers']['losses']}
• <b>Причины проблем:</b> {', '.join(test_data['answers']['reasons'])}
• <b>Срочность:</b> {test_data['answers']['urgency']}
• <b>Ценник:</b> {test_data['answers']['price']}

🏷 <b>UTM-параметры:</b>
• <b>utm_source:</b> {test_data['utm_data']['utm_source']}
• <b>utm_medium:</b> {test_data['utm_data']['utm_medium']}

✅ <b>Данные успешно загружены в Google Sheets!</b>
"""
        
        # Отправляем уведомление
        await bot.send_message(Config.PRIVATE_CHANNEL_ID, notification_text, parse_mode='HTML')
        print("✅ Тестовое уведомление отправлено в канал")
        
        # Закрываем сессию
        await bot.session.close()
        
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления: {e}")
        print(f"Детали ошибки: {type(e).__name__}")

if __name__ == "__main__":
    asyncio.run(test_notification())
