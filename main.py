import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardRemove
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.utils import executor
from database import Database
from states import Registration, PaymentVerification, Darslik
from buttons import *
from datetime import datetime, timedelta
import asyncio



API_TOKEN = '6824723033:AAGYDwhh3aK9mUXLsui7RGWW1JmHRyW_i5o'
ADMINS_ID = [1921911753, 7149602547]


logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
database = Database()

# Foydalanuvchini registratsiya qilish jarayoni
@dp.message_handler(commands="start")
async def start_command(message: types.Message):
    chat_id = message.chat.id
    full_name = message.from_user.full_name

    # Agar foydalanuvchi registratsiyadan o'tgan bo'lsa
    if database.get_user(chat_id):
        user_status = database.get_user_status(chat_id)
        if user_status == 'False':
            await message.answer("Siz botdan foydalanishingiz uchun to'lov qilishingiz kerak.\n\nTo'lov qilish uchun admin @Abdulloh_Mirasqarov")
        else:
            user_profile_link = f"tg://user?id={message.from_user.id}"
            await message.answer(f"👋 Salom <b><a href='{user_profile_link}'>{full_name}</a></b>, botimizga xush kelibsiz!")
            await message.answer("Bugun nima qilamiz ❓", reply_markup=main())
    else:
        # Yangi foydalanuvchini ro'yxatdan o'tkazish
        user_profile_link = f"tg://user?id={message.from_user.id}"
        await message.answer(f"👋 Salom <b><a href='{user_profile_link}'>{full_name}</a></b>, botimizga xush kelibsiz!")        
        await message.answer("Botdan foydalanish uchun ro'yxatdan o'tishingiz kerak!")
        await message.answer("Ismingizni kiriting:")
        await Registration.waiting_for_name.set()

