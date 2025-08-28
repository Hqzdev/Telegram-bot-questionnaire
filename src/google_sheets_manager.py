#!/usr/bin/env python3
"""
Менеджер для работы с Google Sheets API
"""

import asyncio
import logging
from typing import Dict, Any, List
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import Config

logger = logging.getLogger(__name__)

class GoogleSheetsManager:
    """Класс для работы с Google Sheets API"""
    
    def __init__(self):
        self.service = None
        self.enabled = False
        self._initialize_service()
    
    def _initialize_service(self):
        """Инициализирует Google Sheets API сервис"""
        try:
            # Получаем учетные данные
            credentials_data = Config.get_google_credentials()
            
            # Создаем credentials объект
            credentials = Credentials.from_service_account_info(
                credentials_data,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            
            # Создаем сервис
            self.service = build('sheets', 'v4', credentials=credentials)
            self.enabled = True
            
            logger.info("Google Sheets API сервис инициализирован успешно")
            
        except Exception as e:
            logger.warning(f"Ошибка инициализации Google Sheets API: {e}. Google Sheets отключен.")
            self.enabled = False
    
    async def save_lead(self, data: Dict[str, Any]) -> bool:
        """Сохраняет данные лида в Google Sheets"""
        if not self.enabled:
            logger.warning("Google Sheets отключен. Данные не будут сохранены.")
            return False
        
        try:
            # Проверяем, что SHEET_ID настроен
            if not Config.SHEET_ID:
                logger.error("SHEET_ID не настроен в конфигурации")
                return False
                
            # Форматируем данные для записи
            row_data = self._format_lead_data(data)
            logger.info(f"Подготовлены данные для записи: {len(row_data)} полей")
            
            # Добавляем строку в таблицу
            body = {
                'values': [row_data]
            }
            
            logger.info(f"Отправляем запрос к Google Sheets API...")
            result = self.service.spreadsheets().values().append(
                spreadsheetId=Config.SHEET_ID,
                range='A:Z',  # Добавляем в конец таблицы
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            updated_rows = result.get('updates', {}).get('updatedRows', 0)
            logger.info(f"Данные успешно сохранены в Google Sheets: {updated_rows} строк")
            return True
            
        except HttpError as e:
            logger.error(f"Ошибка Google Sheets API: {e}")
            logger.error(f"HTTP статус: {e.resp.status}")
            logger.error(f"Детали ошибки: {e.error_details}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при сохранении в Google Sheets: {e}")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            return False
    
    def _format_lead_data(self, data: Dict[str, Any]) -> List[Any]:
        """Форматирует данные лида для записи в Google Sheets"""
        # Базовые данные
        row_data = [
            data.get('lead_id', ''),           # Lead ID
            data.get('user_id', ''),           # User ID
            data.get('username', ''),          # Username
            data.get('tg_start', ''),          # TG Start
            data.get('tg_complete', ''),       # TG Complete
        ]
        
        # Ответы на вопросы (в порядке из конфигурации)
        answers = data.get('answers', {})
        for question in self._get_question_order():
            answer = answers.get(question, 'Не указано')
            if isinstance(answer, list):
                answer = ', '.join(answer)
            row_data.append(answer)
        
        # UTM-параметры
        utm_data = data.get('utm_data', {})
        utm_fields = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content']
        for field in utm_fields:
            row_data.append(utm_data.get(field, ''))
        
        return row_data
    
    def _get_question_order(self) -> List[str]:
        """Возвращает порядок вопросов для правильного форматирования данных"""
        # Этот метод должен возвращать порядок вопросов в том же порядке,
        # что и в конфигурации анкеты в main.py
        return [
            'platforms',
            'work_type',
            'volume_fbs',
            'volume_fbo',
            'main_concern',
            'frequency',
            'losses',
            'reasons',
            'urgency',
            'price'
        ]
    
    async def setup_headers(self) -> bool:
        """Настраивает заголовки в Google Sheets"""
        if not self.enabled:
            logger.warning("Google Sheets отключен. Заголовки не будут настроены.")
            return False
        
        try:
            # Заголовки для таблицы
            headers = [
                'Lead ID',
                'User ID',
                'Username', 
                'TG Start',
                'TG Complete',
                'Где продаёте',
                'Как работаете',
                'FBS заказы в месяц',
                'FBO/FBW поставки в месяц',
                'Главная проблема',
                'Частота проблем',
                'Потери за 30 дней',
                'Причины проблем',
                'Срочность',
                'Ценник',
                'UTM Source',
                'UTM Medium',
                'UTM Campaign',
                'UTM Term',
                'UTM Content'
            ]
            
            # Очищаем существующие данные
            self.service.spreadsheets().values().clear(
                spreadsheetId=Config.SHEET_ID,
                range='A:Z'
            ).execute()
            
            # Добавляем заголовки
            body = {
                'values': [headers]
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=Config.SHEET_ID,
                range='A1',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            # Форматируем заголовки (делаем их жирными)
            requests = [
                {
                    'repeatCell': {
                        'range': {
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
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=Config.SHEET_ID,
                body={'requests': requests}
            ).execute()
            
            logger.info(f"Заголовки успешно настроены: {result.get('updatedCells', 0)} ячеек")
            return True
            
        except HttpError as e:
            logger.error(f"Ошибка при настройке заголовков: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при настройке заголовков: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, int]:
        """Получает статистику лидов"""
        if not self.enabled:
            return {'total_leads': 0, 'today_leads': 0}
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=Config.SHEET_ID,
                range='A:Z'
            ).execute()
            
            values = result.get('values', [])
            if len(values) <= 1:  # Только заголовки
                return {'total_leads': 0, 'today_leads': 0}
            
            # Подсчитываем общее количество лидов (исключая заголовок)
            total_leads = len(values) - 1
            
            # Подсчитываем лиды за сегодня
            from datetime import datetime
            today = datetime.now().strftime('%Y-%m-%d')
            today_leads = 0
            
            for row in values[1:]:  # Пропускаем заголовок
                if len(row) > 4:  # Проверяем, что есть поле с датой завершения
                    try:
                        row_date = datetime.fromisoformat(row[4].split()[0]).strftime('%Y-%m-%d')
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

