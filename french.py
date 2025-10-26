#!/usr/bin/env python3
"""
French Expressions CLI Tool
Quick capture and AI-enhanced review of French slang and expressions
"""

import os
import sys
import argparse
import json
import datetime
import logging
import random
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv

# Try to find .env in common locations
env_paths = [
    Path.home() / "dev" / "scripts" / ".env",
    Path.home() / ".env",
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break

# Paths from environment variables
HOME = Path.home()
FRENCH_DIR = Path(os.path.expanduser(os.getenv("FRENCH_DIR", "~/eurecom/french")))
FRENCH_DIR.mkdir(parents=True, exist_ok=True)

EXPRESSIONS_FILE = FRENCH_DIR / "expressions.json"
CONFIG_FILE = FRENCH_DIR / ".fr_config.json"

# Setup logging
LOG_DIR = Path(os.path.expanduser(os.getenv("FRENCH_LOG_DIR", "~/dev/scripts/logs")))
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "fr.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
    ]
)
logger = logging.getLogger('fr')

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

def load_expressions():
    """Load expressions from JSON file"""
    if EXPRESSIONS_FILE.exists():
        with open(EXPRESSIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_expressions(expressions):
    """Save expressions to JSON file"""
    with open(EXPRESSIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(expressions, f, indent=2, ensure_ascii=False)

def load_config():
    """Load configuration"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_config(config):
    """Save configuration"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# ============ COMMANDS ============

def cmd_add(args):
    """Add a new French expression"""
    expressions = load_expressions()
    
    expression = args.expression.lower().strip()
    
    if expression in expressions:
        print(f"{Colors.YELLOW}⚠{Colors.END} Expression already exists!")
        print(f"  Use 'fr show \"{expression}\"' to view it")
        return
    
    expressions[expression] = {
        'raw_context': args.context or '',
        'enhanced': False,
        'added': datetime.datetime.now().isoformat(),
    }
    
    save_expressions(expressions)
    logger.info(f"Added expression: {expression}")
    
    print(f"{Colors.GREEN}✓{Colors.END} Added: {Colors.BOLD}{expression}{Colors.END}")
    if args.context:
        print(f"  Context: {args.context}")

def cmd_enhance(args):
    """Enhance expression(s) with AI"""
    expressions = load_expressions()
    
    if args.all:
        # Enhance all unprocessed expressions
        unenhanced = [expr for expr, data in expressions.items() if not data.get('enhanced', False)]
        
        if not unenhanced:
            print(f"{Colors.GREEN}✓{Colors.END} All expressions are already enhanced!")
            return
        
        print(f"{Colors.CYAN}Found {len(unenhanced)} expressions to enhance{Colors.END}")
        print(f"{Colors.YELLOW}Note:{Colors.END} This will use Claude API to enhance expressions.")
        confirm = input("Continue? (y/n): ").strip().lower()
        
        if confirm != 'y':
            print("Cancelled.")
            return
        
        for expr in unenhanced:
            print(f"\n{Colors.CYAN}Enhancing:{Colors.END} {expr}")
            # TODO: Call Claude API here to enhance
            print(f"{Colors.YELLOW}⚠{Colors.END} AI enhancement not yet implemented!")
            print(f"  For now, manually edit: {EXPRESSIONS_FILE}")
            break
    
    elif args.expression:
        # Enhance specific expression
        expr = args.expression.lower().strip()
        
        if expr not in expressions:
            print(f"{Colors.RED}✗{Colors.END} Expression not found: {expr}")
            return
        
        if expressions[expr].get('enhanced', False):
            print(f"{Colors.YELLOW}⚠{Colors.END} Expression already enhanced!")
            print(f"  Use 'fr show \"{expr}\"' to view it")
            return
        
        print(f"{Colors.CYAN}Enhancing:{Colors.END} {expr}")
        print(f"{Colors.YELLOW}⚠{Colors.END} AI enhancement not yet implemented!")
        print(f"  For now, manually edit: {EXPRESSIONS_FILE}")
        print(f"\n  Add these fields:")
        print(f"    - translation: English meaning")
        print(f"    - register: banlieue/informal/formal")
        print(f"    - usage: When/how to use it")
        print(f"    - examples: [list of example sentences]")
        print(f"    - similar: [similar expressions]")
        print(f"    - enhanced: true")
    
    else:
        print(f"{Colors.RED}✗{Colors.END} Specify --all or provide an expression")

def cmd_list(args):
    """List all expressions"""
    expressions = load_expressions()
    
    if not expressions:
        print(f"{Colors.YELLOW}⚠{Colors.END} No expressions yet!")
        print(f"  Add one with: fr add \"expression\" --context \"context\"")
        return
    
    enhanced_count = sum(1 for data in expressions.values() if data.get('enhanced', False))
    total = len(expressions)
    
    print(f"{Colors.BOLD}📚 French Expressions ({enhanced_count}/{total} enhanced){Colors.END}\n")
    
    for i, (expr, data) in enumerate(sorted(expressions.items()), 1):
        status = f"{Colors.GREEN}✓{Colors.END}" if data.get('enhanced') else f"{Colors.YELLOW}○{Colors.END}"
        print(f"{status} {i}. {Colors.BOLD}{expr}{Colors.END}")
        
        if data.get('translation'):
            print(f"   → {data['translation']}")
        elif data.get('raw_context'):
            print(f"   Context: {data['raw_context']}")
        
        if args.verbose and data.get('register'):
            print(f"   Style: {data['register']}")

def cmd_show(args):
    """Show details of a specific expression"""
    expressions = load_expressions()
    expr = args.expression.lower().strip()
    
    if expr not in expressions:
        print(f"{Colors.RED}✗{Colors.END} Expression not found: {expr}")
        print(f"  Use 'fr search' to find similar expressions")
        return
    
    data = expressions[expr]
    
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}{expr}{Colors.END}")
    print("=" * len(expr))
    
    if data.get('translation'):
        print(f"\n{Colors.GREEN}Translation:{Colors.END} {data['translation']}")
    
    if data.get('register'):
        print(f"{Colors.CYAN}Register:{Colors.END} {data['register']}")
    
    if data.get('raw_context'):
        print(f"\n{Colors.BLUE}Original Context:{Colors.END}")
        print(f"  {data['raw_context']}")
    
    if data.get('usage'):
        print(f"\n{Colors.YELLOW}Usage:{Colors.END}")
        print(f"  {data['usage']}")
    
    if data.get('examples'):
        print(f"\n{Colors.GREEN}Examples:{Colors.END}")
        for ex in data['examples']:
            print(f"  • {ex}")
    
    if data.get('similar'):
        print(f"\n{Colors.CYAN}Similar expressions:{Colors.END}")
        print(f"  {', '.join(data['similar'])}")
    
    print(f"\n{Colors.BOLD}Added:{Colors.END} {data['added'][:10]}")
    if data.get('enhanced_date'):
        print(f"{Colors.BOLD}Enhanced:{Colors.END} {data['enhanced_date'][:10]}")
    print()

def cmd_search(args):
    """Search for expressions"""
    expressions = load_expressions()
    query = args.query.lower()
    
    results = []
    for expr, data in expressions.items():
        if query in expr.lower():
            results.append((expr, data))
        elif data.get('translation') and query in data['translation'].lower():
            results.append((expr, data))
        elif data.get('raw_context') and query in data['raw_context'].lower():
            results.append((expr, data))
    
    if not results:
        print(f"{Colors.YELLOW}⚠{Colors.END} No expressions found matching '{query}'")
        return
    
    print(f"{Colors.CYAN}Found {len(results)} expression(s):{Colors.END}\n")
    
    for expr, data in results:
        status = f"{Colors.GREEN}✓{Colors.END}" if data.get('enhanced') else f"{Colors.YELLOW}○{Colors.END}"
        print(f"{status} {Colors.BOLD}{expr}{Colors.END}")
        
        if data.get('translation'):
            print(f"   → {data['translation']}")
        elif data.get('raw_context'):
            print(f"   Context: {data['raw_context']}")
        print()

def cmd_random(args):
    """Get a random expression to review"""
    expressions = load_expressions()
    
    if not expressions:
        print(f"{Colors.YELLOW}⚠{Colors.END} No expressions yet!")
        return
    
    # Prefer enhanced expressions
    enhanced = [(expr, data) for expr, data in expressions.items() if data.get('enhanced')]
    
    if enhanced:
        expr, data = random.choice(enhanced)
    else:
        expr, data = random.choice(list(expressions.items()))
    
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}{expr}{Colors.END}\n")
    
    input(f"{Colors.CYAN}Think of the meaning... (press Enter to reveal){Colors.END}")
    
    if data.get('translation'):
        print(f"\n{Colors.GREEN}Translation:{Colors.END} {data['translation']}")
    
    if data.get('usage'):
        print(f"{Colors.YELLOW}Usage:{Colors.END} {data['usage']}")
    
    if data.get('examples'):
        print(f"\n{Colors.GREEN}Example:{Colors.END}")
        print(f"  {random.choice(data['examples'])}")
    
    print()

