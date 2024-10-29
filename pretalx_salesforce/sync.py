import logging
from contextlib import suppress

import requests
from django.db.models import Count, Q
from django_scopes import scope
from pretalx.person.models import SpeakerProfile
from simple_salesforce import Salesforce

from pretalx_salesforce.models import (
    SalesforceSettings,
    SpeakerProfileSalesforceSync,
    SubmissionSalesforceSync,
)

logger = logging.getLogger(__name__)


def sync_event_with_salesforce(event):
    """
    Syncs an event with Salesforce. The sync maps objects as follows, and requires
    the custom ContactSession and Session objects to be created in Salesforce:

    - User/SpeakerProfile -> Contact, setting
        - Contact.pretalx_LegacyID__c = User.code
        - Contact.FirstName = User.name.split(" ", maxsplit=1)[0]
        - Contact.LastName = User.name.split(" ", maxsplit=1)[1] (or empty)
        - Contact.Email = User.email
        - Contact.Biography__c = User.event_profile.biography
        - Contact.Profile_Picture__c = User.avatar.url

    - [nothing] -> ContactSession
        - ID
        - Session__c = Session
        - Contact__c = Contact

    - Submission -> Session
        - ID
        - CreatedDate = Submission.created
        - pretalx_LegacyID__c = Submission.code
        - Name = Submission.title
        - Track__c = Submission.track.name
        - Status__c = Submission.state
        - Abstract__c = Submission.abstract + Submission.description
        - Pretalx_Record__c = Submission.urls.public.full
    """
    with suppress(Exception):
        sf = get_salesforce_client(event)

    if not sf:
        logger.error(
            f"Failed to get Salesforce client for event {event.slug}, aborting sync"
        )
        return

    with scope(event=event):
        salesforce_full_speaker_sync(sf, event)
        salesforce_full_submission_sync(sf, event)


def get_salesforce_client(event):
    try:
        salesforce_settings = event.pretalx_salesforce_settings
    except SalesforceSettings.DoesNotExist:
        logger.error(f"Salesforce settings for event {event.slug} do not exist.")
        return

    if (
        not salesforce_settings.client_id
        or not salesforce_settings.client_secret
        or not salesforce_settings.username
        or not salesforce_settings.password
    ):
        logger.error(f"Salesforce settings for event {event.slug} are incomplete.")
        return

    url = salesforce_settings.salesforce_instance or "https://salesforce.com"
    auth_url = f"{url}/services/oauth2/token"
    payload = {
        "grant_type": "password",
        "client_id": salesforce_settings.client_id,
        "client_secret": salesforce_settings.client_secret,
        "username": salesforce_settings.username,
        "password": salesforce_settings.password,
    }
    response = requests.post(auth_url, data=payload)
    if response.status_code != 200:
        logger.error(f"Failed to authenticate with Salesforce: {response.text}")
        return

    response = response.json()
    access_token = response["access_token"]
    instance_url = response["instance_url"]

    return Salesforce(instance_url=instance_url, session_id=access_token)


def salesforce_full_speaker_sync(sf, event):
    profiles = (
        SpeakerProfile.objects.filter(event=event)
        .select_related("user")
        .prefetch_related("user__submissions")
        .annotate(
            event_submission_count=Count(
                "user__submissions",
                distinct=True,
                filter=Q(user__submissions__event=event),
            )
        )
        .filter(event_submission_count__gt=0)
    )

    for profile in profiles:
        try:
            sync = profile.salesforce_profile_sync
        except SpeakerProfileSalesforceSync.DoesNotExist:
            sync = SpeakerProfileSalesforceSync.objects.create(profile=profile)

        sync.sync()


def salesforce_full_submission_sync(sf, event):
    submissions = event.submissions.all().prefetch_related("speakers")

    for submission in submissions:
        try:
            sync = submission.salesforce_submission_sync
        except SubmissionSalesforceSync.DoesNotExist:
            sync = SubmissionSalesforceSync.objects.create(submission=submission)

        sync.sync()
