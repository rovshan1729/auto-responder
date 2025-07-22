from django import forms
from tinymce.widgets import TinyMCE

from .choices import GroupChoice
from .models import ReplyMessage, Mask


class ReplyMessageForm(forms.ModelForm):
    class Meta:
        model = ReplyMessage
        fields = (
            "text",
        )

        widgets = {
            "text": TinyMCE(attrs={'cols': 80, 'rows': 30, 'class': 'form-control'}),
        }



class MaskModelForm(forms.ModelForm):
    groups = forms.MultipleChoiceField(
        choices=GroupChoice.choices,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Mask
        fields = '__all__'



