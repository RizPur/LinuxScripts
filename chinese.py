#!/usr/bin/env python3
"""
Chinese Notes CLI Tool
All-in-one HSK learning: notes + vocab review with spaced repetition
"""

import os
import sys
import argparse
import json
import datetime
import subprocess
import random
import csv
from pathlib import Path
from collections import defaultdict

# Paths
HOME = Path.home()
NOTES_DIR = HOME / "eurecom" / "chinese" / "notes"
CLOUD_DIR = HOME / "Google" / "Chinese"
CONFIG_FILE = NOTES_DIR / ".cn_config.json"
REVIEW_DATA_FILE = NOTES_DIR / ".cn_review_data.json"

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    END = '\033[0m'

# Spaced repetition intervals (in days)
SR_INTERVALS = {
    'again': 0,      # Review today
    'hard': 1,       # Review tomorrow
    'good': 3,       # Review in 3 days
    'easy': 7,       # Review in 7 days
}

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

def load_review_data():
    """Load vocab review data"""
    if REVIEW_DATA_FILE.exists():
        with open(REVIEW_DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_review_data(data):
    """Save vocab review data"""
    REVIEW_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REVIEW_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_lesson_file(hsk_level, lesson_num):
    """Get the markdown file path for a lesson"""
    lesson_dir = NOTES_DIR / f"HSK{hsk_level}"
    lesson_dir.mkdir(parents=True, exist_ok=True)
    return lesson_dir / f"Lesson_{lesson_num:02d}.md"

def get_words_dir(hsk_level):
    """Get the words directory for an HSK level"""
    words_dir = NOTES_DIR / f"HSK{hsk_level}" / "words"
    words_dir.mkdir(parents=True, exist_ok=True)
    return words_dir

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

def parse_languageplayer_csv(csv_path):
    """Parse LanguagePlayer CSV and extract vocab"""
    words = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            word = {
                'simplified': row.get('simplified', ''),
                'pinyin': row.get('pinyin', ''),
                'definitions': row.get('definitions', ''),
                'example': row.get('example', ''),
                'example_translation': row.get('exampleTranslation', ''),
            }
            if word['simplified']:  # Only add if there's a character
                words.append(word)
    return words

def get_due_words(review_data, hsk_level, lesson_num):
    """Get words due for review"""
    today = datetime.date.today().isoformat()
    key = f"HSK{hsk_level}_L{lesson_num}"
    
    if key not in review_data:
        return []
    
    due_words = []
    for word_id, data in review_data[key].items():
        if data.get('next_review', today) <= today:
            due_words.append({'id': word_id, **data})
    
    return due_words

def get_new_words(csv_path, review_data, hsk_level, lesson_num, limit=10):
    """Get new words that haven't been studied yet"""
    words = parse_languageplayer_csv(csv_path)
    key = f"HSK{hsk_level}_L{lesson_num}"
    
    if key not in review_data:
        review_data[key] = {}
    
    new_words = []
    for word in words:
        word_id = word['simplified']
        if word_id not in review_data[key]:
            new_words.append(word)
            if len(new_words) >= limit:
                break
    
    return new_words

def update_word_review(review_data, hsk_level, lesson_num, word_id, rating):
    """Update review data for a word based on rating"""
    key = f"HSK{hsk_level}_L{lesson_num}"
    
    if key not in review_data:
        review_data[key] = {}
    
    if word_id not in review_data[key]:
        review_data[key][word_id] = {
            'reviews': 0,
            'last_review': None,
            'next_review': None,
        }
    
    word_data = review_data[key][word_id]
    word_data['reviews'] += 1
    word_data['last_review'] = datetime.date.today().isoformat()
    
    # Calculate next review date
    interval = SR_INTERVALS.get(rating, 1)
    next_date = datetime.date.today() + datetime.timedelta(days=interval)
    word_data['next_review'] = next_date.isoformat()
    
    return review_data

# ============ COMMANDS ============

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

def cmd_import(args):
    """Import vocab from LanguagePlayer CSV"""
    config = load_config()
    hsk = args.hsk or config['current_hsk']
    lesson = args.lesson or config['current_lesson']
    
    # Check if CSV exists
    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        print(f"{Colors.RED}✗{Colors.END} CSV file not found: {csv_path}")
        return
    
    # Copy to words directory
    words_dir = get_words_dir(hsk)
    dest_path = words_dir / f"lesson_{lesson:02d}.csv"
    
    import shutil
    shutil.copy(csv_path, dest_path)
    
    # Count words
    words = parse_languageplayer_csv(dest_path)
    
    print(f"{Colors.GREEN}✓{Colors.END} Imported {len(words)} words to HSK{hsk} Lesson {lesson}")
    print(f"  Saved to: {dest_path}")
    print(f"\n{Colors.CYAN}Start learning:{Colors.END} cn vocab --new 10")

def cmd_vocab(args):
    """Review vocabulary with spaced repetition"""
    config = load_config()
    review_data = load_review_data()
    hsk = config['current_hsk']
    lesson = config['current_lesson']
    
    # Get CSV path
    words_dir = get_words_dir(hsk)
    csv_path = words_dir / f"lesson_{lesson:02d}.csv"
    
    if not csv_path.exists():
        print(f"{Colors.RED}✗{Colors.END} No vocab imported for HSK{hsk} Lesson {lesson}")
        print(f"  Import with: cn import <csv_file>")
        return
    
    # Determine what to review
    if args.new:
        words_to_study = get_new_words(csv_path, review_data, hsk, lesson, args.new)
        if not words_to_study:
            print(f"{Colors.GREEN}✓{Colors.END} You've already studied all words in this lesson!")
            return
        print(f"{Colors.CYAN}Learning {len(words_to_study)} new words...{Colors.END}\n")
    elif args.all:
        all_words = parse_languageplayer_csv(csv_path)
        words_to_study = all_words
        print(f"{Colors.CYAN}Reviewing all {len(words_to_study)} words...{Colors.END}\n")
    else:
        # Default: review due words
        due_words = get_due_words(review_data, hsk, lesson)
        if not due_words:
            print(f"{Colors.GREEN}✓{Colors.END} No words due for review!")
            print(f"  Learn new words: cn vocab --new 10")
            return
        
        # Load full word data from CSV
        all_words = {w['simplified']: w for w in parse_languageplayer_csv(csv_path)}
        words_to_study = [all_words.get(w['id']) for w in due_words if all_words.get(w['id'])]
        print(f"{Colors.CYAN}Reviewing {len(words_to_study)} due words...{Colors.END}\n")
    
    # Review each word
    for i, word in enumerate(words_to_study, 1):
        if not word:
            continue
            
        print(f"{Colors.BOLD}[{i}/{len(words_to_study)}]{Colors.END}")
        print(f"{Colors.MAGENTA}Character:{Colors.END} {Colors.BOLD}{word['simplified']}{Colors.END}")
        
        input(f"{Colors.CYAN}Think of the meaning... (press Enter to reveal){Colors.END}")
        
        print(f"{Colors.GREEN}Pinyin:{Colors.END} {word['pinyin']}")
        print(f"{Colors.GREEN}Meaning:{Colors.END} {word['definitions']}")
        
        if word.get('example'):
            print(f"{Colors.BLUE}Example:{Colors.END} {word['example']}")
            if word.get('example_translation'):
                print(f"  → {word['example_translation']}")
        
        print(f"\n{Colors.YELLOW}How well did you know it?{Colors.END}")
        print("  1 = Again (didn't know)")
        print("  2 = Hard (barely knew)")
        print("  3 = Good (knew it)")
        print("  4 = Easy (knew it perfectly)")
        
        while True:
            rating_input = input(f"{Colors.CYAN}Rating [1-4]:{Colors.END} ").strip()
            if rating_input in ['1', '2', '3', '4']:
                break
            print("Please enter 1, 2, 3, or 4")
        
        rating_map = {'1': 'again', '2': 'hard', '3': 'good', '4': 'easy'}
        rating = rating_map[rating_input]
        
        review_data = update_word_review(review_data, hsk, lesson, word['simplified'], rating)
        save_review_data(review_data)
        
        print()
    
    print(f"{Colors.GREEN}✓{Colors.END} Review complete! Great work! 加油！")

def cmd_stats(args):
    """Show vocabulary statistics"""
    config = load_config()
    review_data = load_review_data()
    hsk = config['current_hsk']
    lesson = config['current_lesson']
    
    # Get CSV path
    words_dir = get_words_dir(hsk)
    csv_path = words_dir / f"lesson_{lesson:02d}.csv"
    
    if not csv_path.exists():
        print(f"{Colors.YELLOW}⚠{Colors.END} No vocab imported for HSK{hsk} Lesson {lesson}")
        return
    
    all_words = parse_languageplayer_csv(csv_path)
    total_words = len(all_words)
    
    key = f"HSK{hsk}_L{lesson}"
    studied = len(review_data.get(key, {}))
    new = total_words - studied
    
    due = len(get_due_words(review_data, hsk, lesson))
    
    print(f"{Colors.BOLD}📊 HSK{hsk} Lesson {lesson} Stats{Colors.END}")
    print(f"  Total words: {total_words}")
    print(f"  {Colors.GREEN}Studied: {studied}{Colors.END}")
    print(f"  {Colors.CYAN}New: {new}{Colors.END}")
    print(f"  {Colors.YELLOW}Due for review: {due}{Colors.END}")

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
    parser = argparse.ArgumentParser(description='Chinese Notes & Vocab CLI Tool')
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
    
    # import command (NEW!)
    import_parser = subparsers.add_parser('import', help='Import vocab from LanguagePlayer CSV')
    import_parser.add_argument('csv_file', help='Path to CSV file')
    import_parser.add_argument('--lesson', type=int, help='Lesson number (default: current)')
    import_parser.add_argument('--hsk', type=int, help='HSK level (default: current)')
    
    # vocab command (NEW!)
    vocab_parser = subparsers.add_parser('vocab', help='Review vocabulary')
    vocab_parser.add_argument('--new', type=int, help='Learn N new words')
    vocab_parser.add_argument('--all', action='store_true', help='Review all words')
    
    # stats command (NEW!)
    stats_parser = subparsers.add_parser('stats', help='Show vocabulary statistics')
    
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
        'import': cmd_import,
        'vocab': cmd_vocab,
        'stats': cmd_stats,
        'sync': cmd_sync,
    }
    
    commands[args.command](args)

if __name__ == '__main__':
    main()
