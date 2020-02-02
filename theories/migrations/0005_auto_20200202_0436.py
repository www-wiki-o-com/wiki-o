# Generated by Django 2.1.3 on 2020-02-02 04:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('theories', '0004_theorynode_utilization'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='theorynode',
            options={'ordering': ['-rank'], 'permissions': (('swap_title', 'Can swap true/false title.'), ('change_title', 'Can change title.'), ('change_details', 'Can change details.'), ('delete_reversion', 'Can delete revision.'), ('merge_theorynode', 'Can merge nodes.'), ('backup_theorynode', 'Can create backup.'), ('remove_theorynode', 'Can remove Theory Node.'), ('restore_theorynode', 'Can restore/revert from revision.'), ('convert_theorynode', 'Can convert theory <=> evidence.')), 'verbose_name': 'Theory Node', 'verbose_name_plural': 'Theory Nodes'},
        ),
    ]