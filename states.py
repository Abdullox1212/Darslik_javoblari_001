from aiogram.dispatcher.filters.state import State, StatesGroup

class Registration(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()

class PaymentVerification(StatesGroup):
    waiting_for_user_chat_id = State()

class Darslik(StatesGroup):
    chooice_fan = State()
    waiting_for_mavzu = State()
    waiting_for_problem = State()
