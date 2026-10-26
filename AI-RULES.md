# AI-RULES: paste this into your AI's instructions

<!-- Clawnveyor 克鸟驿站 · by Miaomiao (github.com/Miaomiaomeowmeow) · CC BY-NC-SA 4.0 -->

Copy the block below into `AGENTS.md` (Codex and most agents), `CLAUDE.md` (Claude Code) or `GEMINI.md`, and change the folder path to where Clawnveyor lives. Claude Code users can install the `clawnveyor` plugin instead (see README.md); it teaches the same thing.

```markdown
## Report progress to the Clawnveyor board

The board for this work lives in `PATH/TO/clawnveyor` (it has `tools/flow.py`). Never edit `data/flow.json` by hand; run these from that folder:

- Start an item: `python tools/flow.py crew <me> "<what I'm doing>" --active`
- Finish an item: `python tools/flow.py count done +1`, `count waiting -1`, and `log <me> "<item> -> <where it went>"`; if it went to a named output or pack cart, also `output <name> +1` or `cart <name> +1`
- Send one back: `python tools/flow.py count today_returned +1` and a `log` line saying why
- New items arrive: `python tools/flow.py count waiting +N`
- Stop or hand over: `python tools/flow.py crew <me> "<handed to X>" --idle`

`<me>` is one short name I always use (e.g. `Sort-1`). Report each event when it happens, not at the end. Run `python tools/flow.py show` to see the names of stations, carts and outputs; don't invent new ones. In a batch, add `--no-build` and finish with `python tools/flow.py build`. If a command fails, keep doing the real work and mention it once.
```
