# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
        ('cms', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('can_change', models.BooleanField(default=True, verbose_name='can edit')),
                ('can_add', models.BooleanField(default=True, verbose_name='can add')),
                ('can_delete', models.BooleanField(default=True, verbose_name='can delete')),
                ('can_change_advanced_settings', models.BooleanField(default=False, verbose_name='can change advanced settings')),
                ('can_publish', models.BooleanField(default=True, verbose_name='can publish')),
                ('can_set_navigation', models.BooleanField(default=True, verbose_name='can set navigation')),
                ('can_change_permissions', models.BooleanField(default=False, help_text='on page level', verbose_name='can change permissions')),
                ('can_move_page', models.BooleanField(default=True, verbose_name='can move')),
                ('can_moderate', models.BooleanField(default=True, verbose_name='can moderate')),
                ('can_view', models.BooleanField(default=False, help_text='frontend view restriction', verbose_name='view restricted')),
                ('name', models.CharField(unique=True, max_length=50)),
                ('is_site_wide', models.BooleanField(default=True)),
                ('derived_global_permissions', models.ManyToManyField(to='cms.GlobalPagePermission', null=True, blank=True)),
                ('derived_page_permissions', models.ManyToManyField(to='cms.PagePermission', null=True, blank=True)),
                ('group', models.ForeignKey(verbose_name='group', blank=True, to='auth.Group', null=True)),
                ('user', models.ForeignKey(verbose_name='user', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'abstract': False,
                'verbose_name': 'role',
                'verbose_name_plural': 'roles',
                'permissions': (('user_setup', 'Can access user setup'),),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserSetup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
                'verbose_name_plural': 'User Setup',
                'permissions': (),
            },
            bases=(models.Model,),
        ),
    ]
