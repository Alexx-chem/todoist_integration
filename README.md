# Todoist Integration

This project extends [Todoist](https://todoist.com/) functionality and adds external integration with Telegram.

Uses OOP to implement Todoist object types (projects, tasks, labels and events) and own objects

## Main features
1. Plans for day, week, month, quarter and year planning horizons. Plans are composed automatically by number of configurable criteria
2. Automated plan progress tracking by analyzing Todoist events and persisting tasks state in the DB (Postgres)
3. Scheduled messages to Telegram via bot (bot code not included here)
