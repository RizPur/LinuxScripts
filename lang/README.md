# Language Learning Tools

This directory contains powerful command-line tools for learning Chinese (`cn`) and French (`fr`). Both tools are designed to help you quickly capture, enrich, and study vocabulary using an AI assistant and sync your flashcards with [Anki](https://apps.ankiweb.net/).

## 1. First-Time Setup

Before using the scripts, you need to complete a one-time setup.

### a. Configure Environment Variables

1.  Copy the example environment file:
    ```bash
    cp ../env.example .env
    ```
2.  Edit the `.env` file and add your **OpenAI API Key**.
    ```ini
    # .env
    OPENAI_API_KEY="sk-..."
    ```
3.  The default paths for vocabulary files are set to save within `lang/zh` and `lang/fr`. You can override these in the `.env` file if you wish.

### b. Install Anki and AnkiConnect

1.  Download and install the **Anki desktop application**.
2.  Inside Anki, go to `Tools > Add-ons`.
3.  Click `Get Add-ons...` and paste in the code: `2055492159`
4.  Restart Anki.

### c. Run the Script Setups

With Anki open, run the setup command for each script. This will create the necessary card templates in Anki.

```bash
# For Chinese
python3 chinese.py setup-anki

# For French
python3 french.py setup-anki
```

## 2. Chinese Tool (`cn`) Workflow

The Chinese tool helps you build a vocabulary list that is organized by HSK level.

**Your workflow will be:**
1.  Set your HSK context.
2.  Add new words (individually or in bulk).
3.  Sync to Anki.

### Commands

- **`cn hsk <level>`**
  Sets your current HSK context. Run this before adding new words.
  ```bash
  python3 chinese.py hsk 2
  ```

- **`cn new "phrase" [-l, --lang <type>]`**
  The main command. Takes a phrase, uses AI to generate its Pinyin, English translation, and a level-appropriate example, and adds it to your central `chinese_vocab.csv`.
  ```bash
  # Input is English by default
  python3 chinese.py new "practice makes perfect"

  # Use the lang flag for Chinese or Pinyin
  python3 chinese.py new "熟能生巧" --lang zh
  ```

- **`cn import <file_path>`**
  Bulk-imports words from an external CSV file. It will tag all imported words with your currently set HSK level.
  ```bash
  python3 chinese.py import ~/Downloads/my_hsk_words.csv
  ```

- **`cn vocab`**
  Quickly shows you the last 5 words you've added.

- **`cn sync`**
  Syncs all new words from your `chinese_vocab.csv` to Anki. It automatically creates decks based on HSK level (e.g., `Chinese::HSK1`).

## 3. French Tool (`fr`) Workflow

The French tool is simpler and designed for quickly capturing and understanding expressions.

**Your workflow will be:**
1.  Add a new expression.
2.  Sync to Anki.

### Commands

- **`fr new "phrase" [-l, --lang <type>]`**
  The main command. Takes a phrase (in French, English, etc.), uses AI to generate its translation, register (slang, formal), usage, and an example, and adds it to `expressions.json`.
  ```bash
  # Input is French by default
  python3 french.py new "c'est pas la mer à boire"

  # Use the lang flag for other languages
  python3 french.py new "it's not a big deal" --lang en
  ```

- **`fr list [-n <number>]`**
  Shows you the last 5 (or a specified number) of expressions you've added.

- **`fr sync`**
  Syncs all new expressions from your `expressions.json` file to Anki into a "French" deck.


  ┌─────────────────────────────────────────────────────────┐
  │                    User Commands                         │
  │         cn new "在"              fr new "bonjour"        │
  └────────────────┬─────────────────────┬──────────────────┘
                   │                     │
                   ▼                     ▼
          ┌────────────────┐    ┌────────────────┐
          │  cn_wrapper.sh │    │  fr_wrapper.sh │
          │                │    │                │
          │ Calls:         │    │ Calls:         │
          │ lang.py cn ... │    │ lang.py fr ... │
          └────────┬───────┘    └────────┬───────┘
                   │                     │
                   └──────────┬──────────┘
                              ▼
                     ┌─────────────────┐
                     │    lang.py      │
                     │ (Unified Logic) │
                     └────────┬────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ configs/ │  │   Data   │  │  anki.py │
        │  cn.json │  │  Storage │  │ (Anki    │
        │  fr.json │  │          │  │  Sync)   │
        └──────────┘  └──────────┘  └──────────┘
