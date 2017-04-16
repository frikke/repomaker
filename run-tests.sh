#!/usr/bin/env bash

pep8 --show-pep8 --max-line-length=100 --exclude=migrations . &&
coverage3 run --source='.' manage.py test &&
coverage3 report &&
echo "All tests ran successfully! \o/"