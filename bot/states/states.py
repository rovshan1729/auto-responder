from aiogram.fsm.state import StatesGroup, State

class UserStartState(StatesGroup):
    phone_number = State()

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
    new_dispute_count = State()
    resolved_dispute_count = State()
    cycle = State()
    get_problem = State()
    add_problem = State()


class HeadReportState(StatesGroup):
    date_from = State()
    date_to = State()


class BroadcastState(StatesGroup):
    title = State()
    template_id = State()
    content = State()
    group_choice = State()
    scheduled_at = State()
    media_file = State()
    media_position = State()
    get_button_title = State()
    get_button_url = State()
    get_button_order = State()


class MaskState(StatesGroup):
    groups = State()
    text = State()
    content = State()


class MaskEditState(StatesGroup):
    content = State()


class MaskEditGroupsState(StatesGroup):
    groups = State()
