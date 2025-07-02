import os
import time
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
import openai

# ========== LOAD ENV ==========
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "123456789"))  # Use your Telegram ID

if not TELEGRAM_TOKEN or not OPENAI_API_KEY or not PINECONE_API_KEY:
    raise Exception("One or more API keys are missing in your .env!")

openai.api_key = OPENAI_API_KEY

# ========== LOGGING ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("psychologist_bot")

# ========== PINECONE ==========
from pinecone import Pinecone, ServerlessSpec
pc = Pinecone(api_key=PINECONE_API_KEY)
INDEX_NAME = "psychologist-bot"
DIMENSION = 1536
if INDEX_NAME not in [i.name for i in pc.list_indexes()]:
    pc.create_index(
        name=INDEX_NAME,
        dimension=DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
    logger.info(f"Created Pinecone index '{INDEX_NAME}' with dimension {DIMENSION}")
index = pc.Index(INDEX_NAME)

# ========== LANGUAGES ==========
LANGUAGES = {
    "en": {
        "greet": "👋 Hello! I'm your Psychologist Helper. Write your message and I'll try to help.",
        "help": "I am here to support you. Just share your worries, and I will listen and help you reflect.",
        "abilities": "I can listen, support, analyze your feelings, clear memory, and switch language.",
        "recent": "Your recent messages:\n— ",
        "recent_none": "You don't have recent messages yet.",
        "cleared": "Your chat memory has been cleared.",
        "nothing_clear": "You have no saved memory to clear.",
        "choose_language": "🌐 Choose your language:",
        "lang_en": "English 🇬🇧",
        "lang_it": "Italiano 🇮🇹",
        "lang_ru": "Русский 🇷🇺",
        "prompt": "You are a friendly AI psychologist assistant. Be supportive, warm, avoid medical advice.",
        "menu": [
            [InlineKeyboardButton("❓ Help", callback_data='help')],
            [InlineKeyboardButton("💡 What can you do?", callback_data='abilities')],
            [InlineKeyboardButton("🕓 My recent queries", callback_data='recent')],
            [InlineKeyboardButton("🗑️ Clear my memory", callback_data='clear')],
            [InlineKeyboardButton("🌐 Language", callback_data='language')],
        ],
    },
    "it": {
        "greet": "👋 Ciao! Sono il tuo assistente psicologo. Scrivimi il tuo messaggio e proverò ad aiutarti.",
        "help": "Sono qui per supportarti. Raccontami cosa ti preoccupa, ti ascolto.",
        "abilities": "Posso ascoltare, supportare, analizzare i tuoi sentimenti, cancellare la memoria, cambiare lingua.",
        "recent": "I tuoi messaggi recenti:\n— ",
        "recent_none": "Non hai ancora messaggi recenti.",
        "cleared": "La tua memoria è stata cancellata.",
        "nothing_clear": "Non hai memoria salvata da cancellare.",
        "choose_language": "🌐 Scegli la tua lingua:",
        "lang_en": "English 🇬🇧",
        "lang_it": "Italiano 🇮🇹",
        "lang_ru": "Русский 🇷🇺",
        "prompt": "Sei un assistente psicologo AI gentile. Sii di supporto, positivo, evita consigli medici.",
        "menu": [
            [InlineKeyboardButton("❓ Aiuto", callback_data='help')],
            [InlineKeyboardButton("💡 Cosa puoi fare?", callback_data='abilities')],
            [InlineKeyboardButton("🕓 I miei messaggi recenti", callback_data='recent')],
            [InlineKeyboardButton("🗑️ Cancella la memoria", callback_data='clear')],
            [InlineKeyboardButton("🌐 Lingua", callback_data='language')],
        ],
    },
    "ru": {
        "greet": "👋 Привет! Я — твой помощник-психолог. Напиши сообщение, я помогу.",
        "help": "Я здесь, чтобы поддержать тебя. Просто напиши, что тебя тревожит, я выслушаю.",
        "abilities": "Я умею слушать, поддерживать, анализировать чувства, очищать память, менять язык.",
        "recent": "Твои последние сообщения:\n— ",
        "recent_none": "У тебя пока нет недавних сообщений.",
        "cleared": "Память чата очищена.",
        "nothing_clear": "Память пуста, нечего очищать.",
        "choose_language": "🌐 Выбери язык:",
        "lang_en": "English 🇬🇧",
        "lang_it": "Italiano 🇮🇹",
        "lang_ru": "Русский 🇷🇺",
        "prompt": "Ты дружелюбный психолог-ассистент. Будь поддержкой, не давай медицинских советов.",
        "menu": [
            [InlineKeyboardButton("❓ Помощь", callback_data='help')],
            [InlineKeyboardButton("💡 Что ты умеешь?", callback_data='abilities')],
            [InlineKeyboardButton("🕓 Мои последние вопросы", callback_data='recent')],
            [InlineKeyboardButton("🗑️ Очистить память", callback_data='clear')],
            [InlineKeyboardButton("🌐 Язык", callback_data='language')],
        ],
    }
}
DEFAULT_LANG = "en"

def get_lang(context):
    return context.user_data.get("lang", DEFAULT_LANG)

def set_lang(context, lang_code):
    context.user_data["lang"] = lang_code

def menu_keyboard(context):
    lang = get_lang(context)
    return InlineKeyboardMarkup(LANGUAGES[lang]["menu"])

def lang_choice_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(LANGUAGES['en']["lang_en"], callback_data='setlang_en')],
        [InlineKeyboardButton(LANGUAGES['it']["lang_it"], callback_data='setlang_it')],
        [InlineKeyboardButton(LANGUAGES['ru']["lang_ru"], callback_data='setlang_ru')]
    ])

