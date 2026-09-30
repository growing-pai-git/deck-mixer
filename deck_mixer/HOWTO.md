# Pandoro — a howto for complete beginners

Never used a command line before? You may not need one — see
[The easiest way](#the-easiest-way-use-it-inside-claude-no-terminal-at-all)
below. If you already know your way around a terminal and Python, the
[README](README.md) is faster than this guide. If any step here doesn't
work, see [Troubleshooting](#troubleshooting) at the bottom.

## What Pandoro actually does

You give Pandoro two things:

1. A **case library** — a folder of write-ups about past projects (client,
   what you did, results). You write these once; Pandoro reuses them forever.
2. Optionally, a **theme** — your company's colors/logo, or just a sentence
   describing your brand.

Pandoro turns those into a **PowerPoint file** (`.pptx`) — a real, editable
deck you can open in PowerPoint, Keynote, or Google Slides, not a picture of
one. There are four deck "shapes" it can build:

| You ask for | You get |
|---|---|
| `reference` | A deep dive on one or a few specific cases |
| `capabilities` | A portfolio overview — "here's everything we do" |
| `tender` | Evidence slides answering a specific RFP/tender |
| `plan` | A deck built from a plain markdown document you already wrote |

## The easiest way: use it inside Claude, no terminal at all

If someone handed you a `deck-mixer-skill.zip` file, you don't need any of
the terminal steps below — skip straight to this:

1. Unzip it, then drop the `deck-mixer` folder it contains into your Claude
   Skills folder (in Claude Desktop: Settings → Capabilities → Skills → Add
   skill; in Claude Code: `~/.claude/skills/`).
2. Open a chat with Claude and just ask, in plain language: *"Build me a
   reference deck for our work with Acme"* or *"I need a capabilities
   overview deck."*

Claude runs every command in this guide for you (including the one-time
setup) and hands you back the finished `.pptx`. It'll ask you where your
case library is and whether you have brand colors — you can answer those in
a sentence, no file formats to learn. Case-library setup ([Step 4](#step-4--use-your-own-cases))
and theming ([Step 5](#step-5--make-it-look-like-your-brand)) work the same
way — just describe what you want and let Claude run the commands.

The rest of this guide is for people who'd rather (or need to) drive Pandoro
directly from a terminal — for example, to build that `deck-mixer-skill.zip`
in the first place (see [Step 7](#step-7-optional--package-it-as-a-claude-skill-for-others)),
or to script/automate deck building.

## What you need before starting

- **A terminal.** This is the black (or white) text-only window on your
  computer where you type commands. On Mac: open Spotlight (`Cmd+Space`),
  type "Terminal", hit enter. On Windows: open "PowerShell" or "Windows
  Terminal" from the Start menu. On Linux: you're probably already in one.
- **Python 3.10 or newer.** Check by typing this in your terminal and
  pressing enter:
  ```bash
  python3 --version
  ```
  If you see a number like `3.10.x` or higher, you're good. If you get an
  error, install Python from [python.org](https://www.python.org/downloads/)
  first, then come back.

That's it — no coding required for the steps below, just copying and
pasting commands.

## Step 1 — Get the code

```bash
git clone https://github.com/growing-pai-git/deck-mixer.git
cd deck-mixer
```

(If you don't have `git`, you can also download the code as a ZIP from
GitHub — click the green "Code" button, then "Download ZIP" — and unzip it,
then use `cd` to move into that unzipped folder in your terminal.)

## Step 2 — Install Pandoro

Still in that same terminal window:

```bash
python3 -m venv .venv
source .venv/bin/activate      # on Windows: .venv\Scripts\activate
pip install -e .
```

What that did: created an isolated Python environment just for Pandoro
(so it can't conflict with anything else on your computer), turned it on
(`activate`), and installed Pandoro into it.

**Every time you open a new terminal window to use Pandoro**, you'll need to
run that `source .venv/bin/activate` line again first (from inside the
`pandoro` folder). Installing (`pip install -e .`) you only do once.

## Step 3 — Build your first deck

Pandoro ships with a small made-up example library so you can try it before
writing anything real. Let's see what's in it:

```bash
pandoro deck-mixer list --library deck_mixer/examples/sample-library
```

You'll see a short list of example case names. Now build a deck from one of
them:

```bash
pandoro deck-mixer build reference --library deck_mixer/examples/sample-library --cases northwind-retail-support
```

You should see something like:

```
Created reference deck (1 case(s)): reference-20260101-120000.pptx
```

That `.pptx` file is now sitting in your current folder. Open it — double
click it, or open it from PowerPoint/Keynote/Google Slides. That's a real
deck, fully editable, built in a few seconds with zero setup.

Try the other deck types too:

```bash
pandoro deck-mixer build capabilities --library deck_mixer/examples/sample-library
pandoro deck-mixer build tender --library deck_mixer/examples/sample-library --tender-tags "human in the loop"
```

## Step 4 — Use your own cases

The sample library is just for trying things out. To use Pandoro for real,
scaffold your own library:

```bash
pandoro deck-mixer library init ~/my-cases
```

This creates a folder at `~/my-cases` with a `templates/case.md` file
inside — a fill-in-the-blanks template. Copy it into a new folder per case
and fill it in:

```bash
mkdir ~/my-cases/cases/my-first-case
cp ~/my-cases/templates/case.md ~/my-cases/cases/my-first-case/case.md
```

Open `~/my-cases/cases/my-first-case/case.md` in any text editor and replace
the placeholders with your actual project details — client, what you did,
results, etc. Once you've written a few of these, check they're formatted
correctly:

```bash
pandoro deck-mixer library validate ~/my-cases
```

Fix anything it flags, then build from your own library:

```bash
pandoro deck-mixer build reference --library ~/my-cases --cases my-first-case
```

The full format (every field, what's required, what's optional) is in
[`CASE_LIBRARY_SCHEMA.md`](CASE_LIBRARY_SCHEMA.md) — the sample cases in
`deck_mixer/examples/sample-library/cases/` are also good to copy from directly.

## Step 5 — Make it look like your brand

By default, decks use a plain neutral color scheme. To brand it as your own,
either describe your brand in a sentence:

```bash
pandoro deck-mixer build reference --library ~/my-cases --cases my-first-case \
    --brand-description "a friendly fintech startup, navy and coral"
```

or scaffold a proper theme file you can reuse every time:

```bash
pandoro deck-mixer theme init ~/my-brand --company "Acme Corp"
```

This writes `~/my-brand/theme.yaml`. Open it in a text editor and adjust the
colors (they're just hex codes, e.g. `1E293B`) to match your brand. Drop a
`logo.png` next to it if you have one. Then use it on every build:

```bash
pandoro deck-mixer build reference --library ~/my-cases --cases my-first-case --theme ~/my-brand/theme.yaml
```

## Step 6 (optional) — Make decks smarter with an API key

Everything above works with **zero setup** — no accounts, no API keys.
Adding one free API key unlocks two upgrades: an AI "art director" that
picks each slide's layout more thoughtfully, and AI-generated imagery
instead of grey image placeholders.

The easiest option is a free Google Gemini key:

1. Go to [aistudio.google.com](https://aistudio.google.com/) and get a free
   API key.
2. Save it so Pandoro remembers it:
   ```bash
   pandoro deck-mixer configure --gemini-api-key AIzaSy...your-key-here
   ```
3. Build a deck as usual — it'll automatically be richer now.

This step is entirely optional and skippable. Decks built without a key are
still complete, real, editable decks — just simpler layouts, with marked image placeholders where a picture would go.

## Step 7 (optional) — Package it as a Claude Skill for others

If you've got Pandoro installed via the steps above, you can hand it to
teammates who'd rather not touch a terminal at all:

```bash
pandoro deck-mixer skill pack
```

This writes `deck-mixer-skill.zip` in your current folder — a self-contained
copy of Pandoro (no PyPI or GitHub access needed to install it) plus
instructions for Claude on how to use it. Send that file to anyone with
Claude Desktop or Claude Code and point them at
[The easiest way](#the-easiest-way-use-it-inside-claude-no-terminal-at-all)
above.

## Cheat sheet

```bash
# Every new terminal session, from inside the pandoro folder:
source .venv/bin/activate

# See what's in a library
pandoro deck-mixer list --library <path>

# Build a deck
pandoro deck-mixer build reference --library <path> --cases <slug1> <slug2>
pandoro deck-mixer build capabilities --library <path>
pandoro deck-mixer build tender --library <path> --tender-tags <tag1> <tag2>
pandoro deck-mixer build plan --title "My Plan" --content my-plan.md

# Libraries
pandoro deck-mixer library init <path>
pandoro deck-mixer library validate <path>

# Themes
pandoro deck-mixer theme init <path> --company "..."
pandoro deck-mixer theme init <path> --describe "a playful startup, coral and navy"

# Save an API key
pandoro deck-mixer configure --gemini-api-key <key>
```

## Troubleshooting

**`pandoro: command not found`** (Mac/Linux) or **`'pandoro' is not
recognized as an internal or external command`** (Windows) — you likely
forgot to activate the environment in this terminal window. Run
`source .venv/bin/activate` (or `.venv\Scripts\activate` on Windows) from
inside the `pandoro` folder, then try again.

**`externally-managed-environment` error during `pip install`** — you're not
inside the virtual environment. Make sure you ran the `python3 -m venv .venv`
and `source .venv/bin/activate` steps first.

**`No cases found for: [...]`** — the case slug you typed doesn't match
anything in the library. Run `pandoro deck-mixer list --library <path>` first and copy
the exact slug from that output.

**The deck looks plain / has no images** — that's expected with no API key
configured; see [Step 6](#step-6-optional--make-decks-smarter-with-an-api-key).
It's not a bug.

**Still stuck?** Open an issue on the GitHub repo with the exact command you
ran and the error message.

## Where to go next

- [`README.md`](README.md) — the fast-reference version of everything above.
- [`CASE_LIBRARY_SCHEMA.md`](CASE_LIBRARY_SCHEMA.md) — every field a case
  file can have.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — if you want to modify Pandoro
  itself, not just use it.
