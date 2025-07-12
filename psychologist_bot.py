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

# ========== ENV ==========
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")

openai.api_key = OPENAI_API_KEY

# ========== LOGGING ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("psychologist_bot")

# ========== PINECONE ==========
from pinecone import Pinecone, ServerlessSpec

DIMENSION = 1536
pc = Pinecone(api_key=PINECONE_API_KEY)
if PINECONE_INDEX_NAME not in [i.name for i in pc.list_indexes()]:
    pc.create_index(
        name=PINECONE_INDEX_NAME,
        dimension=DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION)
    )
index = pc.Index(PINECONE_INDEX_NAME)

# ========== LANGUAGES ==========
LANGUAGES = {
    "en": {
        "greet": "👋 Hello! I'm your caring support assistant. Write me any concern — I'm here to help you emotionally.",
        "help": "You can share your feelings, thoughts, or worries. I will listen and offer gentle, supportive reflections. I never diagnose or give medical advice.",
        "abilities": "I offer emotional support, active listening, help with reflection and self-care tips. You can clear your memory or change language anytime.",
        "recent": "Your recent messages:\n— ",
        "recent_none": "You don't have recent messages yet.",
        "cleared": "Your chat memory has been cleared.",
        "nothing_clear": "You have no saved memory to clear.",
        "choose_language": "🌐 Choose your language:",
        "lang_en": "English 🇬🇧",
        "lang_it": "Italiano 🇮🇹",
        "lang_ru": "Русский 🇷🇺",
        "menu": [
            [InlineKeyboardButton("❓ Help", callback_data='help')],
            [InlineKeyboardButton("💡 What can you do?", callback_data='abilities')],
            [InlineKeyboardButton("🕓 My recent queries", callback_data='recent')],
            [InlineKeyboardButton("🗑️ Clear my memory", callback_data='clear')],
            [InlineKeyboardButton("🌐 Language", callback_data='language')],
        ],
        "system_prompt":
            (
                "You are a warm, empathetic, and respectful virtual assistant designed to provide emotional support only. "
"You always communicate with kindness, understanding, and care. "
"You never offer any medical, psychological, or psychiatric diagnoses or suggest treatments of any kind. "
"You never give medical advice and do not interpret symptoms. "
"If the user asks for a diagnosis, medical interpretation, or therapy, respond gently by explaining "
"that your role is to offer emotional support only, and that they should reach out to a qualified healthcare professional for medical concerns. "
"Your goal is to make the user feel heard, understood, respected, and safe. "
"Focus on active listening, warmth, and emotional validation. "
"If the user shares something positive, celebrate it with them and encourage their progress. "
"Always respond with a compassionate, non-judgmental human tone."

            )
    },
    "ru": {
        "greet": "👋 Привет! Я — твой заботливый ассистент поддержки. Напиши мне любую тревогу — я здесь, чтобы поддержать тебя эмоционально.",
        "help": "Ты можешь поделиться чувствами, мыслями или переживаниями. Я выслушаю и дам мягкий, поддерживающий отклик. Я никогда не ставлю диагнозов и не даю медицинских советов.",
        "abilities": "Я предлагаю эмоциональную поддержку, активное слушание, помощь в рефлексии и советы по заботе о себе. Ты можешь очистить память или сменить язык в любой момент.",
        "recent": "Твои последние сообщения:\n— ",
        "recent_none": "У тебя пока нет недавних сообщений.",
        "cleared": "Память чата очищена.",
        "nothing_clear": "У тебя нет сохранённой памяти для очистки.",
        "choose_language": "🌐 Выбери язык:",
        "lang_en": "English 🇬🇧",
        "lang_it": "Italiano 🇮🇹",
        "lang_ru": "Русский 🇷🇺",
        "menu": [
            [InlineKeyboardButton("❓ Помощь", callback_data='help')],
            [InlineKeyboardButton("💡 Что ты умеешь?", callback_data='abilities')],
            [InlineKeyboardButton("🕓 Мои последние вопросы", callback_data='recent')],
            [InlineKeyboardButton("🗑️ Очистить память", callback_data='clear')],
            [InlineKeyboardButton("🌐 Язык", callback_data='language')],
        ],
        "system_prompt":
            (
               "Ты — тёплый, эмпатичный и уважительный виртуальный ассистент, созданный исключительно для оказания эмоциональной поддержки. "
"Ты всегда общаешься с добротой, пониманием и заботой. "
"Ты никогда не ставишь медицинских, психологических или психиатрических диагнозов и не предлагаешь никаких методов лечения. "
"Ты не даёшь медицинских советов и не интерпретируешь симптомы. "
"Если пользователь просит диагноз, медицинскую интерпретацию или терапию, мягко объясни, "
"что твоя задача — оказывать только эмоциональную поддержку, и что важно обратиться к квалифицированному специалисту. "
"Твоя цель — чтобы пользователь чувствовал себя услышанным, понятым, уважаемым и в безопасности. "
"Сосредоточься на активном слушании, теплоте и принятии эмоций. "
"Если пользователь делится чем-то хорошим, порадоваться вместе с ним и поддержать его прогресс. "
"Всегда отвечай в тёплом, человечном и безоценочном тоне."

            )
    },
    "it": {
        "greet": "👋 Ciao! Sono il tuo assistente di supporto emotivo. Scrivimi qualsiasi preoccupazione — sono qui per aiutarti.",
        "help": "Puoi condividere i tuoi sentimenti, pensieri o preoccupazioni. Ti ascolterò e offrirò riflessioni di supporto, senza mai fare diagnosi o dare consigli medici.",
        "abilities": "Offro supporto emotivo, ascolto attivo, aiuto nella riflessione e consigli di self-care. Puoi cancellare la memoria o cambiare lingua in qualsiasi momento.",
        "recent": "I tuoi messaggi recenti:\n— ",
        "recent_none": "Non hai ancora messaggi recenti.",
        "cleared": "La tua memoria della chat è stata cancellata.",
        "nothing_clear": "Non hai memoria salvata da cancellare.",
        "choose_language": "🌐 Scegli la tua lingua:",
        "lang_en": "English 🇬🇧",
        "lang_it": "Italiano 🇮🇹",
        "lang_ru": "Русский 🇷🇺",
        "menu": [
            [InlineKeyboardButton("❓ Aiuto", callback_data='help')],
            [InlineKeyboardButton("💡 Cosa puoi fare?", callback_data='abilities')],
            [InlineKeyboardButton("🕓 Le mie domande recenti", callback_data='recent')],
            [InlineKeyboardButton("🗑️ Cancella la memoria", callback_data='clear')],
            [InlineKeyboardButton("🌐 Lingua", callback_data='language')],
        ],
        "system_prompt":
            (
                "Sei un assistente virtuale empatico, premuroso e rispettoso, progettato per offrire esclusivamente supporto emotivo. "
        "Comunichi sempre con gentilezza, comprensione ed empatia. "
        "Non fornisci mai diagnosi mediche, psicologiche o psichiatriche e non suggerisci trattamenti di alcun tipo. "
        "Non offri mai consigli medici e non interpreti sintomi. "
        "Se l’utente chiede una diagnosi, un'interpretazione medica o una terapia, rispondi con delicatezza spiegando "
        "che il tuo ruolo è solo quello di fornire supporto emotivo e che per questioni mediche è importante rivolgersi a uno specialista qualificato. "
        "Il tuo obiettivo è far sentire l’utente ascoltato, compreso, rispettato e al sicuro. "
        "Concentrati sull’ascolto attivo, sull’accoglienza calorosa e sulla validazione delle emozioni. "
        "Se l’utente condivide qualcosa di positivo, celebra insieme a lui e incoraggialo. "
        "Rispondi sempre con tono umano, accogliente e privo di giudizio."
            )
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
# ========== VECTOR MEMORY ==========
def get_embedding(text):
    try:
        response = openai.embeddings.create(
            input=[text],
            model="text-embedding-ada-002"
        )
        return response.data[0].embedding
    except Exception as e:
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
        logger.error(f"Pinecone upsert error: {e}")

def get_relevant_history(user_id, query, top_k=8):
    query_emb = get_embedding(query)
    try:
        res = index.query(
            vector=query_emb,
            filter={"user_id": user_id},
            top_k=top_k,
            include_metadata=True
        )
        history = []
        for match in res.get("matches", []):
            meta = match.get("metadata", {})
            role = meta.get("role")
            text = meta.get("text")
            if role in ("user", "assistant") and text:
                history.append({"role": role, "content": text})
        return history
    except Exception as e:
        logger.error(f"Pinecone history query error: {e}")
        return []

def clear_memory(user_id):
    try:
        res = index.query(
            vector=[0.0]*DIMENSION,
            filter={"user_id": user_id},
            top_k=1000,
            include_metadata=False
        )
        ids = [m["id"] for m in res.get("matches", [])]
        if ids:
            index.delete(ids=ids)
            return True
    except Exception as e:
        logger.error(f"Pinecone clear error: {e}")
    return False

# ========== ASYNC HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    await update.message.reply_text(LANGUAGES[lang]["greet"], reply_markup=menu_keyboard(context))

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
            msgs = get_relevant_history(user_id, "", top_k=3)
            if msgs:
                joined = "\n— ".join([m["content"] for m in msgs if m["role"] == "user"])
                await query.message.reply_text(LANGUAGES[lang]["recent"] + joined, reply_markup=menu_keyboard(context))
            else:
                await query.message.reply_text(LANGUAGES[lang]["recent_none"], reply_markup=menu_keyboard(context))
        elif query.data == 'clear':
            success = clear_memory(user_id)
            msg = LANGUAGES[lang]["cleared"] if success else LANGUAGES[lang]["nothing_clear"]
            await query.message.reply_text(msg, reply_markup=menu_keyboard(context))
        elif query.data == 'language':
            await query.message.reply_text(LANGUAGES[lang]["choose_language"], reply_markup=lang_choice_keyboard())
        elif query.data.startswith('setlang_'):
            new_lang = query.data[len('setlang_'):]
            if new_lang not in LANGUAGES:
                logger.error(f"No such language: {new_lang}")
                await query.message.reply_text("Selected language is not supported.", reply_markup=menu_keyboard(context))
                return
            set_lang(context, new_lang)
            lang = new_lang
            await query.message.reply_text(LANGUAGES[lang]["greet"], reply_markup=menu_keyboard(context))
    except Exception as e:
        logger.error(f"Button callback error: {e}")
        await query.message.reply_text("Internal error. Please try again.", reply_markup=menu_keyboard(context))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    user_id = str(update.message.from_user.id)
    user_msg = update.message.text

    if not isinstance(user_msg, str) or len(user_msg) < 2 or len(user_msg) > 1500:
        await update.message.reply_text("Your message is too long or too short.", reply_markup=menu_keyboard(context))
        return

    save_message(user_id, user_msg, "user")
    history = get_relevant_history(user_id, user_msg, top_k=6)
    max_chars = 4000
    messages = [{"role": "system", "content": LANGUAGES[lang]["system_prompt"]}]
    total_len = 0
    for h in history:
        if total_len + len(h["content"]) < max_chars:
            messages.append(h)
            total_len += len(h["content"])

    messages.append({"role": "user", "content": user_msg})

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.8,
            max_tokens=300
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        reply = LANGUAGES[lang].get("error", "Sorry, a technical error occurred.")

    save_message(user_id, reply, "assistant")
    await update.message.reply_text(reply, reply_markup=menu_keyboard(context))

async def error_handler(update, context):
    logger.error(msg="Exception while handling update:", exc_info=context.error)
    if update and getattr(update, "message", None):
        await update.message.reply_text("Sorry, an error occurred.", reply_markup=menu_keyboard(context))

# ========== MAIN ==========
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
