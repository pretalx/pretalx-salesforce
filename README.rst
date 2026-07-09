SalesForce integration
==========================

.. image:: https://img.shields.io/pypi/v/pretalx-salesforce.svg
   :target: https://pypi.org/project/pretalx-salesforce/
   :alt: PyPI version

This is a plugin for `pretalx`_ that serves to send speaker and proposal information to SalesForce.

Information is sent every eight hours or on manual sync, and is mapped as follows:

- Users and their speaker profiles are sent as contacts:
    - Contact.pretalx_LegacyID__c is set to the pretalx user ID
    - Contact.FirstName is set to the first part of a user's name, separated by whitespace.
    - Contact.LastName is set to any remaining part of a user's name.
    - Contact.Email is set to the user's email address.
    - Contact.Biography__c is set to the user's biography.
    - Contact.pretalx_Profile_Picture__c is set to the user's profile picture URL.
- Submission objects are set synced to the custom Session object:
    - pretalx_LegacyID__c is set to the submission's pretalx ID.
    - Name is set to the submission's title.
    - Session_Title__c is the submission's full title, as Name is truncated to 80 characters.
    - Track__c is set to the submission's track (by name, not by ID).
    - Submission_Format__c is set to the submission's type (by name, not by ID).
    - Status__c is set to the submission's status.
    - Abstract__c is set to the submission's abstract plus the submission's description, separated by two newlines and then stripped of whitespace.
    - Pretalx_Record__c is set to the submission's public URL.
- The mapping between Contacts and Sessions is synced to the custom Contact_Session__c object:
    - Contact__c is set to the Salesforce Contact.
    - Session__c is set to the Salesforce Session.

Installation
------------

Install the plugin with pip, in the same environment as your pretalx
installation::

    (env)$ python -m pip install pretalx-salesforce

Afterwards, run ``migrate`` and ``rebuild`` and restart your pretalx services,
just like after any pretalx update (see `performing updates`_ in the
administrator documentation).

You can then enable the plugin under "Settings → Plugins" in your event settings.

Development setup
-----------------

1. Make sure that you have a working `pretalx development setup`_.

2. Clone this repository, eg to ``local/pretalx-salesforce``.

3. Activate the virtual environment you use for pretalx development.

4. Run ``pip install -e .`` within this directory to register this application with pretalx's plugin registry.

5. Restart your local pretalx server. This plugin should show up in the plugin list shown on startup in the console.
   You can now use the plugin from this repository for your events by enabling it in the 'plugins' tab in the settings.

Development commands
~~~~~~~~~~~~~~~~~~~~

This plugin uses `just`_ as a task runner and `uv`_ for dependency management.
Run ``just`` with no arguments to list every available command. The most useful ones
are:

``just fmt``
    Auto-format and lint the code.

``just test``
    Run the full test suite with pytest.

Installing pretalx
~~~~~~~~~~~~~~~~~~~~

The tests need pretalx installed in the environment. ``just test`` handles this for
you: if pretalx cannot be imported, it installs the latest version from git before
running the test suite.

If you already have a development version of pretalx around (for example if you want
to test your changes against a specific commit or branch of pretalx), you can also
install pretalx up front yourself:

``just install-pretalx-local /path/to/pretalx``
    Install pretalx from a local checkout as an editable install.

``just install-pretalx``
    Install the latest pretalx from git (runs before tests if no pretalx is installed).


License
-------

Copyright 2024 Tobias Kunze

Released under the terms of the Apache License 2.0


.. _pretalx: https://github.com/pretalx/pretalx
.. _pretalx development setup: https://docs.pretalx.org/en/latest/developer/setup.html
.. _just: https://just.systems/
.. _uv: https://docs.astral.sh/uv/
.. _performing updates: https://docs.pretalx.org/administrator/maintenance/#performing-updates
