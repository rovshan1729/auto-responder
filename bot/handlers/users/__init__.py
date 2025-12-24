from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.filters import Command

from bot.filters import users, common
from bot.handlers.users.handle import *
from bot.states.states import RegistrationState


def prepare_router():
    router = Router()
    router.message.filter(F.chat.type == ChatType.PRIVATE)
    router.message.filter(common.IsSleepFilter())

    router.message.register(kyc_command_handler, Command("kyc"))
    router.message.register(get_user_start_verification_handler, RegistrationState.start)
    router.message.register(get_phone_number_keyboard_handler, RegistrationState.phone_number)
    router.message.register(get_phone_number_addition_handler, RegistrationState.addition_number)
    router.message.register(get_email_handler, RegistrationState.email)
    router.message.register(get_token_handler, RegistrationState.token)
    router.message.register(get_team_lead_handler, RegistrationState.team_lead)
    router.message.register(get_recommend_user_handler, RegistrationState.recommend_user)
    router.message.register(get_country_handler, RegistrationState.country)
    router.message.register(get_user_fullname_handler, RegistrationState.fullname)
    router.message.register(get_user_current_live_address_handler, RegistrationState.live_address)
    router.message.register(get_user_main_page_passport_handler, RegistrationState.main_page_passport)
    router.message.register(get_user_registration_page_passport_handler, RegistrationState.registration_page_passport)
    router.message.register(get_user_additional_information_passport_handler,
                            RegistrationState.additional_information_passport)
    router.message.register(get_user_round_video_handler, RegistrationState.round_video)
    router.message.register(get_user_geo_handler, RegistrationState.geo)
    router.message.register(get_user_experience_handler, RegistrationState.experience)
    router.message.register(get_user_worked_platform_handler, RegistrationState.worked_platform)
    router.message.register(get_user_recommendation_user_contact_handler, RegistrationState.recommendation_user_contact)



    router.message.register(command_handler, users.IsCommandFilter())
    router.callback_query.register(accept_handler, F.data.split("|")[0] == "accepted")
    router.callback_query.register(closed_handler, F.data.split("|")[0] == "closed")
    router.message.register(respond_handler)

    return router
