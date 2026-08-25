---
name: aidlc-git-merge
description: Resolve git merge conflicts in AI-DLC projects where multiple developers work in parallel and merge their work back together. Use this skill whenever the user mentions merge conflicts, git merge, rebase conflicts, pull/push conflicts, "both modified", conflict markers (<<<<<<<), or describes multiple people working on different units/Bolts/branches of the same AI-DLC project and needing to combine the results. Handles the three things git surfaces — AI-DLC state files (aidlc-state.md, audit.md), shared application code, and configuration files — AND the silent semantic conflicts git does NOT flag (a shared contract changed on one branch, clean-merged, but now broken at runtime). Works across any AI-DLC project regardless of language, stack, or unit layout — it discovers the project's actual structure instead of assuming fixed paths.
---

# Git Merge Conflict Resolver for AI-DLC Projects

Multiple developers split an AI-DLC project into units (or Bolts) and work in
parallel, then merge back to `main`. This skill resolves the conflicts that
result. It is deliberately project-agnostic: it discovers the repo's real
layout and adapts, rather than assuming a particular folder structure.

## The mental model you need first

Git only raises a conflict when two branches edit **the same lines of the same
file**. That makes three kinds of trouble in an AI-DLC merge, and they are NOT
equally dangerous:

1. **State files** (`aidlc-docs/aidlc-state.md`, `aidlc-docs/audit.md`) — these
   are written by the AI-DLC engine, not by hand. They conflict constantly
   because every developer's run advances the same bookkeeping. They are the
   most *mechanical* to resolve but also the easiest to corrupt, because a
   text-merge that looks fine can still be invalid to the engine.

2. **Code and config** — shared modules, routers, schemas, type definitions,
   dependency manifests. Git flags these when two branches touch the same
   region. Resolving them needs you to understand intent.

3. **Silent semantic conflicts** — the dangerous ones. When unit A changes a
   shared contract (an event type, a function signature, an API shape) and unit
   B depends on it from a *different* file, git merges both cleanly with **no
   conflict markers at all**. The merge "succeeds" and the build breaks — or
   worse, it compiles and misbehaves at runtime. No merge tool catches this.
   You only catch it by building and running the tests after the merge.

A merge that git reports as clean is NOT proven correct. Plan to verify.

## Workflow

### Step 0: Orient yourself in this specific project

Don't assume paths. Different AI-DLC projects lay out units differently (per-unit
folders, a single combined codebase, Bolt worktrees), and the framework's folder
names evolve. Spend a moment discovering the truth:

- `git status` and `git diff --name-only --diff-filter=U` — the actual conflicted files.
- List `aidlc-docs/construction/` — the subfolders named like units (`u1-*`,
  `u2-*`, or similar) tell you the unit boundaries that were planned.
- Find the code-generation artifacts: they may live at
  `aidlc-docs/construction/code-generation/`, under per-unit folders, or a
  `plans/` directory. Use search, not a hardcoded path, to locate
  `*code-generation*` and `*functional-design*` files.
- Note where application code actually lives — it's usually outside
  `aidlc-docs/` (commonly the workspace root, in whatever layout the stack uses:
  source folders, packages, modules, etc.). That's where code conflicts are, so
  find the real source tree before diving in.

Carry these discovered locations forward; the reference files tell you what to
read, not where it must be.

### Step 1: Classify every conflicted file

For each path from `git diff --name-only --diff-filter=U`, bucket it:

- **State file** — `aidlc-docs/aidlc-state.md` or `aidlc-docs/audit.md`.
- **Code or config** — everything else.

Then, separately, write down the **shared contracts** that the parallel units
depend on (events, shared models/types, service entry points, API routes). These
are your watch-list for the silent-conflict check in Step 4, whether or not git
flagged them.

### Step 2: Resolve state-file conflicts

**First check: was this a worktree/Bolt merge? Then the engine already merged the
state — do NOT hand-merge it.** If the parallel work used the engine's worktree
primitives (`aidlc-bolt start --worktree` on fork, `aidlc-bolt complete --merge`
on merge), the engine merges `aidlc-state.md`, the audit shard, and the
runtime-graph fragment together as a unit — there is no hand-merge to do, and
forcing a raw `git merge` of those files instead is what *creates* the state
conflict. If you are staring at conflict markers in `aidlc-state.md` after a
worktree Bolt, the fix is to redo the merge through `aidlc-bolt complete --merge`,
not to reconcile the markers by hand. Hand-merging state files (below) applies
only when the team ran **raw git branches without the worktree primitives** — a
setup the framework's design steers away from (see the prevention note at the
end).

For that raw-git case, read `references/state-file-merge.md` for the detailed
strategy.

The short version: the audit log is append-only and merges cleanly by
interleaving entries chronologically. `aidlc-state.md` is trickier — it is
engine-owned, and several of its fields are scalars (state version, current
stage, active agent) that genuinely diverge between branches. Resolve the
text, then **validate with the engine** rather than trusting your hand-merge.
The reference file explains how, including the tooling to recompute and check
state.

### Step 3: Resolve code and config conflicts

Read `references/code-conflict-merge.md` for the detailed strategy.

It classifies each git-flagged conflict as additive (both changes coexist),
overlapping (one must win — needs a human decision), or dependency (a shared
unit's contract changed and a consumer must adapt). It covers shared
models/types, the central registration/wiring point every unit appends to
(whatever the stack calls it), and dependency manifests. For anything that isn't
a mechanical additive merge, present the options and the rationale to the user
before applying.

### Step 4: Verify — including what git did NOT flag

This is the step that separates a real resolution from a merge that only looks
done. After all markers are gone:

```bash
git diff --name-only --diff-filter=U   # expect zero
```

Then actually exercise the code, because of the silent-conflict risk:

- Build/compile the project.
- Run the test suite (AI-DLC projects keep tests alongside code — find and run
  them with the project's documented commands; check the README or build
  instructions).
- If the project has an integration or smoke path documented in its
  build-and-test artifacts, run it. Cross-unit contracts (the kind git merges
  silently) only prove out end-to-end.

For each shared contract on your Step 1 watch-list, confirm both the producer
and every consumer still agree after the merge. If a contract changed on one
branch, the consumers on the other branch won't show a git conflict but may now
be calling a signature that no longer exists.

If verification fails, the failure is part of the merge — fix it now, while the
context is fresh, rather than committing a broken merge.

### Step 5: Complete

Report to the user: which files conflicted, how each was resolved (and which
needed their decision), what you verified (build, tests, smoke), and anything on
the contract watch-list that warrants a closer human look. Only then is the
merge ready to commit.

## A note on prevention

If you find yourself resolving the same painful conflicts every merge (a single
shared file — schemas, types, a shared constants module — that every unit edits,
or one central registration point every unit appends to), that's a structural
smell worth surfacing to the user. Splitting shared single-file hotspots per
unit, or moving registration to auto-discovery, removes the contention at the
source. And if the team is running fully independent state machines per
developer and merging `aidlc-state.md`, that fights the framework's design —
worktree/Bolt workflows keep one owned state and avoid the divergence entirely.
Mention these when you see them; don't silently paper over a recurring conflict.
