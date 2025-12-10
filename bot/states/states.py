from aiogram.fsm.state import StatesGroup, State

class RegistrationState(StatesGroup):
    phone_number = State()
    addition_number = State()
    email = State()
