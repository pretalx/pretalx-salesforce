from django.dispatch import receiver
from django.urls import reverse
from pretalx.common.signals import minimum_interval, periodic_task
from pretalx.orga.signals import nav_event_settings


@receiver(nav_event_settings)
def pretalx_salesforce_settings(sender, request, **kwargs):
    if not request.user.has_perm("event.update_event", sender):
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


@receiver(periodic_task)
@minimum_interval(minutes_after_success=60 * 8)
def periodic_salesforce_sync(sender, **kwargs):
    from .models import SalesforceSettings
    from .tasks import salesforce_event_sync

    for settings in SalesforceSettings.objects.all().filter(
        event__plugins__contains="pretalx_salesforce"
    ):
        if settings.sync_ready:
            salesforce_event_sync.apply_async(kwargs={"event_id": settings.event_id})