# ========== OPENAI/PINECONE UTILS ==========
def get_embedding(text):
    try:
        response = openai.embeddings.create(
            input=[text],
            model="text-embedding-ada-002"
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"\n\n===== OpenAI embedding error! =====\n{repr(e)}\n\n")
        logger.error(f"Embedding error: {e}", exc_info=True)
        return [0.0] * DIMENSION

def save_message(user_id, message, role):
    emb = get_embedding(message)
    meta = {
        "user_id": user_id,
        "role": role,
        "text": message,
        "timestamp": str(time.time())
    }
    vector_id = f"{user_id}-{int(time.time()*1000)}"
    try:
        index.upsert(vectors=[(vector_id, emb, meta)])
    except Exception as e:
        print(f"\n\n===== Pinecone upsert error! =====\n{repr(e)}\n\n")
        logger.error(f"Pinecone upsert error: {e}")

def get_recent_msgs(user_id, n=3):
    try:
        results = index.query(
            vector=[0.0]*DIMENSION,
            filter={"user_id": user_id, "role": "user"},
            top_k=n,
            include_metadata=True
        )
        return [m['metadata']['text'] for m in results.get('matches', [])]
    except Exception as e:
        logger.error(f"Pinecone query error: {e}")
        return []

def clear_memory(user_id):
    try:
        results = index.query(
            vector=[0.0]*DIMENSION,
            filter={"user_id": user_id},
            top_k=1000,
            include_metadata=False
        )
        ids_to_delete = [m['id'] for m in results.get('matches', [])]
        if ids_to_delete:
            index.delete(ids=ids_to_delete)
            return True
    except Exception as e:
        logger.error(f"Pinecone clear error: {e}")
    return False

def get_relevant_history(user_id, query, top_k=5):
    query_emb = get_embedding(query)
    try:
        res = index.query(
            vector=query_emb,
            filter={"user_id": user_id},
            top_k=top_k,
            include_metadata=True
        )
        results = []
        for match in res.get("matches", []):
            meta = match.get("metadata", {})
            if meta.get("role") == "user":
                results.append(meta.get("text", ""))
        return results
    except Exception as e:
        logger.error(f"Pinecone query error: {e}")
        return []

