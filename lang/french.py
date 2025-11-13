#!/usr/bin/env python3
"""
French Expressions CLI Tool
Capture, enrich, and sync French vocabulary to Anki.
"""

import os
import sys
import argparse
import json
import datetime
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
    from anki import AnkiConnect, setup_french_model
except ImportError:
    AnkiConnect = None
    setup_french_model = None

# --- Configuration ---
HOME = Path.home()
# Set default paths relative to the script's absolute location
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_FRENCH_DIR = SCRIPT_DIR / 'fr'
FRENCH_DIR = Path(os.path.expanduser(os.getenv("FRENCH_DIR", DEFAULT_FRENCH_DIR)))
FRENCH_DIR.mkdir(parents=True, exist_ok=True)
EXPRESSIONS_FILE = FRENCH_DIR / "expressions.json"

LOG_DIR = Path(os.path.expanduser(os.getenv("FRENCH_LOG_DIR", SCRIPT_DIR.parent / "logs")))
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "fr.log"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler(LOG_FILE)])
logger = logging.getLogger('fr')

class Colors:
    GREEN, BLUE, YELLOW, RED, BOLD, END = '\033[92m', '\033[94m', '\033[93m', '\033[91m', '\033[1m', '\033[0m'

# --- Core Functions ---

def load_expressions():
    if not EXPRESSIONS_FILE.exists():
        return {}
    with open(EXPRESSIONS_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_expressions(expressions):
    sorted_expressions = dict(sorted(expressions.items(), key=lambda x: x[1].get('added', ''), reverse=True))
    with open(EXPRESSIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(sorted_expressions, f, indent=2, ensure_ascii=False)

def get_anki_connect():
    if AnkiConnect is None:
        raise ImportError("Could not import anki.py. Make sure it's in the same directory.")
    anki = AnkiConnect()
    if not anki.check_connection():
        raise ConnectionError("Could not connect to Anki. Is Anki running with AnkiConnect installed?")
    return anki

def enrich_with_ai(phrase, lang):
    """Use AI to get structured data for a French word or phrase."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    lang_map = {'fr': 'French', 'en': 'English', 'zh': 'Chinese'}
    prompt = f"""
You are a French language expert. A student has given you a word/phrase in {lang_map.get(lang, 'French')}.
The phrase is: "{phrase}"

Your task is to return a JSON object with the following fields for the corresponding FRENCH expression:
- "expression": The French expression.
- "translation": A natural English translation.
- "register": The language register (e.g., "formal", "informal", "slang", "verlan").
- "usage": A short, practical explanation of when to use it.
- "example": A single, useful example sentence in French.
- "example_translation": The English translation of the example sentence.
- "notes": Any brief cultural context or notes.

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

def cmd_new(args):
    """Adds a new, AI-enriched expression to the list."""
    print(f"Creating new entry for '{args.phrase}'...")
    try:
        ai_data = enrich_with_ai(args.phrase, args.lang)
        expression = ai_data.get('expression')
        if not expression:
            raise ValueError("AI did not return a valid expression.")

        expressions = load_expressions()
        if expression.lower() in expressions:
            print(f"{Colors.YELLOW}⚠ This expression already exists.{Colors.END}")
            return

        print(f"  {Colors.BLUE}Expression:{Colors.END} {expression}")
        print(f"  {Colors.BLUE}Translation:{Colors.END} {ai_data.get('translation')}")
        print(f"  {Colors.BLUE}Register:{Colors.END} {ai_data.get('register')}")

        # Prepare new entry
        expressions[expression.lower()] = {
            'expression': expression,
            'translation': ai_data.get('translation', ''),
            'register': ai_data.get('register', ''),
            'usage': ai_data.get('usage', ''),
            'examples': [f"{ai_data.get('example', '')} | {ai_data.get('example_translation', '')}"],
            'notes': ai_data.get('notes', ''),
            'added': datetime.datetime.now().isoformat(),
            'anki_note_id': None
        }
        
        save_expressions(expressions)
        print(f"\n{Colors.GREEN}✓{Colors.END} Successfully added '{expression}' to your list.")
        print("  Run `fr sync` to add it to Anki.")

    except Exception as e:
        print(f"{Colors.RED}✗ Error creating new entry:{Colors.END} {e}")

def cmd_list(args):
    """Lists the most recent expressions."""
    expressions = load_expressions()
    if not expressions:
        print("No expressions found. Add one with `fr new`!")
        return

    limit = args.limit or 5
    print(f"Showing last {limit} added expressions...")
    
    for i, (key, data) in enumerate(list(expressions.items())[:limit], 1):
        anki_status = f"{Colors.GREEN}✓{Colors.END}" if data.get('anki_note_id') else f"{Colors.YELLOW}○{Colors.END}"
        print(f"\n{i}. {anki_status} {Colors.BOLD}{data.get('expression', key)}{Colors.END} ({data.get('register')})")
        print(f"   → {data.get('translation')}")

def cmd_sync(args):
    """Syncs new expressions to Anki."""
    print("Syncing expressions to Anki...")
    try:
        anki = get_anki_connect()
    except (ConnectionError, ImportError) as e:
        print(f"{Colors.RED}✗ Error:{Colors.END} {e}")
        return

    expressions = load_expressions()
    to_sync = {k: v for k, v in expressions.items() if not v.get('anki_note_id')}

    if not to_sync:
        print(f"{Colors.GREEN}✓{Colors.END} All expressions are already synced to Anki.")
        return

    print(f"Found {len(to_sync)} new expressions to sync...")
    created_count, failed_count = 0, 0
    deck_name = "French"

    for key, data in to_sync.items():
        try:
            if deck_name not in anki.get_deck_names():
                anki.create_deck(deck_name)
                print(f"  Created Anki deck: {deck_name}")

            example_full = data.get('examples', [""])[0]
            example_fr = example_full.split('|')[0].strip() if '|' in example_full else example_full

            fields = {
                "Expression": data.get('expression', key),
                "English": data.get('translation', ''),
                "Register": data.get('register', ''),
                "Usage": data.get('usage', ''),
                "Example": example_fr,
                "Notes": data.get('notes', '')
            }
            
            note_id = anki.add_note(deck_name, "French (CLI)", fields, tags=["french-cli"])
            expressions[key]['anki_note_id'] = note_id
            created_count += 1
            print(f"  {Colors.GREEN}✓{Colors.END} Synced '{data.get('expression', key)}'")

        except Exception as e:
            failed_count += 1
            print(f"  {Colors.RED}✗{Colors.END} Failed to sync '{data.get('expression', key)}': {e}")

    save_expressions(expressions)
    print(f"\n{Colors.BOLD}Sync complete!{Colors.END}")
    print(f"  {Colors.GREEN}Added to Anki: {created_count}{Colors.END}, {Colors.RED}Failed: {failed_count}{Colors.END}")

def cmd_setup_anki(args):
    """One-time setup for Anki connection and note types."""
    print("Setting up Anki integration for French...")
    try:
        anki = get_anki_connect()
        print(f"{Colors.GREEN}✓{Colors.END} Anki connection successful.")
        
        if setup_french_model(anki):
            print(f"{Colors.GREEN}✓{Colors.END} Created 'French (CLI)' model in Anki.")
        else:
            print(f"{Colors.BLUE}ℹ{Colors.END} 'French (CLI)' model already exists or was updated.")
            
        print("\nSetup complete! You can now use `fr new` and `fr sync`.")

    except (ConnectionError, ImportError) as e:
        print(f"{Colors.RED}✗ Error:{Colors.END} {e}")

def main():
    parser = argparse.ArgumentParser(description='French Expressions CLI Tool')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # fr new
    new_parser = subparsers.add_parser('new', help='Add a new, AI-enriched expression')
    new_parser.add_argument('phrase', help='The expression to add (in French, English, etc.)')
    new_parser.add_argument('-l', '--lang', choices=['fr', 'en', 'zh'], default='fr', help='Language of the input phrase')

    # fr list
    list_parser = subparsers.add_parser('list', help='List the most recent expressions')
    list_parser.add_argument('-n', '--limit', type=int, help='Number of expressions to show (default: 5)')

    # fr sync
    sync_parser = subparsers.add_parser('sync', help='Sync new expressions to Anki')

    # fr setup-anki
    setup_parser = subparsers.add_parser('setup-anki', help='One-time setup for Anki')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return
    
    try:
        commands = {
            'new': cmd_new,
            'list': cmd_list,
            'sync': cmd_sync,
            'setup-anki': cmd_setup_anki,
        }
        commands[args.command](args)
    except Exception as e:
        logger.error(f"Error executing command '{args.command}': {e}", exc_info=True)
        print(f"{Colors.RED}✗ Error:{Colors.END} {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
