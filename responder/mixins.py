from django.utils.html import format_html


class VerificationAdminMixin:
    def main_passport_preview(self, obj):
        if obj.main_page_passport:
            return format_html(
                '<img src="{}" style="max-height: 120px;"/>',
                obj.main_page_passport.url
            )
        return "-"

    main_passport_preview.short_description = "Passport (main)"

    def registration_passport_preview(self, obj):
        if obj.registration_page_passport:
            return format_html(
                '<img src="{}" style="max-height: 120px;"/>',
                obj.registration_page_passport.url
            )
        return "-"

    registration_passport_preview.short_description = "Passport (registration)"

    def additional_passport_preview(self, obj):
        if obj.additional_information_passport:
            return format_html(
                '<img src="{}" style="max-height: 120px;"/>',
                obj.additional_information_passport.url
            )
        return "-"

    additional_passport_preview.short_description = "Passport (additional)"

    def round_video_preview(self, obj):
        if obj.round_video:
            return format_html(
                '''
                <video width="200" controls>
                    <source src="{}" type="video/mp4">
                </video>
                ''',
                obj.round_video.url
            )
        return "-"

    round_video_preview.short_description = "Round video"
