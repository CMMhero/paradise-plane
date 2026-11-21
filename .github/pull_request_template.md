### What changed

<!-- One paragraph. What is different now compared to before. -->

### Why

<!-- The problem this solves, or the request it answers. If there is an issue,
mention it here with "Closes #123" so the issue closes when this merges. -->

### Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Visual or user experience fix
- [ ] Refactor, behavior unchanged
- [ ] Performance
- [ ] Documentation
- [ ] Infrastructure, CI, or operations script

### How I tested it

<!-- Not "tested". Write what was actually run, for example:
     - `pnpm --filter web check:types` clean
     - `docker compose -f docker-compose-local.yml exec -T api python -m pytest plane/tests/x.py` passes
     - opened at localhost:4000, tried with a staff account and an admin account
   If it hasn't been tested at all, say so plainly. That is information, not a disgrace. -->

### Screenshots

<!-- Required if this touches the UI. Before and after is better than after alone. -->

### Before asking for review

- [ ] `pnpm check` is green on my machine, or I say which part is red and why
- [ ] No secrets were committed: no `.env`, tokens, passwords, or keys in the diff
- [ ] Added a new environment variable? The relevant `.env.example` is updated too
- [ ] Touched locale files? I checked `git status` and the `packages/i18n/locales` junction is still intact
- [ ] Changed documented behavior? The README or the docs in `paradise/` are updated too

### What the reviewer should look at

<!-- The part you are least sure about, a decision you made on purpose, or
something deliberately NOT done in this PR. This saves the most review time. -->
