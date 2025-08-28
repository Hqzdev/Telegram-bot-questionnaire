#!/usr/bin/env python3
"""
Скрипт для настройки Google Sheets с заголовками
Запускайте этот скрипт один раз для инициализации таблицы
"""

import asyncio
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import Config
from utils import DataFormatter, logger

async def setup_google_sheets():
    """Настраивает Google Sheets с заголовками"""
    
    try:
        # Инициализируем Google Sheets API
        credentials = Credentials.from_service_account_file(
            Config.GOOGLE_SHEETS_CREDENTIALS_FILE,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        service = build('sheets', 'v4', credentials=credentials)
        
        # Получаем заголовки
        headers = DataFormatter.get_sheet_headers()
        
        # Очищаем существующие данные (если есть)
        try:
            service.spreadsheets().values().clear(
                spreadsheetId=Config.SPREADSHEET_ID,
                range=f"{Config.SHEET_NAME}!A:Z"
            ).execute()
            logger.info("Существующие данные очищены")
        except HttpError:
            pass
        
        # Добавляем заголовки
        body = {
            'values': [headers]
        }
        
        result = service.spreadsheets().values().update(
            spreadsheetId=Config.SPREADSHEET_ID,
            range=f"{Config.SHEET_NAME}!A1",
            valueInputOption='RAW',
            body=body
        ).execute()
        
        logger.info(f"Заголовки успешно добавлены: {result.get('updatedCells', 0)} ячеек")
        
        # Форматируем заголовки (делаем их жирными)
        requests = [
            {
                'repeatCell': {
                    'range': {
                        'sheetId': 0,  # ID первого листа
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 0,
                        'endColumnIndex': len(headers)
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {
                                'bold': True
                            },
                            'backgroundColor': {
                                'red': 0.9,
                                'green': 0.9,
                                'blue': 0.9
                            }
                        }
                    },
                    'fields': 'userEnteredFormat.textFormat.bold,userEnteredFormat.backgroundColor'
                }
            }
        ]
        
        service.spreadsheets().batchUpdate(
            spreadsheetId=Config.SPREADSHEET_ID,
            body={'requests': requests}
        ).execute()
        
        logger.info("Заголовки отформатированы")
        
        print("✅ Google Sheets успешно настроена!")
        print(f"📊 Таблица: {Config.SPREADSHEET_ID}")
        print(f"📋 Лист: {Config.SHEET_NAME}")
        print(f"📝 Количество колонок: {len(headers)}")
        
    except FileNotFoundError:
        print("❌ Файл service-account-key.json не найден!")
        print("📝 Создайте сервисный аккаунт Google и скачайте ключ")
    except HttpError as e:
        print(f"❌ Ошибка Google Sheets API: {e}")
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")

if __name__ == "__main__":
    # Проверяем конфигурацию
    try:
        Config.validate()
        asyncio.run(setup_google_sheets())
    except ValueError as e:
        print(f"❌ Ошибка конфигурации: {e}")
        print("📝 Проверьте файл .env")





