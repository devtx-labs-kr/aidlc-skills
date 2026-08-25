# State File Merge Strategy

`aidlc-docs/aidlc-state.md` and `aidlc-docs/audit.md` are written by the AI-DLC
engine, not by hand. That single fact drives the whole strategy: your job is not
to produce text that *reads* right, but text the **engine** accepts as valid. A
hand-merge that looks plausible can still leave the state machine inconsistent
(a stage count that doesn't match the checkboxes, a version that didn't advance,
a current-stage that contradicts the audit log). So for `aidlc-state.md` you
resolve the text and then let the tooling check and recompute it.

The two files behave very differently. `audit.md` is the easy one. `aidlc-state.md`
is the one that bites.

## audit.md — append-only log (the easy case)

### Structure

A flat, chronological log. Each entry is a block delimited by `---`, and every
entry carries a `**Timestamp**:` field in ISO 8601. Every developer's session
appends entries to the end, so two branches almost always conflict in a single
large region at the tail.

### Merge logic

1. Extract every entry from **both** sides of the conflict (ours and theirs).
2. Deduplicate: if an entry is identical on both sides (same timestamp **and**
   same content), keep one copy.
3. Sort all surviving entries chronologically by timestamp.
4. Write the merged result, preserving the `---` delimiters.

This is safe to do automatically — the log is additive by nature and no
information is lost by interleaving.

### Edge cases

- **Identical timestamps** (common — many engine events fire within the same
  second). Stable order is fine: keep HEAD's entries before theirs when the
  timestamp ties. The audit log is a record, not a causal proof; second-level
  ordering is good enough.
- **Entries with no timestamp** — place them at the end, grouped by the branch
  they came from, so nothing is dropped.

## aidlc-state.md — engine-owned state (the hard case)

### Structure varies — read before you assume

The state file's shape differs across AI-DLC projects and framework versions.
Before merging, read both sides and notice which layout you have:

- **Single global progress list** — one set of stage checkboxes for the whole
  project (e.g. a `### CONSTRUCTION PHASE` block listing `functional-design`,
  `code-generation`, etc.). Two developers advancing in parallel edit the **same
  lines**, so conflicts are line-for-line on identical entries.
- **Per-unit sections** — progress tracked separately per unit/Bolt. Here each
  developer mostly edits their own unit's lines, and the two sides describe
  different units.

Don't assume per-unit sections exist. If they don't, the "keep both lines, they
describe different units" trick does not apply — you have a genuine same-line
conflict to reconcile.

### Field-by-field resolution

**Stage checkboxes** (`- [ ]`, `- [-]`, `- [x]`, `- [S]`):
Progress only moves forward, so for the same stage line, take the most-advanced
state across both sides. Completed (`[x]`) beats in-progress (`[-]`) beats not-
started (`[ ]`). A skip (`[S]`) reflects an explicit jump — if one side skipped
and the other executed, prefer the executed/completed state and flag it, since
the divergence means the two branches disagreed about scope.

**Scalar bookkeeping fields** — these are where the real damage hides, because
both branches changed the *same* field to *different* values and there's no
"merge" that's automatically correct:

- **State Version** (a monotonic counter): do NOT just pick one side's number.
  Two parallel increments both advanced from the same base, so the true post-
  merge version is higher than either. Let the engine recompute it (below)
  rather than guessing.
- **Current Stage / Next Stage / Active Agent / Status**: these describe "where
  the workflow is," which is ambiguous after a parallel merge. Resolve to the
  combined reality — the furthest-along stage consistent with the merged
  checkboxes — and treat it as provisional until validation confirms it.
- **Last Updated**: use the later timestamp.
- **Completed / Total stage counts**: don't hand-type these. They must match the
  merged checkboxes exactly, so recompute them.

**Configuration fields** (Project Type, Scope, Start Date, Stages to Execute/
Skip, Depth): set during earlier phases and should be identical on both sides.
If they differ, that's a real disagreement about the project's shape — stop and
flag it for the user rather than silently picking one.

### Validate and recompute with the engine — don't trust the hand-merge

After you've produced merged text, reconcile it with the tooling so the state
machine stays internally consistent. These tools run via `bun` and are
harness-neutral (paths are relative to the workspace root):

- Recompute a stage count instead of trusting a typed number:
  ```bash
  bun .kiro/tools/aidlc-state.ts count completed
  ```
- Read a field to confirm what the merged file actually says:
  ```bash
  bun .kiro/tools/aidlc-state.ts get "Current Stage"
  ```
- Correct a field through the engine (so related invariants update) rather than
  editing text by hand:
  ```bash
  bun .kiro/tools/aidlc-state.ts set "<field>=<value>"
  ```
- Validate that the phase's recorded outputs line up with the merged state:
  ```bash
  bun .kiro/tools/aidlc-validate.ts outputs all
  ```

If the project exposes other state subcommands, prefer them over manual edits.
The principle: the engine owns this file, so let the engine have the last word.

### When to involve the user

The original instinct to "resolve state files automatically without
confirmation" is fine for `audit.md`, but `aidlc-state.md` deserves a check-in
when:

- Configuration fields diverged (scope, stages-to-execute, project type).
- One side skipped a stage the other executed.
- Validation (`aidlc-validate.ts`) still reports inconsistencies after your
  recompute.
- The same unit was advanced by two different developers (shouldn't happen if
  units are assigned to individuals — treat it as a signal that the parallel
  split itself went wrong).

In these cases, surface the conflict and your proposed resolution and let the
user decide. Quietly picking a side can lose someone's work or leave the
workflow pointing at the wrong stage.
