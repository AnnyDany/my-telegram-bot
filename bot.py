import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InputMediaPhoto, InputMediaVideo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, ConversationHandler
from telegram.error import BadRequest

BOT_TOKEN = "7044465296:AAF37DIq7S70h4YA4_q8-XuEg0D3WY2pUTc"  # ← ВСТАВЬТЕ ВАШ ТОКЕН
CHANNEL_ID = -1003385501617  # ← ВСТАВЬТЕ ID ВАШЕГО КАНАЛА
ADMIN_ID = 398545467  # ← ВСТАВЬТЕ ВАШ ID (от @userinfobot)

WAITING_FOR_POST_TEXT = 1
WAITING_FOR_POST_PHOTO = 2
WAITING_FOR_LINK_URL = 4
WAITING_FOR_LINK_EXPIRY = 5
EDITING_LINK_NAME = 6
WAITING_FOR_DISCLAIMER = 7
WAITING_FOR_LIMIT_ACTION = 8

NO_BUTTON_MARK = '#'
ARROWS_LINE = '⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️'

class LinkManager:
    def __init__(self):
        self.file = "referral_links.json"
        self.links = self.load()

    def load(self):
        if Path(self.file).exists():
            try:
                with open(self.file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'disclaimer' not in data:
                        data['disclaimer'] = "ᴿᵉᵏˡᵃᵐᵃ"
                    return data
            except:
                return self.default()
        return self.default()

    def default(self):
        return {
            "disclaimer": "ᴿᵉᵏˡᵃᵐᵃ",
            "links": {
                "tour": {"name": "🎯 Подобрать тур", "url": "https://t.me/your_username", "expires_at": (datetime.now() + timedelta(days=365)).isoformat(), "active": True},
                "tours": {"name": "🎭 Экскурсии", "url": "https://www.tripadvisor.com/?aid=YOUR_ID", "expires_at": (datetime.now() + timedelta(days=365)).isoformat(), "active": True},
                "flights": {"name": "✈️ Авиабилеты", "url": "https://www.aviasales.com/?marker=YOUR_MARKER", "expires_at": (datetime.now() + timedelta(days=365)).isoformat(), "active": True}
            }
        }

    def save(self):
        with open(self.file, 'w', encoding='utf-8') as f:
            json.dump({"disclaimer": self.links.get('disclaimer', 'ᴿᵉᵏˡᵃᵐᵃ'), "links": {k: v for k, v in self.links.items() if k != 'disclaimer'}}, f, ensure_ascii=False, indent=2)

    def update_link(self, key, name, url, days):
        self.links[key] = {"name": name, "url": url, "expires_at": (datetime.now() + timedelta(days=days)).isoformat(), "active": True}
        self.save()

    def update_disclaimer(self, text):
        self.links['disclaimer'] = text
        self.save()

    def get_disclaimer(self):
        return self.links.get('disclaimer', 'ᴿᵉᵏˡᵃᵐᵃ')

    def get_buttons(self):
        buttons = []
        for key, link in self.links.items():
            if key == 'disclaimer':
                continue
            if link.get('active'):
                exp = datetime.fromisoformat(link['expires_at'])
                if exp > datetime.now():
                    buttons.append([InlineKeyboardButton(text=link['name'], url=link['url'])])
        disclaimer_text = self.get_disclaimer()
        buttons.append([InlineKeyboardButton(text=disclaimer_text, callback_data="show_disclaimer")])
        return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None

    def status(self):
        msg = "📊 СТАТУС ССЫЛОК:\n\n"
        for key, link in self.links.items():
            if key == 'disclaimer':
                continue
            if key == "tour":
                msg += f"✅ {link['name']}\n   Без срока\n\n"
                continue
            exp = datetime.fromisoformat(link['expires_at'])
            days = (exp - datetime.now()).days
            emoji = "✅" if days > 3 else "⚠️" if days > 0 else "❌"
            msg += f"{emoji} {link['name']}\n   {days} дн. | {link['expires_at'][:10]}\n\n"
        return msg

mgr = LinkManager()

saved_data = mgr.load()
if 'links' in saved_data:
    mgr.links = saved_data['links']
    mgr.links['disclaimer'] = saved_data.get('disclaimer', 'ᴿᵉᵏˡᵃᵐᵃ')
else:
    mgr.links = saved_data

def menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📝 Пост")],
        [KeyboardButton("🔗 Ссылки"), KeyboardButton("🔘 Кнопки")],
        [KeyboardButton("📊 Статус"), KeyboardButton("📋 Реклама")],
        [KeyboardButton("❓ Помощь")]
    ], resize_keyboard=True)

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Добро пожаловать! Выберите действие:", reply_markup=menu())

