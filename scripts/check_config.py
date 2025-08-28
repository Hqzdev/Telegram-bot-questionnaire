#!/usr/bin/env python3
"""
Скрипт для проверки конфигурации перед запуском бота
Проверяет все необходимые файлы и настройки
"""

import os
import json
from config import Config

def check_env_file():
    """Проверяет наличие и корректность .env файла"""
    print("🔍 Проверка .env файла...")
    
    if not os.path.exists('.env'):
        print("❌ Файл .env не найден!")
        print("📝 Скопируйте env.example в .env и заполните переменные")
        return False
    
    print("✅ Файл .env найден")
    return True

def check_service_account():
    """Проверяет наличие файла сервисного аккаунта"""
    print("🔍 Проверка Google Service Account...")
    
    if not os.path.exists(Config.GOOGLE_SHEETS_CREDENTIALS_FILE):
        print(f"❌ Файл {Config.GOOGLE_SHEETS_CREDENTIALS_FILE} не найден!")
        print("📝 Скачайте ключ сервисного аккаунта из Google Cloud Console")
        return False
    
    try:
        with open(Config.GOOGLE_SHEETS_CREDENTIALS_FILE, 'r') as f:
            data = json.load(f)
        
        if 'type' not in data or data['type'] != 'service_account':
            print("❌ Неверный формат файла сервисного аккаунта!")
            return False
        
        print("✅ Файл сервисного аккаунта корректен")
        return True
        
    except json.JSONDecodeError:
        print("❌ Ошибка в формате JSON файла сервисного аккаунта!")
        return False
    except Exception as e:
        print(f"❌ Ошибка чтения файла сервисного аккаунта: {e}")
        return False

def check_survey_config():
    """Проверяет конфигурацию анкеты"""
    print("🔍 Проверка конфигурации анкеты...")
    
    try:
        survey_config = Config.load_survey()
        
        if 'steps' not in survey_config:
            print("❌ Отсутствует секция 'steps' в survey.json!")
            return False
        
        steps = survey_config['steps']
        if not steps:
            print("❌ Анкета не содержит шагов!")
            return False
        
        print(f"✅ Анкета содержит {len(steps)} шагов")
        
        # Проверяем каждый шаг
        for i, step in enumerate(steps):
            if 'id' not in step:
                print(f"❌ Шаг {i+1} не имеет ID!")
                return False
            if 'question' not in step:
                print(f"❌ Шаг {i+1} не имеет вопроса!")
                return False
            if 'type' not in step:
                print(f"❌ Шаг {i+1} не имеет типа!")
                return False
            
            if step['type'] == 'buttons' and 'options' not in step:
                print(f"❌ Шаг {i+1} типа 'buttons' не имеет опций!")
                return False
        
        print("✅ Конфигурация анкеты корректна")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации анкеты: {e}")
        return False

def check_config_variables():
    """Проверяет переменные конфигурации"""
    print("🔍 Проверка переменных конфигурации...")
    
    try:
        Config.validate()
        print("✅ Все обязательные переменные настроены")
        return True
    except ValueError as e:
        print(f"❌ Ошибка в переменных конфигурации: {e}")
        return False

def check_dependencies():
    """Проверяет наличие зависимостей"""
    print("🔍 Проверка зависимостей...")
    
    required_modules = [
        'aiogram',
        'google.auth',
        'googleapiclient',
        'dotenv'
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print(f"❌ Отсутствуют модули: {', '.join(missing_modules)}")
        print("📝 Установите зависимости: pip install -r requirements.txt")
        return False
    
    print("✅ Все зависимости установлены")
    return True

def main():
    """Основная функция проверки"""
    print("🔧 Проверка конфигурации Telegram бота\n")
    
    checks = [
        check_env_file,
        check_service_account,
        check_survey_config,
        check_config_variables,
        check_dependencies
    ]
    
    all_passed = True
    
    for check in checks:
        if not check():
            all_passed = False
        print()
    
    if all_passed:
        print("🎉 Все проверки пройдены! Бот готов к запуску.")
        print("🚀 Запустите бота командой: python main.py")
    else:
        print("❌ Некоторые проверки не пройдены. Исправьте ошибки и повторите проверку.")
    
    return all_passed

if __name__ == "__main__":
    main()





