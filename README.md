<!-- __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

Copyright (C) 2018 Wiki-O, Frank Imeson

This source code is licensed under the GPL license found in the
LICENSE.md file in the root directory of this source tree.
-->

<p align="center">
    <img
    src="docs/images/logo.svg"
    width="500px;">
</p>
<p align="center">
    A web service for sharing opinions and avoiding arguments.
</p>
<p align="center">
    <a href="LICENSE.md">
        <img alt="GPL v3" src="https://img.shields.io/badge/License-GPLv3-blue.svg" style="max-width:100%;"/>
    </a>
    <a href="https://travis-ci.com/github/www-wiki-o-com/www-wiki-o-com">
        <img alt="Build Status" src="https://travis-ci.org/www-wiki-o-com/www-wiki-o-com.png?branch=master" style="max-width:100%;"/>
    </a>
    <a href="https://codecov.io/gh/www-wiki-o-com/www-wiki-o-com">
        <img alt="Code Coverage" src="https://codecov.io/gh/www-wiki-o-com/www-wiki-o-com/branch/master/graph/badge.svg" style="max-width:100%;"/>
    </a>
    <!-- <a href="https://codeclimate.com/github/www-wiki-o-com/www-wiki-o-com/maintainability">
        <img src="https://api.codeclimate.com/v1/badges/0262c54df6ffeaf33973/maintainability" />
    </a> -->
    <a href="https://scrutinizer-ci.com/g/www-wiki-o-com/www-wiki-o-com/?branch=master">
        <img alt="Code Quality" src="https://scrutinizer-ci.com/g/www-wiki-o-com/www-wiki-o-com/badges/quality-score.png?b=master" />
    </a>
    <a href="https://lgtm.com/projects/g/www-wiki-o-com/www-wiki-o-com/alerts/">
        <img alt="Total alerts" src="https://img.shields.io/lgtm/alerts/g/www-wiki-o-com/www-wiki-o-com.svg?logo=lgtm&logoWidth=18"/>
    </a>
    <a href="https://lgtm.com/projects/g/www-wiki-o-com/www-wiki-o-com/context:python">
        <img alt="Language grade: Python" src="https://img.shields.io/lgtm/grade/python/g/www-wiki-o-com/www-wiki-o-com.svg?logo=lgtm&logoWidth=18"/>
    </a>
    <a href="https://lgtm.com/projects/g/www-wiki-o-com/www-wiki-o-com/context:python">
        <img alt="Language grade: Python" src="https://img.shields.io/lgtm/grade/python/g/www-wiki-o-com/www-wiki-o-com.svg?logo=lgtm&logoWidth=18"/>
    </a>
    <img src="https://img.shields.io/website?url=http%3A%2F%2Fwiki-o.com" />
</p>

# Requirements

- Ubuntu 16 (VPS)
- Python 3.5, 3.6
- Django 2.1, 2.2
- Bootstrap 4.1

Ubuntu Packages
::

    $ sudo apt update
    $ sudo apt install git
    $ sudo apt install postgresql
    $ sudo apt install alpine
    $ sudo apt install python3
    $ sudo apt install python3-pip
    $ sudo apt install apache2
    $ sudo apt install libapache2-mod-wsgi-py3
    $ sudo apt install dnsutils
    $ sudo apt install vim
    $ export LC_ALL=C
    $ pip3 install virtualenv

# Virtual Envionment

Step 1: Setup Environment (add config to bashrc)
::

    $ cd /home/django/www.wiki-o.com
    $ virtualenv venv
    $ source venv/bin/activate

Step 2: Install Packages
::

To install requirments:

    $ pip3 install -r /home/django/www.wiki-o.com/requirements.freeze

To show the requirments:

    $ pip3 freeze

# Postgrsql

Step 1: Setup Database
::

    $ cd ~
    $ sudo -u postgres psql -c "create database wiki_o;"
    $ sudo -u postgres psql -c "create user django with encrypted password 'mypass';"
    $ sudo -u postgres psql -c "grant all privileges on database wiki_o to django;"
    $ sudo -u postgres psql -c "alter user django CREATEDB;"

# Django

Step 1: Migrate
::

    $ cd /home/django/www.wiki-o.com
    $ link -s local.django.settings.py settings.py
    $ cd ..
    $ python3 manage.py migrate
    $ python3 manage.py collectstatic

Step 2: Restore Database
::

    $ python3 manage.py loaddata /home/django/backup.json

Step 3: Test
::

    $ python3 manage.py runserver IP_ADDRESS:8000
