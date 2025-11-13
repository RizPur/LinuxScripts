#!/usr/bin/env python3
"""
Chinese Vocabulary CLI Tool
Capture, enrich, and sync Chinese vocabulary to Anki.
"""

import os
import sys
import argparse
import json
import datetime
import csv
import logging
import requests
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
env_paths = [Path.home() / "dev" / "scripts" / ".env", Path.home() / ".env", Path(__file__).parent / ".env"]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break

# AnkiConnect integration
try:
    from anki import AnkiConnect, setup_chinese_model
except ImportError:
    AnkiConnect = None
    setup_chinese_model = None

# --- Configuration ---
HOME = Path.home()
# Set default paths relative to the script's absolute location
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_ZH_DIR = SCRIPT_DIR / 'zh'
DEFAULT_ZH_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = Path(os.path.expanduser(os.getenv("CHINESE_CONFIG_FILE", DEFAULT_ZH_DIR / ".cn_config.json")))
LOG_DIR = Path(os.path.expanduser(os.getenv("CHINESE_LOG_DIR", SCRIPT_DIR.parent / "logs")))
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "cn.log"

# Central CSV file for vocabulary
DEFAULT_CSV_PATH = DEFAULT_ZH_DIR / "chinese_vocab.csv"
VOCAB_CSV_PATH = Path(os.path.expanduser(os.getenv("CHINESE_VOCAB_CSV", DEFAULT_CSV_PATH)))

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler(LOG_FILE)])
logger = logging.getLogger('cn')

class Colors:
    GREEN, BLUE, YELLOW, RED, BOLD, END = '\033[92m', '\033[94m', '\033[93m', '\033[91m', '\033[1m', '\033[0m'

# --- Core Functions ---

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"current_hsk": 1}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    logger.info(f"Config saved: HSK {config['current_hsk']}")

