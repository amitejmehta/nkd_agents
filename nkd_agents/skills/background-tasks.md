# Background Work

For autonomous tasks that should produce isolated, reviewable changes:

## Protocol

1. **Branch**: `git checkout -b descriptive-branch-name`
2. **Implement**: Make your changes
3. **Test**: Run relevant tests/checks to verify correctness
4. **Commit**: `git add -A && git commit -m "clear description"`
5. **PR**: `gh pr create --title "Title" --body "Description"`

## Use Cases

**Parallel work** - User launches multiple CLI instances in separate terminals, each working on different tasks simultaneously. Each creates its own branch and PR.

**Sequential alternatives** - Agent uses `subtask()` to try multiple implementation approaches for the same problem, each producing a separate PR for comparison.

The main branch stays clean while experimentation happens in isolated branches.