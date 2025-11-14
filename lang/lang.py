#!/usr/bin/env python3
"""
Unified Language Learning CLI Tool
Capture, enrich, and sync vocabulary to Anki for any language.
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
    from anki import AnkiConnect
except ImportError:
    AnkiConnect = None

# --- Configuration ---
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIGS_DIR = SCRIPT_DIR / 'configs'
LOG_DIR = Path(os.path.expanduser(os.getenv("LANG_LOG_DIR", SCRIPT_DIR.parent / "logs")))
LOG_DIR.mkdir(parents=True, exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class Colors:
    GREEN, BLUE, YELLOW, RED, BOLD, END = '\033[92m', '\033[94m', '\033[93m', '\033[91m', '\033[1m', '\033[0m'

# --- Core Configuration Functions ---

def load_language_config(language_code):
    """Load language-specific configuration from JSON file."""
    config_file = CONFIGS_DIR / f"{language_code}.json"
    if not config_file.exists():
        raise ValueError(f"No configuration found for language '{language_code}' at {config_file}")

    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

class LanguageContext:
    """Holds all language-specific configuration and paths."""
    def __init__(self, language_code):
        self.config = load_language_config(language_code)
        self.language = self.config['language']
        self.language_full = self.config['language_full']

        # Setup paths
        self.data_dir = SCRIPT_DIR / self.config['storage']['data_dir']
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.vocab_file = self.data_dir / self.config['storage']['vocab_file']
        self.config_file = self.data_dir / self.config['storage']['config_file']
        self.last_action_file = self.data_dir / f".{language_code}_last_action.json"

        # Setup logging
        self.log_file = LOG_DIR / f"{language_code}.log"
        self.logger = logging.getLogger(language_code)
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file)
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # Fields mapping
        self.fields = self.config['fields']
        self.anki_config = self.config['anki']
        self.levels = self.config['levels']

# --- Data Management Functions ---

def load_vocab_data(ctx):
    """Load vocabulary data from JSON file."""
    if not ctx.vocab_file.exists():
        return {}
    with open(ctx.vocab_file, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_vocab_data(ctx, data):
    """Save vocabulary data to JSON file (sorted by date added)."""
    sorted_data = dict(sorted(data.items(), key=lambda item: item[1].get('added', '1970-01-01'), reverse=True))
    with open(ctx.vocab_file, 'w', encoding='utf-8') as f:
        json.dump(sorted_data, f, indent=2, ensure_ascii=False)

def load_user_config(ctx):
    """Load user-specific config (like current level)."""
    if ctx.config_file.exists():
        with open(ctx.config_file, 'r') as f:
            return json.load(f)
    return {"current_level": ctx.levels['default']}

def save_user_config(ctx, config):
    """Save user-specific config."""
    with open(ctx.config_file, 'w') as f:
        json.dump(config, f, indent=2)

def save_last_action(ctx, action_data):
    """Save last action for undo functionality."""
    with open(ctx.last_action_file, 'w') as f:
        json.dump(action_data, f)

def load_last_action(ctx):
    """Load last action."""
    if not ctx.last_action_file.exists():
        return None
    with open(ctx.last_action_file, 'r') as f:
        return json.load(f)

def clear_last_action(ctx):
    """Clear last action file."""
    if ctx.last_action_file.exists():
        ctx.last_action_file.unlink()

def get_anki_connect():
    """Get AnkiConnect instance."""
    if AnkiConnect is None:
        raise ImportError("Could not import anki.py.")
    anki = AnkiConnect()
    if not anki.check_connection():
        raise ConnectionError("Could not connect to Anki.")
    return anki

# --- AI Enrichment ---

def enrich_with_ai(ctx, phrase, lang, level, context=None, grammar=None):
    """Use AI to enrich vocabulary with translations, examples, etc."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not found.")

    # Build the prompt using config
    ai_config = ctx.config.get('ai', {})
    prompt_template = ai_config.get('prompt_template', '')

    # Default prompt if not in config
    if not prompt_template:
        prompt_parts = [
            f"You are a {ctx.language_full} language teacher. A student at {ctx.levels['type']} Level {level} has given you a word/phrase.",
            f"- The phrase is: \"{phrase}\" (input language: {lang})",
        ]
    else:
        # Use custom prompt from config (can include placeholders)
        prompt_parts = [
            prompt_template.format(
                language_full=ctx.language_full,
                level_type=ctx.levels['type'],
                level=level,
                phrase=phrase,
                lang=lang
            )
        ]

    if context:
        prompt_parts.append(f"- The student saw it in this context: \"{context}\"")

    # Describe expected JSON output based on config fields
    prompt_parts.extend([
        f"\nYour task is to return a JSON object with the following fields:",
        f"- \"{ctx.fields['primary']}\": The word/phrase in {ctx.language_full}.",
    ])

    if ctx.fields.get('phonetic'):
        prompt_parts.append(f"- \"{ctx.fields['phonetic']}\": Pronunciation/romanization.")

    prompt_parts.extend([
        f"- \"{ctx.fields['translation']}\": English translation.",
        f"- \"{ctx.fields['example']}\": A simple example sentence in {ctx.language_full}.",
        f"- \"{ctx.fields['example_translation']}\": English translation of the example.",
    ])

    if grammar:
        prompt_parts.append(f"- The student added this grammar note: \"{grammar}\"")
        prompt_parts.append(f"- \"{ctx.fields['grammar']}\": Expand on the student's grammar note.")
    else:
        prompt_parts.append(f"- \"{ctx.fields['grammar']}\": Brief grammar notes (can be empty if not relevant).")

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
        ctx.logger.error(f"AI enrichment failed: {e}")
        raise