def get_vocab_data():
    """Reads the central vocabulary CSV file."""
    if not VOCAB_CSV_PATH.exists():
        return []
    with open(VOCAB_CSV_PATH, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def save_vocab_data(data, headers):
    """Saves data to the central vocabulary CSV file."""
    with open(VOCAB_CSV_PATH, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)

def get_anki_connect():
    if AnkiConnect is None:
        raise ImportError("Could not import anki.py. Make sure it's in the same directory.")
    anki = AnkiConnect()
    if not anki.check_connection():
        raise ConnectionError("Could not connect to Anki. Is Anki running with AnkiConnect installed?")
    return anki

def enrich_with_ai(phrase, lang, hsk_level):
    """Use AI to get structured data for a word or phrase."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    lang_map = {'zh': 'Chinese', 'en': 'English', 'pinyin': 'Pinyin'}
    prompt = f"""
You are a Chinese language teacher. A student at HSK Level {hsk_level} has given you a word/phrase in {lang_map.get(lang, 'Chinese')}.
The phrase is: "{phrase}"

Your task is to return a JSON object with the following fields:
- "hanzi": The Chinese characters for the phrase.
- "pinyin": The Hanyu Pinyin with tone marks.
- "english": A concise English translation.
- "example_hanzi": A simple example sentence using the phrase, appropriate for an HSK {hsk_level} learner.
- "example_english": The English translation of the example sentence.

Example response for the input "你好":
{{
    "hanzi": "你好",
    "pinyin": "nǐ hǎo",
    "english": "hello, hi",
    "example_hanzi": "你好，你叫什么名字？",
    "example_english": "Hello, what is your name?"
}}

Return ONLY the valid JSON object.
"""
    try:
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {OPENAI_API_KEY}', 'Content-Type': 'application/json'},
            json={'model': 'gpt-3.5-turbo', 'messages': [{'role': 'user', 'content': prompt}], 'temperature': 0.5},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()['choices'][0]['message']['content'].strip()
        return json.loads(result)
    except Exception as e:
        logger.error(f"AI enrichment failed: {e}")
        raise

# --- CLI Commands ---

def cmd_hsk(args):
    config = load_config()
    config['current_hsk'] = args.level
    save_config(config)
    print(f"{Colors.GREEN}✓{Colors.END} Set current HSK context to {Colors.BOLD}{args.level}{Colors.END}")

def cmd_new(args):
    config = load_config()
    hsk_level = config.get('current_hsk', 1)
    print(f"Adding new word with HSK {hsk_level} context...")

    try:
        ai_data = enrich_with_ai(args.phrase, args.lang, hsk_level)
        hanzi = ai_data.get('hanzi')
        if not hanzi:
            raise ValueError("AI did not return valid Hanzi.")

        print(f"  {Colors.BLUE}Hanzi:{Colors.END} {hanzi}")
        print(f"  {Colors.BLUE}Pinyin:{Colors.END} {ai_data.get('pinyin')}")
        print(f"  {Colors.BLUE}English:{Colors.END} {ai_data.get('english')}")

        # Prepare new row for CSV
        new_row = {
            'Hanzi': hanzi,
            'Pinyin': ai_data.get('pinyin', ''),
            'English': ai_data.get('english', ''),
            'ExampleSentence': ai_data.get('example_hanzi', ''),
            'ExampleTranslation': ai_data.get('example_english', ''),
            'HSKLevel': hsk_level,
            'AnkiNoteID': ''
        }

        # Append to CSV
        headers = list(new_row.keys())
        file_exists = VOCAB_CSV_PATH.exists()
        with open(VOCAB_CSV_PATH, 'a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            if not file_exists:
                writer.writeheader()
            writer.writerow(new_row)
        
        print(f"\n{Colors.GREEN}✓{Colors.END} Successfully added '{hanzi}' to your vocabulary list.")
        print("  Run `cn sync` to add it to Anki.")

    except Exception as e:
        print(f"{Colors.RED}✗ Error adding new word:{Colors.END} {e}")

def cmd_import(args):
    config = load_config()
    hsk_level = config.get('current_hsk', 1)
    
    external_csv_path = Path(args.csv_file).expanduser()
    if not external_csv_path.exists():
        print(f"{Colors.RED}✗ Error:{Colors.END} File not found at {external_csv_path}")
        return

    try:
        with open(external_csv_path, 'r', encoding='utf-8') as f:
            external_words = list(csv.DictReader(f))
    except Exception as e:
        print(f"{Colors.RED}✗ Error:{Colors.END} Could not read CSV file: {e}")
        return

    headers = ['Hanzi', 'Pinyin', 'English', 'ExampleSentence', 'ExampleTranslation', 'HSKLevel', 'AnkiNoteID']
    file_exists = VOCAB_CSV_PATH.exists()
    
    new_rows = []
    for word in external_words:
        new_rows.append({
            'Hanzi': word.get('Hanzi', word.get('simplified', '')),
            'Pinyin': word.get('Pinyin', word.get('pinyin', '')),
            'English': word.get('English', word.get('definitions', '')),
            'ExampleSentence': word.get('ExampleSentence', word.get('example', '')),
            'ExampleTranslation': word.get('ExampleTranslation', word.get('exampleTranslation', '')),
            'HSKLevel': hsk_level,
            'AnkiNoteID': ''
        })

    with open(VOCAB_CSV_PATH, 'a', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if not file_exists:
            writer.writeheader()
        writer.writerows(new_rows)

    print(f"{Colors.GREEN}✓{Colors.END} Imported {len(new_rows)} words from '{external_csv_path.name}' and tagged them as HSK {hsk_level}.")
    print("  Run `cn sync` to add them to Anki.")

def cmd_vocab(args):
    """Shows the last 5 words added to the vocabulary list."""
    print("Showing last 5 added words...")
    vocab_data = get_vocab_data()
    if not vocab_data:
        print("No vocabulary found. Add some with `cn new`!")
        return
    
    for i, row in enumerate(reversed(vocab_data[-5:]), 1):
        anki_status = f"{Colors.GREEN}✓{Colors.END}" if row.get('AnkiNoteID') else f"{Colors.YELLOW}○{Colors.END}"
        print(f"\n{i}. {anki_status} {Colors.BOLD}{row.get('Hanzi')}{Colors.END} (HSK {row.get('HSKLevel')})")
        print(f"   {row.get('Pinyin')} — {row.get('English')}")

def cmd_sync_anki(args):
    """Syncs new words from the central CSV to Anki."""
    print("Syncing vocabulary to Anki...")
    try:
        anki = get_anki_connect()
    except (ConnectionError, ImportError) as e:
        print(f"{Colors.RED}✗ Error:{Colors.END} {e}")
        return

    vocab_data = get_vocab_data()
    if not vocab_data:
        print("Vocabulary list is empty. Nothing to sync.")
        return
    
    headers = vocab_data[0].keys() if vocab_data else []
    if 'AnkiNoteID' not in headers:
        print(f"{Colors.RED}✗ Error:{Colors.END} CSV file must have an 'AnkiNoteID' column.")
        return

    words_to_sync = [word for word in vocab_data if not word.get('AnkiNoteID')]

    if not words_to_sync:
        print(f"{Colors.GREEN}✓{Colors.END} All vocabulary is already synced to Anki.")
        return

    print(f"Found {len(words_to_sync)} new words to sync...")
    created_count, failed_count = 0, 0

    for i, word in enumerate(words_to_sync, 1):
        hsk_level = word.get('HSKLevel', 'N/A')
        deck_name = f"Chinese::HSK{hsk_level}"
        
        try:
            if deck_name not in anki.get_deck_names():
                anki.create_deck(deck_name)
                print(f"  Created Anki deck: {deck_name}")

            fields = {
                "Hanzi": word.get('Hanzi', ''),
                "Pinyin": word.get('Pinyin', ''),
                "English": word.get('English', ''),
                "ExampleSentence": word.get('ExampleSentence', ''),
                "ExampleTranslation": word.get('ExampleTranslation', ''),
                "Lesson": f"HSK {hsk_level}"
            }
            
            note_id = anki.add_note(deck_name, "Chinese (CLI)", fields, tags=[f"hsk{hsk_level}"])
            word['AnkiNoteID'] = note_id
            created_count += 1
            print(f"  [{i}/{len(words_to_sync)}] {Colors.GREEN}✓{Colors.END} Synced '{word['Hanzi']}'")

        except Exception as e:
            failed_count += 1
            print(f"  [{i}/{len(words_to_sync)}] {Colors.RED}✗{Colors.END} Failed to sync '{word.get('Hanzi', 'Unknown')}': {e}")

    save_vocab_data(vocab_data, headers)
    print(f"\n{Colors.BOLD}Sync complete!{Colors.END}")
    print(f"  {Colors.GREEN}Added to Anki: {created_count}{Colors.END}, {Colors.RED}Failed: {failed_count}{Colors.END}")

def cmd_setup_anki(args):
    """Setup Anki connection and models"""
    print("Setting up Anki integration...")
    try:
        anki = get_anki_connect()
        print(f"{Colors.GREEN}✓{Colors.END} Anki connection successful.")
        
        print("Checking for 'Chinese (CLI)' model...")
        if setup_chinese_model(anki):
            print(f"{Colors.GREEN}✓{Colors.END} Created 'Chinese (CLI)' model in Anki.")
        else:
            print(f"{Colors.BLUE}ℹ{Colors.END} 'Chinese (CLI)' model already exists or was updated.")
            
        print("\nSetup complete! You can now use `cn new` and `cn sync`.")

    except (ConnectionError, ImportError) as e:
        print(f"{Colors.RED}✗ Error:{Colors.END} {e}")
        print("  Please ensure Anki is running and the AnkiConnect addon is installed.")

def main():
    parser = argparse.ArgumentParser(description='Chinese Vocabulary CLI Tool')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # cn hsk
    hsk_parser = subparsers.add_parser('hsk', help='Set the current HSK context for new words')
    hsk_parser.add_argument('level', type=int, choices=[1, 2, 3, 4, 5, 6], help='HSK level (1-6)')

    # cn new
    new_parser = subparsers.add_parser('new', help='Add a new word or phrase using AI')
    new_parser.add_argument('phrase', help='The word/phrase to add')
    new_parser.add_argument('-l', '--lang', choices=['zh', 'en', 'pinyin'], default='en', help='The language of the input phrase')

    # cn import
    import_parser = subparsers.add_parser('import', help='Bulk-import words from an external CSV file')
    import_parser.add_argument('csv_file', help='Path to the CSV file to import')

    # cn vocab
    vocab_parser = subparsers.add_parser('vocab', help='Show the last 5 words added')

    # cn sync
    sync_parser = subparsers.add_parser('sync', help='Sync new words to Anki')

    # cn setup-anki
    setup_parser = subparsers.add_parser('setup-anki', help='One-time setup for Anki connection and note types')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return
    
    try:
        commands = {
            'hsk': cmd_hsk,
            'new': cmd_new,
            'import': cmd_import,
            'vocab': cmd_vocab,
            'sync': cmd_sync_anki,
            'setup-anki': cmd_setup_anki,
        }
        commands[args.command](args)
    except Exception as e:
        logger.error(f"Error executing command '{args.command}': {e}", exc_info=True)
        print(f"{Colors.RED}✗ Error:{Colors.END} {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