def cmd_stats(args):
    """Show statistics"""
    expressions = load_expressions()
    
    if not expressions:
        print(f"{Colors.YELLOW}⚠{Colors.END} No expressions yet!")
        return
    
    total = len(expressions)
    enhanced = sum(1 for data in expressions.values() if data.get('enhanced', False))
    unenhanced = total - enhanced
    
    # Count by register
    registers = {}
    for data in expressions.values():
        if data.get('register'):
            reg = data['register']
            registers[reg] = registers.get(reg, 0) + 1
    
    print(f"{Colors.BOLD}📊 French Expressions Stats{Colors.END}\n")
    print(f"  Total expressions: {total}")
    print(f"  {Colors.GREEN}Enhanced: {enhanced}{Colors.END}")
    print(f"  {Colors.YELLOW}Unenhanced: {unenhanced}{Colors.END}")
    
    if registers:
        print(f"\n{Colors.CYAN}By register:{Colors.END}")
        for reg, count in sorted(registers.items(), key=lambda x: x[1], reverse=True):
            print(f"  {reg}: {count}")

def cmd_sync(args):
    """Sync to Google Drive"""
    cloud_dir = Path(os.path.expanduser(os.getenv("FRENCH_CLOUD_DIR", "~/Google/French")))
    cloud_dir.mkdir(parents=True, exist_ok=True)
    
    import shutil
    
    # Copy expressions file
    if EXPRESSIONS_FILE.exists():
        shutil.copy(EXPRESSIONS_FILE, cloud_dir / "expressions.json")
        print(f"{Colors.GREEN}✓{Colors.END} Synced to Google Drive!")
        logger.info("Synced expressions to Google Drive")
    else:
        print(f"{Colors.YELLOW}⚠{Colors.END} No expressions file to sync")

