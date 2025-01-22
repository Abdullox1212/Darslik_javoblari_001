from aiogram.dispatcher.filters.state import State, StatesGroup

class Registration(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()


class Darslik(StatesGroup):
    chooice_sinf = State()  # Yangi holat qo'shildi
    chooice_fan = State()
    waiting_for_mavzu = State()
    waiting_for_problem = State()


class PaymentVerification(StatesGroup):
    waiting_for_user_chat_id = State()  # Foydalanuvchini ID bo'yicha qidirish
    waiting_for_payment_confirmation = State()  # To'lovni tasdiqlash


class Xabar_Yuborish(StatesGroup):
    waiting_for_message = State()
    waiting_for_image = State()