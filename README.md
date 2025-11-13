# Joel's CLI Scripts

Basically a collection of personal CLI tools to make life easier. One part for language learning, one part productivity tools.

Go into the sub-folders for the real docs.

---

### [`./lang/`](./lang/) &mdash; Language Tools

Home of the `cn` and `fr` scripts. These are for jottin down words and phrases you run into, using AI to get all the important details (pinyin, translation, usage, etc.), and then syncing them straight to Anki.

**Quick Example:**
```bash
# Set your HSK level
cn hsk 3

# Add a new word you just heard
cn new "一寸光阴 一寸金"

# Sync your new card to Anki
cn sync

#########

joel@la-cene:~/dev/scripts$ cn new "寸金难买 寸光阴" 
Adding new word with HSK 1 context...
  Hanzi: 寸金难买 寸光阴
  Pinyin: cùn jīn nán mǎi cùn guāng yīn
  English: Time is precious

✓ Successfully added '寸金难买 寸光阴' to your vocabulary list.
  Run `cn sync` to add it to Anki.
joel@la-cene:~/dev/scripts$ cn sync
Syncing vocabulary to Anki...
Found 2 new words to sync...
  [1/2] ✓ Synced '一寸光阴 一寸金'
  [2/2] ✓ Synced '寸金难买 寸光阴'

Sync complete!

```


&rarr; See the **[Language Tools README](./lang/README.md)** for the full setup and usage guide.

---

### [`./productivity/`](./productivity/) &mdash; Productivity Tools

A bunch of scripts to keep your life from descending into chaos. Includes a dead-simple Pomodoro timer (`pomo`), a no-frills task manager (`tasks`), and an agenda script (`agenda`).

**Quick Example:**
```bash
# 25-minute focus timer when you're supposed to be studying

joel@la-cene:~/dev/scripts$ pomo -c 2

🍅 POMODORO SESSION STARTING
📋 Plan: 2 cycles of 25 min work
☕ Breaks: 5 min short, 15 min long

Press ENTER to begin...


##########

joel@la-cene:~/dev/scripts$ tasks list
1. Claude code session for matrix project that Sam described (2025-10-19)
2. fix the nxp board
3. create a central log folder in dev
joel@la-cene:~/dev/scripts$ 

```

&rarr; See the **[Productivity Tools README](./productivity/README.md)** for more details.