def main():
    parser = argparse.ArgumentParser(description='French Expressions CLI Tool')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # add command
    add_parser = subparsers.add_parser('add', help='Add a new expression')
    add_parser.add_argument('expression', help='French expression')
    add_parser.add_argument('--context', '-c', help='Context where it was used')
    
    # enhance command
    enhance_parser = subparsers.add_parser('enhance', help='Enhance expression(s) with AI')
    enhance_parser.add_argument('expression', nargs='?', help='Specific expression to enhance')
    enhance_parser.add_argument('--all', action='store_true', help='Enhance all unprocessed expressions')
    
    # list command
    list_parser = subparsers.add_parser('list', help='List all expressions')
    list_parser.add_argument('-v', '--verbose', action='store_true', help='Show more details')
    
    # show command
    show_parser = subparsers.add_parser('show', help='Show details of an expression')
    show_parser.add_argument('expression', help='Expression to show')
    
    # search command
    search_parser = subparsers.add_parser('search', help='Search expressions')
    search_parser.add_argument('query', help='Search query')
    
    # random command
    random_parser = subparsers.add_parser('random', help='Get random expression to review')
    
    # stats command
    stats_parser = subparsers.add_parser('stats', help='Show statistics')
    
    # sync command
    sync_parser = subparsers.add_parser('sync', help='Sync to Google Drive')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        commands = {
            'add': cmd_add,
            'enhance': cmd_enhance,
            'list': cmd_list,
            'show': cmd_show,
            'search': cmd_search,
            'random': cmd_random,
            'stats': cmd_stats,
            'sync': cmd_sync,
        }
        
        commands[args.command](args)
    except Exception as e:
        logger.error(f"Error executing command '{args.command}': {str(e)}", exc_info=True)
        print(f"{Colors.RED}✗ Error:{Colors.END} {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
