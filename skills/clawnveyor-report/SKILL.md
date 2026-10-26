---
name: clawnveyor-report
description: Report progress to a Clawnveyor dashboard (a 3D warehouse board drawn from data/flow.json) with tools/flow.py. Use whenever you are working on a step-by-step flow that has a Clawnveyor board, i.e. a folder with tools/flow.py and data/flow.json, or the user mentions Clawnveyor, the board, the warehouse or "report progress". Report when you start an item, finish one, send one back, or hand work to someone else. This skill only covers reporting; it does not say how to do the work itself.
---

# Clawnveyor: report what you are doing

Clawnveyor draws a flow as a little warehouse: 01 Pickup → 02 Sort → 03 Store → 04 Pack → 05 Process → 06 Deliver (each board may rename them). The numbers come from `data/flow.json`. Never edit that file by hand: run `tools/flow.py`, which takes a lock (several AI sessions can report at once) and rebuilds the page.

Find the Clawnveyor folder first: the one that holds `tools/flow.py`. If you can't tell which one, ask the user once and write the path into your project notes. Run commands from that folder:

```bash
python tools/flow.py show            # look before you report: names of stations, carts, outputs, crew
```

## When to report

| Moment | Command |
|---|---|
| You start an item | `crew <you> "<what you are doing>" --active` |
| You finish an item | `count done +1`, `count waiting -1`, plus a `log` line; and `output <where it went> +1` or `cart <topic> +1` if it went somewhere |
| An item can't be done and goes back | `count today_returned +1` + a `log` line saying why |
| New items arrive | `count waiting +N` (and `count today_in +N`) |
| You stop, or hand over to someone else | `crew <you> "<handed to X>" --idle`, then the other one reports `--active` |
| A step of the flow is skipped for now | `station <id> off` (06 is the finish line and can't be turned off) |

`<you>` is a short, stable name for this worker, e.g. `Sort-1` or `runner-2`. Use the same name every time so the board keeps one Clawd per worker.

Counts you can set: `unloading`, `waiting`, `done`, `today_in`, `today_done`, `today_returned`, `stored`. Use `+N` / `-N` to change, a plain number to set.

## Examples

Start, finish, move on (a sorting worker):

```bash
python tools/flow.py crew Sort-1 "Reading item web-0412" --active
python tools/flow.py count waiting -1 --no-build
python tools/flow.py count done +1 --no-build
python tools/flow.py output "Design refs" +1 --no-build
python tools/flow.py log Sort-1 "web-0412 -> Design refs"
```

Send one back:

```bash
python tools/flow.py count today_returned +1 --no-build
python tools/flow.py log Sort-1 "web-0413 sent back: the link is dead"
```

A pack cart fills up (it lights up on the board when it reaches its threshold):

```bash
python tools/flow.py cart Writing +1
```

End of a batch:

```bash
python tools/flow.py crew Sort-1 "Batch done, waiting for more" --idle
```

## Rules

- One event, one report. Don't save them up for the end; the board is only useful while it's current.
- Use only names that `show` lists. If a cart, output or station you need is missing, tell the user instead of inventing one.
- Several updates in a row: add `--no-build` to all but the last (or run `python tools/flow.py build` once at the end).
- Keep crew and log text short (under ~40 characters). Add `--en "..."` when the board is bilingual and you wrote the text in another language.
- If `flow.py` fails, carry on with the real work and mention the error once; reporting must never block the job.
