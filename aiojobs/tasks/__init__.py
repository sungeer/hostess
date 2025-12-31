# tasks/__init__.py

from aiojobs.tasks.hourly_sync import ts as hourly_sync

tasks = [hourly_sync]
