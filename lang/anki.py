#!/usr/bin/env python3
"""
AnkiConnect API Wrapper
A module for interacting with the AnkiConnect addon for Anki.
"""

import json
import logging
import requests

# Setup logging
logger = logging.getLogger('anki_sync')

ANKI_CONNECT_URL = "http://localhost:8765"

class AnkiConnect:
    """A wrapper for the AnkiConnect API"""

    def __init__(self, url=ANKI_CONNECT_URL):
        self.url = url
        self.session = requests.Session()

    def _invoke(self, action, **params):
        """Invoke an AnkiConnect action"""
        payload = {"action": action, "version": 6, "params": params}
        try:
            response = self.session.post(self.url, data=json.dumps(payload), timeout=5)
            response.raise_for_status()
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            return result.get('result')
        except requests.exceptions.RequestException as e:
            logger.error(f"AnkiConnect API request failed: {e}")
            raise ConnectionError("Could not connect to Anki. Is Anki running with AnkiConnect installed?") from e
        except Exception as e:
            logger.error(f"AnkiConnect action '{action}' failed: {e}")
            raise

    def check_connection(self):
        """Check if AnkiConnect is running"""
        try:
            self._invoke('deckNames')
            return True
        except ConnectionError:
            return False

    def get_deck_names(self):
        """Get a list of all deck names"""
        return self._invoke('deckNames')

    def create_deck(self, deck_name):
        """Create a new deck"""
        return self._invoke('createDeck', deck=deck_name)

    def get_model_names(self):
        """Get a list of all model (note type) names"""
        return self._invoke('modelNames')

    def create_model(self, model_name, in_order_fields, card_templates, css):
        """Create a new model (note type)"""
        params = {
            "modelName": model_name,
            "inOrderFields": in_order_fields,
            "cardTemplates": card_templates,
            "css": css
        }
        return self._invoke('createModel', **params)

    def find_notes(self, query):
        """Find notes using a query"""
        return self._invoke('findNotes', query=query)

    def add_note(self, deck_name, model_name, fields, tags=None):
        """Add a new note to a deck"""
        if tags is None:
            tags = []
        
        note = {
            "deckName": deck_name,
            "modelName": model_name,
            "fields": fields,
            "tags": tags
        }
        return self._invoke('addNote', note=note)

    def update_note_fields(self, note_id, fields):
        """Update the fields of an existing note"""
        note = {
            "id": note_id,
            "fields": fields
        }
        return self._invoke('updateNoteFields', note=note)

# Example usage and setup functions
def setup_chinese_model(anki_connect):
    """Ensure the Chinese note type exists with an improved layout"""
    model_name = "Chinese (CLI)"
    
    # Define the new template and CSS
    new_card_template = {
        "Name": "Recognition (EN -> CN)",
        "Front": """
<div class='front-english'>{{English}}</div>
{{#ExampleTranslation}}
<div class='front-example'>{{ExampleTranslation}}</div>
{{/ExampleTranslation}}
""",
        "Back": """
{{FrontSide}}
<hr id=answer>
<div class='hanzi'>{{Hanzi}}</div>
<div class='pinyin'>{{Pinyin}}</div>

{{#ExampleSentence}}
<div class='example-section'>
    <div class='example-hanzi'>{{ExampleSentence}}</div>
</div>
{{/ExampleSentence}}

{{#Lesson}}
<div class='lesson-tag'>{{Lesson}}</div>
{{/Lesson}}
"""
    }
    
    new_css = """
.card {
    font-family: Arial, sans-serif;
    font-size: 22px;
    text-align: center;
    color: #333;
    background-color: #f7f7f7;
}

.front-english {
    font-size: 28px;
    padding: 10px;
}

.front-example {
    font-size: 18px;
    color: #666;
    font-style: italic;
    padding: 10px;
}

.hanzi {
    font-size: 60px;
    font-weight: bold;
    margin-top: 10px;
    margin-bottom: 10px;
}

.pinyin {
    font-size: 24px;
    color: #666;
    margin-bottom: 20px;
}

.example-section {
    border-top: 1px solid #e5e5e5;
    padding: 15px;
    margin: 20px auto 0 auto;
    max-width: 80%;
    background-color: #fff;
    border-radius: 8px;
}

.example-hanzi {
    font-size: 22px;
    font-weight: 500;
    color: #333; /* Explicitly set color for normal mode */
}

.lesson-tag {
    position: absolute;
    bottom: 5px;
    right: 10px;
    font-size: 12px;
    color: #aaa;
    background-color: #eee;
    padding: 2px 6px;
    border-radius: 4px;
}

/* --- Night Mode Styles --- */
.nightMode .card {
    background-color: #2f343a;
    color: #f0f0f0;
}

.nightMode .front-example {
    color: #ccc;
}

.nightMode .pinyin {
    color: #ccc;
}

.nightMode .example-section {
    background-color: #3a3f45;
    border-top: 1px solid #555;
}

.nightMode .example-hanzi {
    color: #f0f0f0;
}

.nightMode .lesson-tag {
    background-color: #555;
    color: #ccc;
}
"""
    
    # Check if model exists
    if model_name not in anki_connect.get_model_names():
        logger.info(f"Creating Anki model: {model_name}")
        anki_connect.create_model(
            model_name=model_name,
            in_order_fields=["Hanzi", "Pinyin", "English", "ExampleSentence", "ExampleTranslation", "Lesson"],
            card_templates=[new_card_template],
            css=new_css
        )
        return True
    else:
        # If model exists, update its template and styling
        logger.info(f"Updating Anki model: {model_name}")
        anki_connect._invoke('updateModelTemplates', model={
            "name": model_name,
            "templates": {
                new_card_template['Name']: {
                    'Front': new_card_template['Front'],
                    'Back': new_card_template['Back']
                }
            }
        })
        anki_connect._invoke('updateModelStyling', model={
            "name": model_name,
            "css": new_css
        })
        return False

