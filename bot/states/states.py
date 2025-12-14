from aiogram.fsm.state import StatesGroup, State


class RegistrationState(StatesGroup):
    start = State()
    phone_number = State()
    addition_number = State()
    email = State()
    token = State()
    team_lead = State()
    recommend_user = State()
    country = State()

    fullname = State()
    live_address = State()
    main_page_passport = State()
    registration_page_passport = State()
    additional_information_passport = State()
    round_video = State()
    geo = State()
    experience = State()
    worked_platform = State()
    recommendation_user_contact = State()
    verify = State()
