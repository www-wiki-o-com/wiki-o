"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       core/management/command/clean.py
@copyright  GNU Public License, 2018
@authors    Frank Imeson
@brief      A managment script for cleaning up the database
"""

# *******************************************************************************
# Imports
# *******************************************************************************
import re

from django.core.management.base import BaseCommand
from django.template.defaultfilters import slugify

from theories.models import Category, Content

# *******************************************************************************
# Defines
# *******************************************************************************
RE_PUNCTUATOIN = r'\s*[\.!?]\s*$'

# *******************************************************************************
# Methods
# *******************************************************************************
# Blahs


class Command(BaseCommand):
    """Runs a series of scripts to clean up the database."""
    help = __doc__

    def add_arguments(self, parser):
        # Optional arguments.
        parser.add_argument(
            '--categories',
            action='store_true',
            help='Remove empty cateogires.',
        )

        parser.add_argument(
            '--punctuation',
            action='store_true',
            help='Remove punctuation from theories, evidence, and cateogires.',
        )

    def handle(self, *args, **options):
        """The method that is run when the commandline is invoked."""
        print("Cleaning up the categories.")

        # Clean up categories.
        if options['categories']:
            for category in Category.objects.all():
                if category.count() == 0:
                    category.delete()

        # Clean up punctuation.
        if options['punctuation']:
            for category in Category.objects.all():
                if re.search(RE_PUNCTUATOIN, category.title):
                    category.title = re.sub(RE_PUNCTUATOIN, '', category.title)
                    category.slug = slugify(category.title)
                    category.save()
            for content in Content.objects.all():
                save = False
                if content.title00 and re.search(RE_PUNCTUATOIN, content.title00):
                    content.title00 = re.sub(RE_PUNCTUATOIN, '', content.title00)
                    save = True
                if content.title01 and re.search(RE_PUNCTUATOIN, content.title01):
                    content.title01 = re.sub(RE_PUNCTUATOIN, '', content.title01)
                    save = True
                if save:
                    content.save()

        print("Done")
