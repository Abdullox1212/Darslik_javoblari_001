from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from subjects import subjects

def contact_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    contact_button = KeyboardButton(text="📞 Raqamni yuborish", request_contact=True)
    keyboard.add(contact_button)
    return keyboard

def main():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    start_button = KeyboardButton(text="📚 Darsliklar javobini ko'rish")
    keyboard.add(start_button)
    return keyboard

def sinflar():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for sinf in subjects.keys():
        keyboard.add(KeyboardButton(text=sinf))
    return keyboard

def fanlar(sinf_name):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for subject in subjects[sinf_name].keys():
        keyboard.add(KeyboardButton(text=subject))
    return keyboard

# Helper function to create buttons for topics
def generate_subject_buttons(sinf_name, subject_name):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for topic in subjects[sinf_name][subject_name]:
        keyboard.add(KeyboardButton(text=topic))
    keyboard.add(KeyboardButton(text="🔙 Orqaga"))
    return keyboard

def generate_problem_buttons(sinf_name, subject_name, topic_name):
    problems = subjects[sinf_name][subject_name][topic_name]
    buttons = [KeyboardButton(text=problem["name"]) for problem in problems]
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🔙 Orqaga"))
    keyboard.add(*buttons)
    return keyboard

def admin_buttons():
    buttons = [
        KeyboardButton("💳 To'lovni tasdiqlash"),
        KeyboardButton("👨‍💼 Foydalanuvchilarni ko'rish"),
        KeyboardButton("📨 Xabar yuborish")
    ]
    return ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add(*buttons)