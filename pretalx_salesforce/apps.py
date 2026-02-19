from django.apps import AppConfig
from django.utils.translation import gettext_lazy

from . import __version__


class PluginApp(AppConfig):
    name = "pretalx_salesforce"
    verbose_name = "SalesForce integration"

    class PretalxPluginMeta:
        name = gettext_lazy("SalesForce integration")
        author = "Tobias Kunze"
        description = gettext_lazy(
            "Send speaker and proposal information to SalesForce"
        )
        visible = True
        version = __version__
        category = "INTEGRATION"
        settings_links = [
            (gettext_lazy("Settings"), "plugins:pretalx_salesforce:settings", {}),
        ]

    def ready(self):
        from . import signals  # NOQA
