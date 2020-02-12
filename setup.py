"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       theories/views.py
@brief      A collection of app specific views
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""

#!/usr/bin/env python
from setuptools import setup, find_packages

setup(name='Wiki-O',
      version='0.0',
      description='A web service for sharing opinions and avoiding arguments',
      author='Frank Imeson',
      author_email='fcimeson@wiki-o.com',
      url='https://github.com/www-wiki-o-com/wiki-o-django',
      packages=find_packages(),
      license='GPL',
      scripts=['manage.py'])
