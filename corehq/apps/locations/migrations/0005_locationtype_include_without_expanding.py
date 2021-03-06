# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0004_auto_20160914_2030'),
    ]

    operations = [
        migrations.AddField(
            model_name='locationtype',
            name='include_without_expanding',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, to='locations.LocationType', null=True),
        ),
    ]
