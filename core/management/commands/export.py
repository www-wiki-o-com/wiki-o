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
import sys

from django.core import serializers
from django.core.management.base import BaseCommand

from theories.models.categories import Category
from theories.models.content import Content
from theories.models.opinions import Opinion, OpinionDependency
from theories.models.statistics import Stats, StatsDependency, StatsFlatDependency
from users.models import User, Violation, ViolationFeedback, ViolationVote

# *******************************************************************************
# Defines
# *******************************************************************************
VALID_MODELS = {'Content', 'Opinion', 'Stats'}

# *******************************************************************************
# Methods
# *******************************************************************************


class Command(BaseCommand):
    """Export wiki-o data as json."""

    help = __doc__

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('archive_path', nargs='?', type=str)

        # Named (optional) arguments
        parser.add_argument(
            '--forum_sync_data',
            action='store_true',
            help='Export the user data used to sync the forums.',
        )
        parser.add_argument(
            '--models',
            nargs='+',
            help='Choose the model(s) to export.',
        )
        parser.add_argument(
            '--model_fields',
            nargs='+',
            help='Choose the model and field to export.',
        )

    def handle(self, *args, **options):
        """The method that is run when the commandline is invoked."""
        # Get data
        data = ""
        if options['model_fields']:
            querry_set = {}
            for model_field in options['model_fields']:
                model = None
                field = None
                if re.match(r'^\w+$', model_field):
                    model = model_field
                    field = None
                elif re.match(r'^\w+\.\w+$', model_field):
                    model = model_field.split('.')[0]
                    field = model_field.split('.')[1]
                else:
                    print('Error, model fields are formated as "model" or "model.field"')
                    sys.exit()
                if model in VALID_MODELS:
                    if model in querry_set and field:
                        querry_set[model].append(field)
                    elif field:
                        querry_set[model] = [field]
                    else:
                        querry_set[model] = []
                else:
                    print('Error, model not implemented', model)
                    sys.exit()
            if 'Content' in querry_set:
                if querry_set['Content']:
                    data += serializers.serialize(
                        'json', Content.objects.all(), fields=querry_set['Content']).strip() + ','
                else:
                    data += serializers.serialize('json', Content.objects.all()).strip() + ','
            if 'Opinion' in querry_set:
                if querry_set['Opinion']:
                    data += serializers.serialize(
                        'json', Opinion.objects.all(), fields=querry_set['Opinion']).strip() + ','
                else:
                    data += serializers.serialize('json', Opinion.objects.all()).strip() + ','
            if 'Stats' in querry_set:
                if querry_set['Stats']:
                    data += serializers.serialize(
                        'json', Stats.objects.all(), fields=querry_set['Stats']).strip() + ','
                else:
                    data += serializers.serialize('json', Stats.objects.all()).strip() + ','
            data = '[' + data.strip(',') + ']'
        elif options['forum_sync_data']:
            data = self.get_forum_sync_data()
        else:
            data = self.get_database()
        # Output data
        if options['archive_path']:
            with open(options['archive_path'], 'w') as f:
                f.write(data)
        else:
            print(data)

    @classmethod
    def get_database(cls):
        data = ""
        if Category.objects.count() > 0:
            data += serializers.serialize('json', Category.objects.all()).strip('[]') + ','
        if Content.objects.count() > 0:
            data += serializers.serialize('json', Content.objects.all()).strip('[]') + ','
        if Opinion.objects.count() > 0:
            data += serializers.serialize('json', Opinion.objects.all()).strip('[]') + ','
        if OpinionDependency.objects.count() > 0:
            data += serializers.serialize('json', OpinionDependency.objects.all()).strip('[]') + ','
        if Stats.objects.count() > 0:
            data += serializers.serialize('json', Stats.objects.all()).strip('[]') + ','
        if StatsDependency.objects.count() > 0:
            data += serializers.serialize('json', StatsDependency.objects.all()).strip('[]') + ','
        if StatsFlatDependency.objects.count() > 0:
            data += serializers.serialize('json',
                                          StatsFlatDependency.objects.all()).strip('[]') + ','
        if User.objects.count() > 0:
            data += serializers.serialize('json', User.objects.all()).strip('[]') + ','
        if Violation.objects.count() > 0:
            data += serializers.serialize('json', Violation.objects.all()).strip('[]') + ','
        if ViolationFeedback.objects.count() > 0:
            data += serializers.serialize('json', ViolationFeedback.objects.all()).strip('[]') + ','
        if ViolationVote.objects.count() > 0:
            data += serializers.serialize('json', ViolationVote.objects.all()).strip('[]') + ','
        data = '[' + data.strip(',') + ']'
        return data

    @classmethod
    def get_forum_sync_data(cls):
        data = serializers.serialize('json', User.objects.all(), fields=['username', 'password'])
        return data
