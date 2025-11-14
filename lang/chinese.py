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
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_ZH_DIR = SCRIPT_DIR / 'zh'
DEFAULT_ZH_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = Path(os.path.expanduser(os.getenv("CHINESE_CONFIG_FILE", DEFAULT_ZH_DIR / ".cn_config.json")))
LAST_ACTION_FILE = DEFAULT_ZH_DIR / ".cn_last_action.json"
LOG_DIR = Path(os.path.expanduser(os.getenv("CHINESE_LOG_DIR", SCRIPT_DIR.parent.parent / "logs")))
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "cn.log"

DEFAULT_JSON_PATH = DEFAULT_ZH_DIR / "chinese_vocab.json"
VOCAB_JSON_PATH = Path(os.path.expanduser(os.getenv("CHINESE_VOCAB_JSON", DEFAULT_JSON_PATH)))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler(LOG_FILE)])
logger = logging.getLogger('cn')

class Colors:
    GREEN, BLUE, YELLOW, RED, BOLD, END = '\033[92m', '\033[94m', '\033[93m', '\033[91m', '\033[1m', '\033[0m'

# --- Core Data Functions ---

def migrate_csv_to_json():
    """One-time migration from CSV to JSON."""
    old_csv_path = VOCAB_JSON_PATH.with_suffix('.csv')
    if old_csv_path.exists() and not VOCAB_JSON_PATH.exists():
        print(f"{Colors.YELLOW}Migrating old CSV to new JSON format...{Colors.END}")
        vocab_dict = {}
        try:
            with open(old_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    hanzi = row.get('Hanzi')
                    if hanzi:
                        row['added'] = datetime.datetime.now().isoformat()
                        vocab_dict[hanzi] = row
            
            with open(VOCAB_JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump(vocab_dict, f, indent=2, ensure_ascii=False)
            
            old_csv_path.rename(old_csv_path.with_suffix('.csv.bak'))
            print(f"{Colors.GREEN}✓ Migration complete. Old CSV renamed to {old_csv_path.name}.bak{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}✗ Migration failed: {e}{Colors.END}")
        return True
    return False

def load_vocab_data():
    if not VOCAB_JSON_PATH.exists():
        return {}
    with open(VOCAB_JSON_PATH, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_vocab_data(data):
    sorted_data = dict(sorted(data.items(), key=lambda item: item[1].get('added', '1970-01-01'), reverse=True))
    with open(VOCAB_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(sorted_data, f, indent=2, ensure_ascii=False)

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"current_hsk": 1}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def save_last_action(action_data):
    with open(LAST_ACTION_FILE, 'w') as f:
        json.dump(action_data, f)

def load_last_action():
    if not LAST_ACTION_FILE.exists():
        return None
    with open(LAST_ACTION_FILE, 'r') as f:
        return json.load(f)

def clear_last_action():
    if LAST_ACTION_FILE.exists():
        LAST_ACTION_FILE.unlink()

def get_anki_connect():
    if AnkiConnect is None: raise ImportError("Could not import anki.py.")
    anki = AnkiConnect()
    if not anki.check_connection(): raise ConnectionError("Could not connect to Anki.")
    return anki

def enrich_with_ai(phrase, lang, hsk_level, context=None, grammar=None):
    if not OPENAI_API_KEY: raise ValueError("OPENAI_API_KEY not found.")
    lang_map = {'zh': 'Chinese', 'en': 'English', 'pinyin': 'Pinyin'}
    prompt_parts = [
        f"You are a Chinese language teacher. A student at HSK Level {hsk_level} has given you a word/phrase.",
        f"- The phrase is: \"{phrase}\" (language: {lang_map.get(lang, 'Chinese')})",
    ]
    if context: prompt_parts.append(f"- The student saw it in this context: \"{context}\"")

    prompt_parts.extend([
        "\nYour task is to return a JSON object with the following fields: \"hanzi\", \"pinyin\", \"english\", \"example_hanzi\", \"example_english\", \"grammar_notes\".",
        "- Always provide a simple, clear example sentence in `example_hanzi` and its translation in `example_english`.",
        "- If context was provided, use it to inspire your example.",
    ])

    if grammar:
        prompt_parts.append(f"- The student added this grammar note: \"{grammar}\"")
        prompt_parts.append("- Expand on the student's grammar note in the `grammar_notes` field.")
    else:
        prompt_parts.append("- The `grammar_notes` field should only be populated if the user asks a specific grammar question. Otherwise, leave it as an empty string.")

    prompt_parts.append("\nReturn ONLY the valid JSON object.")
    prompt = "\n".join(prompt_parts)
    try:
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {OPENAI_API_KEY}', 'Content-Type': 'application/json'},
            json={'model': 'gpt-3.5-turbo', 'messages': [{'role': 'user', 'content': prompt}], 'temperature': 0.5},
            timeout=45
        )
        response.raise_for_status()
        return json.loads(response.json()['choices'][0]['message']['content'].strip())
    except Exception as e:
        logger.error(f"AI enrichment failed: {e}"); raise

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
        ai_data = enrich_with_ai(args.phrase, args.lang, hsk_level, args.context, args.grammar)
        hanzi = ai_data.get('hanzi')
        if not hanzi: raise ValueError("AI did not return valid Hanzi.")
        vocab_data = load_vocab_data()
        if hanzi in vocab_data:
            print(f"{Colors.YELLOW}⚠ This word already exists.{Colors.END}")
            return
        print(f"  {Colors.BLUE}Hanzi:{Colors.END} {hanzi}")
        print(f"  {Colors.BLUE}Pinyin:{Colors.END} {ai_data.get('pinyin')}")
        print(f"  {Colors.BLUE}English:{Colors.END} {ai_data.get('english')}")
        if ai_data.get('example_hanzi'):
            print(f"  {Colors.BLUE}Example:{Colors.END} {ai_data.get('example_hanzi')}")
            print(f"           {ai_data.get('example_english')}")
        if ai_data.get('grammar_notes'):
            print(f"  {Colors.BLUE}Grammar:{Colors.END} {ai_data.get('grammar_notes')[:100]}...")
        vocab_data[hanzi] = {
            'Hanzi': hanzi, 'Pinyin': ai_data.get('pinyin', ''), 'English': ai_data.get('english', ''),
            'ExampleSentence': ai_data.get('example_hanzi', ''), 'ExampleTranslation': ai_data.get('example_english', ''),
            'Grammar': ai_data.get('grammar_notes', ''), 'HSKLevel': hsk_level, 'AnkiNoteID': None,
            'added': datetime.datetime.now().isoformat()
        }
        save_vocab_data(vocab_data)
        save_last_action({'type': 'new', 'key': hanzi})
        print(f"\n{Colors.GREEN}✓{Colors.END} Successfully added '{hanzi}'. You can use `cn undo` to revert.")
    except Exception as e:
        print(f"{Colors.RED}✗ Error adding new word:{Colors.END} {e}")

def cmd_import(args):
    config = load_config()
    hsk_level = config.get('current_hsk', 1)
    external_csv_path = Path(args.csv_file).expanduser()
    if not external_csv_path.exists():
        print(f"{Colors.RED}✗ Error:{Colors.END} File not found at {external_csv_path}"); return
    try:
        with open(external_csv_path, 'r', encoding='utf-8') as f:
            external_words = list(csv.DictReader(f))
    except Exception as e:
        print(f"{Colors.RED}✗ Error:{Colors.END} Could not read CSV file: {e}"); return
    vocab_data = load_vocab_data()
    added_count = 0
    for word in external_words:
        hanzi = word.get('Hanzi', word.get('simplified', ''))
        if not hanzi or hanzi in vocab_data: continue
        vocab_data[hanzi] = {
            'Hanzi': hanzi, 'Pinyin': word.get('Pinyin', word.get('pinyin', '')),
            'English': word.get('English', word.get('definitions', '')),
            'ExampleSentence': word.get('ExampleSentence', word.get('example', '')),
            'ExampleTranslation': word.get('ExampleTranslation', word.get('exampleTranslation', '')),
            'Grammar': word.get('Grammar', ''), 'HSKLevel': hsk_level, 'AnkiNoteID': None,
            'added': datetime.datetime.now().isoformat()
        }
        added_count += 1
    save_vocab_data(vocab_data)
    print(f"{Colors.GREEN}✓{Colors.END} Imported {added_count} new words and tagged as HSK {hsk_level}.")

def cmd_vocab(args):
    print("Showing last 5 added words...")
    vocab_data = load_vocab_data()
    if not vocab_data: print("No vocabulary found. Add some with `cn new`!"); return
    sorted_vocab = sorted(vocab_data.values(), key=lambda x: x.get('added', ''), reverse=True)
    for i, row in enumerate(sorted_vocab[:5], 1):
        anki_status = f"{Colors.GREEN}✓{Colors.END}" if row.get('AnkiNoteID') else f"{Colors.YELLOW}○{Colors.END}"
        print(f"\n{i}. {anki_status} {Colors.BOLD}{row.get('Hanzi')}{Colors.END} (HSK {row.get('HSKLevel')})")
        print(f"   {row.get('Pinyin')} — {row.get('English')}")

def cmd_sync(args):
    print("Syncing vocabulary to Anki...")
    try: anki = get_anki_connect()
    except (ConnectionError, ImportError) as e: print(f"{Colors.RED}✗ Error:{Colors.END} {e}"); return
    vocab_data = load_vocab_data()
    if not vocab_data: print("Vocabulary list is empty."); return
    words_to_sync = [word for word in vocab_data.values() if not word.get('AnkiNoteID')]
    if not words_to_sync: print(f"{Colors.GREEN}✓{Colors.END} All vocabulary is already synced."); return
    print(f"Found {len(words_to_sync)} new words to sync...")
    created_count, failed_count = 0, 0
    for i, word in enumerate(words_to_sync, 1):
        hsk_level = word.get('HSKLevel', 'N/A')
        deck_name = f"Chinese::HSK{hsk_level}"
        try:
            if deck_name not in anki.get_deck_names(): anki.create_deck(deck_name); print(f"  Created Anki deck: {deck_name}")
            example_sentence = word.get('ExampleSentence', ''); grammar_notes = word.get('Grammar', '')
            combined_example = f"{example_sentence}<br><hr><div style='font-size: 16px; text-align: left; font-style: italic;'>{grammar_notes}</div>" if grammar_notes else example_sentence
            fields = {
                "Hanzi": word.get('Hanzi', ''), "Pinyin": word.get('Pinyin', ''), "English": word.get('English', ''),
                "ExampleSentence": combined_example, "ExampleTranslation": word.get('ExampleTranslation', ''),
                "Lesson": f"HSK {hsk_level}"
            }
            note_id = anki.add_note(deck_name, "Chinese (CLI)", fields, tags=[f"hsk{hsk_level}"])
            vocab_data[word['Hanzi']]['AnkiNoteID'] = note_id
            created_count += 1
            print(f"  [{i}/{len(words_to_sync)}] {Colors.GREEN}✓{Colors.END} Synced '{word['Hanzi']}'")
        except Exception as e:
            failed_count += 1; print(f"  [{i}/{len(words_to_sync)}] {Colors.RED}✗{Colors.END} Failed to sync '{word.get('Hanzi', 'Unknown')}': {e}")
    save_vocab_data(vocab_data)
    print(f"\n{Colors.BOLD}Sync complete!{Colors.END}\n  {Colors.GREEN}Added: {created_count}{Colors.END}, {Colors.RED}Failed: {failed_count}{Colors.END}")

def cmd_setup_anki(args):
    print("Setting up Anki integration...")
    try:
        anki = get_anki_connect()
        print(f"{Colors.GREEN}✓{Colors.END} Anki connection successful.")
        if setup_chinese_model(anki): print(f"{Colors.GREEN}✓{Colors.END} Created 'Chinese (CLI)' model in Anki.")
        else: print(f"{Colors.BLUE}ℹ{Colors.END} 'Chinese (CLI)' model already exists or was updated.")
        print("\nSetup complete! You can now use `cn new` and `cn sync`.")
    except (ConnectionError, ImportError) as e:
        print(f"{Colors.RED}✗ Error:{Colors.END} {e}\n  Please ensure Anki is running and the AnkiConnect addon is installed.")

def cmd_undo(args):
    last_action = load_last_action()
    if not last_action or last_action.get('type') != 'new':
        print(f"{Colors.YELLOW}No 'new' action to undo.{Colors.END}"); return
    key_to_remove = last_action.get('key')
    if not key_to_remove: print(f"{Colors.RED}✗ Undo failed: last action had no key.{Colors.END}"); return
    vocab_data = load_vocab_data()
    if key_to_remove in vocab_data:
        removed_item = vocab_data.pop(key_to_remove)
        save_vocab_data(vocab_data)
        print(f"{Colors.GREEN}✓{Colors.END} Undid the addition of '{removed_item.get('Hanzi')}'.")
        clear_last_action()
    else:
        print(f"{Colors.YELLOW}⚠ Could not find '{key_to_remove}' to undo.{Colors.END}"); clear_last_action()

def main():
    print(f"DEBUG: Arguments received: {sys.argv}")
    migrate_csv_to_json()
    parser = argparse.ArgumentParser(description='Chinese Vocabulary CLI Tool', formatter_class=argparse.RawTextHelpFormatter)
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    hsk_parser = subparsers.add_parser('hsk', help='Set the current HSK context for new words')
    hsk_parser.add_argument('level', type=int, choices=[1, 2, 3, 4, 5, 6], help='HSK level (1-6)')
    new_parser = subparsers.add_parser('new', help='Add a new word or phrase using AI')
    new_parser.add_argument('phrase', help='The word or phrase to add. Use quotes for multiple words.')
    new_parser.add_argument('-l', '--lang', choices=['zh', 'en', 'pinyin'], default='en', help='The language of the input phrase')
    new_parser.add_argument('-c', '--context', help='Provide context (e.g., a sentence) where you saw the phrase')
    new_parser.add_argument('-g', '--grammar', help='Add a specific grammar note for the AI to expand on')
    import_parser = subparsers.add_parser('import', help='Bulk-import words from an external CSV file')
    import_parser.add_argument('csv_file', help='Path to the CSV file to import')
    vocab_parser = subparsers.add_parser('vocab', help='Show the last 5 words added')
    sync_parser = subparsers.add_parser('sync', help='Sync new words to Anki')
    setup_parser = subparsers.add_parser('setup-anki', help='One-time setup for Anki connection and note types')
    undo_parser = subparsers.add_parser('undo', help='Undo the last word addition')
    args = parser.parse_args()
    if not args.command: parser.print_help(); return
    try:
        commands = {'hsk': cmd_hsk, 'new': cmd_new, 'import': cmd_import, 'vocab': cmd_vocab, 'sync': cmd_sync, 'setup-anki': cmd_setup_anki, 'undo': cmd_undo}
        commands[args.command](args)
    except Exception as e:
        logger.error(f"Error executing command '{args.command}': {e}", exc_info=True)
        print(f"{Colors.RED}✗ Error:{Colors.END} {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
