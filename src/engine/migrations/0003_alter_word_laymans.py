# Generated by Django 4.1.11 on 2024-03-01 04:36

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("engine", "0002_alter_word_laymans"),
    ]

    operations = [
        migrations.AlterField(
            model_name="word",
            name="laymans",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(blank=True, max_length=100),
                blank=True,
                default=list,
                size=None,
            ),
        ),
    ]
