#!/usr/bin/env python3
"""
Chinese Notes CLI Tool
Organize your HSK learning with markdown notes
"""

import os
import sys
import argparse
import json
import datetime
import subprocess
import random
from pathlib import Path

# Paths
HOME = Path.home()
NOTES_DIR = HOME / "eurecom" / "chinese" / "notes"
CLOUD_DIR = HOME / "Google" / "Chinese"
CONFIG_FILE = NOTES_DIR / ".cn_config.json"

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

def load_config():
    """Load configuration (current lesson, etc.)"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"current_lesson": 1, "current_hsk": 1}

def save_config(config):
    """Save configuration"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def get_lesson_file(hsk_level, lesson_num):
    """Get the markdown file path for a lesson"""
    lesson_dir = NOTES_DIR / f"HSK{hsk_level}"
    lesson_dir.mkdir(parents=True, exist_ok=True)
    return lesson_dir / f"Lesson_{lesson_num:02d}.md"

def init_lesson_file(filepath, hsk_level, lesson_num):
    """Initialize a new lesson markdown file"""
    if not filepath.exists():
        content = f"""# HSK{hsk_level} - Lesson {lesson_num}

## Grammar Points

## Example Sentences

## Common Mistakes

## Practice Log
"""
        filepath.write_text(content)

def append_to_section(filepath, section, content, timestamp=True):
    """Append content to a specific section in the markdown file"""
    init_lesson_file(filepath, *parse_lesson_from_path(filepath))
    
    text = filepath.read_text()
    
    # Find the section
    section_header = f"## {section}"
    if section_header not in text:
        # Add section if it doesn't exist
        text += f"\n{section_header}\n"
    
    # Prepare the entry
    ts = f"*({datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})*" if timestamp else ""
    entry = f"- {content} {ts}\n"
    
    # Insert after section header
    lines = text.split('\n')
    result = []
    in_section = False
    added = False
    
    for i, line in enumerate(lines):
        result.append(line)
        if line.startswith(section_header):
            in_section = True
        elif in_section and not added and (line.startswith('##') or i == len(lines) - 1):
            result.insert(-1 if line.startswith('##') else len(result), entry)
            added = True
            in_section = False
    
    if not added:
        result.append(entry)
    
    filepath.write_text('\n'.join(result))

def parse_lesson_from_path(filepath):
    """Extract HSK level and lesson number from filepath"""
    parts = str(filepath).split('/')
    hsk = int(parts[-2].replace('HSK', ''))
    lesson = int(parts[-1].replace('Lesson_', '').replace('.md', ''))
    return hsk, lesson

def cmd_lesson(args):
    """Set current lesson"""
    config = load_config()
    config['current_lesson'] = args.lesson_num
    if args.hsk:
        config['current_hsk'] = args.hsk
    save_config(config)
    print(f"{Colors.GREEN}✓{Colors.END} Set to HSK{config['current_hsk']} Lesson {args.lesson_num}")

def cmd_note(args):
    """Add a grammar note"""
    config = load_config()
    filepath = get_lesson_file(config['current_hsk'], config['current_lesson'])
    append_to_section(filepath, "Grammar Points", args.content)
    print(f"{Colors.GREEN}✓{Colors.END} Added grammar note to Lesson {config['current_lesson']}")

def cmd_example(args):
    """Add an example sentence"""
    config = load_config()
    filepath = get_lesson_file(config['current_hsk'], config['current_lesson'])
    
    if args.translation:
        content = f"**{args.sentence}** — {args.translation}"
    else:
        content = f"**{args.sentence}**"
    
    append_to_section(filepath, "Example Sentences", content)
    print(f"{Colors.GREEN}✓{Colors.END} Added example to Lesson {config['current_lesson']}")

def cmd_mistake(args):
    """Log a common mistake"""
    config = load_config()
    filepath = get_lesson_file(config['current_hsk'], config['current_lesson'])
    append_to_section(filepath, "Common Mistakes", f"❌ {args.content}")
    print(f"{Colors.YELLOW}⚠{Colors.END} Logged mistake to Lesson {config['current_lesson']}")

