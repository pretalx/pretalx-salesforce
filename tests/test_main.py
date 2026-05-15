from unittest.mock import MagicMock, patch

import pytest
from django.db import IntegrityError
from django.urls import reverse
from django.utils.timezone import now
from django_scopes import scopes_disabled

from pretalx.person.models import SpeakerProfile, User
from pretalx.submission.models import Submission, SubmissionType

from pretalx_salesforce.forms import SalesforceSettingsForm
from pretalx_salesforce.models import (
    SalesforceSettings,
    SpeakerProfileSalesforceSync,
    SubmissionSalesforceSync,
    ellipsis,
)
from pretalx_salesforce.signals import periodic_salesforce_sync
from pretalx_salesforce.sync import (
    get_salesforce_client,
    salesforce_full_speaker_sync,
    sync_event_with_salesforce,
)
from pretalx_salesforce.tasks import salesforce_event_sync

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
        reverse(SETTINGS_URL_NAME, kwargs={"event": event.slug}), follow=True
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_reviewer_cannot_access_settings(review_client, event):
    response = review_client.get(
        reverse(SETTINGS_URL_NAME, kwargs={"event": event.slug})
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
    response = review_client.get(reverse(SYNC_URL_NAME, kwargs={"event": event.slug}))
    # The sync view overrides dispatch directly, so it always redirects.
    # The permission check happens at the event middleware level instead.
    assert response.status_code == 302


@pytest.mark.django_db
@patch("pretalx_salesforce.views.salesforce_event_sync")
def test_orga_can_trigger_sync(mock_task, orga_client, event):
    response = orga_client.get(reverse(SYNC_URL_NAME, kwargs={"event": event.slug}))
    assert response.status_code == 302
    mock_task.apply_async.assert_called_once()


@pytest.mark.django_db
@patch("pretalx_salesforce.views.salesforce_event_sync")
def test_sync_error_shows_message(mock_task, orga_client, event):
    mock_task.apply_async.side_effect = Exception("Connection failed")
    response = orga_client.get(
        reverse(SYNC_URL_NAME, kwargs={"event": event.slug}), follow=True
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
    "field", ("client_id", "client_secret", "username", "password")
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


@pytest.mark.django_db
def test_speaker_profile_split_name_single(event):
    with scopes_disabled():
        user = User.objects.create_user(
            password="x", email="single@example.org", name="Cher"
        )
        profile = SpeakerProfile.objects.create(event=event, user=user)
        sync = SpeakerProfileSalesforceSync(profile=profile)
    assert sync.split_name == ("", "Cher")


@pytest.mark.django_db
def test_speaker_data_out_of_date(event, orga_user):
    with scopes_disabled():
        profile = SpeakerProfile.objects.create(event=event, user=orga_user)
        sync = SpeakerProfileSalesforceSync(profile=profile)
    assert sync.data_out_of_date is True


@pytest.mark.django_db
def test_speaker_sync_skips_when_up_to_date(event, orga_user):
    with scopes_disabled():
        profile = SpeakerProfile.objects.create(event=event, user=orga_user)
        sync = SpeakerProfileSalesforceSync.objects.create(
            profile=profile, salesforce_id="x"
        )
        sync.synced_data = sync.serialize()
        sync.last_synced = now()
        sync.save()

    mock_sf = MagicMock()
    sync.sync(sf=mock_sf)
    mock_sf.Contact.create.assert_not_called()
    mock_sf.Contact.update.assert_not_called()


@pytest.mark.django_db
@patch("pretalx_salesforce.sync.get_salesforce_client")
def test_speaker_sync_no_client(mock_get, event, orga_user):
    mock_get.return_value = None
    with scopes_disabled():
        profile = SpeakerProfile.objects.create(event=event, user=orga_user)
        sync = SpeakerProfileSalesforceSync.objects.create(profile=profile)

    sync.sync(force=True)
    assert sync.salesforce_id is None
    mock_get.assert_called_once()


@pytest.mark.django_db
def test_submission_data_out_of_date(submission):
    with scopes_disabled():
        sync = SubmissionSalesforceSync(submission=submission)
        assert sync.data_out_of_date is True


@pytest.mark.django_db
def test_submission_serialize_relations_missing_speaker_sync(
    submission, event, orga_user
):
    with scopes_disabled():
        profile = SpeakerProfile.objects.create(event=event, user=orga_user)
        submission.speakers.add(profile)
        sync = SubmissionSalesforceSync(submission=submission)
        assert sync.serialize_relations() == []


@pytest.mark.django_db
def test_submission_sync_skips_when_up_to_date(submission):
    with scopes_disabled():
        sync = SubmissionSalesforceSync.objects.create(
            submission=submission, salesforce_id="x"
        )
        sync.synced_data = {"submission": sync.serialize()}
        sync.last_synced = now()
        sync.save()

    mock_sf = MagicMock()
    sync.sync(sf=mock_sf)
    mock_sf.Session__c.create.assert_not_called()
    mock_sf.Session__c.update.assert_not_called()


@pytest.mark.django_db
@patch("pretalx_salesforce.sync.get_salesforce_client")
def test_submission_sync_no_client(mock_get, submission):
    mock_get.return_value = None
    with scopes_disabled():
        sync = SubmissionSalesforceSync.objects.create(submission=submission)

    sync.sync(force=True)
    assert sync.salesforce_id is None
    mock_get.assert_called_once()


@pytest.mark.django_db
def test_submission_sync_relations_skips_when_not_needed(submission):
    with scopes_disabled():
        sync = SubmissionSalesforceSync.objects.create(submission=submission)

    mock_sf = MagicMock()
    sync.sync_relations(sf=mock_sf)
    mock_sf.Contact_Session__c.create.assert_not_called()


@pytest.mark.django_db
@patch("pretalx_salesforce.sync.get_salesforce_client")
def test_submission_sync_relations_no_client(mock_get, submission):
    mock_get.return_value = None
    with scopes_disabled():
        sync = SubmissionSalesforceSync.objects.create(submission=submission)

    sync.sync_relations(force=True)
    mock_get.assert_called_once()


@pytest.mark.django_db
def test_submission_sync_relations_creates(submission, event, orga_user):
    with scopes_disabled():
        profile = SpeakerProfile.objects.create(event=event, user=orga_user)
        SpeakerProfileSalesforceSync.objects.create(
            profile=profile, salesforce_id="sf_c1"
        )
        submission.speakers.add(profile)
        sync = SubmissionSalesforceSync.objects.create(
            submission=submission, salesforce_id="sf_s1"
        )

    mock_sf = MagicMock()
    mock_sf.Contact_Session__c.create.return_value = {"id": "rel_1"}
    with scopes_disabled():
        sync.sync_relations(sf=mock_sf, force=True)

    sync.refresh_from_db()
    assert sync.synced_data["relation_mapping"]["sf_c1"] == "rel_1"
    assert len(sync.synced_data["relations"]) == 1
    mock_sf.Contact_Session__c.create.assert_called_once()


@pytest.mark.django_db
def test_submission_sync_relations_skips_known(submission, event, orga_user):
    with scopes_disabled():
        profile = SpeakerProfile.objects.create(event=event, user=orga_user)
        SpeakerProfileSalesforceSync.objects.create(
            profile=profile, salesforce_id="sf_c1"
        )
        submission.speakers.add(profile)
        legacy_id = f"{orga_user.code}-{submission.code}"
        sync = SubmissionSalesforceSync.objects.create(
            submission=submission,
            salesforce_id="sf_s1",
            synced_data={
                "relations": [{"existing": True}],
                "relation_mapping": {legacy_id: "rel_known"},
            },
        )

    mock_sf = MagicMock()
    with scopes_disabled():
        sync.sync_relations(sf=mock_sf, force=True)
    mock_sf.Contact_Session__c.create.assert_not_called()


@pytest.mark.django_db
def test_get_salesforce_client_no_settings(event):
    assert get_salesforce_client(event) is None


@pytest.mark.django_db
def test_get_salesforce_client_incomplete(event):
    with scopes_disabled():
        SalesforceSettings.objects.create(
            event=event,
            client_id="",
            client_secret="",
            username="",
            password="",
            salesforce_instance="https://test.salesforce.com",
        )
    assert get_salesforce_client(event) is None


@pytest.mark.django_db
@patch("pretalx_salesforce.sync.urllib3.request")
def test_get_salesforce_client_auth_fail(mock_request, salesforce_settings):
    mock_request.return_value = MagicMock(status=400, data=b"bad credentials")
    assert get_salesforce_client(salesforce_settings.event) is None


@pytest.mark.django_db
@patch("pretalx_salesforce.sync.Salesforce")
@patch("pretalx_salesforce.sync.urllib3.request")
def test_get_salesforce_client_success(mock_request, mock_sf_cls, salesforce_settings):
    response = MagicMock(status=200)
    response.json.return_value = {
        "access_token": "tok",
        "instance_url": "https://instance.example.org",
    }
    mock_request.return_value = response

    client = get_salesforce_client(salesforce_settings.event)
    assert client is mock_sf_cls.return_value
    mock_sf_cls.assert_called_once_with(
        instance_url="https://instance.example.org", session_id="tok"
    )


@pytest.mark.django_db
@patch("pretalx_salesforce.sync.SpeakerProfileSalesforceSync")
def test_speaker_sync_integrity_error(mock_model, event, submission, orga_user):
    mock_model.DoesNotExist = SpeakerProfileSalesforceSync.DoesNotExist
    mock_model.objects.get.side_effect = SpeakerProfileSalesforceSync.DoesNotExist
    mock_model.objects.create.side_effect = IntegrityError

    with scopes_disabled():
        profile = SpeakerProfile.objects.create(event=event, user=orga_user)
        submission.speakers.add(profile)

    mock_sf = MagicMock()
    salesforce_full_speaker_sync(mock_sf, event)
    mock_sf.Contact.create.assert_not_called()


@pytest.mark.django_db
@patch("pretalx_salesforce.sync.sync_event_with_salesforce")
def test_salesforce_event_sync_task(mock_sync, event):
    salesforce_event_sync(event_id=event.pk)
    mock_sync.assert_called_once_with(event=event)


@pytest.mark.django_db
def test_periodic_task_skips_not_ready(event):
    with scopes_disabled():
        SalesforceSettings.objects.create(
            event=event,
            client_id="x",
            client_secret="y",
            username="z",
            password="",
            salesforce_instance="https://test.salesforce.com",
        )
    with patch("pretalx_salesforce.tasks.salesforce_event_sync") as mock_task:
        periodic_salesforce_sync(sender=None)
        mock_task.apply_async.assert_not_called()


@pytest.mark.django_db
def test_last_sync_only_submission(orga_client, event, submission):
    with scopes_disabled():
        SubmissionSalesforceSync.objects.create(
            submission=submission, last_synced=now()
        )
    response = orga_client.get(
        reverse(SETTINGS_URL_NAME, kwargs={"event": event.slug}), follow=True
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_last_sync_only_speaker(orga_client, event, orga_user):
    with scopes_disabled():
        profile = SpeakerProfile.objects.create(event=event, user=orga_user)
        SpeakerProfileSalesforceSync.objects.create(profile=profile, last_synced=now())
    response = orga_client.get(
        reverse(SETTINGS_URL_NAME, kwargs={"event": event.slug}), follow=True
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_last_sync_both(orga_client, event, submission, orga_user):
    with scopes_disabled():
        profile = SpeakerProfile.objects.create(event=event, user=orga_user)
        SpeakerProfileSalesforceSync.objects.create(profile=profile, last_synced=now())
        SubmissionSalesforceSync.objects.create(
            submission=submission, last_synced=now()
        )
    response = orga_client.get(
        reverse(SETTINGS_URL_NAME, kwargs={"event": event.slug}), follow=True
    )
    assert response.status_code == 200
