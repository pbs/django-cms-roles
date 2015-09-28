# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cmsroles', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='role',
            name='derived_global_permissions',
            field=models.ManyToManyField(to='cms.GlobalPagePermission', blank=True),
        ),
        migrations.AlterField(
            model_name='role',
            name='derived_page_permissions',
            field=models.ManyToManyField(to='cms.PagePermission', blank=True),
        ),
    ]
