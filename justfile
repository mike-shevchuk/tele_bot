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


review_watcher:
  #!/usr/bin/env bash
  tmux new-session -d -s review-queue 'just queue-watch'

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

        local base pr caller caller_id ts
        base=$(basename "$file")
        echo "──────────────────────────────────────────"
        echo "[$(date +'%F %T')] 📨 picking up $base"
        echo "[$(date +'%F %T')] 📄 content:"
        jq . "$file" 2>/dev/null | sed 's/^/     /' || echo "     (invalid JSON)"

        pr=$(jq -r '.pr_number // empty' "$file" 2>/dev/null)
        caller=$(jq -r '.caller_full_name // "unknown"' "$file" 2>/dev/null)
        caller_id=$(jq -r '.caller_id // "?"' "$file" 2>/dev/null)
        ts=$(jq -r '.requested_at // "?"' "$file" 2>/dev/null)

        if [[ ! "$pr" =~ ^[0-9]+$ ]]; then
            echo "[$(date +'%F %T')] ⚠️  SKIP: pr_number=$pr is not a positive integer"
            mv "$file" "$processed/bad-$base"
            echo "[$(date +'%F %T')] 🗂  moved → processed/bad-$base"
            return 0
        fi

        echo "[$(date +'%F %T')] ▶  pr=$pr caller=$caller(id=$caller_id) requested=$ts"
        local s="review-pr-$pr"

        # Dedup: if a review for this PR is already running, DO NOT kill it —
        # keep the request file for retry (queue it back).
        if tmux has-session -t "$s" 2>/dev/null; then
            echo "[$(date +'%F %T')] ⏳ session '$s' already running — requeuing $base for later"
            local stamp=$(date +%s)
            mv "$file" "$pending/$stamp-$base"
            return 0
        fi

        local logdir="/tmp/tele-bot-review-queue/logs"
        local log="$logdir/pr-$pr-$(date +%Y%m%dT%H%M%S).log"
        mkdir -p "$logdir"
        echo "[$(date +'%F %T')] 📝 log → $log"
        echo "[$(date +'%F %T')] 🚀 spawning tmux session '$s' (attach: tmux attach -t $s)"

        # Tee claude output to $log so diagnosis works even if scrollback is lost.
        # --verbose makes claude print each agent turn (tool uses, thinking, etc).
        # A background heartbeat keeps the session alive-looking during long pauses.
        # awk prefixes every line with a timestamp so you see progress in real time.
        # When claude exits, jq stamps completion info into the processed JSON.
        local pfile="$processed/$base"
        if tmux new-session -d -s "$s" \
            "exec > >(tee -a '$log') 2>&1; \
             echo '=== $(date +%FT%T) /review-pr-ukr $pr (requested by $caller id=$caller_id) ==='; \
             echo 'which claude:'; which claude || echo '  ❌ claude NOT in PATH'; \
             echo 'claude --version:'; claude --version 2>/dev/null || true; \
             echo 'PWD:' \$(pwd); \
             echo; \
             echo '──── claude output ────'; \
             claude --output-format stream-json '/review-pr-ukr $pr' 2>&1 \
               | jq -r --unbuffered 'if .type == \"assistant\" then (.message.content[] | select(.type == \"text\") | .text) elif .type == \"result\" then \"\\n✅ Done (exit=\\(.subtype))\" else empty end' 2>/dev/null \
               | awk '{ print strftime(\"[%F %T]\"), \$0; fflush() }'; \
             rc=\${PIPESTATUS[0]}; \
             echo; echo \"──── claude exit=\$rc ────\"; \
             jq --arg ts \"\$(date -u +%FT%TZ)\" --argjson rc \$rc --arg log '$log' \
                '. + {completed_at: \$ts, exit_code: \$rc, status: (if \$rc == 0 then \"success\" else \"failed\" end), log_file: \$log}' \
                '$pfile' > '$pfile.tmp' && mv '$pfile.tmp' '$pfile' \
                && echo \"📋 status written to $pfile\" \
                || echo \"⚠️  failed to update $pfile\"; \
             echo '✅ Done. Session closes in 10 min...'; \
             sleep 600"
        then
            echo "[$(date +'%F %T')] ✅ tmux session '$s' started"
            mv "$file" "$processed/$base"
            echo "[$(date +'%F %T')] 🗂  moved → processed/$base"
        else
            echo "[$(date +'%F %T')] ❌ failed to start tmux session '$s' — keeping $base for retry"
        fi
    }

    echo "[$(date +'%F %T')] 🛰  queue-watch started ($pending)"
    while true; do
        for f in "$pending"/*.json; do
            [[ -e "$f" ]] && process_file "$f"
        done
        echo "$pending/.keep" | entr -d -n -z true 2>/dev/null || true
    done
