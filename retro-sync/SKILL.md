---
name: retro-sync
description: Scrub, pseudonymize, and push local retros in ~/retros to the shared public GitHub repo (EndofLineTech/retros). Push-only — /retro-mine pulls the corpus down for analysis. Anyone using these skills can contribute.
when_to_use: sync retros, push retros, share retros, contribute retros
user-invocable: true
version: 0.3.0
---

# Retro Sync

Push local retros in `~/retros/` to the shared learning corpus: `https://github.com/EndofLineTech/retros` (**public**). Push-only — pulling the corpus down for analysis is `/retro-mine`'s job. Retros are pseudonymized — the corpus is about process lessons, not about whose project it was.

## Process

1. **Bootstrap** (only if `~/retros` is not already a git repo):
   ```bash
   git -C ~/retros init -b main
   git -C ~/retros remote add origin https://github.com/EndofLineTech/retros.git
   git -C ~/retros fetch origin
   ```

2. **Project map** — `~/.claude/retro-project-map.txt` holds stable pseudonyms, one `real-name=pseudonym` per line:
   ```
   acme-billing=project-a
   claude-agent-dev-team=project-b
   ```
   Check that every project referenced by the retros being synced has an entry. If one is missing, assign the next unused `project-<letter>` and append it. The map is local and private — never commit it, never mention real names in the retro repo. Ceiling: the map is per-machine; keep it consistent across your machines by copying it once (it changes rarely).

3. **Scrub** — run the scrub script that lives next to this SKILL.md:
   ```bash
   bash <skill-dir>/scrub.sh ~/retros
   ```
   It applies, in place: project-map pseudonymization (content and filenames), then redaction of emails, IPs, private keys, common credential formats (AWS, GitHub, Anthropic/OpenAI, Slack, bearer tokens), then any literal strings in `~/.claude/retro-scrub.txt` (one per line — client names, employer names, internal hostnames).

4. **Review** — if the scrub redacted anything (`[REDACTED]`, `[EMAIL]`, key markers — pseudonym renames don't count), show the user what and where. A redaction hit means the retro-writing rules leaked something; name the category so the rules can be tightened.

5. **Commit and push** (no hostnames or usernames in the commit message):
   ```bash
   git -C ~/retros add -A
   git -C ~/retros commit -m "retro sync: <n> retro(s)"
   git -C ~/retros pull --rebase origin main   # prerequisite for the push, not a gathering step
   git -C ~/retros push -u origin main
   ```
   Nothing staged and nothing unpushed → stop; there's nothing to sync.

6. **No write access?** If the push is rejected for permissions, contribute via fork:
   ```bash
   gh repo fork EndofLineTech/retros --remote --remote-name fork
   git -C ~/retros push -u fork main
   gh pr create --repo EndofLineTech/retros --head <your-user>:main --title "retro sync: <n> retro(s)" --fill
   ```

7. **Report** — one line: N pushed, anything redacted.

## Public repo rules

The repo is public and multi-contributor. Never push a retro you have reason to believe contains customer data, credentials, PII, or un-pseudonymized project/org names the scrub can't catch — flag it to the PO instead. The scrub is a backstop; the real control is the Anonymization section of the `retro` skill, which keeps sensitive data out at generation time.
