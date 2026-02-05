from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.filters import Command, StateFilter

from bot.filters import users, common
from bot.handlers.users.handle import *
from bot.states.states import RegistrationState


def prepare_router():
    router = Router()
    router.message.filter(F.chat.type == ChatType.PRIVATE)
    router.message.filter(common.IsSleepFilter())

    router.message.register(support_worker_handler, Command("work")),
    router.message.register(kyc_command_handler, Command("kyc"))
    router.message.register(broadcast_command_handler, Command("broadcast"))
    router.message.register(head_report_command, Command("report"))
    router.message.register(add_merchant_handler, Command("addmerchant"))
    router.message.register(check_kyc_handler, Command("check_kyc"))
    router.message.register(mask_add_handler, Command("mask_add"))
    router.message.register(mask_find_handler, Command("mask_find"))
    router.message.register(mask_edit_handler, Command("mask_edit"))
    router.message.register(mask_edit_groups_handler, Command("mask_edit_groups"))
    router.message.register(mask_delete_handler, Command("mask_delete"))
    router.message.register(command_handler, users.IsCommandFilter())

    router.message.register(get_user_start_verification_handler, RegistrationState.start)
    router.message.register(start_verification_after_close_handler, F.text == "Приступить к верификации")
    router.message.register(get_phone_number_keyboard_handler, StateFilter(RegistrationState.phone_number), F.contact)
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

    router.callback_query.register(worker_start_work_handler, F.data == "stated_work")
    router.callback_query.register(worker_finish_work_handler, F.data == "finished_work")
    router.callback_query.register(cancel_finish_work_handler, F.data == "cancel")
    router.callback_query.register(dispute_add_handler, StateFilter(WorkerState.finish_work), F.data == "add_dispute")
    router.callback_query.register(get_merchant_handler, StateFilter(WorkerState.merchant),
                                   F.data.split("|")[0] == "merchant")
    router.message.register(get_problem_text_handler, WorkerState.get_problem)
    router.message.register(get_new_dispute_handler, WorkerState.new_dispute_count)
    router.message.register(get_resolved_dispute_count_handler, WorkerState.resolved_dispute_count)
    router.callback_query.register(get_add_more_dispute_handler, StateFilter(WorkerState.cycle),
                                   (F.data == "add_more_dispute") | (F.data == "add_more_text"))
    router.callback_query.register(get_add_problem_support_handler, F.data == "add_problem")
    router.message.register(get_add_problem_text_support_handler, WorkerState.add_problem)
    router.message.register(head_report_date_from_handler, HeadReportState.date_from)
    router.message.register(head_report_date_to_handler, HeadReportState.date_to)

    router.message.register(broadcast_title_handler, BroadcastState.title)
    router.message.register(broadcast_template_id_handler, BroadcastState.template_id)
    router.message.register(broadcast_content_handler, BroadcastState.content)
    router.callback_query.register(broadcast_group_choice, BroadcastState.group_choice,
                                   F.data.startswith("broadcast_group|"))
    router.callback_query.register(broadcast_group_done, BroadcastState.group_choice, F.data == "broadcast_group_done")
    router.message.register(broadcast_scheduled_at_handler, BroadcastState.scheduled_at)
    router.message.register(broadcast_media_file_handler, BroadcastState.media_file)
    router.message.register(broadcast_media_position_handler, BroadcastState.media_position)
    router.message.register(broadcast_button_title_handler, BroadcastState.get_button_title)
    router.message.register(broadcast_button_url_handler, BroadcastState.get_button_url)
    router.message.register(broadcast_button_order, BroadcastState.get_button_order)

    router.callback_query.register(mask_add_groups_choice, MaskState.groups, F.data.startswith("broadcast_group|"))

    router.callback_query.register(mask_add_groups_done, MaskState.groups, F.data == "broadcast_group_done")

    router.message.register(mask_add_text_handler, MaskState.text)
    router.message.register(mask_add_content_handler, MaskState.content)

    router.message.register(mask_edit_content_handler, MaskEditState.content)

    router.callback_query.register(mask_edit_groups_choice, MaskEditGroupsState.groups,
                                   F.data.startswith("broadcast_group|"))
    router.callback_query.register(mask_edit_groups_done, MaskEditGroupsState.groups, F.data == "broadcast_group_done")

    router.message.register(mask_handler)

    router.callback_query.register(accept_handler, F.data.split("|")[0] == "accepted")
    router.callback_query.register(closed_handler, F.data.split("|")[0] == "closed")
    router.message.register(respond_handler)

    return router
