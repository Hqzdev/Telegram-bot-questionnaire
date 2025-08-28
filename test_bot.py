#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы бота
"""

import asyncio
import sys
import os

# Добавляем путь к src для импортов
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from config import Config
from google_sheets_manager import GoogleSheetsManager

async def test_config():
    """Тестирует конфигурацию"""
    print("🔧 Тестирование конфигурации...")
    
    try:
        Config.validate()
        print("✅ Конфигурация корректна")
        print(f"📱 BOT_TOKEN: {'✅' if Config.BOT_TOKEN else '❌'}")
        print(f"📢 PRIVATE_CHANNEL_ID: {'✅' if Config.PRIVATE_CHANNEL_ID else '❌'}")
        print(f"📊 SHEET_ID: {'✅' if Config.SHEET_ID else '❌'}")
        
        # Тестируем Google Sheets
        print("\n🔧 Тестирование Google Sheets...")
        sheets_manager = GoogleSheetsManager()
        
        if sheets_manager.enabled:
            print("✅ Google Sheets API инициализирован")
            
            # Тестируем сохранение
            test_data = {
                'lead_id': 'test-123',
                'user_id': 123456789,
                'username': 'test_user',
                'tg_start': '2024-01-01T12:00:00',
                'tg_complete': '2024-01-01T12:05:00',
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
            
            success = await sheets_manager.save_lead(test_data)
            if success:
                print("✅ Тестовые данные успешно сохранены в Google Sheets")
            else:
                print("❌ Ошибка при сохранении тестовых данных")
        else:
            print("❌ Google Sheets API не инициализирован")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(test_config())
