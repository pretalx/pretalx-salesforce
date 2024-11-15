from django.db import models
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _


def ellipsis(string, length=80):
    if len(string) > length:
        return string[: length - 1] + "…"
    return string


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

    @property
    def sync_ready(self):
        return all(
            [
                self.client_id,
                self.client_secret,
                self.username,
                self.password,
                self.salesforce_instance,
            ]
        )


class SpeakerProfileSalesforceSync(models.Model):
    profile = models.OneToOneField(
        to="person.SpeakerProfile",
        on_delete=models.CASCADE,
        related_name="salesforce_profile_sync",
    )
    last_synced = models.DateTimeField(null=True, blank=True)
    salesforce_id = models.CharField(max_length=255, null=True, blank=True)
    synced_data = models.JSONField(null=True, blank=True, default=dict)

    @cached_property
    def split_name(self):
        result = self.profile.user.name.split(" ", maxsplit=1)
        if len(result) == 1:
            return "", result[0]
        return result

    def serialize(self):
        return {
            "pretalx_LegacyID__c": self.profile.user.code,
            "FirstName": self.split_name[0],
            "LastName": self.split_name[1],
            "Email": self.profile.user.email,
            "Biography__c": self.profile.biography,
            "pretalx_Profile_Picture__c": self.profile.user.avatar_url,
            "RecordTypeID": "0124x000000A5QuAAK",
        }

    @property
    def data_out_of_date(self):
        return self.serialize() != self.synced_data

    def should_sync(self):
        last_modified = self.profile.updated
        if (
            not self.last_synced
            or not self.salesforce_id
            or self.last_synced < last_modified
            or self.data_out_of_date
        ):
            return True
        return False

    def sync(self, sf=None, force=False):
        if not self.should_sync() and not force:
            return
        if not sf:
            from pretalx_salesforce.sync import get_salesforce_client

            sf = get_salesforce_client(self.profile.event)
        if not sf:
            return

        data = self.serialize()
        if not self.salesforce_id:
            result = sf.Contact.create(data)
            self.salesforce_id = result["id"]
        else:
            sf.Contact.update(self.salesforce_id, data)

        self.synced_data = data
        self.last_synced = now()
        self.save()


class SubmissionSalesforceSync(models.Model):
    """
    This model handles both the sync of the submission object itself, as well as the
    sync of the mapping object between a submission and a contact.
    """

    submission = models.OneToOneField(
        to="submission.Submission",
        on_delete=models.CASCADE,
        related_name="salesforce_sync",
    )
    last_synced = models.DateTimeField(null=True, blank=True)
    salesforce_id = models.CharField(max_length=255, null=True, blank=True)
    synced_data = models.JSONField(null=True, blank=True, default=dict)

    @property
    def serialized_state(self):
        if self.submission.state in ("submitted", "accepted", "rejected", "confirmed"):
            return self.submission.state.capitalize()
        return "Rejected"

    def serialize(self):
        return {
            # "CreatedDate": self.submission.created.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pretalx_LegacyID__c": self.submission.code,
            "Name": ellipsis(self.submission.title, 80),
            "Track__c": (
                str(self.submission.track.name) if self.submission.track else ""
            ),
            "Status__c": self.serialized_state,
            "Abstract__c": (
                (self.submission.abstract or "")
                + "\n"
                + (self.submission.description or "")
            ).strip(),
            "Pretalx_Record__c": self.submission.urls.public.full(),
        }

    def serialize_relations(self):
        try:
            return [
                {
                    "Session__c": self.salesforce_id,
                    "Contact__c": speaker.event_profile(
                        self.submission.event
                    ).salesforce_profile_sync.salesforce_id,
                    "Name": ellipsis(f"{speaker.name} – {self.submission.title}"),
                    "pretalx_LegacyID__c": f"{speaker.code}-{self.submission.code}",
                }
                for speaker in self.submission.speakers.all()
            ]
        except SpeakerProfileSalesforceSync.DoesNotExist:
            return []

    @property
    def data_out_of_date(self):
        return self.serialize() != self.synced_data.get("submission", {})

    @property
    def relations_out_of_date(self):
        return self.serialize_relations() != self.synced_data.get("relations", [])

    def should_sync(self):
        if (
            not self.last_synced
            or not self.salesforce_id
            or self.last_synced < self.submission.updated
            or self.data_out_of_date
        ):
            return True
        return False

    def should_sync_relations(self):
        if not self.last_synced or not self.salesforce_id:
            return False
        return self.relations_out_of_date

    def sync(self, sf=None, force=False):
        if not self.should_sync() and not force:
            return
        if not sf:
            from pretalx_salesforce.sync import get_salesforce_client

            sf = get_salesforce_client(self.submission.event)
        if not sf:
            return

        data = self.serialize()
        if not self.salesforce_id:
            result = sf.Session__c.create(data)
            self.salesforce_id = result["id"]
        else:
            sf.Session__c.update(self.salesforce_id, data)

        self.synced_data["submission"] = data
        self.last_synced = now()
        self.save()

    def sync_relations(self, sf=None, force=False):
        if not self.should_sync_relations() and not force:
            return
        if not sf:
            from pretalx_salesforce.sync import get_salesforce_client

            sf = get_salesforce_client(self.submission.event)
        if not sf:
            return

        data = self.serialize_relations()
        if not self.synced_data.get("relations"):
            self.synced_data["relations"] = []
        if not self.synced_data.get("relation_mapping"):
            self.synced_data["relation_mapping"] = {}

        for relation in data:
            if relation["pretalx_LegacyID__c"] in self.synced_data["relation_mapping"]:
                # This is a known relation, and it holds no data of its own, so we don’t
                # need to update it
                continue
            result = sf.Contact_Session__c.create(relation)
            speaker_id = relation["Contact__c"]
            self.synced_data["relation_mapping"][speaker_id] = result["id"]
            self.synced_data["relations"].append(relation)

        self.save()
