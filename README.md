# Scripts Collection

A collection of CLI tools i made for managing my Google Calendar, Google Tasks from my PC with some currency conversion stuff for my WayBar appbar display.

## Prerequisites

1. **Python Environment**: Create a virtual environment with required packages
   ```bash
   python3 -m venv ~/.venvs/taskscli
   pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client tzlocal dotenv
   ```

2. **Google API Credentials**:
   - Set up Google Calendar and Tasks API credentials
   - Download `credentials.json` to `~/.venvs/taskscli/credentials.json`

3. **Environment Variables**: Create a `.env` file in this directory:
   ```bash
   GOOGLE_CREDENTIALS_PATH=~/.venvs/taskscli/credentials.json
   GOOGLE_TOKEN_PATH=~/.venvs/taskscli/token.pickle
   SCHOOL_CALENDAR_ID=your_school_id@import.calendar.google.com #school calendar
   EXCHANGE_API_KEY=your_exchange_api_key
   LOG_FILE=~/Scripts/logs.log
   WORKFLOWS_SRC_DIR=~/Documents/Eurecom/8-Semester/Workflows
   WORKFLOWS_DEST_DIR=~/Google/Workflow
   ```

## Tools

### 📅 agenda.py - Google Calendar Management

Manage your Google Calendar events from the command line.

**Usage:**
```bash
# Show upcoming events (default: 7 days)
./agenda.py list [days]

# Add a new event
./agenda.py add "Rice Supermarket Run" "14:30" [day_offset] [--end_datetime YYYY-MM-DDTHH:MM]
```

**Examples:**
```bash
# Show next 7 days of events
./agenda.py list

# Show next 3 days
./agenda.py list 3

# Add meeting today at 2:30 PM
./agenda.py add "Digicel Team Meeting" "14:30"

# Add meeting tomorrow at 10:00 AM
./agenda.py add "Dentist Appointment" "10:00" 1

# Add meeting with custom end time
./agenda.py add "Call with Lil Tecca" "09:00" 0 --end_datetime 2024-01-15T11:00
```

### ✅ tasks.py - Google Tasks Management

Manage your Google Tasks from the command line with smart due date sorting.

**Usage:**
```bash
# List all pending tasks (sorted by due date)
./tasks.py list

# Add a new task
./tasks.py add "Task title" [due_offset] [time]

# Mark task as completed
./tasks.py done [task_number]

# Delete a task
./tasks.py delete [task_number]
```

**Examples:**
```bash
# List all tasks
./tasks.py list

# Add task due today
./tasks.py add "Finish report" 0

# Add task due tomorrow at 2 PM
./tasks.py add "Call dentist" 1 14

# Add task due in 3 days at 9:30 AM
./tasks.py add "Project deadline" 3 9:30

# Complete task #2
./tasks.py done 2

# Delete task #1
./tasks.py delete 1
```

**Task Sorting:**
- Tasks due today (highlighted in red)
- Tasks due tomorrow (highlighted in green)
- Tasks due later (by date)
- Tasks with no due date (last)

### 💱 convert.sh - Currency Converter

Convert between fiat currencies and cryptocurrencies.

**Usage:**
```bash
./convert.sh <from_currency> <to_currency> <amount>
```

**Examples:**
```bash
# Fiat currency conversion
./convert.sh usd jmd 100

# Cryptocurrency conversion
./convert.sh btc usd 1

# Mixed conversion
./convert.sh eth jmd 0.5
```

**Supported Cryptocurrencies:** BTC, ETH, LTC, XRP, ADA, DOGE

### 📊 today.sh - Daily Calendar Summary (old version to Agenda.py)

Display today's calendar events using gcalcli. 

**Usage:**
```bash
# Show events for next 7 days
./today.sh

# Show events for next N days
./today.sh 3
```

### 📄 workflows.sh - Document Backup System

Automatically convert modified Markdown files to PDF and backup to Google Drive.

**Features:**
- Monitors source directory for modified `.md` files
- Converts to PDF using Pandoc with XeLaTeX
- Only processes files modified since last backup
- Logs all operations with timestamps

**Usage:**
```bash
./workflows.sh
```

**Configuration:**
- `WORKFLOWS_SRC_DIR`: Source directory containing `.md` files
- `WORKFLOWS_DEST_DIR`: Destination directory for PDF files
- `LAST_BACKUP_FILE`: Tracks last backup timestamp

## Authentication

### First-time Setup

1. **Google APIs**: Run any script for the first time to trigger OAuth flow:
   ```bash
   ./agenda.py list
   # Follow browser prompts to authenticate
   ```

2. **Token Refresh**: If authentication expires, delete the token file:
   ```bash
   rm ~/.venvs/taskscli/token.pickle
   ./tasks.py list  # Re-authenticate
   ```

## Logging

Most scripts log operations to `~/Scripts/logs.log` with timestamps. Check this file for debugging and operation history.

## Dependencies

- **Python packages**: `google-auth`, `google-auth-oauthlib`, `google-api-python-client`, `python-dotenv`, `tzlocal`
- **System tools**: `pandoc`, `xelatex`, `gcalcli`, `curl`, `jq`, `bc`

## Notes

- All scripts use the local timezone automatically
- Task and event numbers in lists start from 1
- Date offsets: 0=today, 1=tomorrow, etc.
- Time format: 24-hour clock (HH:MM or HH)
- Scripts are designed to work together as a productivity suite