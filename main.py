import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardRemove, InputMediaPhoto
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.utils import executor
from database import Database
from states import *
from buttons import *
from datetime import datetime, timedelta
import asyncio
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DarslikBot:
    def __init__(self, token: str, admin_ids: List[int]):
        self.bot = Bot(token=token, parse_mode="HTML")
        self.storage = MemoryStorage()
        self.dp = Dispatcher(self.bot, storage=self.storage)
        self.db = Database()
        self.admin_ids = admin_ids
        
        # Register handlers
        self._register_handlers()
        
    def _register_handlers(self):
        # User handlers
        self.dp.register_message_handler(self.start_command, commands="start")
        self.dp.register_message_handler(self.process_name, state=Registration.waiting_for_name)
        self.dp.register_message_handler(self.process_phone, content_types=types.ContentType.CONTACT, state=Registration.waiting_for_phone)
        
        # Darslik handlers
        self.dp.register_message_handler(self.darslik_handler, text="📚 Darsliklar javobini ko'rish")
        self.dp.register_message_handler(self.sinf_handler, state=Darslik.chooice_sinf)
        self.dp.register_message_handler(self.subject_handler, state=Darslik.chooice_fan)
        self.dp.register_message_handler(self.topic_handler, state=Darslik.waiting_for_mavzu)
        self.dp.register_message_handler(self.problem_handler, state=Darslik.waiting_for_problem)

        # Asoschi handler
        self.dp.register_message_handler(
            lambda message: message.answer("""👨‍🏫 Asoschi haqida ma'lumot:
<b>Abdulloh Mirasqarov</b> - 2011-yil 14-may kuni Toshkent shahrida tug'ilgan. Hozirda u yuzlab loyihalar yaratgan, jumladan, Telegram botlari va veb-saytlar. U dasturlashni 2023-yilda boshlagan va hozirda o'zining Telegram botlari va veb-saytlari orqali foydalanuvchilarga yordam beradi."""), text="👨‍🏫 Asoschi haqida"
        )

        # Admin handlers
        self.dp.register_message_handler(self.admin_panel, commands=['admin'], user_id=self.admin_ids)
        self.dp.register_message_handler(self.show_users, text="👨‍💼 Foydalanuvchilarni ko'rish", user_id=self.admin_ids)
        self.dp.register_message_handler(self.payment_verification, text="💳 To'lovni tasdiqlash", user_id=self.admin_ids)
        self.dp.register_message_handler(self.process_payment_verification, state=PaymentVerification.waiting_for_user_chat_id)
        self.dp.register_message_handler(self.broadcast_message, text="📨 Xabar yuborish", user_id=self.admin_ids)
        self.dp.register_message_handler(self.process_broadcast_image, state=Xabar_Yuborish.waiting_for_image, content_types=types.ContentType.PHOTO)
        self.dp.register_message_handler(self.process_broadcast_caption, state=Xabar_Yuborish.waiting_for_message)
        self.dp.register_message_handler(self.clear_user_chat, text="👤 User chatini tozalash", user_id=self.admin_ids)
        self.dp.register_message_handler(self.process_clear_user_chat, state=User_Chatini_Tozalash.waiting_for_user_chat_id)
    
    async def start_command(self, message: types.Message):
        """Bosh menyuni ko'rsatish va foydalanuvchini tekshirish"""
        chat_id = message.chat.id
        full_name = message.from_user.full_name
        
        try:
            user = self.db.get_user(chat_id)
            if user:
                await self._handle_existing_user(user, chat_id)
            else:
                await self._start_registration(message, full_name)
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await message.answer("⚠️ Botda texnik nosozlik yuz berdi. Iltimos, keyinroq urinib ko'ring.")

    async def _handle_existing_user(self, user: Tuple, chat_id: int):
        """Mavjud foydalanuvchi uchun ishlov"""
        user_status = user[4]
        expiry_date_str = user[5]

        if not user_status:
            await self.bot.send_message(
                chat_id,
                "Siz botdan foydalanishingiz uchun to'lov qilishingiz kerak.\n\nTo'lov qilish uchun admin @Abdulloh_Mirasqarov",
                protect_content=True
            )
        else:
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d %H:%M:%S.%f')
            await self.bot.send_message(
                chat_id,
                f"Sizning to'lov muddatingiz: {expiry_date.date()} gacha",
                protect_content=True
            )
            await self.bot.send_message(
                chat_id,
                "Bugun nima qilamiz ❓",
                reply_markup=main(),
                protect_content=True
            )

    async def _start_registration(self, message: types.Message, full_name: str):
        """Yangi foydalanuvchi registratsiyasi"""
        await message.answer(
            f"👋 Salom {full_name}, botimizga xush kelibsiz!",
            protect_content=True
        )
        await message.answer(
            "Botdan foydalanish uchun ro'yxatdan o'tishingiz kerak! Ismingizni kiriting:",
            protect_content=True
        )
        await Registration.waiting_for_name.set()

    async def process_name(self, message: types.Message, state: FSMContext):
        """Ismni qabul qilish"""
        await state.update_data(name=message.text)
        await message.answer(
            "Iltimos, telefon raqamingizni yuboring:",
            reply_markup=contact_keyboard(),
            protect_content=True
        )
        await Registration.waiting_for_phone.set()

    async def process_phone(self, message: types.Message, state: FSMContext):
        """Telefon raqamini qabul qilish"""
        contact = message.contact
        chat_id = message.chat.id

        if contact is None or contact.user_id != chat_id:
            await message.answer("Iltimos, o'z telefon raqamingizni yuboring.", protect_content=True)
            return

        data = await state.get_data()
        name = data['name']
        phone_number = contact.phone_number

        try:
            self.db.add_user(name, phone_number, chat_id)
            await message.answer(
                "Registratsiyadan muvaffaqqiyatli o'tdingiz! Endi botdan foydalanish uchun to'lov qilishingiz kerak.\n\nTo'lov qilish uchun admin @Abdulloh_Mirasqarov",
                reply_markup=ReplyKeyboardRemove(),
                protect_content=True
            )
        except Exception as e:
            logger.error(f"Error adding user to DB: {e}")
            await message.answer("⚠️ Registratsiya jarayonida xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

        await state.finish()

    # DARSLIKLAR BOLIMI ======================================================
    async def darslik_handler(self, message: types.Message):
        """Darsliklar bo'limini boshlash"""
        chat_id = message.chat.id
        try:
            user_status = self.db.get_user_status(chat_id)
            
            if user_status == 'True':
                await message.answer("Qaysi sinf❓", reply_markup=sinflar(), protect_content=True)
                await Darslik.chooice_sinf.set()
            else:
                await message.answer("Siz botdan foydalanishingiz uchun to'lov qilishingiz kerak.", protect_content=True)
        except Exception as e:
            logger.error(f"Error in darslik handler: {e}")
            await message.answer("⚠️ Darsliklarni yuklashda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.")

    async def sinf_handler(self, message: types.Message, state: FSMContext):
        """Sinfni tanlash"""
        sinf_name = message.text
        await state.update_data(sinf_name=sinf_name)
        await message.answer(
            "📔 Qaysi fan❓",
            reply_markup=fanlar(sinf_name),
            protect_content=True
        )
        await Darslik.chooice_fan.set()

    async def subject_handler(self, message: types.Message, state: FSMContext):
        """Fanni tanlash"""
        data = await state.get_data()
        sinf_name = data.get("sinf_name")
        subject_name = message.text
        
        try:
            if subject_name in subjects[sinf_name]:
                await state.update_data(subject_name=subject_name)
                await message.answer(
                    f"{subject_name} uchun mavzuni tanlang:",
                    reply_markup=generate_subject_buttons(sinf_name, subject_name)
                )
                await Darslik.waiting_for_mavzu.set()
            else:
                await message.answer("Iltimos, to'g'ri fan tanlang.", protect_content=True)
        except KeyError:
            await message.answer("⚠️ Kechirasiz, bu sinf uchun fanlar topilmadi.")
            await state.finish()

    async def topic_handler(self, message: types.Message, state: FSMContext):
        """Mavzuni tanlash"""
        data = await state.get_data()
        sinf_name = data.get("sinf_name")
        subject_name = data.get("subject_name")
        topic_name = message.text

        # Orqaga qaytish
        if topic_name == "🔙 Orqaga":
            await self.subject_handler(message, state)
            return

        try:
            if topic_name in subjects[sinf_name][subject_name]:
                await state.update_data(topic_name=topic_name)
                await message.answer(
                    f"{subject_name} -> {topic_name} uchun misol tanlang:",
                    reply_markup=generate_problem_buttons(sinf_name, subject_name, topic_name),
                    protect_content=True
                )
                await Darslik.waiting_for_problem.set()
        except KeyError:
            await message.answer("⚠️ Kechirasiz, bu mavzuda misollar topilmadi.")
            await state.finish()

    async def problem_handler(self, message: types.Message, state: FSMContext):
        """Misolni tanlash va ko'rsatish"""
        data = await state.get_data()
        sinf_name = data.get("sinf_name")
        subject_name = data.get("subject_name")
        topic_name = data.get("topic_name")
        problem_name = message.text

        # Orqaga qaytish
        if problem_name == "🔙 Orqaga":
            await self.topic_handler(message, state)
            return

        try:
            selected_problem = next(
                (item for item in subjects[sinf_name][subject_name][topic_name] 
                 if item["name"] == problem_name),
                None
            )

            if selected_problem:
                await self._send_problem_solution(message, selected_problem)
            else:
                await message.answer("Iltimos, to'g'ri misol tanlang.", protect_content=True)
        except Exception as e:
            logger.error(f"Error showing problem: {e}")
            await message.answer("⚠️ Misolni ko'rsatishda xatolik yuz berdi.")

        await message.answer("Bosh menu:", reply_markup=main(), protect_content=True)
        await state.finish()

    async def _send_problem_solution(self, message: types.Message, problem: Dict):
        """Misol yechimini yuborish"""
        images = problem.get("images", [])
        caption = problem.get("caption", "Bu misol uchun izoh mavjud emas.")

        if images:
            media = [
                InputMediaPhoto(media=image, caption=caption if i == 0 else "") 
                for i, image in enumerate(images)
            ]
            await message.answer_media_group(media, protect_content=True)
        else:
            await message.answer(caption, protect_content=True)

    # ADMIN FUNCTIONS ========================================================
    async def admin_panel(self, message: types.Message):
        """Admin panelini ko'rsatish"""
        full_name = message.from_user.full_name
        await message.answer(
            f"Salom, Hurmatli <b>{full_name}</b>! Botimizga xush kelibsiz",
            reply_markup=admin_buttons(),
            protect_content=True
        )

    async def show_users(self, message: types.Message):
        """Foydalanuvchilar sonini ko'rsatish"""
        try:
            user_count = self.db.get_users_count()[0]
            await message.answer(
                f"📊 Statistikalar:\n\n"
                f"🔹 Jami foydalanuvchilar: {user_count}\n",
                protect_content=True
            )
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            await message.answer("⚠️ Statistikani yuklashda xatolik yuz berdi.")

    async def payment_verification(self, message: types.Message):
        """To'lovni tasdiqlash jarayonini boshlash"""
        await message.answer("Foydalanuvchi chat ID sini kiriting:", protect_content=True)
        await PaymentVerification.waiting_for_user_chat_id.set()

    async def process_payment_verification(self, message: types.Message, state: FSMContext):
        """To'lovni tasdiqlash"""
        try:
            chat_id = int(message.text)
            user = self.db.get_user(chat_id)
            
            if user:
                self.db.update_user_status(chat_id, 'True')
                self.db.update_user_expiry(chat_id, datetime.now() + timedelta(days=30))

                await message.answer(
                    f"Foydalanuvchining to'lovi tasdiqlandi. U endi 30 kun davomida botdan foydalanishi mumkin."
                )
                await self.bot.send_message(
                    chat_id,
                    "Sizning to'lovingiz tasdiqlandi. Endi botdan foydalanishingiz mumkin.\n\n/start ni bosing va bemalol foydalaning",
                    protect_content=True
                )
            else:
                await message.answer("Bunday foydalanuvchi topilmadi.")
        except ValueError:
            await message.answer("Iltimos, to'g'ri chat ID kiriting.")
        except Exception as e:
            logger.error(f"Error in payment verification: {e}")
            await message.answer("⚠️ To'lovni tasdiqlashda xatolik yuz berdi.")

        await state.finish()

    async def broadcast_message(self, message: types.Message):
        """Xabar yuborishni boshlash"""
        await message.answer("Rasm yuboring:")
        await Xabar_Yuborish.waiting_for_image.set()

    async def process_broadcast_image(self, message: types.Message, state: FSMContext):
        """Broadcast uchun rasmni qabul qilish"""
        photo_id = message.photo[-1].file_id
        await state.update_data(photo_id=photo_id)
        await message.answer("Rasm qabul qilindi. Caption yuboring: ")
        await Xabar_Yuborish.waiting_for_message.set()

    async def process_broadcast_caption(self, message: types.Message, state: FSMContext):
        """Broadcast xabarini yuborish"""
        caption = message.text
        data = await state.get_data()
        photo_id = data['photo_id']
        
        try:
            chat_ids = self.db.get_all_chat_ids()
            success = 0
            failed = 0
            
            for chat_id in chat_ids:
                try:
                    await self.bot.send_photo(
                        chat_id=chat_id,
                        photo=photo_id,
                        caption=caption
                    )
                    success += 1
                    await asyncio.sleep(0.1)  # Rate limit uchun
                except Exception as e:
                    logger.error(f"Failed to send to {chat_id}: {e}")
                    failed += 1
            
            await message.answer(
                f"📊 Xabar yuborish natijasi:\n\n"
                f"✅ Muvaffaqiyatli: {success}\n"
                f"❌ Xatolik: {failed}"
            )
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
            await message.answer("⚠️ Xabar yuborishda xatolik yuz berdi.")

        await state.finish()

    async def clear_user_chat(self, message: types.Message):
        """Foydalanuvchi chatini tozalash"""
        await message.answer("Foydalanuvchi chat ID sini kiriting:", protect_content=True)
        await User_Chatini_Tozalash.waiting_for_user_chat_id.set()

    async def process_clear_user_chat(self, message: types.Message, state: FSMContext):
        """Foydalanuvchi chatini tozalash jarayoni"""
        try:
            chat_id = int(message.text)
            deleted_count = 0

            for message_id in range(message.message_id, message.message_id - 500, -1):
                try:
                    await self.bot.delete_message(chat_id, message_id)
                    deleted_count += 1
                    await asyncio.sleep(0.1)
                except Exception:
                    continue

            await message.answer(
                f"✅ Bot yuborgan {deleted_count} ta xabar o'chirildi.",
                reply_markup=admin_buttons(),
                protect_content=True
            )
        except ValueError:
            await message.answer(
                "🚫 Noto'g'ri chat ID! Raqam kiriting.",
                reply_markup=admin_buttons()
            )
        except Exception as e:
            await message.answer(
                f"❌ Xatolik: {e}",
                reply_markup=admin_buttons()
            )

        await state.finish()

    async def on_startup(self, dp):
        """Bot ishga tushganda"""
        for admin_id in self.admin_ids:
            try:
                await self.bot.send_message(admin_id, 'Bot ishga tushdi!')
            except Exception as e:
                logger.error(f"Error sending startup message to admin {admin_id}: {e}")

    async def on_shutdown(self, dp):
        """Bot o'chganda"""
        for admin_id in self.admin_ids:
            try:
                await self.bot.send_message(admin_id, 'Bot o\'chdi!')
            except Exception as e:
                logger.error(f"Error sending shutdown message to admin {admin_id}: {e}")

    def run(self):
        """Botni ishga tushirish"""
        executor.start_polling(
            self.dp,
            skip_updates=True,
            on_startup=self.on_startup,
            on_shutdown=self.on_shutdown
        )


if __name__ == '__main__':
    API_TOKEN = '6824723033:AAFq5cP0TYi7DKvT84B2JZMyE8O2PSqOsZM'
    ADMINS_ID = [7149602547]
    
    bot = DarslikBot(API_TOKEN, ADMINS_ID)
    
    # Check user status periodically
    async def check_user_status():
        while True:
            try:
                users = bot.db.get_all_users()
                for user in users:
                    chat_id = user[1]
                    expiry_date_str = user[5]
                    
                    if expiry_date_str:
                        expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d %H:%M:%S.%f')
                        time_left = expiry_date - datetime.now()

                        if 0 < time_left.days <= 2:
                            await bot.bot.send_message(
                                chat_id,
                                "To'lov muddatingiz tugashiga 2 kundan kam vaqt qoldi. Iltimos, yana to'lov qiling.",
                                protect_content=True
                            )
                        
                        elif datetime.now() > expiry_date:
                            bot.db.update_user_status(chat_id, False)
                            await bot.bot.send_message(
                                chat_id,
                                "Sizning to'lov muddatingiz tugadi. Iltimos, yana to'lov qiling.\n\nTo'lov qilish uchun admin @Abdulloh_Mirasqarov",
                                protect_content=True
                            )
            except Exception as e:
                logger.error(f"Error in check_user_status: {e}")
            
            await asyncio.sleep(43200)  # 12 soatda bir tekshirish

    # Background taskni ishga tushirish
    loop = asyncio.get_event_loop()
    loop.create_task(check_user_status())
    
    # Botni ishga tushirish
    bot.run()