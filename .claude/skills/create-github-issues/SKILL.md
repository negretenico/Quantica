---
name: create-github-issues
description: Create GitHub issues for Scout.gg from the scout-gg-issues.md roadmap file. Use when setting up the repo or adding new issues from the requirements doc.
---

# Create GitHub Issues

Reads `scout-gg-issues.md` and creates GitHub issues using the GitHub CLI (`gh`).

## Prerequisite Check
```bash
# Verify gh CLI is authenticated
gh auth status

# Verify you're in the right repo
gh repo view
```

## Create All Issues from Roadmap
```bash
# Parse and create issues from the roadmap markdown
# Run this script from the repo root where scout-gg-issues.md lives

while IFS= read -r line; do
  if [[ $line == "### Issue: "* ]]; then
    TITLE="${line#### Issue: }"
  fi
  if [[ $line == "- **Labels:**"* ]]; then
    LABELS=$(echo "$line" | grep -oP '`[^`]+`' | tr -d '`' | tr '\n' ',' | sed 's/,$//')
  fi
done < scout-gg-issues.md
```

## Preferred Approach: Create Issues One Epic at a Time
Use `gh issue create` for each issue. Example:

```bash
gh issue create \
  --title "Ingest live LCS audio stream from YouTube Live / Twitch" \
  --body "**Epic:** Real-Time Broadcast Ingestion Pipeline

**Description:**
Connect to the live LCS broadcast stream and capture audio for downstream transcription.

**Acceptance Criteria:**
- [ ] System can connect to a live LCS YouTube Live or Twitch stream URL
- [ ] Raw audio is extracted and passed to the transcription step
- [ ] Connection holds stable for up to 3 hours
- [ ] Stream interruptions handled gracefully with auto-reconnect
- [ ] Logs stream status (connected, reconnecting, dropped)" \
  --label "epic:pipeline-realtime,priority:high,type:feature"
```

## Create Required Labels First
Before creating issues, ensure labels exist:
```bash
# Epics
gh label create "epic:pipeline-realtime" --color "0075ca"
gh label create "epic:pipeline-vod" --color "0075ca"
gh label create "epic:riot-api" --color "0075ca"
gh label create "epic:player-profiles" --color "0075ca"
gh label create "epic:team-narratives" --color "0075ca"
gh label create "epic:search-discovery" --color "0075ca"
gh label create "epic:homepage" --color "0075ca"

# Priority
gh label create "priority:high" --color "d93f0b"
gh label create "priority:medium" --color "e4e669"

# Type
gh label create "type:feature" --color "0e8a16"
gh label create "type:performance" --color "1d76db"
gh label create "type:design" --color "5319e7"
gh label create "type:constraint" --color "b60205"
```

## Verify After Creation
```bash
# List all open issues grouped by label
gh issue list --label "epic:pipeline-realtime"
gh issue list --label "epic:riot-api"
gh issue list --label "epic:player-profiles"

# Count total
gh issue list --state open | wc -l
# Expected: 32
```

## Notes
- Work one epic at a time — don't try to create all 32 at once
- If an issue already exists, `gh issue create` will create a duplicate — check first with `gh issue list --search "title:..."`
- The roadmap source of truth is `scout-gg-issues.md` — always refer back to it for acceptance criteria
