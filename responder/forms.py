from django import forms

from .models import ReplyMessage


class ReplyMessageForm(forms.ModelForm):
    class Meta:
        model = ReplyMessage
        fields = (
            "text", "is_retry"
        )




