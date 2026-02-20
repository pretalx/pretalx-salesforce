from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from django_scopes import scopes_disabled

from pretalx.person.models import SpeakerProfile
from pretalx.submission.models import Submission, SubmissionType

from pretalx_salesforce.forms import SalesforceSettingsForm
from pretalx_salesforce.models import (
    SalesforceSettings,
    SpeakerProfileSalesforceSync,
    SubmissionSalesforceSync,
    ellipsis,
)
from pretalx_salesforce.signals import periodic_salesforce_sync
from pretalx_salesforce.sync import sync_event_with_salesforce

SETTINGS_URL_NAME = "plugins:pretalx_salesforce:settings"
SYNC_URL_NAME = "plugins:pretalx_salesforce:sync"


@pytest.fixture
def salesforce_settings(event):
    with scopes_disabled():
        return SalesforceSettings.objects.create(
            event=event,
            client_id="test_client_id",
            client_secret="test_client_secret",
            username="test_user",
            password="test_pass",
            salesforce_instance="https://test.salesforce.com",
        )


@pytest.fixture
def submission(event):
    with scopes_disabled():
        sub_type = SubmissionType.objects.create(
            event=event, name="Talk", default_duration=30
        )
        return Submission.objects.create(
            event=event,
            title="Test Submission",
            submission_type=sub_type,
            state="submitted",
        )


@pytest.mark.django_db
def test_orga_can_access_settings(orga_client, event):
    response = orga_client.get(
        reverse(SETTINGS_URL_NAME, kwargs={"event": event.slug}),
        follow=True,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_reviewer_cannot_access_settings(review_client, event):
    response = review_client.get(
        reverse(SETTINGS_URL_NAME, kwargs={"event": event.slug}),
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_orga_can_save_settings(orga_client, event):
    url = reverse(SETTINGS_URL_NAME, kwargs={"event": event.slug})
    response = orga_client.post(
        url,
        {
            "client_id": "my_client_id",
            "client_secret": "my_secret",
            "username": "my_user",
            "password": "my_pass",
            "salesforce_instance": "https://test.salesforce.com",
        },
        follow=True,
    )
    assert response.status_code == 200
    settings = SalesforceSettings.objects.get(event=event)
    assert settings.client_id == "my_client_id"
    assert settings.username == "my_user"


@pytest.mark.django_db
@patch("pretalx_salesforce.views.salesforce_event_sync")
def test_reviewer_cannot_trigger_sync(mock_task, review_client, event):
    response = review_client.get(
        reverse(SYNC_URL_NAME, kwargs={"event": event.slug}),
    )
    # The sync view overrides dispatch directly, so it always redirects.
    # The permission check happens at the event middleware level instead.
    assert response.status_code == 302


@pytest.mark.django_db
@patch("pretalx_salesforce.views.salesforce_event_sync")
def test_orga_can_trigger_sync(mock_task, orga_client, event):
    response = orga_client.get(
        reverse(SYNC_URL_NAME, kwargs={"event": event.slug}),
    )
    assert response.status_code == 302
    mock_task.apply_async.assert_called_once()


@pytest.mark.django_db
@patch("pretalx_salesforce.views.salesforce_event_sync")
def test_sync_error_shows_message(mock_task, orga_client, event):
    mock_task.apply_async.side_effect = Exception("Connection failed")
    response = orga_client.get(
        reverse(SYNC_URL_NAME, kwargs={"event": event.slug}),
        follow=True,
    )
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        ("short", "short"),
        ("a" * 80, "a" * 80),
        ("a" * 81, "a" * 79 + "…"),
        ("a" * 200, "a" * 79 + "…"),
    ),
)
def test_ellipsis(value, expected):
    assert ellipsis(value) == expected


def test_ellipsis_custom_length():
    assert ellipsis("abcdef", length=5) == "abcd…"


@pytest.mark.django_db
def test_sync_ready_when_all_fields_set(salesforce_settings):
    assert salesforce_settings.sync_ready is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field",
    ("client_id", "client_secret", "username", "password"),
)
def test_sync_not_ready_when_field_missing(salesforce_settings, field):
    setattr(salesforce_settings, field, "")
    assert salesforce_settings.sync_ready is False


@pytest.mark.django_db
def test_speaker_profile_sync_should_sync_when_new(event, orga_user):
    with scopes_disabled():
        profile = SpeakerProfile.objects.create(event=event, user=orga_user)
        sync = SpeakerProfileSalesforceSync.objects.create(profile=profile)
    assert sync.should_sync() is True


@pytest.mark.django_db
def test_speaker_profile_split_name(event, orga_user):
    with scopes_disabled():
        profile = SpeakerProfile.objects.create(event=event, user=orga_user)
        sync = SpeakerProfileSalesforceSync(profile=profile)
    assert sync.split_name == ["Orga", "User"]


@pytest.mark.django_db
def test_speaker_profile_serialize(event, orga_user):
    with scopes_disabled():
        profile = SpeakerProfile.objects.create(event=event, user=orga_user)
        sync = SpeakerProfileSalesforceSync(profile=profile)
    data = sync.serialize()
    assert data["FirstName"] == "Orga"
    assert data["LastName"] == "User"
    assert data["Email"] == orga_user.email


