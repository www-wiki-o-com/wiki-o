#!/usr/bin/env python
"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

Copyright (C) 2018 Wiki-O, Frank Imeson

This source code is licensed under the GPL license found in the
LICENSE.md file in the root directory of this source tree.
"""

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
