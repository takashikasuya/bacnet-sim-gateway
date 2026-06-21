<!-- Thanks for contributing! Keep PRs focused (1 epic / 1 concern). -->

## Summary

<!-- What does this PR change and why? -->

## Related issues

<!-- e.g. Closes #123 -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Docs only
- [ ] Refactor / chore
- [ ] CI / tooling

## Checklist

- [ ] `uv run ruff check` and `uv run ruff format --check` pass
- [ ] `uv run mypy` passes
- [ ] `uv run pytest` passes (unit + loopback); integration run if relevant
- [ ] New/changed behaviour is covered by tests
- [ ] Stays in scope; no unrelated changes
- [ ] Respects invariants (northbound BACnet / southbound binding; `gateway_id` ≠ `bbc_id`; SBCO-only input, YAML intermediate model)

## Spec / design impact

<!-- Does this touch an ADR, PRD, or spec? Note it here. Manual acceptance steps (YABE, ARM hardware, BTL) if any. -->

## Compatibility

<!-- Any breaking change to config schema, CLI, or APIs? (0.x allows breaking changes — call them out.) -->
