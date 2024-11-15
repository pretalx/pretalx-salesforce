SalesForce integration
==========================

This is a plugin for `pretalx`_ that serves to send speaker and proposal information to SalesForce.

Information is sent every eight hours or on manual sync, and is mapped as follows:

- Users and their speaker profiles are sent as contacts:
    - Contact.pretalx_LegacyID__c is set to the pretalx user ID
    - Contact.FirstName is set to the first part of a user’s name, separated by whitespace.
    - Contact.LastName is set to any remaining part of a user’s name.
    - Contact.Email is set to the user’s email address.
    - Contact.Biography__c is set to the user’s biography.
    - Contact.pretalx_Profile_Picture__c is set to the user’s profile picture URL.
- Submission objects are set synced to the custom Session object:
    - CreatedDate is set to the submission’s creation date.
    - pretalx_LegacyID__c is set to the submission’s pretalx ID.
    - Name is set to the submission’s title.
    - Track__c is set to the submission’s track (by name, not by ID).
    - Status__c is set to the submission’s status.
    - Abstract__c is set to the submission’s abstract plus the submission’s description, separated by two newlines and then stripped of whitespace.
    - Pretalx_Record__c is set to the submission’s public URL.
- The mapping between Contacts and Sessions is synced to the custom Contact_Session object:
    - Contact__c is set to the Salesforce Contact.
    - Session__c is set to the Salesforce Session.

Development setup
-----------------

1. Make sure that you have a working `pretalx development setup`_.

2. Clone this repository, eg to ``local/pretalx-salesforce``.

3. Activate the virtual environment you use for pretalx development.

4. Run ``pip install -e .`` within this directory to register this application with pretalx's plugin registry.

5. Run ``make`` within this directory to compile translations.

6. Restart your local pretalx server. This plugin should show up in the plugin list shown on startup in the console.
   You can now use the plugin from this repository for your events by enabling it in the 'plugins' tab in the settings.

This plugin has CI set up to enforce a few code style rules. To check locally, you need these packages installed::

    pip install flake8 flake8-bugbear isort black

To check your plugin for rule violations, run::

    black --check .
    isort -c .
    flake8 .

You can auto-fix some of these issues by running::

    isort .
    black .


License
-------

Copyright 2024 Tobias Kunze

Released under the terms of the Apache License 2.0


.. _pretalx: https://github.com/pretalx/pretalx
.. _pretalx development setup: https://docs.pretalx.org/en/latest/developer/setup.html
