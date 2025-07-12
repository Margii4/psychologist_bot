# 🤖 AI Emotional Support Telegram Bot

An empathetic, multilingual emotional support assistant powered by OpenAI (GPT-3.5-turbo), Pinecone, and Telegram.

## 🧠 Features

- 💬 Conversational support in **English, Italian, and Russian**
- 🌐 Language switch via built-in Telegram menu
- 🧘 Speaks in a **caring, supportive, non-judgmental tone**
- ❌ Never gives medical advice or makes diagnoses
- 🧠 Stores recent user messages in **Pinecone Vector DB (v2)** for better memory and contextual replies
- 📂 Supports context clearing and viewing recent messages
- 🛡️ Secure system prompt enforces strict emotional-support-only behavior

## ⚙️ Tech Stack

- Python 3.11+
- [`python-telegram-bot`](https://github.com/python-telegram-bot/python-telegram-bot)
- OpenAI `gpt-3.5-turbo`
- Pinecone (Vector DB v2 / serverless)
- `.env`-based secret management

## 🚀 How to Run Locally

1. **Clone the repo** and install dependencies:

```bash
git clone https://github.com/Margii4/emotional-support-bot.git
cd emotional-support-bot
pip install -r requirements.txt
```

2. **Add a `.env` file** with your credentials:

```env
TELEGRAM_TOKEN=your_bot_token
OPENAI_API_KEY=your_openai_key
PINECONE_API_KEY=your_pinecone_key
PINECONE_INDEX_NAME=your_index_name
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1
```

3. **Run the bot:**

```bash
python psychologist_bot.py
```

The bot is now live on Telegram and ready to chat.

## 🧪 Demo Scenario

> **User:** "I feel really anxious and can't focus on anything today."  
> **Bot:** "I'm really sorry you're feeling this way. It sounds like you're under a lot of pressure. You're not alone — I'm here for you. Would you like to talk more about it?"

> **User:** "I feel proud of myself today!"  
> **Bot:** "That's wonderful to hear! You deserve to feel proud — it's important to celebrate small wins too."

## 🛠 Future Extensions

- 📝 Daily journaling & mood tracking
- 📈 Sentiment-aware memory logic
- 🧘 Breathing and mindfulness exercises
- 🌙 Night mode or bedtime reflection

## 📦 Project Structure

```
📦 emotional-support-bot/
├── psychologist_bot.py        # Main bot logic
├── requirements.txt
├── .env                       # Your secrets (not pushed to Git)
```

## 🧷 Prompt Design

The assistant uses a system prompt instructing it to:
- Respond with warmth, empathy, and emotional support
- Never make medical claims or diagnoses
- Encourage users to speak openly without fear of judgment
- Celebrate positive emotions and gently validate hard ones

This results in natural, safe, and helpful conversations across multiple languages.

## 🧑‍💻 Author

Created by [Margarita Viviers](https://github.com/Margii4)  
Open-source, safe-by-design AI project to support mental well-being.

---

> 💡 *Disclaimer: This bot does not replace professional therapy or medical advice. It is intended for emotional support only.*