# --- Command Implementations ---

def cmd_level(ctx, args):
    """Set the current proficiency level."""
    user_config = load_user_config(ctx)
    user_config['current_level'] = args.level
    save_user_config(ctx, user_config)
    print(f"{Colors.GREEN}✓{Colors.END} Set current {ctx.levels['type']} context to {Colors.BOLD}{args.level}{Colors.END}")

def cmd_new(ctx, args):
    """Add a new vocabulary item."""
    user_config = load_user_config(ctx)
    current_level = user_config.get('current_level', ctx.levels['default'])
    print(f"Adding new word with {ctx.levels['type']} {current_level} context...")

    try:
        ai_data = enrich_with_ai(ctx, args.phrase, args.lang, current_level, args.context, args.grammar)
        primary_key = ai_data.get(ctx.fields['primary'])

        if not primary_key:
            raise ValueError(f"AI did not return valid {ctx.fields['primary']}.")

        vocab_data = load_vocab_data(ctx)

        # Use lowercase as key for case-insensitive lookups
        lookup_key = primary_key.lower() if ctx.config.get('case_insensitive_keys', True) else primary_key

        if lookup_key in vocab_data:
            print(f"{Colors.YELLOW}⚠ This word already exists.{Colors.END}")
            return

        # Display what was enriched
        print(f"  {Colors.BLUE}{ctx.fields['primary']}:{Colors.END} {primary_key}")

        if ctx.fields.get('phonetic') and ai_data.get(ctx.fields['phonetic']):
            print(f"  {Colors.BLUE}{ctx.fields['phonetic']}:{Colors.END} {ai_data.get(ctx.fields['phonetic'])}")

        print(f"  {Colors.BLUE}{ctx.fields['translation']}:{Colors.END} {ai_data.get(ctx.fields['translation'])}")

        if ai_data.get(ctx.fields['example']):
            print(f"  {Colors.BLUE}Example:{Colors.END} {ai_data.get(ctx.fields['example'])}")
            print(f"           {ai_data.get(ctx.fields['example_translation'])}")

        if ai_data.get(ctx.fields['grammar']):
            grammar_preview = ai_data.get(ctx.fields['grammar'])[:100]
            print(f"  {Colors.BLUE}Grammar:{Colors.END} {grammar_preview}...")

        # Build vocab entry
        entry = {
            ctx.fields['primary']: primary_key,
            ctx.fields['translation']: ai_data.get(ctx.fields['translation'], ''),
            ctx.fields['example']: ai_data.get(ctx.fields['example'], ''),
            ctx.fields['example_translation']: ai_data.get(ctx.fields['example_translation'], ''),
            ctx.fields['grammar']: ai_data.get(ctx.fields['grammar'], ''),
            'Level': current_level,
            'AnkiNoteID': None,
            'added': datetime.datetime.now().isoformat()
        }

        # Add phonetic if applicable
        if ctx.fields.get('phonetic'):
            entry[ctx.fields['phonetic']] = ai_data.get(ctx.fields['phonetic'], '')

        vocab_data[lookup_key] = entry
        save_vocab_data(ctx, vocab_data)
        save_last_action(ctx, {'type': 'new', 'key': lookup_key})

        print(f"\n{Colors.GREEN}✓{Colors.END} Successfully added '{primary_key}'. You can use `{ctx.config['command_alias']} undo` to revert.")

    except Exception as e:
        print(f"{Colors.RED}✗ Error adding new word:{Colors.END} {e}")

