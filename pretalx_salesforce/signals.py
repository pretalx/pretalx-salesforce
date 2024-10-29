
from django.dispatch import receiver
from django.urls import reverse
from pretalx.orga.signals import nav_event_settings


@receiver(nav_event_settings)
def pretalx_salesforce_settings(sender, request, **kwargs):
    if not request.user.has_perm("orga.change_settings", sender):
        return []
    return [
        {
            "label": "SalesForce integration",
            "url": reverse(
                "plugins:pretalx_salesforce:settings",
                kwargs={"event": request.event.slug},
            ),
            "active": request.resolver_match.url_name
            == "plugins:pretalx_salesforce:settings",
        }
    ]