async def stop_bot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == ADMIN_ID:
        await update.message.reply_text("🛑 Бот останавливается...", reply_markup=ReplyKeyboardRemove())
        # Сигнализируем в main(), что пора останавливаться
        ctx.application.bot_data['stop_event'].set()
    else:
        await update.message.reply_text("❌ Только администратор может остановить бота.")

async def disclaimer_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer(text=mgr.get_disclaimer(), show_alert=True)

async def post_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 Напишите текст поста (с форматированием):", reply_markup=ReplyKeyboardRemove())
    return WAITING_FOR_POST_TEXT

async def post_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['text'] = update.message.text
    ctx.user_data['entities'] = update.message.entities
    ctx.user_data['media'] = []
    skip_kb = ReplyKeyboardMarkup([[KeyboardButton("⏭️ Пропустить")], [KeyboardButton("✅ Готово")]], resize_keyboard=True)
    await update.message.reply_text("📸 Отправьте фото/видео/GIF (можно несколько)\nИли нажмите:", reply_markup=skip_kb)
    return WAITING_FOR_POST_PHOTO

async def handle_limit_action(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📋 Скопировать текст":
        post_text_content = ctx.user_data.get('text', '')
        entities = ctx.user_data.get('entities')
        await update.message.reply_text(post_text_content, entities=entities)
        await update.message.reply_text("✅ Текст отправлен выше.\nВы можете скопировать его и опубликовать вручную.\nБот добавит кнопки автоматически, если вы не добавите # в конце.", reply_markup=menu())
        return ConversationHandler.END

    elif text == "2️⃣ Опубликовать двумя сообщениями":
        try:
            media_list = ctx.user_data.get('media', [])
            post_text_content = ctx.user_data.get('text', '')
            entities = ctx.user_data.get('entities')
            buttons = mgr.get_buttons()

            # 1. Отправляем медиа (без подписи)
            if len(media_list) == 1:
                media = media_list[0]
                if media['type'] == 'photo':
                    await ctx.bot.send_photo(CHANNEL_ID, media['file_id'])
                elif media['type'] == 'video':
                    await ctx.bot.send_video(CHANNEL_ID, media['file_id'])
                elif media['type'] == 'animation':
                    await ctx.bot.send_animation(CHANNEL_ID, media['file_id'])
            else:
                # Альбом
                media_group = []
                for media in media_list:
                    if media['type'] == 'photo':
                        media_group.append(InputMediaPhoto(media=media['file_id']))
                    elif media['type'] == 'video':
                        media_group.append(InputMediaVideo(media=media['file_id']))
                if media_group:
                    await ctx.bot.send_media_group(CHANNEL_ID, media_group)

                # GIFы отправляем отдельно, если были
                animations = [m for m in media_list if m['type'] == 'animation']
                for anim in animations:
                    await ctx.bot.send_animation(CHANNEL_ID, anim['file_id'])

            # 2. Отправляем текст следом + кнопки
            if buttons and not post_text_content.rstrip().endswith(NO_BUTTON_MARK):
                await ctx.bot.send_message(CHANNEL_ID, post_text_content, entities=entities, reply_markup=buttons)
            else:
                await ctx.bot.send_message(CHANNEL_ID, post_text_content, entities=entities)

            await update.message.reply_text("✅ Опубликовано двумя сообщениями (Медиа -> Текст+Кнопки)", reply_markup=menu())
            return ConversationHandler.END

        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при публикации: {e}", reply_markup=menu())
            return ConversationHandler.END

    else:
        await update.message.reply_text("Выберите действие:", reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("📋 Скопировать текст")],
            [KeyboardButton("2️⃣ Опубликовать двумя сообщениями")]
        ], resize_keyboard=True))
        return WAITING_FOR_LIMIT_ACTION

