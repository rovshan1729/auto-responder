from django import forms
from tinymce.widgets import TinyMCE

from .models import ReplyMessage


class ReplyMessageForm(forms.ModelForm):
    class Meta:
        model = ReplyMessage
        fields = (
            "text",
        )

        widgets = {
            "text": TinyMCE(attrs={'cols': 80, 'rows': 30, 'class': 'form-control'}),
        }




