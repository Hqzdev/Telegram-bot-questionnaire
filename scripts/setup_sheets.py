#!/usr/bin/env python3
"""
Скрипт для настройки Google Sheets
Запускайте этот скрипт один раз для инициализации таблицы
"""

import asyncio
import logging
from google_sheets_manager import GoogleSheetsManager
from config import Config

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_google_sheets():
    """Настраивает Google Sheets с заголовками"""
    try:
        # Проверяем конфигурацию
        Config.validate()
        logger.info("Конфигурация проверена успешно")
        
        # Инициализируем менеджер Google Sheets
        sheets_manager = GoogleSheetsManager()
        
        if not sheets_manager.enabled:
            logger.error("Google Sheets не инициализирован. Проверьте учетные данные.")
            return
        
        # Настраиваем заголовки
        success = await sheets_manager.setup_headers()
        
        if success:
            print("✅ Google Sheets успешно настроена!")
            print(f"📊 Таблица: {Config.SHEET_ID}")
            print("📝 Заголовки добавлены и отформатированы")
        else:
            print("❌ Ошибка при настройке Google Sheets")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(setup_google_sheets())

