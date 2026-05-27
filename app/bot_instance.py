import telebot
from groq import Groq
from app.config import TELEGRAM_TOKEN, GROQ_API_KEY

bot = telebot.TeleBot(TELEGRAM_TOKEN)
groq_client = Groq(api_key=GROQ_API_KEY)