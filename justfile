# Lint: blocking errors only (same as CI)
lint:
    ruff check --select E9,F63,F7,F82 .

# Lint: all style warnings (non-blocking)
lint-warn:
    ruff check . || true

# Auto-fix all auto-fixable ruff issues
lint-fix:
    ruff check --fix .

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
