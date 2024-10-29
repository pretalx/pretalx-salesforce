from django import forms

from .models import SalesforceSettings


class SalesforceSettingsForm(forms.ModelForm):

    def __init__(self, *args, event=None, **kwargs):
        self.instance, _ = SalesforceSettings.objects.get_or_create(event=event)
        super().__init__(*args, **kwargs, instance=self.instance, locales=event.locales)

    class Meta:
        model = SalesforceSettings
        fields = (
            "client_id",
            "client_secret",
            "username",
            "password",
            "salesforce_instance",
        )
        widgets = {
            "password": forms.PasswordInput,
        }