def cmd_vocab(ctx, args):
    """Show recent vocabulary."""
    limit = args.limit if args.limit else 5
    print(f"Showing last {limit} added words...")

    vocab_data = load_vocab_data(ctx)
    if not vocab_data:
        print(f"No vocabulary found. Add some with `{ctx.config['command_alias']} new`!")
        return

    sorted_vocab = sorted(vocab_data.values(), key=lambda x: x.get('added', ''), reverse=True)

    for i, entry in enumerate(sorted_vocab[:limit], 1):
        anki_status = f"{Colors.GREEN}✓{Colors.END}" if entry.get('AnkiNoteID') or entry.get('anki_note_id') else f"{Colors.YELLOW}○{Colors.END}"

        # Handle backward compatibility with legacy field names
        primary = entry.get(ctx.fields['primary']) or entry.get(ctx.fields['primary'].lower()) or entry.get('expression') or '?'
        level = entry.get('Level') or entry.get('HSKLevel') or entry.get('CEFRLevel') or '?'
        translation = entry.get(ctx.fields['translation']) or entry.get(ctx.fields['translation'].lower()) or entry.get('translation') or ''

        print(f"\n{i}. {anki_status} {Colors.BOLD}{primary}{Colors.END} ({ctx.levels['type']} {level})")

        if ctx.fields.get('phonetic'):
            phonetic = entry.get(ctx.fields['phonetic']) or entry.get(ctx.fields['phonetic'].lower()) or ''
            if phonetic:
                print(f"   {phonetic} — {translation}")
            else:
                print(f"   {translation}")
        else:
            print(f"   {translation}")

