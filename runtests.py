#!/usr/bin/env python
"""Run the test suite against the test project in tests/.

Takes the arguments of `manage.py test`, e.g. `python runtests.py -v 2 tests.test_models`.
"""

import os
import sys

from django.core.management import execute_from_command_line

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
    execute_from_command_line([sys.argv[0], "test", *sys.argv[1:]])
