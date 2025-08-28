#!/usr/bin/env python3
"""
Конфигурация для Telegram бота
"""

import os
import json
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

class Config:
    """Класс конфигурации"""
    
    # Telegram Bot Configuration
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    PRIVATE_CHANNEL_ID = os.getenv('PRIVATE_CHANNEL_ID')
    
    # Google Sheets Configuration
    SHEET_ID = os.getenv('SHEET_ID')
    SPREADSHEET_ID = os.getenv('SHEET_ID')  # Для совместимости
    GOOGLE_CREDENTIALS_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON')
    
    # Дополнительные настройки
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'bot.log')
    
    @classmethod
    def validate(cls):
        """Проверяет обязательные переменные окружения"""
        required_vars = [
            'BOT_TOKEN',
            'PRIVATE_CHANNEL_ID',
            'SHEET_ID'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}")
        
        return True
    
    @classmethod
    def get_google_credentials(cls):
        """Получает учетные данные Google из переменной окружения или файла"""
        if cls.GOOGLE_CREDENTIALS_JSON:
            try:
                return json.loads(cls.GOOGLE_CREDENTIALS_JSON)
            except json.JSONDecodeError:
                raise ValueError("Неверный формат GOOGLE_CREDENTIALS_JSON")
        
        # Если нет переменной окружения, ищем файл
        credentials_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'service-account-key.json')
        if os.path.exists(credentials_file):
            try:
                with open(credentials_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                raise ValueError(f"Ошибка чтения файла {credentials_file}: {e}")
        
        raise ValueError("Не найдены учетные данные Google Sheets. Укажите GOOGLE_CREDENTIALS_JSON или создайте файл config/service-account-key.json")