@dp.message_handler(state=Registration.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Iltimos, telefon raqamingizni yuboring:", reply_markup=contact_keyboard())
    await Registration.waiting_for_phone.set()

@dp.message_handler(content_types=types.ContentType.CONTACT, state=Registration.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    contact = message.contact
    chat_id = message.chat.id

    if contact is None or contact.user_id != chat_id:
        await message.answer("Iltimos, o'z telefon raqamingizni yuboring.")
        return

    data = await state.get_data()
    name = data['name']
    phone_number = contact.phone_number

    # Foydalanuvchini bazaga qo'shish (status False)
    database.add_user(name, phone_number, chat_id)

    await message.answer("Registratsiyadan muvaffaqqiyatli o'tdingiz! Endi botdan foydalanish uchun to'lov qilishingiz kerak.\n\nTo'lov qilish uchun admin @Abdulloh_Mirasqarov", reply_markup=ReplyKeyboardRemove())
    await state.finish()


@dp.message_handler(commands=['admin'])
async def send_admin_welcome(message: types.Message):
    full_name = message.from_user.full_name
    user_id = message.from_user.id
    for admin_id in ADMINS_ID:
        if user_id == admin_id:
            await message.answer(f"Salom, Hurmatli <b>{full_name}</b>! Botimizga xush kelibsiz", reply_markup=admin_buttons())
        else:
            pass

    
# # Admin foydalanuvchini to'lov qilgan deb tasdiqlashi
# @dp.message_handler(Text(equals="💳 To'lovni tasdiqlash"), user_id=ADMINS_ID)
# async def payment_verification(message: types.Message):
#     await message.answer("Foydalanuvchi chat ID sini kiriting:")
#     await PaymentVerification.waiting_for_user_chat_id.set()


@dp.message_handler(text="👨‍💼 Foydalanuvchilarni ko'rish")
async def show_users(message: types.Message):
    user_count = database.get_users_count()[0]
    await message.answer(f"Foydalanuvchilar soni: {user_count}")
    
    
# Admin foydalanuvchini to'lov qilgan deb tasdiqlashi
@dp.message_handler(text="💳 To'lovni tasdiqlash", user_id=ADMINS_ID)
async def payment_verification(message: types.Message):
    await message.answer("Foydalanuvchi chat ID sini kiriting:")
    await PaymentVerification.waiting_for_user_chat_id.set()



@dp.message_handler(state=PaymentVerification.waiting_for_user_chat_id)
async def process_payment_verification(message: types.Message, state: FSMContext):
    try:
        chat_id = int(message.text)
        if database.get_user(chat_id):
            # Foydalanuvchi to'lov qilgan deb belgilash va 30 kun davomida botdan foydalanish imkonini berish
            database.update_user_status(chat_id, 'True')
            database.update_user_expiry(chat_id, datetime.now() + timedelta(days=30))

            await message.answer(f"Foydalanuvchining to'lovi tasdiqlandi. U endi 30 kun davomida botdan foydalanishi mumkin.")
            await bot.send_message(chat_id, "Sizning to'lovingiz tasdiqlandi. Endi botdan foydalanishingiz mumkin.\n\n/start ni bosing va bemalol foydalaning")
        else:
            await message.answer("Bunday foydalanuvchi topilmadi.")
    except ValueError:
        await message.answer("Iltimos, to'g'ri chat ID kiriting.")

    await state.finish()

async def check_user_status():
    while True:
        users = database.get_all_users()
        for user in users:
            chat_id = user[3]
            expiry_date_str = user[5]

            if expiry_date_str:
                try:
                    # Millisekundlar bo'lgan formatni qabul qilish
                    expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d %H:%M:%S.%f')
                    if datetime.now() > expiry_date:
                        database.update_user_status(chat_id, False)
                        await bot.send_message(chat_id, "Sizning to'lov muddatingiz tugadi. Iltimos, yana to'lov qiling.\n\nTo'lob qilish uchun admin @Abdulloh_Mirasqarov")
                except ValueError as e:
                    # Agar format noto'g'ri bo'lsa
                    await bot.send_message(chat_id, f"Expiry date formatida xatolik bor. Administrator bilan bog'laning. ({e})")
            
        await asyncio.sleep(86400)  # 24 soatda bir marta

# Handler for the "📚 Darsliklar javobini ko'rish" command
@dp.message_handler(text="📚 Darsliklar javobini ko'rish")
async def darslik_handler(message: types.Message):
    chat_id = message.chat.id
    user_status = database.get_user_status(chat_id)
    
    if user_status == 'True':
        await message.answer("📔 Qaysi fan❓", reply_markup=fanlar())
        await Darslik.chooice_fan.set()
    else:
        await message.answer("Siz botdan foydalanishingiz uchun to'lov qilishingiz kerak.")

# Handler for selecting subject
@dp.message_handler(lambda message: message.text in subjects.keys(), state=Darslik.chooice_fan)
async def subject_handler(message: types.Message, state: FSMContext):
    subject_name = message.text
    await state.update_data(subject_name=subject_name)
    await message.answer(f"{subject_name} uchun mavzuni tanlang:", reply_markup=generate_subject_buttons(subject_name))
    await Darslik.waiting_for_mavzu.set()

# Handler for selecting topic
@dp.message_handler(state=Darslik.waiting_for_mavzu)
async def topic_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    subject_name = data.get("subject_name")
    topic_name = message.text

    # Check if "Orqaga" button was pressed
    if topic_name == "🔙 Orqaga":
        await start_command(message)
        await state.finish()
        return

    if topic_name in subjects[subject_name]:
        await state.update_data(topic_name=topic_name)
        await message.answer(f"{subject_name} -> {topic_name} uchun misol tanlang:", reply_markup=generate_problem_buttons(subject_name, topic_name))
        await Darslik.waiting_for_problem.set()

# Handler for selecting problem
@dp.message_handler(state=Darslik.waiting_for_problem)
async def problem_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    subject_name = data.get("subject_name")
    topic_name = data.get("topic_name")
    problem_name = message.text

    # Orqaga qaytish
    if problem_name == "🔙 Orqaga":
        await topic_handler(message, state)
        return

    # Misolni tanlash
    selected_problem = next((item for item in subjects[subject_name][topic_name] if item["name"] == problem_name), None)

    if selected_problem:
        images = selected_problem.get("images", [])
        caption = selected_problem.get("caption", "Bu misol uchun izoh mavjud emas.")

        # Rasmlarni bir guruhga to'plash
        media = [types.InputMediaPhoto(media=image, caption=caption if i == 0 else "") for i, image in enumerate(images)]
        
        if media:
            await message.answer_media_group(media)
        
        await message.answer("Bosh menu:", reply_markup=main())
        await state.finish()
    else:
        await message.answer("Iltimos, to'g'ri misol tanlang.")





async def on_start_up(dp):
    for admin_id in ADMINS_ID:
        await bot.send_message(chat_id=admin_id, text='Bot ishga tushdi!')

async def on_shutdown(dp):
    for admin_id in ADMINS_ID:
        await bot.send_message(chat_id=admin_id, text='Bot o\'chdi!')




if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(check_user_status())
#   executor.start_polling(dp, skip_updates=True, on_start_up=on_start_up, on_shutdown=on_shutdown)
    executor.start_polling(dp, skip_updates=True, on_startup=on_start_up, on_shutdown=on_shutdown)
