"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       forum/apps.py
@brief      A collection of app specific configurations
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""

from django.apps import AppConfig


class ForumConfig(AppConfig):
    name = 'forum'
