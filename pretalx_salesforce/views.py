from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from django_context_decorator import context
from pretalx.common.views.mixins import PermissionRequired

from .forms import SalesforceSettingsForm
from .models import SpeakerProfileSalesforceSync, SubmissionSalesforceSync
from .tasks import salesforce_event_sync


class SalesforceSettingsView(PermissionRequired, FormView):
    permission_required = "orga.change_settings"
    template_name = "pretalx_salesforce/settings.html"
    form_class = SalesforceSettingsForm

    def get_success_url(self):
        return self.request.path

    def get_object(self):
        return self.request.event

    @context
    def last_sync(self):
        last_speaker_sync = SpeakerProfileSalesforceSync.objects.order_by(
            "last_synced"
        ).last()
        last_submission_sync = SubmissionSalesforceSync.objects.order_by(
            "last_synced"
        ).last()
        if not last_speaker_sync and not last_submission_sync:
            return None
        if not last_speaker_sync:
            return last_submission_sync.last_synced
        if not last_submission_sync:
            return last_speaker_sync.last_synced
        return max(last_speaker_sync.last_synced, last_submission_sync.last_synced)

    def post(self, request, *args, **kwargs):
        if "sync-now" not in request.POST:
            return super().post(request, *args, **kwargs)

        try:
            salesforce_event_sync.apply_async(kwargs={"event_id": request.event.pk})
            messages.success(self.request, _("The event was synced with SalesForce."))
        except Exception as e:
            messages.error(
                self.request,
                _("An error occurred while syncing the event with SalesForce.")
                + f" {e}",
            )
        return self.get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["event"] = self.request.event
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(
            self.request, _("The SalesForce integration settings were updated.")
        )
        return super().form_valid(form)