def cmd_sync(ctx, args):
    """Sync vocabulary to Anki."""
    print("Syncing vocabulary to Anki...")

    try:
        anki = get_anki_connect()
    except (ConnectionError, ImportError) as e:
        print(f"{Colors.RED}✗ Error:{Colors.END} {e}")
        return

    vocab_data = load_vocab_data(ctx)
    if not vocab_data:
        print("Vocabulary list is empty.")
        return

    words_to_sync = [word for word in vocab_data.values() if not word.get('AnkiNoteID')]

    if not words_to_sync:
        print(f"{Colors.GREEN}✓{Colors.END} All vocabulary is already synced.")
        return

    print(f"Found {len(words_to_sync)} new words to sync...")

    created_count, failed_count = 0, 0

    for i, word in enumerate(words_to_sync, 1):
        # Determine deck name
        use_levels = ctx.anki_config.get('use_levels', True)

        if use_levels:
            # Handle backward compatibility with legacy field names
            level = word.get('Level') or word.get('HSKLevel') or word.get('CEFRLevel') or ctx.levels['default']
            deck_name = f"{ctx.anki_config['deck_prefix']}{level}"
        else:
            # Use single deck for languages like French
            deck_name = ctx.anki_config.get('deck_name', ctx.anki_config['deck_prefix'])

        try:
            # Create deck if needed
            if deck_name not in anki.get_deck_names():
                anki.create_deck(deck_name)
                print(f"  Created Anki deck: {deck_name}")

            # Build Anki fields
            # Get example and grammar
            example_raw = word.get(ctx.fields['example'], '')
            grammar = word.get(ctx.fields['grammar'], '')

            # Handle array format (French uses: ["sentence | translation"])
            if isinstance(example_raw, list) and example_raw:
                example_full = example_raw[0] if example_raw else ''
                if '|' in example_full:
                    example = example_full.split('|')[0].strip()
                else:
                    example = example_full
            else:
                example = example_raw

            # Combine grammar notes with example if present
            if grammar:
                combined_example = f"{example}<br><hr><div style='font-size: 16px; text-align: left; font-style: italic;'>{grammar}</div>"
            else:
                combined_example = example

            # Get field mapping from config
            field_mapping = ctx.anki_config.get('field_mapping', {})

            # Build anki_fields using the mapping
            anki_fields = {}

            # Map all fields from field_mapping
            for data_field, anki_field in field_mapping.items():
                if data_field == ctx.fields['example']:
                    # Use combined example (with grammar if present)
                    anki_fields[anki_field] = combined_example
                elif data_field in word:
                    # Map other fields directly from word data
                    anki_fields[anki_field] = word.get(data_field, '')

            # Map phonetic field if applicable (and not already mapped)
            if ctx.fields.get('phonetic') and ctx.fields['phonetic'] not in field_mapping:
                phonetic_value = word.get(ctx.fields['phonetic'], '')
                if phonetic_value:
                    anki_fields[ctx.fields['phonetic']] = phonetic_value

            # Add Lesson field for level-based languages
            if use_levels and 'Lesson' in field_mapping:
                level = word.get('Level') or word.get('HSKLevel') or word.get('CEFRLevel') or ctx.levels['default']
                anki_fields[field_mapping['Lesson']] = f"{ctx.levels['type']} {level}"
                tag = f"{ctx.anki_config['tag_prefix']}{level}".lower().replace(' ', '')
            else:
                tag = ctx.anki_config['tag_prefix']

            note_id = anki.add_note(deck_name, ctx.anki_config['model_name'], anki_fields, tags=[tag])

            # Update vocab with Anki note ID
            for key, entry in vocab_data.items():
                if entry.get(ctx.fields['primary']) == word.get(ctx.fields['primary']):
                    vocab_data[key]['AnkiNoteID'] = note_id
                    break

            created_count += 1
            print(f"  [{i}/{len(words_to_sync)}] {Colors.GREEN}✓{Colors.END} Synced '{word.get(ctx.fields['primary'])}'")

        except Exception as e:
            failed_count += 1
            print(f"  [{i}/{len(words_to_sync)}] {Colors.RED}✗{Colors.END} Failed to sync '{word.get(ctx.fields['primary'], 'Unknown')}': {e}")

    save_vocab_data(ctx, vocab_data)
    print(f"\n{Colors.BOLD}Sync complete!{Colors.END}\n  {Colors.GREEN}Added: {created_count}{Colors.END}, {Colors.RED}Failed: {failed_count}{Colors.END}")

def cmd_setup_anki(ctx, args):
    """Setup Anki integration."""
    print(f"Setting up Anki integration for {ctx.language_full}...")

    try:
        anki = get_anki_connect()
        print(f"{Colors.GREEN}✓{Colors.END} Anki connection successful.")

        # Import language-specific setup function
        model_name = ctx.anki_config['model_name']

        try:
            if ctx.language == 'chinese':
                from anki import setup_chinese_model
                if setup_chinese_model(anki):
                    print(f"{Colors.GREEN}✓{Colors.END} Created '{model_name}' model in Anki.")
                else:
                    print(f"{Colors.BLUE}ℹ{Colors.END} '{model_name}' model already exists or was updated.")
            elif ctx.language == 'french':
                from anki import setup_french_model
                if setup_french_model(anki):
                    print(f"{Colors.GREEN}✓{Colors.END} Created '{model_name}' model in Anki.")
                else:
                    print(f"{Colors.BLUE}ℹ{Colors.END} '{model_name}' model already exists or was updated.")
            else:
                print(f"{Colors.YELLOW}⚠{Colors.END} No automatic model setup available for {ctx.language_full}.")
                print(f"  Please create the '{model_name}' model manually in Anki.")
        except (ImportError, AttributeError) as e:
            print(f"{Colors.YELLOW}⚠{Colors.END} Could not setup model automatically: {e}")
            print(f"  You may need to create '{model_name}' manually in Anki.")

        print(f"\nSetup complete! You can now use `{ctx.config['command_alias']} new` and `{ctx.config['command_alias']} sync`.")

    except (ConnectionError, ImportError) as e:
        print(f"{Colors.RED}✗ Error:{Colors.END} {e}")
        print("  Please ensure Anki is running and the AnkiConnect addon is installed.")

