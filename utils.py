import json
import base64
import urllib.parse
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import Config

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class UTMProcessor:
    """Класс для обработки UTM-параметров из start payload"""
    
    @staticmethod
    def parse_start_payload(payload: str) -> Dict[str, str]:
        """Парсит start payload и извлекает UTM-параметры"""
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

class GoogleSheetsManager:
    """Класс для работы с Google Sheets API с retry логикой"""
    
    def __init__(self):
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Инициализирует Google Sheets API сервис"""
        try:
            credentials = Credentials.from_service_account_file(
                Config.GOOGLE_SHEETS_CREDENTIALS_FILE,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            self.service = build('sheets', 'v4', credentials=credentials)
            logger.info("Google Sheets API сервис инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации Google Sheets API: {e}")
            raise
    
    async def append_row(self, data: list) -> bool:
        """Добавляет строку в Google Sheets с retry логикой"""
        for attempt in range(Config.MAX_RETRIES):
            try:
                body = {
                    'values': [data]
                }
                
                result = self.service.spreadsheets().values().append(
                    spreadsheetId=Config.SPREADSHEET_ID,
                    range=f"{Config.SHEET_NAME}!A:Z",
                    valueInputOption='RAW',
                    insertDataOption='INSERT_ROWS',
                    body=body
                ).execute()
                
                logger.info(f"Данные успешно добавлены в Google Sheets: {result.get('updates', {}).get('updatedRows', 0)} строк")
                return True
                
            except HttpError as e:
                logger.warning(f"Попытка {attempt + 1}/{Config.MAX_RETRIES} не удалась: {e}")
                if attempt < Config.MAX_RETRIES - 1:
                    await asyncio.sleep(Config.RETRY_DELAY * (2 ** attempt))  # Exponential backoff
                else:
                    logger.error(f"Не удалось добавить данные в Google Sheets после {Config.MAX_RETRIES} попыток")
                    return False
            except Exception as e:
                logger.error(f"Неожиданная ошибка при работе с Google Sheets: {e}")
                return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Получает статистику из Google Sheets"""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=Config.SPREADSHEET_ID,
                range=f"{Config.SHEET_NAME}!A:Z"
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return {'total_leads': 0, 'today_leads': 0}
            
            # Подсчитываем общее количество лидов (исключая заголовок)
            total_leads = len(values) - 1 if len(values) > 1 else 0
            
            # Подсчитываем лиды за сегодня
            today = datetime.now().strftime('%Y-%m-%d')
            today_leads = 0
            
            for row in values[1:]:  # Пропускаем заголовок
                if len(row) > 2:  # Проверяем, что есть поле с датой
                    try:
                        row_date = datetime.fromisoformat(row[2].split()[0]).strftime('%Y-%m-%d')
                        if row_date == today:
                            today_leads += 1
                    except (ValueError, IndexError):
                        continue
            
            return {
                'total_leads': total_leads,
                'today_leads': today_leads
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            return {'total_leads': 0, 'today_leads': 0}

class DataFormatter:
    """Класс для форматирования данных для Google Sheets"""
    
    @staticmethod
    def format_lead_data(lead_id: str, user_id: int, username: str, answers: Dict[str, str], 
                        utm_data: Dict[str, str], tg_start: str, tg_complete: str) -> list:
        """Форматирует данные лида для записи в Google Sheets"""
        # Создаем список с данными в правильном порядке
        row_data = [
            lead_id,                    # Lead ID
            user_id,                    # User ID
            username or '',             # Username
            tg_start,                   # TG Start
            tg_complete,                # TG Complete
        ]
        
        # Добавляем ответы на вопросы анкеты
        survey_config = Config.load_survey()
        for step in survey_config['steps']:
            step_id = step['id']
            answer = answers.get(step_id, '')
            row_data.append(answer)
        
        # Добавляем UTM-параметры
        utm_fields = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content']
        for field in utm_fields:
            row_data.append(utm_data.get(field, ''))
        
        return row_data
    
    @staticmethod
    def get_sheet_headers() -> list:
        """Возвращает заголовки для Google Sheets"""
        survey_config = Config.load_survey()
        
        headers = [
            'Lead ID',
            'User ID', 
            'Username',
            'TG Start',
            'TG Complete'
        ]
        
        # Добавляем заголовки для вопросов анкеты
        for step in survey_config['steps']:
            headers.append(f"Answer: {step['id']}")
        
        # Добавляем заголовки для UTM-параметров
        utm_headers = ['UTM Source', 'UTM Medium', 'UTM Campaign', 'UTM Term', 'UTM Content']
        headers.extend(utm_headers)
        
        return headers