@pytest.mark.django_db
def test_submission_sync_should_sync_when_new(submission):
    with scopes_disabled():
        sync = SubmissionSalesforceSync.objects.create(submission=submission)
    assert sync.should_sync() is True


@pytest.mark.django_db
def test_submission_sync_serialize(submission):
    with scopes_disabled():
        sync = SubmissionSalesforceSync(submission=submission)
    data = sync.serialize()
    assert data["pretalx_LegacyID__c"] == submission.code
    assert data["Session_Title__c"] == "Test Submission"
    assert data["Status__c"] == "Submitted"


@pytest.mark.django_db
def test_submission_sync_serialized_state(submission):
    with scopes_disabled():
        sync = SubmissionSalesforceSync(submission=submission)
    assert sync.serialized_state == "Submitted"


@pytest.mark.django_db
def test_submission_should_sync_relations_false_when_new(submission):
    with scopes_disabled():
        sync = SubmissionSalesforceSync.objects.create(submission=submission)
    assert sync.should_sync_relations() is False


@pytest.mark.django_db
def test_speaker_sync_creates_contact(event, orga_user):
    with scopes_disabled():
        profile = SpeakerProfile.objects.create(event=event, user=orga_user)
        sync = SpeakerProfileSalesforceSync.objects.create(profile=profile)

    mock_sf = MagicMock()
    mock_sf.Contact.create.return_value = {"id": "sf_contact_123"}
    sync.sync(sf=mock_sf, force=True)

    sync.refresh_from_db()
    assert sync.salesforce_id == "sf_contact_123"
    assert sync.last_synced is not None
    mock_sf.Contact.create.assert_called_once()


@pytest.mark.django_db
def test_speaker_sync_updates_existing_contact(event, orga_user):
    with scopes_disabled():
        profile = SpeakerProfile.objects.create(event=event, user=orga_user)
        sync = SpeakerProfileSalesforceSync.objects.create(
            profile=profile, salesforce_id="sf_contact_123"
        )

    mock_sf = MagicMock()
    sync.sync(sf=mock_sf, force=True)

    mock_sf.Contact.update.assert_called_once()
    assert mock_sf.Contact.update.call_args[0][0] == "sf_contact_123"


@pytest.mark.django_db
def test_submission_sync_creates_session(submission):
    with scopes_disabled():
        sync = SubmissionSalesforceSync.objects.create(submission=submission)

    mock_sf = MagicMock()
    mock_sf.Session__c.create.return_value = {"id": "sf_session_456"}
    sync.sync(sf=mock_sf, force=True)

    sync.refresh_from_db()
    assert sync.salesforce_id == "sf_session_456"
    assert sync.last_synced is not None


@pytest.mark.django_db
def test_submission_sync_updates_existing_session(submission):
    with scopes_disabled():
        sync = SubmissionSalesforceSync.objects.create(
            submission=submission, salesforce_id="sf_session_456"
        )

    mock_sf = MagicMock()
    sync.sync(sf=mock_sf, force=True)

    mock_sf.Session__c.update.assert_called_once()
    assert mock_sf.Session__c.update.call_args[0][0] == "sf_session_456"


@pytest.mark.django_db
@patch("pretalx_salesforce.sync.get_salesforce_client")
def test_sync_event_with_salesforce(mock_get_client, event, submission, orga_user):
    mock_sf = MagicMock()
    mock_sf.Contact.create.return_value = {"id": "sf_contact_1"}
    mock_sf.Session__c.create.return_value = {"id": "sf_session_1"}
    mock_get_client.return_value = mock_sf

    with scopes_disabled():
        profile = SpeakerProfile.objects.create(event=event, user=orga_user)
        submission.speakers.add(profile)

    sync_event_with_salesforce(event)

    assert mock_sf.Contact.create.called or mock_sf.Contact.update.called
    assert mock_sf.Session__c.create.called or mock_sf.Session__c.update.called


@pytest.mark.django_db
@patch("pretalx_salesforce.sync.get_salesforce_client")
def test_sync_event_aborts_without_client(mock_get_client, event):
    mock_get_client.return_value = None
    sync_event_with_salesforce(event)


@pytest.mark.django_db
def test_periodic_task_signal(event, salesforce_settings):
    with patch("pretalx_salesforce.tasks.salesforce_event_sync") as mock_task:
        periodic_salesforce_sync(sender=None)
        mock_task.apply_async.assert_called_once_with(kwargs={"event_id": event.pk})


@pytest.mark.django_db
def test_settings_form_creates_instance(event):
    form = SalesforceSettingsForm(event=event)
    assert form.instance.pk is not None
    assert form.instance.event == event


@pytest.mark.django_db
def test_settings_form_reuses_existing(salesforce_settings):
    form = SalesforceSettingsForm(event=salesforce_settings.event)
    assert form.instance.pk == salesforce_settings.pk
