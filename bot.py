import os

# --- БЕЗОПАСНАЯ КОНФИГУРАЦИЯ ---
# Данные берутся из переменных окружения (на хостинге Bothost).
# Если переменных нет (локальный запуск), используются значения по умолчанию (из кавычек).

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN_HERE")  # <-- Удалили реальный токен
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "0"))       # <-- Удалили ID канала
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))           # <-- Удалили ваш ID

# -------------------------------
import os
import os
import os
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler


WAITING_FOR_POST_TEXT = 1
WAITING_FOR_POST_PHOTO = 2
WAITING_FOR_LINK_URL = 4
WAITING_FOR_LINK_EXPIRY = 5
EDITING_LINK_NAME = 6

class LinkManager:
    def __init__(self):
        self.file = "referral_links.json"
        self.links = self.load()

    def load(self):
        if Path(self.file).exists():
            try:
                with open(self.file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return self.default()
        return self.default()

    def default(self):
        return {
            "tour": {"name": "🎯 Подобрать тур", "url": "https://t.me/your_username", "expires_at": (datetime.now() + timedelta(days=365)).isoformat(), "active": True},
            "tours": {"name": "🎭 Экскурсии", "url": "https://www.tripadvisor.com/?aid=YOUR_ID", "expires_at": (datetime.now() + timedelta(days=365)).isoformat(), "active": True},
            "flights": {"name": "✈️ Авиабилеты", "url": "https://www.aviasales.com/?marker=YOUR_MARKER", "expires_at": (datetime.now() + timedelta(days=365)).isoformat(), "active": True}
        }

    def save(self):
        with open(self.file, 'w', encoding='utf-8') as f:
            json.dump(self.links, f, ensure_ascii=False, indent=2)

    def update_link(self, key, name, url, days):
        self.links[key] = {"name": name, "url": url, "expires_at": (datetime.now() + timedelta(days=days)).isoformat(), "active": True}
        self.save()

    def get_buttons(self):
        buttons = []
        for key, link in self.links.items():
            if link['active']:
                exp = datetime.fromisoformat(link['expires_at'])
                if exp > datetime.now():
                    buttons.append([InlineKeyboardButton(text=link['name'], url=link['url'])])
        return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None

    def status(self):
        msg = "📊 СТАТУС ССЫЛОК:\n\n"
        for key, link in self.links.items():
            exp = datetime.fromisoformat(link['expires_at'])
            days = (exp - datetime.now()).days
            emoji = "✅" if days > 3 else "⚠️" if days > 0 else "❌"
            msg += f"{emoji} {link['name']}\n   {days} дн. | {link['expires_at'][:10]}\n\n"
        return msg

mgr = LinkManager()

def menu():
    return ReplyKeyboardMarkup([[KeyboardButton("📝 Пост")], [KeyboardButton("🔗 Ссылки")], [KeyboardButton("📊 Статус")], [KeyboardButton("❓ Помощь")]], resize_keyboard=True)

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Добро пожаловать! Выберите действие:", reply_markup=menu())

async def post_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 Напишите текст поста:", reply_markup=ReplyKeyboardRemove())
    return WAITING_FOR_POST_TEXT

async def post_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['text'] = update.message.text
    await update.message.reply_text("📸 Отправьте фото для поста")
    return WAITING_FOR_POST_PHOTO

async def post_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        text = ctx.user_data['text']
        buttons = mgr.get_buttons()

        if update.message.photo:
            await ctx.bot.send_photo(CHANNEL_ID, update.message.photo[-1].file_id, caption=text, reply_markup=buttons)
            await update.message.reply_text("✅ Пост опубликован!", reply_markup=menu())
            return ConversationHandler.END
        elif update.message.text and 'пропустить' in update.message.text.lower():
            await ctx.bot.send_message(CHANNEL_ID, text, reply_markup=buttons)
            await update.message.reply_text("✅ Пост опубликован!", reply_markup=menu())
            return ConversationHandler.END
        else:
            skip_buttons = ReplyKeyboardMarkup([[KeyboardButton("⏭️ Пропустить")]], resize_keyboard=True)
            await update.message.reply_text("📸 Отправьте фото или нажмите 'Пропустить':", reply_markup=skip_buttons)
            return WAITING_FOR_POST_PHOTO

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}", reply_markup=menu())
        return ConversationHandler.END

