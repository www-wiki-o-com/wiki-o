# Generated by Django 2.2.10 on 2020-04-04 11:19

from django.db import migrations, models
import django.db.models.deletion
import theories.abstract_models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField()),
                ('title', models.CharField(max_length=50)),
            ],
            options={
                'verbose_name': 'Category',
                'verbose_name_plural': 'Categories',
                'db_table': 'theories_category',
                'ordering': ['title'],
            },
        ),
        migrations.CreateModel(
            name='Content',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content_type', models.SmallIntegerField(choices=[(10, 'Theory'), (20, 'Evidence (other)'), (21, 'Evidence (fact)'), (-10, 'Deleted Theory'), (-20, 'Deleted Evidence (other)'), (-21, 'Deleted Evidence (fact)')])),
                ('title00', models.CharField(blank=True, max_length=255, null=True)),
                ('title01', models.CharField(max_length=255, unique=True)),
                ('details', models.TextField(blank=True, max_length=10000)),
                ('pub_date', models.DateField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(blank=True, null=True, verbose_name=django.db.models.deletion.SET_NULL)),
                ('utilization', models.IntegerField(default=0)),
                ('rank', models.SmallIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Content',
                'verbose_name_plural': 'Content',
                'db_table': 'theories_content',
                'ordering': ['-rank'],
                'permissions': (('swap_title', 'Can swap true/false title.'), ('change_title', 'Can change title.'), ('change_details', 'Can change details.'), ('delete_reversion', 'Can delete revision.'), ('merge_content', 'Can merge dependencies.'), ('backup_content', 'Can create backup.'), ('remove_content', 'Can remove content.'), ('restore_content', 'Can restore/revert from revision.'), ('convert_content', 'Can convert theory <=> evidence.')),
            },
            bases=(theories.abstract_models.SavedOpinions, theories.abstract_models.SavedDependencies, models.Model),
        ),
        migrations.CreateModel(
            name='Opinion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pub_date', models.DateField(auto_now_add=True)),
                ('modified_date', models.DateField(auto_now=True)),
                ('anonymous', models.BooleanField(default=False)),
                ('deleted', models.BooleanField(default=False)),
                ('force', models.BooleanField(default=False)),
                ('true_input', models.SmallIntegerField(default=0)),
                ('false_input', models.SmallIntegerField(default=0)),
                ('true_total', models.SmallIntegerField(default=0)),
                ('false_total', models.SmallIntegerField(default=0)),
                ('rank', models.SmallIntegerField(default=0)),
                ('content', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='opinions', to='theories.Content')),
            ],
            options={
                'verbose_name': 'Opinion',
                'verbose_name_plural': 'Opinions',
                'db_table': 'theories_opinion',
                'ordering': ['-rank'],
            },
            bases=(theories.abstract_models.OpinionBase, models.Model),
        ),
        migrations.CreateModel(
            name='Stats',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stats_type', models.SmallIntegerField(choices=[(0, 'All'), (1, 'Supporters'), (2, 'Moderates'), (3, 'Opposers')])),
                ('total_true_points', models.FloatField(default=0.0)),
                ('total_false_points', models.FloatField(default=0.0)),
                ('content', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stats', to='theories.Content')),
                ('opinions', models.ManyToManyField(blank=True, related_name='stats', to='theories.Opinion')),
            ],
            options={
                'verbose_name': 'Stats',
                'verbose_name_plural': 'Stats',
                'db_table': 'theories_stats',
            },
            bases=(theories.abstract_models.OpinionBase, models.Model),
        ),
        migrations.CreateModel(
            name='StatsFlatDependency',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_true_points', models.FloatField(default=0.0)),
                ('total_false_points', models.FloatField(default=0.0)),
                ('content', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stats_flat_dependencies', to='theories.Content')),
                ('parent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='flat_dependencies', to='theories.Stats')),
            ],
            options={
                'verbose_name': 'Stats Flat Dependency',
                'verbose_name_plural': 'Stats Flat Dependencys',
                'db_table': 'theories_stats_flat_dependency',
            },
            bases=(theories.abstract_models.OpinionDependencyBase, models.Model),
        ),
        migrations.CreateModel(
            name='StatsDependency',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_true_points', models.FloatField(default=0.0)),
                ('total_false_points', models.FloatField(default=0.0)),
                ('content', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stats_dependencies', to='theories.Content')),
                ('parent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dependencies', to='theories.Stats')),
            ],
            options={
                'verbose_name': 'Stats Dependency',
                'verbose_name_plural': 'Stats Dependency',
                'db_table': 'theories_stats_dependency',
            },
            bases=(theories.abstract_models.OpinionDependencyBase, models.Model),
        ),
        migrations.CreateModel(
            name='OpinionDependency',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tt_input', models.SmallIntegerField(default=0)),
                ('tf_input', models.SmallIntegerField(default=0)),
                ('ft_input', models.SmallIntegerField(default=0)),
                ('ff_input', models.SmallIntegerField(default=0)),
                ('content', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='opinion_dependencies', to='theories.Content')),
                ('parent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dependencies', to='theories.Opinion')),
            ],
            options={
                'verbose_name': 'Opinion Dependency',
                'verbose_name_plural': 'Opinion Dependencys',
                'db_table': 'theories_opinion_dependency',
            },
            bases=(theories.abstract_models.OpinionDependencyBase, models.Model),
        ),
    ]
