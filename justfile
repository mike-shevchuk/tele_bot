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

# Run full CI check locally (lint + import check)
ci:
    #!/usr/bin/env bash
    echo "=== Ruff: blocking errors ==="
    ruff check --select E9,F63,F7,F82 . && echo "✅ Clean"
    echo ""
    echo "=== Ruff: all warnings ==="
    ruff check . || true
    echo ""
    echo "=== Import check ==="
    python3 -c "
import ast, sys, pathlib
errors = []
for p in pathlib.Path('.').rglob('*.py'):
    if any(part in p.parts for part in ['.venv', '__pycache__', '.git']):
        continue
    try:
        ast.parse(p.read_text())
    except SyntaxError as e:
        errors.append(f'{p}:{e}')
if errors:
    print('\\n'.join(errors)); sys.exit(1)
else:
    print('✅ All modules parse OK')
"

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