async def links_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Доступ запрещён")
        return

    kb = ReplyKeyboardMarkup([[KeyboardButton("🎯 Тур")], [KeyboardButton("🎭 Экскурсии")], [KeyboardButton("✈️ Авиабилеты")], [KeyboardButton("← Назад")]], resize_keyboard=True)
    await update.message.reply_text("🔗 Выберите ссылку:", reply_markup=kb)
    return EDITING_LINK_NAME

async def link_edit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "← Назад":
        await update.message.reply_text("Главное меню:", reply_markup=menu())
        return ConversationHandler.END

    map_dict = {"🎯 Тур": "tour", "🎭 Экскурсии": "tours", "✈️ Авиабилеты": "flights"}
    key = map_dict.get(text)

    if not key:
        await update.message.reply_text("Выберите из списка")
        return EDITING_LINK_NAME

    ctx.user_data['key'] = key
    link = mgr.links[key]
    await update.message.reply_text(f"📝 {link['name']}\nТекущая: {link['url']}\nВведите новую ссылку:", reply_markup=ReplyKeyboardRemove())
    return WAITING_FOR_LINK_URL

async def link_url(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['url'] = update.message.text
    key = ctx.user_data['key']

    # Если это "tour" - сразу сохраняем (не запрашиваем дни)
    if key == "tour":
        link = mgr.links[key]
        mgr.update_link(key, link['name'], update.message.text, 365)
        await update.message.reply_text(f"✅ {link['name']}\nОбновлена!", reply_markup=menu())
        return ConversationHandler.END

    # Для остальных ссылок запрашиваем дни
    await update.message.reply_text("📅 На сколько дней? (например: 30, 90, 365)")
    return WAITING_FOR_LINK_EXPIRY

async def link_days(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        days = int(update.message.text)
        key = ctx.user_data['key']
        url = ctx.user_data['url']
        link = mgr.links[key]
        mgr.update_link(key, link['name'], url, days)
        await update.message.reply_text(f"✅ {link['name']}\nОбновлена на {days} дней!", reply_markup=menu())
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ Введите число")
        return WAITING_FOR_LINK_EXPIRY

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📝 Пост":
        return await post_start(update, ctx)
    elif text == "🔗 Ссылки":
        return await links_start(update, ctx)
    elif text == "📊 Статус":
        await update.message.reply_text(mgr.status(), reply_markup=menu())
    elif text == "❓ Помощь":
        await update.message.reply_text("📝 Пост - опубликовать\n🔗 Ссылки - менять\n📊 Статус - проверить", reply_markup=menu())

async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    post_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("📝 Пост"), post_start)],
        states={
            WAITING_FOR_POST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_text)],
            WAITING_FOR_POST_PHOTO: [MessageHandler(filters.PHOTO | filters.TEXT, post_photo)]
        },
        fallbacks=[CommandHandler("start", start)]
    )

    link_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("🔗 Ссылки"), links_start)],
        states={
            EDITING_LINK_NAME: [MessageHandler(filters.TEXT, link_edit)],
            WAITING_FOR_LINK_URL: [MessageHandler(filters.TEXT, link_url)],
            WAITING_FOR_LINK_EXPIRY: [MessageHandler(filters.TEXT, link_days)]
        },
        fallbacks=[CommandHandler("start", start)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(post_conv)
    app.add_handler(link_conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🤖 Бот запущен и слушает...")

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    stop_event = asyncio.Event()

    def signal_handler(sig, frame):
        stop_event.set()

    import signal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await stop_event.wait()
    except KeyboardInterrupt:
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
