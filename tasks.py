#!/usr/bin/env python3
import argparse
import os
import datetime
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# If modifying these SCOPES, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/calendar'
]

CREDENTIALS_PATH = os.path.expanduser(os.getenv("GOOGLE_CREDENTIALS_PATH", "~/.venvs/taskscli/credentials.json"))
TOKEN_PATH = os.path.expanduser(os.getenv("GOOGLE_TOKEN_PATH", "~/.venvs/taskscli/token.pickle"))

def get_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        try:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                raise RefreshError("Trigger reauth")
        except RefreshError:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(TOKEN_PATH, 'wb') as token:
                pickle.dump(creds, token)

    return build('tasks', 'v1', credentials=creds)

def sort_key(task):
    due_str = task.get('due')
    if due_str:
        due_date = datetime.date.fromisoformat(due_str[:10])
        if due_date == datetime.date.today():
            return (0, due_str)
        elif due_date == datetime.date.today() + datetime.timedelta(days=1):
            return (1, due_str)
        else:
            return (2, due_str)
    else:
        return (3, '')  # Tasks with no due date go last


def list_tasks(service):
    results = service.tasks().list(tasklist='@default', showCompleted=False).execute()
    items = results.get('items', [])
    if not items:
        print("✅ No pending tasks!")
    else:
        sorted_tasks = sorted(items, key=sort_key)
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        for i, task in enumerate(sorted_tasks, start=1):
            due = task.get('due', '')
            if due:
                due_date = datetime.date.fromisoformat(due[:10])
                if due_date == today:
                    due = "\033[91mDue Today\033[0m"  # Red text
                elif due_date == tomorrow:
                    due = "\033[92mDue Tomorrow\033[0m"  # Green text
                else:
                    due = due[:10]  # Trim time
            print(f"{i}. {task['title']}" + (f" ({due})" if due else ""))

def add_task(service, title, due_offset, due_time=None):
    title = title.strip()
    due = None

    if due_offset is not None:
        try:
            days = int(due_offset)
            due_date = datetime.date.today() + datetime.timedelta(days=days)

            # Parse optional time
            if due_time:
                try:
                    if ":" in due_time:
                        hour, minute = map(int, due_time.split(":"))
                    else:
                        hour = int(due_time)
                        minute = 0
                    if not (0 <= hour <= 23 and 0 <= minute <= 59):
                        raise ValueError
                    due_datetime = datetime.datetime.combine(due_date, datetime.time(hour, minute))
                except ValueError:
                    print("⚠️  Time must be in HH or HH:MM format, 24-hour clock.")
                    return
            else:
                due_datetime = datetime.datetime.combine(due_date, datetime.time.min)

            due = due_datetime.isoformat() + "Z"
        except ValueError:
            print("⚠️  Due date offset must be an integer (e.g., 0 for today, 1 for tomorrow)")
            return

    body = {'title': title}
    if due:
        body['due'] = due

    task = service.tasks().insert(tasklist='@default', body=body).execute()
    print(f"✅ Added task: {task['title']} (Due: {due})" if due else f"✅ Added task: {task['title']}")


def done_task(service, index):
    tasks_unsorted = service.tasks().list(tasklist='@default', showCompleted=False).execute().get('items', [])
    tasks = sorted(tasks_unsorted, key=sort_key)

    if index < 1 or index > len(tasks):
        print("❌ Invalid task number")
        return
    task = tasks[index - 1]
    task['status'] = 'completed'
    task['completed'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    service.tasks().update(tasklist='@default', task=task['id'], body=task).execute()
    print(f"✅ Marked '{task}' as done.")

def delete_task(service, index):
    tasks_unsorted = service.tasks().list(tasklist='@default', showCompleted=False).execute().get('items', [])
    tasks = sorted(tasks_unsorted, key=sort_key)
    
    if index < 1 or index > len(tasks):
        print("❌ Invalid task number")
        return
    task_id = tasks[index - 1]['id']
    service.tasks().delete(tasklist='@default', task=task_id).execute()
    print(f"🗑️ Deleted task #{index}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=['list', 'add', 'delete', 'done'], help="Action to perform")
    parser.add_argument("arg1", nargs="?", help="Title (for add) or index (for delete/done)")
    parser.add_argument("arg2", nargs="?", help="Due date offset (e.g., 0=today, 1=tomorrow)")
    parser.add_argument("arg3", nargs="?", help="Optional time (e.g., 14 or 14:30)")
    args = parser.parse_args()

    service = get_service()

    if args.action == 'list':
        list_tasks(service)
    elif args.action == 'add' and args.arg1:
        add_task(service, args.arg1, args.arg2, args.arg3)
    elif args.action == 'done' and args.arg1:
        try:
            done_task(service, int(args.arg1))
        except ValueError:
            print("❌ Task index must be a number")
    elif args.action == 'delete' and args.arg1:
        try:
            delete_task(service, int(args.arg1))
        except ValueError:
            print("❌ Task index must be a number")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

## When token is expired, you can delete the token.pickle file and run the script again to re-authenticate.
## rm ~/.venvs/taskscli/token.pickle
## python3 tasks.py list