def setup_french_model(anki_connect):
    """Ensure the French note type exists"""
    model_name = "French (CLI)"
    if model_name not in anki_connect.get_model_names():
        logger.info(f"Creating Anki model: {model_name}")
        anki_connect.create_model(
            model_name=model_name,
            in_order_fields=["Expression", "English", "Register", "Usage", "Example", "Notes"],
            card_templates=[
                {
                    "Name": "Recognition (EN -> FR)",
                    "Front": "{{English}}",
                    "Back": """{{FrontSide}}
<hr id=answer>
<div style='font-size: 30px; font-weight: bold;'>{{Expression}}</div>
<div style='font-size: 16px; color: grey;'>{{Register}}</div>
<br>
<div style='font-style: italic;'>{{Usage}}</div>
<br>
{{#Example}}
    <div style='font-style: italic;'>{{Example}}</div>
{{/Example}}
<br>
<div style='font-size: 14px;'>{{Notes}}</div>
"""
                }
            ],
            css="""
.card {
    font-family: arial;
    font-size: 20px;
    text-align: center;
    color: black;
    background-color: white;
}
"""
        )
        return True
    return False

if __name__ == '__main__':
    # Example of how to use the AnkiConnect class
    logging.basicConfig(level=logging.INFO)
    
    print("Checking Anki connection...")
    anki = AnkiConnect()
    
    if not anki.check_connection():
        print("Could not connect to Anki. Please ensure Anki is running with AnkiConnect.")
        exit(1)
    
    print("Connection successful!")
    
    print("\nDecks:")
    print(anki.get_deck_names())
    
    print("\nModels:")
    print(anki.get_model_names())
    
    # Setup models
    if setup_chinese_model(anki):
        print("\nCreated 'Chinese (CLI)' model.")
    
    if setup_french_model(anki):
        print("\nCreated 'French (CLI)' model.")
        
    # Example of adding a card
    try:
        print("\nAttempting to add a test card to 'Default' deck...")
        deck = "Default"
        if deck not in anki.get_deck_names():
            anki.create_deck(deck)
            print(f"Created deck: {deck}")

        note_id = anki.add_note(
            deck_name=deck,
            model_name="French (CLI)",
            fields={
                "Expression": "avoir la flemme",
                "English": "to be lazy, can't be bothered",
                "Register": "informal/slang",
                "Usage": "Used when you don't feel like doing something.",
                "Example": "J'ai la flemme d'aller au supermarché.",
                "Notes": "Very common expression among young people."
            },
            tags=["test_card"]
        )
        print(f"Added note with ID: {note_id}")
    except Exception as e:
        print(f"Error adding test card: {e}")
