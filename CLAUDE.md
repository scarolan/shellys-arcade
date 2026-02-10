# Shelly's Arcade

A collection of terminal games and interactive fiction.

## Repo layout

- `console_games/` — Python terminal games (curses-based), each a single `.py` file with a matching `test_*.py`
- `interactive_fiction/` — Inform 6 interactive fiction games
  - `neon_shadows.inf` — Neon Shadows: A Cyberpunk Detective Noir (source)
  - `neon_shadows.z5` — compiled Z-machine story file
  - `test_neon_shadows.sh` — bash test harness using dfrotz
  - `CLAUDE.md` — game-specific docs for Neon Shadows

## Tech stack

- **Python games:** Python 3.12, curses, no external dependencies. Each game is a single self-contained `.py` file.
- **Interactive fiction:** Inform 6 compiler (`inform6`), Z-machine interpreter (`dfrotz`). Inform 6 library at `/usr/local/share/inform6/lib/`.
- **Tests:** Python games use `pytest`. IF games use a bash harness that pipes commands into dfrotz and greps output.

## Running tests

```bash
# All Python game tests
python3 -m pytest console_games/ -v

# Single Python game
python3 -m pytest console_games/cyberpunk/test_cyberpunk.py -v

# Neon Shadows IF tests (compiles then runs dfrotz scenarios)
cd interactive_fiction && bash test_neon_shadows.sh
```

## Compiling Inform 6 games

```bash
cd interactive_fiction
inform6 +/usr/local/share/inform6/lib/ neon_shadows.inf neon_shadows.z5
```

## Conventions

- Each Python game is a standalone single-file curses app. No shared libraries between games.
- Python games use Nerd Font glyphs (Private Use Area Unicode codepoints) for display.
- Tests must pass before committing. Shelly's pipeline will reject failing tests.
- The `shelly` label on GitHub issues triggers automated processing (see below).

## Shelly automation pipeline

This repo is serviced by **Shelly**, an autonomous agent dispatcher running on `shelly-vm`. When issues are labeled `shelly`, they flow through an automated pipeline:

1. **GitHub Actions** (every 5 min) — syncs the Project board "Ready for Shelly" column to the `shelly` label via `.github/workflows/shelly-label.yml`
2. **Poller daemon** (systemd, every 5 min) — detects new `shelly`-labeled issues
3. **Tidy** — Claude rewrites the issue into a structured spec (Summary, Technical notes, Acceptance criteria)
4. **Delegate** — Claude implements the fix in the working directory
5. **Test** — runs `python3 -m pytest console_games/ -v` (Note: IF tests not yet wired into pipeline — see issue #16)
6. **Retry** — up to 3 retries if tests fail
7. **Commit & push** — `git add -A && git commit && git push`
8. **Notify** — Slack message + GitHub comment with commit hash
9. **Close** — issue is closed automatically

### Filing issues for Shelly

- Use the `bug` and `shelly` labels, or drag to "Ready for Shelly" on the project board
- Prefix IF issues with "Neon Shadows (IF):" to avoid confusion with the cyberpunk roguelite
- Include reproduction steps and expected behavior
- Suggested fixes help Shelly implement faster
- One focused issue per bug — avoid multi-bug issues