def is_valid_message(msg):
    return isinstance(msg, str) and 1 < len(msg) < 1500

# ========== HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    await update.message.reply_text(
        LANGUAGES[lang]["greet"],
        reply_markup=menu_keyboard(context)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_lang(context)
    user_id = str(query.from_user.id)

    try:
        if query.data == 'help':
            await query.message.reply_text(LANGUAGES[lang]["help"], reply_markup=menu_keyboard(context))

        elif query.data == 'abilities':
            await query.message.reply_text(LANGUAGES[lang]["abilities"], reply_markup=menu_keyboard(context))

        elif query.data == 'recent':
            recent = get_recent_msgs(user_id)
            if recent:
                await query.message.reply_text(LANGUAGES[lang]["recent"] + "\n— ".join(recent), reply_markup=menu_keyboard(context))
            else:
                await query.message.reply_text(LANGUAGES[lang]["recent_none"], reply_markup=menu_keyboard(context))

        elif query.data == 'clear':
            cleared = clear_memory(user_id)
            if cleared:
                await query.message.reply_text(LANGUAGES[lang]["cleared"], reply_markup=menu_keyboard(context))
            else:
                await query.message.reply_text(LANGUAGES[lang]["nothing_clear"], reply_markup=menu_keyboard(context))

        elif query.data == 'language':
            await query.message.reply_text(LANGUAGES[lang]["choose_language"], reply_markup=lang_choice_keyboard())

        elif query.data.startswith('setlang_'):
            new_lang = query.data.split("_")[1]
            set_lang(context, new_lang)
            lang = new_lang
            await query.message.reply_text(LANGUAGES[lang]["greet"], reply_markup=menu_keyboard(context))
    except Exception as e:
        logger.error(f"Button callback error: {e}")
        await query.message.reply_text("An internal error occurred. Please try again later.", reply_markup=menu_keyboard(context))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    user_id = str(update.message.from_user.id)
    user_msg = update.message.text

    if not is_valid_message(user_msg):
        await update.message.reply_text("Your message is too long or empty. Please send something shorter.", reply_markup=menu_keyboard(context))
        return

    save_message(user_id, user_msg, "user")
    relevant_history = get_relevant_history(user_id, user_msg, top_k=5)
    max_history_chars = 4000
    total_len = 0
    filtered_history = []
    for msg in relevant_history:
        if not msg:
            continue
        if total_len + len(msg) > max_history_chars:
            break
        filtered_history.append(msg)
        total_len += len(msg)

    messages = [
        {"role": "system", "content": LANGUAGES[lang]["prompt"]}
    ]
    for past_msg in filtered_history:
        messages.append({"role": "user", "content": past_msg})
    messages.append({"role": "user", "content": user_msg})  # <---- исправлено здесь!

    try:
        logger.debug("Sending OpenAI request...")
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.8,
            max_tokens=300
        )
        logger.debug(f"OpenAI response: {response}")
        bot_reply = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"\n\n===== OpenAI error! =====\n{repr(e)}\n\n")
        logger.error(f"OpenAI error: {e}", exc_info=True)
        bot_reply = {
            "en": "Sorry, a technical error occurred. Please try again.",
            "it": "Mi dispiace, sto avendo difficoltà tecniche. Riprova più tardi.",
            "ru": "Извините, возникли технические проблемы. Пожалуйста, попробуйте ещё раз."
        }.get(lang, "Sorry, a technical error occurred. Please try again.")

    save_message(user_id, bot_reply, "assistant")
    await update.message.reply_text(bot_reply, reply_markup=menu_keyboard(context))

async def error_handler(update, context):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    print(f"TELEGRAM ERROR: {context.error}")
    try:
        if update and getattr(update, "message", None):
            await update.message.reply_text("Sorry, a technical error occurred. Please try again.", reply_markup=menu_keyboard(context))
    except Exception as e:
        print(f"Failed to send error message: {e}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    logger.info("Bot is running!")
    app.run_polling()

if __name__ == "__main__":
    main()
