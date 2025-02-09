import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardRemove
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.utils import executor
from database import Database
from states import *
from buttons import *
from datetime import datetime, timedelta
import asyncio



# API_TOKEN = '8001791573:AAH1JpCZBj7_C64E4N-B0CdfBINQ_qiItlo'
API_TOKEN = '6824723033:AAFq5cP0TYi7DKvT84B2JZMyE8O2PSqOsZM'
ADMINS_ID = [1921911753, 7149602547]


logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
database = Database()
@dp.message_handler(commands="start")
async def start_command(message: types.Message):
    chat_id = message.chat.id
    full_name = message.from_user.full_name

    # Agar foydalanuvchi registratsiyadan o'tgan bo'lsa
    user = database.get_user(chat_id)
    if user:
        user_status = user[4]
        expiry_date_str = user[5]

        if user_status == False:
            await message.answer("Siz botdan foydalanishingiz uchun to'lov qilishingiz kerak.\n\nTo'lov qilish uchun admin @Abdulloh_Mirasqarov", protect_content=True)
        else:
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d %H:%M:%S.%f')
            await message.answer(f"Sizning to'lov muddatingiz: {expiry_date.date()} gacha", protect_content=True)
            await message.answer("Bugun nima qilamiz ❓", reply_markup=main(), protect_content=True)
    else:
        # Yangi foydalanuvchini ro'yxatdan o'tkazish
        await message.answer(f"👋 Salom {full_name}, botimizga xush kelibsiz!", protect_content=True)        
        await message.answer("Botdan foydalanish uchun ro'yxatdan o'tishingiz kerak! Ismingizni kiriting:", protect_content=True)
        await Registration.waiting_for_name.set()