def cmd_practice(args):
    """Get a random sentence to practice"""
    config = load_config()
    filepath = get_lesson_file(config['current_hsk'], config['current_lesson'])
    
    if not filepath.exists():
        print(f"{Colors.RED}✗{Colors.END} No notes for current lesson yet!")
        return
    
    text = filepath.read_text()
    
    # Extract example sentences
    examples = []
    in_examples = False
    for line in text.split('\n'):
        if line.startswith('## Example Sentences'):
            in_examples = True
        elif line.startswith('##'):
            in_examples = False
        elif in_examples and line.startswith('- **'):
            # Extract the sentence
            sentence = line.split('**')[1]
            examples.append(sentence)
    
    if not examples:
        print(f"{Colors.YELLOW}⚠{Colors.END} No example sentences yet! Add some with 'cn example'")
        return
    
    sentence = random.choice(examples)
    print(f"{Colors.BLUE}Practice this:{Colors.END} {Colors.BOLD}{sentence}{Colors.END}")

def cmd_show(args):
    """Show current lesson notes"""
    config = load_config()
    filepath = get_lesson_file(config['current_hsk'], config['current_lesson'])
    
    if not filepath.exists():
        print(f"{Colors.YELLOW}⚠{Colors.END} No notes for HSK{config['current_hsk']} Lesson {config['current_lesson']} yet!")
        return
    
    # Open in default editor or print to terminal
    if args.edit:
        editor = os.environ.get('EDITOR', 'nano')
        subprocess.run([editor, str(filepath)])
    else:
        print(filepath.read_text())

def cmd_sync(args):
    """Sync notes to Google Drive"""
    if not NOTES_DIR.exists():
        print(f"{Colors.RED}✗{Colors.END} Notes directory doesn't exist yet!")
        return
    
    CLOUD_DIR.mkdir(parents=True, exist_ok=True)
    
    # Use rsync for syncing
    cmd = ['rsync', '-av', '--delete']
    if args.dry_run:
        cmd.append('--dry-run')
    
    cmd.extend([str(NOTES_DIR) + '/', str(CLOUD_DIR) + '/'])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if args.dry_run:
        print(f"{Colors.BLUE}Dry run - would sync:{Colors.END}")
        print(result.stdout)
    else:
        print(f"{Colors.GREEN}✓{Colors.END} Synced notes to Google Drive!")
        if args.verbose:
            print(result.stdout)

def main():
    parser = argparse.ArgumentParser(description='Chinese Notes CLI Tool')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # lesson command
    lesson_parser = subparsers.add_parser('lesson', help='Set current lesson')
    lesson_parser.add_argument('lesson_num', type=int, help='Lesson number')
    lesson_parser.add_argument('--hsk', type=int, help='HSK level (default: current)')
    
    # note command
    note_parser = subparsers.add_parser('note', help='Add a grammar note')
    note_parser.add_argument('content', help='Note content')
    
    # example command
    example_parser = subparsers.add_parser('example', help='Add an example sentence')
    example_parser.add_argument('sentence', help='Chinese sentence')
    example_parser.add_argument('translation', nargs='?', help='English translation (optional)')
    
    # mistake command
    mistake_parser = subparsers.add_parser('mistake', help='Log a common mistake')
    mistake_parser.add_argument('content', help='Mistake description')
    
    # practice command
    practice_parser = subparsers.add_parser('practice', help='Get random sentence to practice')
    
    # show command
    show_parser = subparsers.add_parser('show', help='Show current lesson notes')
    show_parser.add_argument('-e', '--edit', action='store_true', help='Open in editor')
    
    # sync command
    sync_parser = subparsers.add_parser('sync', help='Sync notes to Google Drive')
    sync_parser.add_argument('--dry-run', action='store_true', help='Preview sync without making changes')
    sync_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Route to appropriate command
    commands = {
        'lesson': cmd_lesson,
        'note': cmd_note,
        'example': cmd_example,
        'mistake': cmd_mistake,
        'practice': cmd_practice,
        'show': cmd_show,
        'sync': cmd_sync,
    }
    
    commands[args.command](args)

if __name__ == '__main__':
    main()
