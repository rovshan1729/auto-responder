from aiogram.fsm.state import StatesGroup, State


class RegistrationState(StatesGroup):
    verification_id = State()
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


class WorkerState(StatesGroup):
    finish_work = State()
    merchant = State()
    dispute_count = State()
    cycle = State()
    get_problem = State()
    add_problem = State()


class HeadReportState(StatesGroup):
    date_from = State()
    date_to = State()


class BroadcastState(StatesGroup):
    text = State()


class MaskState(StatesGroup):
    groups = State()
    text = State()
    content = State()


class MaskEditState(StatesGroup):
    content = State()


class MaskEditGroupsState(StatesGroup):
    groups = State()
