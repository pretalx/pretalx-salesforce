from pretalx.celery_app import app


@app.task(name="pretalx_salesforce.salesforce_event_sync")
def salesforce_event_sync(*args, event_id=None, **kwargs):
    from pretalx.event.models import Event

    from pretalx_salesforce.sync import sync_event_with_salesforce

    event = Event.objects.get(pk=event_id)
    sync_event_with_salesforce(event=event)
