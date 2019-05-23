# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-04-03 10:15
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('hgw_common', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Connector',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('person_identifier', models.CharField(max_length=256)),
                ('dest_public_key', models.CharField(max_length=500)),
                ('channel_id', models.CharField(max_length=256)),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='hgw_common.Profile')),
                ('start_validity', models.DateField(null=True)),
                ('expire_validity', models.DateField(null=True)),
            ],
        ),
    ]
