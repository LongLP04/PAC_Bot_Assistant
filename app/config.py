from pathlib import Path
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

TRAIN_FOLDER = BASE_DIR / "training_materials"
SKILL_FOLDER = BASE_DIR / "skills_materials"

GROQ_MODEL = "llama-3.1-8b-instant"
TEMPERATURE = 0.4
MAX_TOKENS = 1024

BOT_NAME = "PAC Assistant"
BOT_VERSION = "v1.0.0"
BOT_ENV = "Free/Test"

if not TELEGRAM_TOKEN:
    raise ValueError("Thiếu TELEGRAM_TOKEN trong file .env")

if not GROQ_API_KEY:
    raise ValueError("Thiếu GROQ_API_KEY trong file .env")