async def post_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        text = ctx.user_data['text']
        entities = ctx.user_data.get('entities')
        buttons = mgr.get_buttons()
        media_list = ctx.user_data.get('media', [])

        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            media_list.append({"type": "photo", "file_id": file_id})
            ctx.user_data['media'] = media_list
            await update.message.reply_text(f"✅ Фото добавлено ({len(media_list)})\nОтправьте ещё или нажмите 'Готово'")
            return WAITING_FOR_POST_PHOTO
        elif update.message.video:
            file_id = update.message.video.file_id
            media_list.append({"type": "video", "file_id": file_id})
            ctx.user_data['media'] = media_list
            await update.message.reply_text(f"✅ Видео добавлено ({len(media_list)})\nОтправьте ещё или нажмите 'Готово'")
            return WAITING_FOR_POST_PHOTO
        elif update.message.animation:
            file_id = update.message.animation.file_id
            media_list.append({"type": "animation", "file_id": file_id})
            ctx.user_data['media'] = media_list
            await update.message.reply_text(f"✅ GIF добавлен ({len(media_list)})\nОтправьте ещё или нажмите 'Готово'")
            return WAITING_FOR_POST_PHOTO
        elif update.message.document and update.message.document.mime_type == "image/gif":
            file_id = update.message.document.file_id
            media_list.append({"type": "animation", "file_id": file_id})
            ctx.user_data['media'] = media_list
            await update.message.reply_text(f"✅ GIF добавлен ({len(media_list)})\nОтправьте ещё или нажмите 'Готово'")
            return WAITING_FOR_POST_PHOTO
        elif update.message.text:
            text_lower = update.message.text.lower()
            if 'пропустить' in text_lower:
                await ctx.bot.send_message(CHANNEL_ID, text, entities=entities, reply_markup=buttons)
                await update.message.reply_text("✅ Пост опубликован!", reply_markup=menu())
                return ConversationHandler.END
            elif 'готово' in text_lower:
                try:
                    if len(media_list) == 0:
                        await ctx.bot.send_message(CHANNEL_ID, text, entities=entities, reply_markup=buttons)
                    elif len(media_list) == 1:
                        media = media_list[0]
                        if media['type'] == 'photo':
                            await ctx.bot.send_photo(CHANNEL_ID, media['file_id'], caption=text, caption_entities=entities, reply_markup=buttons)
                        elif media['type'] == 'video':
                            await ctx.bot.send_video(CHANNEL_ID, media['file_id'], caption=text, caption_entities=entities, reply_markup=buttons)
                        else:
                            await ctx.bot.send_animation(CHANNEL_ID, media['file_id'], caption=text, caption_entities=entities, reply_markup=buttons)
                    else:
                        animations = [m for m in media_list if m['type'] == 'animation']
                        photos_videos = [m for m in media_list if m['type'] in ['photo', 'video']]
                        if photos_videos:
                            media_group = []
                            for i, media in enumerate(photos_videos):
                                if media['type'] == 'photo':
                                    if i == 0:
                                        media_group.append(InputMediaPhoto(media=media['file_id'], caption=text, caption_entities=entities))
                                    else:
                                        media_group.append(InputMediaPhoto(media=media['file_id']))
                                else:
                                    if i == 0:
                                        media_group.append(InputMediaVideo(media=media['file_id'], caption=text, caption_entities=entities))
                                    else:
                                        media_group.append(InputMediaVideo(media=media['file_id']))
                            await ctx.bot.send_media_group(CHANNEL_ID, media_group)
                            if animations:
                                for anim in animations:
                                    await ctx.bot.send_animation(CHANNEL_ID, anim['file_id'])

                            if buttons and not text.rstrip().endswith(NO_BUTTON_MARK):
                                await ctx.bot.send_message(CHANNEL_ID, ARROWS_LINE, reply_markup=buttons)
                        else:
                            if len(animations) == 1:
                                await ctx.bot.send_animation(CHANNEL_ID, animations[0]['file_id'], caption=text, caption_entities=entities, reply_markup=buttons)
                            else:
                                await ctx.bot.send_animation(CHANNEL_ID, animations[0]['file_id'], caption=text, caption_entities=entities)
                                for anim in animations[1:]:
                                    await ctx.bot.send_animation(CHANNEL_ID, anim['file_id'])
                                if buttons and not text.rstrip().endswith(NO_BUTTON_MARK):
                                    await ctx.bot.send_message(CHANNEL_ID, ARROWS_LINE, reply_markup=buttons)

                    await update.message.reply_text("✅ Пост опубликован!", reply_markup=menu())
                    return ConversationHandler.END

                except BadRequest as e:
                    if "caption is too long" in str(e) or "message is too long" in str(e):
                        kb = ReplyKeyboardMarkup([
                            [KeyboardButton("📋 Скопировать текст")],
                            [KeyboardButton("2️⃣ Опубликовать двумя сообщениями")]
                        ], resize_keyboard=True)
                        await update.message.reply_text("⚠️ Ошибка: Текст слишком длинный для подписи (лимит 1024 символа).\n\nВыберите действие:", reply_markup=kb)
                        return WAITING_FOR_LIMIT_ACTION
                    else:
                        raise e

            else:
                skip_kb = ReplyKeyboardMarkup([[KeyboardButton("⏭️ Пропустить")], [KeyboardButton("✅ Готово")]], resize_keyboard=True)
                await update.message.reply_text("📸 Отправьте фото/видео/GIF или нажмите кнопку:", reply_markup=skip_kb)
                return WAITING_FOR_POST_PHOTO
        else:
            skip_kb = ReplyKeyboardMarkup([[KeyboardButton("⏭️ Пропустить")], [KeyboardButton("✅ Готово")]], resize_keyboard=True)
            await update.message.reply_text("📸 Отправьте фото/видео/GIF или нажмите кнопку:", reply_markup=skip_kb)
            return WAITING_FOR_POST_PHOTO
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}", reply_markup=menu())
        return ConversationHandler.END

