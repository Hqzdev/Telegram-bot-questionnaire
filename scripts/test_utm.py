#!/usr/bin/env python3
"""
Скрипт для тестирования генерации UTM-параметров
Помогает создать правильные ссылки для бота с UTM-трекингом
"""

import base64
import json
import urllib.parse

def generate_utm_links(bot_username: str, utm_data: dict) -> dict:
    """
    Генерирует ссылки с UTM-параметрами в разных форматах
    
    Args:
        bot_username: Username бота без @
        utm_data: Словарь с UTM-параметрами
    
    Returns:
        Словарь с ссылками в разных форматах
    """
    
    # URL-encoded формат
    utm_params = urllib.parse.urlencode(utm_data)
    url_encoded_link = f"https://t.me/{bot_username}?start={utm_params}"
    
    # Base64 JSON формат
    json_data = json.dumps(utm_data, ensure_ascii=False)
    base64_payload = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
    base64_link = f"https://t.me/{bot_username}?start={base64_payload}"
    
    return {
        'url_encoded': url_encoded_link,
        'base64_json': base64_link,
        'utm_params': utm_params,
        'base64_payload': base64_payload
    }

def main():
    """Основная функция для демонстрации"""
    
    print("🔗 Генератор UTM-ссылок для Telegram бота\n")
    
    # Примеры UTM-данных
    examples = [
        {
            'name': 'Google Ads',
            'data': {
                'utm_source': 'google',
                'utm_medium': 'cpc',
                'utm_campaign': 'summer_sale',
                'utm_term': 'курсы программирования',
                'utm_content': 'banner_1'
            }
        },
        {
            'name': 'Facebook Ads',
            'data': {
                'utm_source': 'facebook',
                'utm_medium': 'social',
                'utm_campaign': 'winter_promo',
                'utm_content': 'video_ad'
            }
        },
        {
            'name': 'Email рассылка',
            'data': {
                'utm_source': 'email',
                'utm_medium': 'email',
                'utm_campaign': 'newsletter_jan',
                'utm_content': 'main_cta'
            }
        }
    ]
    
    bot_username = input("Введите username бота (без @): ").strip()
    if not bot_username:
        bot_username = "your_bot_username"
        print(f"Используется пример: {bot_username}")
    
    print(f"\n📊 Сгенерированные ссылки для бота @{bot_username}:\n")
    
    for example in examples:
        print(f"🎯 {example['name']}:")
        links = generate_utm_links(bot_username, example['data'])
        
        print(f"   📝 UTM параметры: {links['utm_params']}")
        print(f"   🔗 URL-encoded: {links['url_encoded']}")
        print(f"   🔗 Base64 JSON: {links['base64_json']}")
        print()
    
    # Интерактивный режим
    print("🛠 Интерактивный режим:")
    print("Введите UTM-параметры (пустая строка для выхода):")
    
    while True:
        source = input("\nutm_source: ").strip()
        if not source:
            break
            
        medium = input("utm_medium: ").strip()
        campaign = input("utm_campaign: ").strip()
        term = input("utm_term (опционально): ").strip()
        content = input("utm_content (опционально): ").strip()
        
        utm_data = {
            'utm_source': source,
            'utm_medium': medium,
            'utm_campaign': campaign
        }
        
        if term:
            utm_data['utm_term'] = term
        if content:
            utm_data['utm_content'] = content
        
        links = generate_utm_links(bot_username, utm_data)
        
        print(f"\n✅ Сгенерированные ссылки:")
        print(f"🔗 URL-encoded: {links['url_encoded']}")
        print(f"🔗 Base64 JSON: {links['base64_json']}")
        print()

if __name__ == "__main__":
    main()





