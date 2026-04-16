# First-time setup: install deps + git hooks (run once after cloning)
setup:
    pip install -r requirements.txt
    git config --unset-all core.hooksPath || true
    pre-commit install

# Lint: blocking errors only (same as CI)
lint:
    ruff check --select E9,F63,F7,F82 .

# Lint: all style warnings (non-blocking)
lint-warn:
    ruff check . || true

# Auto-fix all auto-fixable ruff issues
lint-fix:
    ruff check --fix .

# Format code with ruff
fmt:
    ruff format .

# Show what ruff format would change (dry-run)
fmt-check:
    ruff format --check .

# Lint a specific file: just lint-file handlers/media_bot.py
lint-file file:
    ruff check --select E9,F63,F7,F82 {{file}}

# Run full CI check locally (ruff does syntax + lint in one pass)
ci:
    #!/usr/bin/env bash
    echo "=== Ruff: blocking errors ==="
    ruff check --select E9,F63,F7,F82 . && echo "✅ Clean"
    echo ""
    echo "=== Ruff: all warnings ==="
    ruff check . || true

# Review a PR with Ukrainian beginner-friendly review
# Usage:
#   just review 44
#   just review 45
review pr:
    #!/usr/bin/env bash
    session="review-pr-{{pr}}"
    tmux kill-session -t "$session" 2>/dev/null || true
    tmux new-session -d -s "$session" \
        "claude --print '/review-pr-ukr {{pr}}'; echo ''; echo '✅ Done. Session closes in 10 min...'; sleep 600"
    if [ -n "$TMUX" ]; then
        tmux switch-client -t "$session"
    else
        tmux attach-session -t "$session"
    fi

# Watch /tmp/tele-bot-review-queue/pending/ for review requests from the bot.
# The bot's /review handler writes JSON files there with caller info + PR number.
# This watcher picks each up and spawns `claude --print '/review-pr-ukr N'` in tmux.
#
# Deps:   brew install entr jq   (already installed? `which entr jq`)
# Run:    tmux new-session -d -s review-queue 'just queue-watch'
# Attach: tmux attach -t review-queue
# Stop:   tmux kill-session -t review-queue
#
# JSON file format (written by the bot):
#   { "pr_number": 51, "caller_id": 12345, "caller_full_name": "Mike",
#     "requested_at": "2026-04-16T23:05:00" }
queue-watch:
    #!/usr/bin/env bash
    set -u
    pending="/tmp/tele-bot-review-queue/pending"
    processed="/tmp/tele-bot-review-queue/processed"
    mkdir -p "$pending" "$processed"
    chmod 1777 "$pending" "$processed" 2>/dev/null || true
    touch "$pending/.keep"

    process_file() {
        local file="$1"
        [[ "$file" != *.json ]] && return 0
        [[ ! -f "$file" ]] && return 0
        local pr caller ts
        pr=$(jq -r '.pr_number // empty' "$file" 2>/dev/null)
        caller=$(jq -r '.caller_full_name // "unknown"' "$file" 2>/dev/null)
        ts=$(jq -r '.requested_at // "?"' "$file" 2>/dev/null)
        if [[ ! "$pr" =~ ^[0-9]+$ ]]; then
            echo "[$(date +'%F %T')] ⚠️  SKIP bad pr in $(basename "$file")"
            mv "$file" "$processed/bad-$(basename "$file")"
            return 0
        fi
        echo "[$(date +'%F %T')] ▶  pr=$pr caller=$caller requested=$ts"
        local s="review-pr-$pr"
        tmux kill-session -t "$s" 2>/dev/null || true
        if tmux new-session -d -s "$s" \
            "claude --print '/review-pr-ukr $pr'; echo; echo '✅ Done. Session closes in 10 min...'; sleep 600"
        then
            echo "[$(date +'%F %T')] ✅ tmux session '$s' started"
        else
            echo "[$(date +'%F %T')] ❌ failed to start tmux session '$s'"
        fi
        mv "$file" "$processed/$(basename "$file")"
    }

    echo "[$(date +'%F %T')] 🛰  queue-watch started ($pending)"
    while true; do
        for f in "$pending"/*.json; do
            [[ -e "$f" ]] && process_file "$f"
        done
        echo "$pending/.keep" | entr -d -n -z true 2>/dev/null || true
    done