@dp.message_handler(state=Registration.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Iltimos, telefon raqamingizni yuboring:", reply_markup=contact_keyboard(), protect_content=True)
    await Registration.waiting_for_phone.set()

@dp.message_handler(content_types=types.ContentType.CONTACT, state=Registration.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    contact = message.contact
    chat_id = message.chat.id

    if contact is None or contact.user_id != chat_id:
        await message.answer("Iltimos, o'z telefon raqamingizni yuboring.", protect_content=True)
        return

    data = await state.get_data()
    name = data['name']
    phone_number = contact.phone_number

    # Foydalanuvchini bazaga qo'shish (status False)
    database.add_user(name, phone_number, chat_id)

    await message.answer("Registratsiyadan muvaffaqqiyatli o'tdingiz! Endi botdan foydalanish uchun to'lov qilishingiz kerak.\n\nTo'lov qilish uchun admin @Abdulloh_Mirasqarov", reply_markup=ReplyKeyboardRemove(), protect_content=True)
    await state.finish()


@dp.message_handler(commands=['admin'])
async def send_admin_welcome(message: types.Message):
    full_name = message.from_user.full_name
    user_id = message.from_user.id
    for admin_id in ADMINS_ID:
        if user_id == admin_id:
            await message.answer(f"Salom, Hurmatli <b>{full_name}</b>! Botimizga xush kelibsiz", reply_markup=admin_buttons(), protect_content=True)
        else:
            pass

    


@dp.message_handler(text="👨‍💼 Foydalanuvchilarni ko'rish")
async def show_users(message: types.Message):
    user_count = database.get_users_count()[0]
    await message.answer(f"Foydalanuvchilar soni: {user_count}", protect_content=True)
    
    
# Admin foydalanuvchini to'lov qilgan deb tasdiqlashi
@dp.message_handler(text="💳 To'lovni tasdiqlash", user_id=ADMINS_ID)
async def payment_verification(message: types.Message):
    await message.answer("Foydalanuvchi chat ID sini kiriting:", protect_content=True)
    await PaymentVerification.waiting_for_user_chat_id.set()






@dp.message_handler(text="📨 Xabar yuborish", user_id=ADMINS_ID)
async def xabar_yutborish(message:types.Message):
    await message.answer("Rasm yuboring:")
    await Xabar_Yuborish.waiting_for_image.set()





@dp.message_handler(state=Xabar_Yuborish.waiting_for_image, content_types=types.ContentType.PHOTO)
async def admin_panel_image(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    await message.answer("Rasm qabul qilindi. Caption yuboring: ")
    await Xabar_Yuborish.waiting_for_message.set()

@dp.message_handler(state=Xabar_Yuborish.waiting_for_message)
async def admin_panel_caption(message: types.Message, state: FSMContext):
    caption = message.text
    data = await state.get_data()
    photo_id = data['photo_id']
    
    # Barcha foydalanuvchilarni olish
    chat_ids = database.get_all_chat_ids()
    
    # Har bir foydalanuvchiga rasm va caption yuborish
    for chat_id in chat_ids:
        try:
            await bot.send_photo(chat_id=chat_id, photo=photo_id, caption=caption)
        except Exception as e:
            logging.error(f"Failed to send photo to {chat_id}: {e}")
    
    await message.answer("Rasm va caption barcha foydalanuvchilarga yuborildi.")
    await state.finish()









@dp.message_handler(state=PaymentVerification.waiting_for_user_chat_id)
async def process_payment_verification(message: types.Message, state: FSMContext):
    try:
        chat_id = int(message.text)
        if database.get_user(chat_id):
            # Foydalanuvchi to'lov qilgan deb belgilash va 30 kun davomida botdan foydalanish imkonini berish
            database.update_user_status(chat_id, 'True')
            database.update_user_expiry(chat_id, datetime.now() + timedelta(days=30))

            await message.answer(f"Foydalanuvchining to'lovi tasdiqlandi. U endi 30 kun davomida botdan foydalanishi mumkin.")
            await bot.send_message(chat_id, "Sizning to'lovingiz tasdiqlandi. Endi botdan foydalanishingiz mumkin.\n\n/start ni bosing va bemalol foydalaning", protect_content=True)
        else:
            await message.answer("Bunday foydalanuvchi topilmadi.")
    except ValueError:
        await message.answer("Iltimos, to'g'ri chat ID kiriting.")

    await state.finish()
async def check_user_status():
    while True:
        users = database.get_all_users()
        for user in users:
            chat_id = user[1]
            expiry_date_str = user[5]
            
            if expiry_date_str:
                try:
                    expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d %H:%M:%S.%f')
                    time_left = expiry_date - datetime.now()

                    # Agar to'lov muddati tugashiga 2 kun qolgan bo'lsa
                    if 0 < time_left.days <= 2:
                        await bot.send_message(chat_id, "To'lov muddatingiz tugashiga 2 kundan kam vaqt qoldi. Iltimos, yana to'lov qiling.", protect_content=True)
                    
                    # Agar muddati tugagan bo'lsa
                    elif datetime.now() > expiry_date:
                        database.update_user_status(chat_id, False)
                        try:
                            await bot.send_message(chat_id, "Sizning to'lov muddatingiz tugadi. Iltimos, yana to'lov qiling.\n\nTo'lov qilish uchun admin @Abdulloh_Mirasqarov", protect_content=True)
                        except Exception as e:
                            logging.error(f"Failed to send message to {chat_id}: {e}")
                except ValueError as e:
                    await bot.send_message(chat_id, f"Expiry date formatida xatolik bor. Administrator bilan bog'laning. ({e})", protect_content=True)
            
        await asyncio.sleep(43200)  # 12 soatda bir marta tekshirish


# Handler for the "📚 Darsliklar javobini ko'rish" command
@dp.message_handler(text="📚 Darsliklar javobini ko'rish")
async def darslik_handler(message: types.Message):
    chat_id = message.chat.id
    user_status = database.get_user_status(chat_id)
    
    if user_status == 'True':
        await message.answer("Qaysi sinf❓", reply_markup=sinflar(), protect_content=True)
        await Darslik.chooice_sinf.set()
    else:
        await message.answer("Siz botdan foydalanishingiz uchun to'lov qilishingiz kerak.", protect_content=True)

# Handler for selecting sinf
@dp.message_handler(state=Darslik.chooice_sinf)
async def sinf_handler(message: types.Message, state: FSMContext):
    sinf_name = message.text
    await state.update_data(sinf_name=sinf_name)
    await message.answer("📔 Qaysi fan❓", reply_markup=fanlar(sinf_name), protect_content=True)
    await Darslik.chooice_fan.set()

@dp.message_handler(state=Darslik.chooice_fan)
async def subject_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    sinf_name = data.get("sinf_name")
    subject_name = message.text
    if subject_name in subjects[sinf_name]:
        await state.update_data(subject_name=subject_name)
        await message.answer(f"{subject_name} uchun mavzuni tanlang:", reply_markup=generate_subject_buttons(sinf_name, subject_name))
        await Darslik.waiting_for_mavzu.set()
    else:
        await message.answer("Iltimos, to'g'ri fan tanlang.", protect_content=True)

# Handler for selecting topic
@dp.message_handler(state=Darslik.waiting_for_mavzu)
async def topic_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    sinf_name = data.get("sinf_name")
    subject_name = data.get("subject_name")
    topic_name = message.text

    # Check if "Orqaga" button was pressed
    if topic_name == "🔙 Orqaga":
        await subject_handler(message, state)
        return

    if topic_name in subjects[sinf_name][subject_name]:
        await state.update_data(topic_name=topic_name)
        await message.answer(f"{subject_name} -> {topic_name} uchun misol tanlang:", reply_markup=generate_problem_buttons(sinf_name, subject_name, topic_name), protect_content=True)
        await Darslik.waiting_for_problem.set()

# Handler for selecting problem
@dp.message_handler(state=Darslik.waiting_for_problem)
async def problem_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    sinf_name = data.get("sinf_name")
    subject_name = data.get("subject_name")
    topic_name = data.get("topic_name")
    problem_name = message.text

    # Orqaga qaytish
    if problem_name == "🔙 Orqaga":
        await topic_handler(message, state)
        return

    # Misolni tanlash
    selected_problem = next((item for item in subjects[sinf_name][subject_name][topic_name] if item["name"] == problem_name), None)

    if selected_problem:
        images = selected_problem.get("images", [])
        caption = selected_problem.get("caption", "Bu misol uchun izoh mavjud emas.")

        # Rasmlarni bir guruhga to'plash
        media = [types.InputMediaPhoto(media=image, caption=caption if i == 0 else "") for i, image in enumerate(images)]
        
        if media:
            await message.answer_media_group(media, protect_content=True)
        
        await message.answer("Bosh menu:", reply_markup=main(), protect_content=True)
        await state.finish()
    else:
        await message.answer("Iltimos, to'g'ri misol tanlang.", protect_content=True)

# Foydalanuvchini qidirish
@dp.message_handler(state=PaymentVerification.waiting_for_user_chat_id, content_types=types.ContentTypes.TEXT)
async def process_user_search(message: types.Message, state: FSMContext):
    user_input = message.text
    user = None

    # Foydalanuvchini chat ID bo'yicha qidirish
    if user_input.isdigit():
        user = database.get_user_by_chat_id(int(user_input))  # Foydalanuvchini chat ID bo'yicha olish
    else:
        # Agar raqam kiritilmagan bo'lsa, ismi bo'yicha qidirish
        user = database.get_user_by_name(user_input)

    if user:
        await state.update_data(user=user)
        await message.answer(f"Foydalanuvchi topildi: {user['name']}\nTo'lov holati: {'Tolangan' if user['paid'] else 'Tolanmagan'}\nTasdiqlash uchun 'Tasdiqlash' tugmasini bosing.")

        await PaymentVerification.waiting_for_payment_confirmation.set()
    else:
        await message.answer("Foydalanuvchi topilmadi. Iltimos, qaytadan urinib ko'ring.")
        await PaymentVerification.waiting_for_user_chat_id.set()

# To'lovni tasdiqlash
@dp.message_handler(state=PaymentVerification.waiting_for_payment_confirmation, content_types=types.ContentTypes.TEXT)
async def confirm_payment(message: types.Message, state: FSMContext):
    if message.text.lower() == "tasdiqlash":
        data = await state.get_data()
        user = data.get('user')
        database.mark_user_as_paid(user['chat_id'])  # Foydalanuvchini to'lagan sifatida belgilash
        await message.answer(f"Foydalanuvchi {user['name']} to'lov holati muvaffaqiyatli tasdiqlandi!", protect_content=True)
        await state.finish()
    else:
        await message.answer("To'lovni tasdiqlash uchun \"Tasdiqlash\" deb yozing.")



@dp.message_handler(text="👤 User chatini tozalash", user_id=ADMINS_ID)
async def clear_user_chat(message: types.Message):
    await message.answer("Foydalanuvchi chat ID sini kiriting:", protect_content=True)
    await User_Chatini_Tozalash.waiting_for_user_chat_id.set()

@dp.message_handler(state=User_Chatini_Tozalash.waiting_for_user_chat_id)
async def process_clear_user_chat(message: types.Message, state: FSMContext):
    try:
        chat_id = int(message.text)  # Foydalanuvchi ID sini olish
        deleted_count = 0  # O'chirilgan xabarlar sonini sanash

        for message_id in range(message.message_id, message.message_id - 500, -1):  # Oxirgi 500 ta xabarni tekshirish
            try:
                await bot.delete_message(chat_id, message_id)
                deleted_count += 1
                await asyncio.sleep(0.1)  # Telegram rate limit dan qochish
            except Exception:
                continue  # Agar xabar topilmasa, davom etamiz

        await message.answer(f"✅ Bot yuborgan {deleted_count} ta xabar o‘chirildi.", reply_markup=admin_buttons(), protect_content=True)

    except ValueError:
        await message.answer("🚫 Noto‘g‘ri chat ID! Raqam kiriting.",reply_markup=admin_buttons())
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}",reply_markup=admin_buttons())

    await state.finish()



async def on_start_up(dp):
    for admin_id in ADMINS_ID:
        await bot.send_message(chat_id=admin_id, text='Bot ishga tushdi!')

async def on_shutdown(dp):
    for admin_id in ADMINS_ID:
        await bot.send_message(chat_id=admin_id, text='Bot o\'chdi!')





if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(check_user_status())
    executor.start_polling(dp, skip_updates=True, on_startup=on_start_up, on_shutdown=on_shutdown)