def cmd_undo(ctx, args):
    """Undo the last 'new' action."""
    last_action = load_last_action(ctx)

    if not last_action or last_action.get('type') != 'new':
        print(f"{Colors.YELLOW}No 'new' action to undo.{Colors.END}")
        return

    key_to_remove = last_action.get('key')
    if not key_to_remove:
        print(f"{Colors.RED}✗ Undo failed: last action had no key.{Colors.END}")
        return

    vocab_data = load_vocab_data(ctx)

    if key_to_remove in vocab_data:
        removed_item = vocab_data.pop(key_to_remove)
        save_vocab_data(ctx, vocab_data)
        print(f"{Colors.GREEN}✓{Colors.END} Undid the addition of '{removed_item.get(ctx.fields['primary'])}'.")
        clear_last_action(ctx)
    else:
        print(f"{Colors.YELLOW}⚠ Could not find '{key_to_remove}' to undo.{Colors.END}")
        clear_last_action(ctx)

# --- Main Entry Point ---

def main():
    if len(sys.argv) < 2:
        print(f"{Colors.RED}✗ Error:{Colors.END} Please specify a language code (e.g., 'cn', 'fr')")
        print(f"Usage: lang <language_code> <command> [options]")
        sys.exit(1)

    language_code = sys.argv[1]

    # Load language context
    try:
        ctx = LanguageContext(language_code)
    except Exception as e:
        print(f"{Colors.RED}✗ Error:{Colors.END} {e}")
        sys.exit(1)

    # Parse remaining arguments
    parser = argparse.ArgumentParser(
        description=f'{ctx.language_full} Vocabulary CLI Tool',
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # level command
    level_parser = subparsers.add_parser('level', help=f'Set the current {ctx.levels["type"]} context')
    if isinstance(ctx.levels['values'], list) and isinstance(ctx.levels['values'][0], int):
        level_parser.add_argument('level', type=int, choices=ctx.levels['values'], help=f'{ctx.levels["type"]} level')
    else:
        level_parser.add_argument('level', choices=ctx.levels['values'], help=f'{ctx.levels["type"]} level')

    # new command
    new_parser = subparsers.add_parser('new', help='Add a new word or phrase using AI')
    new_parser.add_argument('phrase', help='The word or phrase to add')
    new_parser.add_argument('-l', '--lang', default=ctx.config.get('default_input_lang', 'en'),
                           help='The language of the input phrase')
    new_parser.add_argument('-c', '--context', help='Provide context where you saw the phrase')
    new_parser.add_argument('-g', '--grammar', help='Add a specific grammar note')

    # vocab command
    vocab_parser = subparsers.add_parser('vocab', help='Show recent vocabulary')
    vocab_parser.add_argument('-n', '--limit', type=int, help='Number of words to show (default: 5)')

    # sync command
    sync_parser = subparsers.add_parser('sync', help='Sync new words to Anki')

    # setup-anki command
    setup_parser = subparsers.add_parser('setup-anki', help='One-time setup for Anki')

    # undo command
    undo_parser = subparsers.add_parser('undo', help='Undo the last word addition')

    # Parse args (skip first two: script name and language code)
    args = parser.parse_args(sys.argv[2:])

    if not args.command:
        parser.print_help()
        return

    try:
        commands = {
            'level': cmd_level,
            'new': cmd_new,
            'vocab': cmd_vocab,
            'sync': cmd_sync,
            'setup-anki': cmd_setup_anki,
            'undo': cmd_undo,
        }
        commands[args.command](ctx, args)
    except Exception as e:
        ctx.logger.error(f"Error executing command '{args.command}': {e}", exc_info=True)
        print(f"{Colors.RED}✗ Error:{Colors.END} {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