async def send_buttons(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        buttons = mgr.get_buttons()
        if buttons:
            await ctx.bot.send_message(CHANNEL_ID, ARROWS_LINE, reply_markup=buttons)
            await update.message.reply_text("✅ Кнопки отправлены в канал!", reply_markup=menu())
        else:
            await update.message.reply_text("❌ Нет активных ссылок", reply_markup=menu())
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}", reply_markup=menu())

async def channel_post_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        if update.channel_post and update.channel_post.chat.id == CHANNEL_ID:
            buttons = mgr.get_buttons()
            if not buttons:
                return
            post = update.channel_post
            txt = (post.text or post.caption or "").rstrip()
            if txt.endswith(NO_BUTTON_MARK):
                return
            await asyncio.sleep(0.5)
            await ctx.bot.send_message(CHANNEL_ID, ARROWS_LINE, reply_markup=buttons)
            print("✅ Автоматически добавлены кнопки")
    except Exception as e:
        print(f"❌ Ошибка в channel_post_handler: {e}")

async def disclaimer_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    current = mgr.get_disclaimer()
    await update.message.reply_text(f"📋 Текущий текст рекламы:\n{current}\n\nОтправьте новый текст:", reply_markup=ReplyKeyboardRemove())
    return WAITING_FOR_DISCLAIMER

async def disclaimer_update(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    new_text = update.message.text
    mgr.update_disclaimer(new_text)
    await update.message.reply_text(f"✅ Текст рекламы обновлён:\n{new_text}", reply_markup=menu())
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
    if key == "tour":
        link = mgr.links[key]
        mgr.update_link(key, link['name'], update.message.text, 365)
        await update.message.reply_text(f"✅ {link['name']}\nОбновлена!", reply_markup=menu())
        return ConversationHandler.END
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
    if not update.message or not update.message.text:
        return
    text = update.message.text
    if text == "📝 Пост":
        return await post_start(update, ctx)
    elif text == "🔗 Ссылки":
        return await links_start(update, ctx)
    elif text == "🔘 Кнопки":
        return await send_buttons(update, ctx)
    elif text == "📋 Реклама":
        return await disclaimer_start(update, ctx)
    elif text == "📊 Статус":
        await update.message.reply_text(mgr.status(), reply_markup=menu())
    elif text == "❓ Помощь":
        await update.message.reply_text("📝 Пост - опубликовать\n🔗 Ссылки - менять\n🔘 Кнопки - отправить вручную\n📋 Реклама - текст кнопки-disclaimer\n📊 Статус - проверить\n🛑 /stop - остановить бота", reply_markup=menu())

async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Создаем событие остановки
    stop_event = asyncio.Event()

    # Сохраняем его в bot_data, чтобы иметь доступ из хендлеров
    app.bot_data['stop_event'] = stop_event

    app.add_handler(CommandHandler("stop", stop_bot))
    app.add_handler(CallbackQueryHandler(disclaimer_callback, pattern="show_disclaimer"))
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL, channel_post_handler), group=-1)

    post_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("📝 Пост"), post_start)],
        states={
            WAITING_FOR_POST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_text)],
            WAITING_FOR_POST_PHOTO: [MessageHandler((filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.Document.MimeType("image/gif") | filters.TEXT) & ~filters.COMMAND, post_photo)],
            WAITING_FOR_LIMIT_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_limit_action)]
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

    disclaimer_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("📋 Реклама"), disclaimer_start)],
        states={
            WAITING_FOR_DISCLAIMER: [MessageHandler(filters.TEXT & ~filters.COMMAND, disclaimer_update)]
        },
        fallbacks=[CommandHandler("start", start)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(post_conv)
    app.add_handler(link_conv)
    app.add_handler(disclaimer_conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🤖 Бот запущен и слушает...")
    print("📢 Автоматические кнопки включены")

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    # Обработка сигналов OS
    import signal
    def signal_handler(sig, frame):
        stop_event.set()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Ждем сигнала остановки (от команды /stop или Ctrl+C)
    await stop_event.wait()

    # Корректная остановка
    await app.updater.stop()
    await app.stop()
    await app.shutdown()
    print("✅ Бот успешно остановлен.")

if __name__ == "__main__":
    asyncio.run(main())
