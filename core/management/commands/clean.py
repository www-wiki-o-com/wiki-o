"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

Copyright (C) 2018 Wiki-O, Frank Imeson

This source code is licensed under the GPL license found in the
LICENSE.md file in the root directory of this source tree.
"""

# *******************************************************************************
# Imports
# *******************************************************************************
import re

from django.core.management.base import BaseCommand
from django.template.defaultfilters import slugify

from theories.models import Category, TheoryNode

# *******************************************************************************
# Defines
# *******************************************************************************
RE_PUNCTUATOIN = r'\s*[\.!?]\s*$'

# *******************************************************************************
# Methods
# *******************************************************************************
# blahs


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
            for theory_node in TheoryNode.objects.all():
                save = False
                if theory_node.title00 and re.search(RE_PUNCTUATOIN, theory_node.title00):
                    theory_node.title00 = re.sub(RE_PUNCTUATOIN, '', theory_node.title00)
                    save = True
                if theory_node.title01 and re.search(RE_PUNCTUATOIN, theory_node.title01):
                    theory_node.title01 = re.sub(RE_PUNCTUATOIN, '', theory_node.title01)
                    save = True
                if save:
                    theory_node.save()

        print("Done")
