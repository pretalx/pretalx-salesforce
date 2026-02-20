# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/pretalx/pretalx-salesforce/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|------------------------------------ | -------: | -------: | -------: | -------: | ------: | --------: |
| pretalx\_salesforce/\_\_init\_\_.py |        1 |        0 |        0 |        0 |    100% |           |
| pretalx\_salesforce/apps.py         |       15 |        0 |        0 |        0 |    100% |           |
| pretalx\_salesforce/forms.py        |       10 |        0 |        0 |        0 |    100% |           |
| pretalx\_salesforce/models.py       |      114 |       15 |       30 |       10 |     83% |58, 74, 87, 91, 93, 157-158, 162, 188, 192, 194, 209, 213, 215, 218->220, 220->223, 227 |
| pretalx\_salesforce/signals.py      |       15 |        0 |        6 |        1 |     95% |    34->31 |
| pretalx\_salesforce/sync.py         |       74 |       24 |       10 |        0 |     67% |66-99, 130-136, 139-140 |
| pretalx\_salesforce/tasks.py        |        5 |        2 |        0 |        0 |     60% |      9-10 |
| pretalx\_salesforce/views.py        |       46 |        5 |        6 |        1 |     81% |     40-44 |
| **TOTAL**                           |  **280** |   **46** |   **52** |   **12** | **80%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/pretalx/pretalx-salesforce/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/pretalx/pretalx-salesforce/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pretalx/pretalx-salesforce/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/pretalx/pretalx-salesforce/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fpretalx%2Fpretalx-salesforce%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/pretalx/pretalx-salesforce/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.