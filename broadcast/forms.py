from django import forms
from responder.choices import GroupChoice
from broadcast.models import Broadcast


class BroadcastModelForm(forms.ModelForm):
    groups = forms.MultipleChoiceField(
        choices=GroupChoice.choices,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Broadcast
        fields = '__all__'


