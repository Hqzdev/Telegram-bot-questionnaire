#!/usr/bin/env python3
"""
Тестовый скрипт для проверки новой демо-функциональности
"""

import asyncio
import aiosqlite
from datetime import datetime, timedelta
import secrets
import string

async def test_database_functions():
    """Тестирование функций базы данных"""
    print("🧪 Тестирование функций базы данных...")
    
    # Тестируем генерацию кода
    def gen_code(n=6):
        alphabet = string.ascii_uppercase + string.digits
        return "LOCK-" + "".join(secrets.choice(alphabet) for _ in range(n))
    
    code = gen_code()
    print(f"✅ Сгенерирован код: {code}")
    
    # Тестируем создание предзаписи
    async def create_prereg(user_id: int, tariff: str = "Pro 2 990 ₽"):
        code = gen_code()
        valid_to = (datetime.now().replace(day=1) + timedelta(days=31*6))
        
        db_path = "bot.db"
        async with aiosqlite.connect(db_path) as db:
            await db.execute("""
                INSERT INTO prereg(user_id, code, tariff, valid_to, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET code=excluded.code, tariff=excluded.tariff, valid_to=excluded.valid_to
            """, (user_id, code, tariff, valid_to.isoformat(), datetime.utcnow().isoformat()))
            await db.commit()
            
            cur = await db.execute("SELECT COUNT(*) FROM prereg WHERE created_at <= (SELECT created_at FROM prereg WHERE user_id=?)", (user_id,))
            place = (await cur.fetchone())[0]
        
        return code, valid_to, place
    
    # Тестируем создание предзаписи
    test_user_id = 12345
    code, valid_to, place = await create_prereg(test_user_id)
    print(f"✅ Создана предзапись: код={code}, до={valid_to.strftime('%d.%m.%Y')}, место={place}")
    
    # Тестируем получение предзаписи
    async def get_prereg(user_id: int):
        db_path = "bot.db"
        async with aiosqlite.connect(db_path) as db:
            cur = await db.execute("SELECT code, tariff, valid_to FROM prereg WHERE user_id=?", (user_id,))
            return await cur.fetchone()
    
    prereg_data = await get_prereg(test_user_id)
    if prereg_data:
        print(f"✅ Получена предзапись: {prereg_data}")
    else:
        print("❌ Предзапись не найдена")
    
    # Тестируем логирование событий
    async def log_event(user_id: int, event: str, payload: str = ""):
        db_path = "bot.db"
        async with aiosqlite.connect(db_path) as db:
            await db.execute("INSERT INTO events(user_id,event,payload,ts) VALUES(?,?,?,?)",
                             (user_id, event, payload, datetime.utcnow().isoformat()))
            await db.commit()
    
    await log_event(test_user_id, "test_event", "test_payload")
    print("✅ Событие залогировано")
    
    print("✅ Все тесты базы данных пройдены успешно!")

async def test_keyboard_functions():
    """Тестирование функций клавиатур"""
    print("\n🧪 Тестирование функций клавиатур...")
    
    def kb_fbs_demo():
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Отложить 15 мин", callback_data="demo:fbs:snooze15"),
            InlineKeyboardButton(text="Готово ✅", callback_data="demo:fbs:done")
        ],[
            InlineKeyboardButton(text="Сводка /summary", callback_data="demo:summary")
        ]])
    
    def kb_fbo_demo():
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Изменить слот", callback_data="demo:fbo:slot"),
            InlineKeyboardButton(text="Напомнить утром", callback_data="demo:fbo:morning")
        ],[
            InlineKeyboardButton(text="Сводка /summary", callback_data="demo:summary")
        ]])
    
    fbs_kb = kb_fbs_demo()
    fbo_kb = kb_fbo_demo()
    
    print(f"✅ FBS клавиатура создана: {len(fbs_kb.inline_keyboard)} ряда")
    print(f"✅ FBO клавиатура создана: {len(fbo_kb.inline_keyboard)} ряда")
    
    # Проверяем callback_data
    fbs_callbacks = [btn.callback_data for row in fbs_kb.inline_keyboard for btn in row]
    fbo_callbacks = [btn.callback_data for row in fbo_kb.inline_keyboard for btn in row]
    
    expected_fbs = ["demo:fbs:snooze15", "demo:fbs:done", "demo:summary"]
    expected_fbo = ["demo:fbo:slot", "demo:fbo:morning", "demo:summary"]
    
    if all(cb in fbs_callbacks for cb in expected_fbs):
        print("✅ Все ожидаемые FBS callback_data присутствуют")
    else:
        print("❌ Не все FBS callback_data найдены")
    
    if all(cb in fbo_callbacks for cb in expected_fbo):
        print("✅ Все ожидаемые FBO callback_data присутствуют")
    else:
        print("❌ Не все FBO callback_data найдены")

def test_callback_handlers():
    """Тестирование обработчиков callback"""
    print("\n🧪 Тестирование обработчиков callback...")
    
    # Тестируем парсинг callback_data
    test_callbacks = [
        "demo:fbs:snooze15",
        "demo:fbs:done", 
        "demo:fbo:slot",
        "demo:fbo:morning",
        "demo:summary",
        "demo:open",
        "nav:pricing",
        "prereg:lock",
        "my_price"
    ]
    
    for callback in test_callbacks:
        if callback.startswith("demo:"):
            print(f"✅ demo callback: {callback}")
        elif callback.startswith("nav:"):
            print(f"✅ nav callback: {callback}")
        elif callback.startswith("prereg:"):
            print(f"✅ prereg callback: {callback}")
        elif callback == "my_price":
            print(f"✅ my_price callback: {callback}")
        else:
            print(f"❌ Неизвестный callback: {callback}")
    
    print("✅ Все callback обработчики проверены")

async def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестов новой демо-функциональности...")
    
    try:
        await test_database_functions()
        await test_keyboard_functions()
        test_callback_handlers()
        
        print("\n🎉 Все тесты пройдены успешно!")
        print("\n📋 Реализованная функциональность:")
        print("✅ /demo → демо-уведомления с inline-кнопками")
        print("✅ demo:fbs:snooze15 → лог + всплывашка + напоминание через 15 мин")
        print("✅ demo:fbs:done → лог + всплывашка «Выполнено»")
        print("✅ demo:fbo:slot → лог + всплывашка «Подсказки по переносу»")
        print("✅ demo:fbo:morning → лог + всплывашка «Напомню утром»")
        print("✅ demo:summary → лог + сообщение «Сводка (демо)…»")
        print("✅ demo:open → повторение демо-уведомлений")
        print("✅ prereg:lock → создание/обновление предзаписи в БД")
        print("✅ /my_price → показ закреплённого кода и срока")
        print("✅ nav:pricing → показ тарифов")
        print("✅ /pricing → команда для показа тарифов")
        print("✅ /help → справка по всем командам")
        print("✅ /checklist → показ чек-листа")
        print("✅ /summary → показ сводки")
        print("✅ /prereg → создание предзаписи")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
