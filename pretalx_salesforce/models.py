from django.db import models
from django.utils.translation import gettext_lazy as _


class SalesforceSettings(models.Model):
    event = models.OneToOneField(
        to="event.Event",
        on_delete=models.CASCADE,
        related_name="pretalx_salesforce_settings",
    )
    client_id = models.CharField(max_length=255, verbose_name=_("Client ID"))
    client_secret = models.CharField(max_length=255, verbose_name=_("Client Secret"))
    username = models.CharField(max_length=255, verbose_name=_("Username"))
    password = models.CharField(max_length=255, verbose_name=_("Password"))
    salesforce_instance = models.URLField(
        verbose_name=_("Salesforce URL"),
        default="https://salesforce.com",
        help_text=_(
            "Use https://salesforce.com for real data, or https://test.salesforce.com for sandbox data"
        ),
    )
