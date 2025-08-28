#!/usr/bin/env python3
"""
Демо-калькулятор уведомлений для Telegram Bot
Только демо-уведомления FBS и FBO с интерактивными кнопками
"""

import asyncio
import aiosqlite
import secrets
import string
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from dotenv import load_dotenv
import os

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
db_path = "demo_bot.db"

# Инициализация бота
bot = Bot(BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# Инициализация базы данных
async def init_db():
    """Инициализация базы данных для демо-уведомлений"""
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, event TEXT, payload TEXT, ts TEXT
        )""")
        await db.commit()

async def log_event(user_id: int, event: str, payload: str = ""):
    """Логирование событий в базу данных"""
    async with aiosqlite.connect(db_path) as db:
        await db.execute("INSERT INTO events(user_id,event,payload,ts) VALUES(?,?,?,?)",
                         (user_id, event, payload, datetime.utcnow().isoformat()))
        await db.commit()

def kb_fbs_demo():
    """Клавиатура для FBS демо-уведомления"""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Отложить 15 мин", callback_data="demo:fbs:snooze15"),
        InlineKeyboardButton(text="Готово ✅", callback_data="demo:fbs:done")
    ],[
        InlineKeyboardButton(text="Сводка /summary", callback_data="demo:summary")
    ]])

def kb_fbo_demo():
    """Клавиатура для FBO демо-уведомления"""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Изменить слот", callback_data="demo:fbo:slot"),
        InlineKeyboardButton(text="Напомнить утром", callback_data="demo:fbo:morning")
    ],[
        InlineKeyboardButton(text="Сводка /summary", callback_data="demo:summary")
    ]])

async def send_demo_notifications(msg: Message):
    """Отправка демо-уведомлений"""
    await msg.answer(
        "🔔 Заказ #308132 — дедлайн через 1 ч 20 мин\n"
        "FBS · ПВЗ: Москва, Ленина 10 · приоритет: важно\n\n"
        "Что сделать:\n— Проверьте сборку и маркировку\n— Подтвердите курьера/самовывоз\n— Не откладывайте: после дедлайна рейтинг и отмены",
        reply_markup=kb_fbs_demo()
    )
    await msg.answer(
        "⏰ Поставка FBO — до «красной зоны» 24 ч\n"
        "Риск удержания: min(5 ₽ × ед., 25 000 ₽)\n\n"
        "Что сделать:\n— Уточните слот (переносите не позднее, чем за 72 ч)\n— Проверьте упаковку, габариты и паллеты\n— Назначьте ответственного",
        reply_markup=kb_fbo_demo()
    )

async def remind_later(chat_id: int, minutes: int):
    """Напоминание через указанное количество минут"""
    await asyncio.sleep(minutes * 60)
    await bot.send_message(chat_id, f"🔔 Демо-напоминание: прошло {minutes} мин.")

# Обработчики команд
@dp.message(CommandStart())
async def cmd_start(msg: Message):
    """Обработчик команды /start"""
    await msg.answer(
        "🎯 Демо-калькулятор уведомлений\n\n"
        "Этот бот показывает, как будут выглядеть уведомления о дедлайнах FBS и штрафах FBO.\n\n"
        "Нажмите /demo чтобы увидеть демо-уведомления"
    )

@dp.message(Command("demo"))
async def demo(msg: Message):
    """Показать демо-уведомления"""
    await send_demo_notifications(msg)

@dp.message(Command("help"))
async def help_cmd(msg: Message):
    """Справка"""
    await msg.answer(
        "📋 Команды бота:\n\n"
        "/start - Начать работу\n"
        "/demo - Показать демо-уведомления\n"
        "/help - Эта справка\n\n"
        "Демо-уведомления показывают:\n"
        "• FBS - уведомления о дедлайнах заказов\n"
        "• FBO - предупреждения о штрафах поставок"
    )

# Обработчики демо-кнопок
@dp.callback_query(F.data.startswith("demo:"))
async def handle_demo_buttons(callback: CallbackQuery):
    """Обработчик демо-кнопок"""
    await log_event(callback.from_user.id, "demo_click", callback.data)
    
    if callback.data == "demo:fbs:snooze15":
        await callback.answer("Ок, напомню через 15 минут (демо).")
        # В демо можно реально напомнить:
        asyncio.create_task(remind_later(callback.message.chat.id, 15))
    elif callback.data == "demo:fbs:done":
        await callback.answer("Отмечено как выполнено (демо).")
    elif callback.data == "demo:fbo:slot":
        await callback.answer("Ок, открою подсказки по переносу слота (демо).")
    elif callback.data == "demo:fbo:morning":
        await callback.answer("Напомню утром (демо).")
    elif callback.data == "demo:summary":
        await callback.message.answer("📊 Сводка (демо): спасено заказов: 7 · избегнуто удержаний: 1")
        await callback.answer()

# Обработчик неизвестных сообщений
@dp.message()
async def handle_unknown(message: Message):
    """Обработчик неизвестных сообщений"""
    await message.answer("👋 Нажмите /start чтобы начать или /demo чтобы увидеть уведомления.")

async def main():
    """Основная функция запуска бота"""
    print("🎯 Демо-калькулятор уведомлений запускается...")
    
    try:
        # Инициализируем базу данных
        await init_db()
        print("✅ База данных инициализирована")
        
        # Запускаем бота
        print("🚀 Бот запущен и готов к работе!")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("⏹ Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())

