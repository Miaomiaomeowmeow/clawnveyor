# AI-SETUP: set up Clawnveyor for your user

<!-- Clawnveyor 克鸟驿站 · by Miaomiao (github.com/Miaomiaomeowmeow) · CC BY-NC-SA 4.0 -->

You are an AI helping someone set up Clawnveyor, a 3D warehouse board for a step-by-step workflow. The user said something like "set up Clawnveyor following AI-SETUP.md". Do the steps below in order. **Ask one question at a time**, wait for the answer, act on it right away, then ask the next one. Keep it short and plain; the user may not be technical.

## 0. Check the computer first (don't ask, just look)

- `python --version` (or `python3 --version`): Python 3.8 or newer is needed. If it's missing, tell the user to install it from https://www.python.org/downloads/ (on Windows, tick "Add python.exe to PATH") and stop until it's there.
- You are in the Clawnveyor folder: it has `tools/flow.py`, `tools/build.py`, `templates/`. If not, ask where they downloaded it.
- Does `data/flow.json` already exist? If yes, the user already has a board: skip to step 4 and only change what they ask for.

## 1. Which template is closest?

Show this list and ask which one fits their flow best:

| Template | Flow |
|---|---|
| `collect-skill` | collect material → sort → notes → batch by topic → turn into skills → deliver |
| `crawl-result` | an AI fetches material → sorts it → a summary |
| `content` | ideas → draft → review → publish |
| `ci-cd` | code in → tests → artifacts → release batches → deploy → live |
| `data-pipeline` | extract → validate → warehouse → aggregate → model → serve |
| `blank` | start from nothing |

Then run `python tools/flow.py init <template>`.

## 2. Map their steps onto the six stations

The board always has six stations in fixed places: 01 Pickup, 02 Sort, 03 Store, 04 Pack, 05 Process, 06 Deliver. Ask the user to describe their flow in a sentence, then propose a mapping as a short table (their step → station), for example "writing drafts → 02 Sort". Rules:

- **06 is always the finish line**, where the result lands (published, deployed, delivered…). Their last step goes there.
- Steps they don't have: turn that station off (`python tools/flow.py station <id> off`). It stays in place, greyed out; things pass straight through.
- More than six steps: merge two small steps into one station, or see "Adding a 7th station" in README.md.

After they agree, edit `data/flow.json`: for each station set `name` (their word), `en` (sign text in capitals), `desc` (one line). If they want an English page too, add `name_en` / `desc_en`.

## 3. Where does the work come from, and what are the workers called?

- Sources: one truck per source (a website, a folder, a repo, a queue…). Edit `sources` in `data/flow.json`: `name`, `en`, `worker` (the name of who fetches from it), `color`.
- Worker names: `roles` (what each kind of worker is called) and `lanes` (names of the three sorting workers). Short names work best, e.g. `Sort-1`.

## 4. Build and open

Run `python tools/build.py` and tell the user to open `out/clawnveyor.html` in a browser (it needs internet for the 3D library). Show them one screenshot if you can.

## 5. Keep it up to date while working

Ask: "Should your AI update the board while it works?"

- **Yes, Claude Code**: install the skill (two lines in Claude Code):
  ```
  /plugin marketplace add Miaomiaomeowmeow/clawnveyor
  /plugin install clawnveyor@clawnveyor
  ```
- **Yes, another AI (Codex, Cursor, Gemini…)**: paste the block from `AI-RULES.md` into their `AGENTS.md` / `CLAUDE.md` / `GEMINI.md`, replacing the folder path with this one.
- **Scripts or CI**: point them at "Let your scripts report numbers" in README.md.
- **No**: fine. They can run `python tools/flow.py ...` by hand or edit `data/flow.json` and rebuild.

## 6. Finish

Tell the user, in two or three lines: where the board is (`out/clawnveyor.html`), how to refresh it (`python tools/build.py`), that the console's Stations panel switches stations on and off, and that README.md explains the rest.
