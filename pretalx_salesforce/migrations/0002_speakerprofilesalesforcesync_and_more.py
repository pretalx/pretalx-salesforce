# Generated by Django 5.1.3 on 2024-11-11 10:44

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("person", "0029_alter_user_avatar_thumbnail_and_more"),
        ("pretalx_salesforce", "0001_initial"),
        ("submission", "0077_answeroption_position"),
    ]

    operations = [
        migrations.CreateModel(
            name="SpeakerProfileSalesforceSync",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False
                    ),
                ),
                ("last_synced", models.DateTimeField(blank=True, null=True)),
                ("salesforce_id", models.CharField(max_length=255, null=True)),
                ("synced_data", models.JSONField(default=dict, null=True)),
                (
                    "profile",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="salesforce_profile_sync",
                        to="person.speakerprofile",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="SubmissionSalesforceSync",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False
                    ),
                ),
                ("last_synced", models.DateTimeField(blank=True, null=True)),
                ("salesforce_id", models.CharField(max_length=255, null=True)),
                ("synced_data", models.JSONField(default=dict, null=True)),
                (
                    "submission",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="salesforce_sync",
                        to="submission.submission",
                    ),
                ),
            ],
        ),
    ]
