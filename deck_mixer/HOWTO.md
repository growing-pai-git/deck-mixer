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

**Claude Desktop:** download `deck-mixer-<version>.mcpb` from the
[Releases page](https://github.com/growing-pai-git/deck-mixer/releases) and
double-click it. In the form that appears, pick your case-library folder (or
leave it empty to try the sample cases) and **paste a free Gemini API key** —
without one, decks come out basic ([Step 6](#step-6--add-your-api-keys-strongly-recommended)
shows how to get it in two minutes). Then ask Claude for a deck. Nothing else
to install.

**A skill zip instead:** if someone handed you a `deck-mixer-skill.zip` file, you don't need any of
the terminal steps below — skip straight to this:

1. Add it to Claude: in claude.ai or Claude Desktop, upload the zip under
   Settings → Capabilities → Skills (code execution must be on); in Claude
   Code, unzip it into `~/.claude/skills/`.
2. Open a chat with Claude and just ask, in plain language: *"Build me a
   reference deck for our work with Acme"* or *"I need a capabilities
   overview deck."*

Claude runs every command in this guide for you (including the one-time
setup) and hands you back the finished `.pptx`. It'll ask about your case
library and whether you have brand colors — you can answer those in a
sentence, no file formats to learn. In a claude.ai or Claude Desktop chat,
Claude works in a sandbox that can't see your computer: upload your case
library as a zip in the chat, and download the deck when it's done. That
sandbox also forgets API keys when the chat ends, so decks built there look
basic unless you give Claude a key each time. For AI-designed decks, use the
Claude Desktop extension above or Claude Code, where you set your key once
([Step 6](#step-6--add-your-api-keys-strongly-recommended)). Case-library setup ([Step 4](#step-4--use-your-own-cases))
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

- **A free Google Gemini API key — strongly recommended.** It's what makes
  the decks look designed: AI slide layouts and generated images. You can
  start without it and add it in
  [Step 6](#step-6--add-your-api-keys-strongly-recommended), but don't show a
  keyless deck to a client.

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

Notice the grey image boxes and the warning printed above the file name?
That's what a deck looks like **without API keys**. Before you go further,
jump to [Step 6](#step-6--add-your-api-keys-strongly-recommended) and add a
free Gemini key — then build the same deck again and compare.

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

## Step 6 — Add your API keys (strongly recommended)

Without API keys, decks look basic: every slide follows the same simple
layout rules, and every picture is a grey placeholder box. With keys, an AI
"art director" designs each slide around what it needs to say (**text**), and
matching pictures are generated for it (**images**). Add at least one key for
text and one for images — a single free Gemini key covers both.

### Which keys do what

| Key | Text (AI slide design) | Images | Cost |
|---|---|---|---|
| **Google Gemini** (recommended) | ✓ | ✓ AI-generated | Free tier |
| OpenAI | ✓ | ✓ AI-generated | Paid, per use |
| Anthropic (Claude) | ✓ | — | Paid, per use |
| Stability, Together, fal, Replicate | — | ✓ AI-generated | Paid, per image |
| Pexels, Unsplash | — | ✓ stock photos | Free |

A Claude or OpenAI text key also works; pair a Claude key with an image key.

Using Deck Mixer inside Claude (the extension or the skill)? Then Claude
designs your **plan** decks itself, so those don't need a text key. You
still want a key for the **images**, and for the AI design of **tender**
decks — the free Gemini key covers both.

### Get a free Gemini key (two minutes)

1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
   and sign in with any Google account.
2. Click **Create API key** and copy it.

Other keys: [Anthropic](https://console.anthropic.com/settings/keys) ·
[OpenAI](https://platform.openai.com/api-keys) ·
[Pexels](https://www.pexels.com/api/) ·
[Unsplash](https://unsplash.com/developers).

### Add it — depending on how you use Deck Mixer

- **In the terminal** (this guide): save it once, and every deck after that
  uses it:
  ```bash
  pandoro deck-mixer configure --gemini-api-key YOUR-KEY
  ```
  Other keys work the same way: `--anthropic-api-key`, `--openai-api-key`,
  `--pexels-api-key`, `--unsplash-access-key`. They're stored in
  `~/.config/pandoro/keys.json`, readable only by you. Run
  `pandoro deck-mixer configure` with no options to see what's set.
- **Claude Desktop extension:** open Claude Desktop's Settings → Extensions →
  Deck Mixer and paste the key into the Gemini field. It's kept in your
  computer's secure keychain.
- **Claude Code (skill or MCP server):** run the `configure` command above in
  your own terminal, not in the chat, then restart Claude Code.
- **Skill in a claude.ai or Claude Desktop chat:** the sandbox forgets keys
  when the chat ends, and anything you paste stays in the chat history. For
  AI-designed decks, the extension or Claude Code is the better home. If you
  do paste a key, use a separate one you can delete afterwards.

### Check that it worked

Build any deck again. The "built without AI keys" warning is gone, the image
boxes are filled with pictures, and slide layouts vary.

**What gets sent:** to design slides and pictures, the text of the cases in
that deck goes to the AI provider whose key you added. Confidential clients
are already replaced with "the client" before anything is sent. A plan deck
sends your document as written.

## Step 7 (optional) — Package it as a Claude Skill for others

If you've got Pandoro installed via the steps above, you can hand it to
teammates who'd rather not touch a terminal at all:

```bash
pandoro deck-mixer skill pack
```

This writes `deck-mixer-skill.zip` in your current folder — a self-contained
copy of Pandoro (no PyPI or GitHub access needed to install it) plus
instructions for Claude on how to use it. It works on macOS, Linux and
Windows. Send that file to anyone using claude.ai, Claude Desktop or Claude
Code and point them at
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
configured; see [Step 6](#step-6--add-your-api-keys-strongly-recommended).
It's not a bug.

**Still stuck?** Deck Mixer is shared as-is, without support — Growing pAI
publishes tools it uses itself to show how it works. Want to explore what AI
can do for your team? Get in touch: [growingpai.com](https://growingpai.com).

## Where to go next

- [`README.md`](README.md) — the fast-reference version of everything above.
- [`CASE_LIBRARY_SCHEMA.md`](CASE_LIBRARY_SCHEMA.md) — every field a case
  file can have.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — if you want to modify Pandoro
  itself, not just use it.
