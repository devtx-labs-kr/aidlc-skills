# Code Conflict Merge Strategy

Code conflicts arise when parallel units touch shared code, or when one unit
changes something a dependent unit relies on. Unlike state files, these need
semantic understanding — you have to grasp *intent*, not just reconcile text.

There are two layers here, and the second is the one that hurts:

- **Git-flagged conflicts** — two branches edited the same region. Git stops and
  shows you markers. This document's classification handles these.
- **Silent semantic conflicts** — a shared contract changed on one branch while
  a consumer on the other branch lives in a *different file*. Git merges both
  with no markers. These are covered at the end, and the only way to catch them
  is to build and test after the merge.

## Locating design context — discover, don't assume

To resolve a conflict well you need the design intent behind each side. Where
that intent lives varies by project and framework version, so **search for it**
rather than reading a fixed path:

- Find functional-design material: search `aidlc-docs/construction/` for
  `*functional-design*` (it may sit under per-unit folders like
  `u1-*/functional-design/` or at a shared level). The actual file names differ
  between projects — business-logic, business-rules, domain model, components —
  so list the folder and read what's there.
- Find code-generation intent: search for `*code-generation*` and any
  `code-summary` or plan file; it may be one combined plan or per-unit plans
  under a `plans/` directory.
- Identify which unit a conflicted file belongs to: check `git log` for the
  commits that touched it, and cross-reference the unit folders you found in
  Step 0 of the main workflow.

If a path you expect doesn't exist, that's normal — projects are laid out
differently. Adapt to what the repo actually contains.

## Classify each git-flagged conflict

### Additive — both changes coexist

New functions/methods added by different units to the same file; new imports on
both sides; new entries appended to a list or config.

Resolution: include both. Order them logically (group related functions,
alphabetize imports). No user decision needed for clean additive merges.

### Overlapping — one must win

The same function, value, or contract changed differently on each side.

Resolution: this needs a human decision. Present both versions with the design
context you gathered, explain the trade-off, and wait for the user to choose.

### Dependency — a shared contract moved

A shared unit's API/type/model changed, and a dependent unit's usage no longer
matches.

Resolution: the shared unit's change is usually authoritative — adapt the
consumer to the new contract. Show the user the change and your proposed
adaptation before applying, because "authoritative" is a judgment call, not a
rule.

## Present resolutions in a consistent shape

For each non-trivial conflict, show the user:

```
## Conflict: <file-path>
**Type**: Additive | Overlapping | Dependency
**Units involved**: <unit-a>, <unit-b>

### Ours (HEAD)
<code from our side>

### Theirs (<branch>)
<code from their side>

### Proposed resolution
<merged code>

### Rationale
<why, referencing the design artifacts you found>
```

Apply after approval. Clean additive merges can be applied directly and
summarized rather than gated one by one.

## Common patterns

**Shared model / type definitions** (a single `models`, `schemas`, or `types`
file that several units edit): if both sides add new fields, merge both. If both
modify the same field, that's Overlapping — flag it. Check each unit's domain/
design artifact for the intent behind the change.

**Central registration / wiring point** — this is the single most common
AI-DLC merge conflict, and it's a structural role, not a stack-specific one. Any
project has *some* place where independent units announce themselves to the
whole: a list each unit appends an entry to, plus the import/reference that entry
needs. Because every unit edits that one place, parallel units collide there.
The shape depends on the stack but the pattern is identical:
- a web API wiring file registering each unit's router/controller (e.g. an
  `include_router(...)` / `app.use(...)` / `MapControllers` block);
- a single-page-app router table mapping paths to each unit's screen;
- a CLI registering each unit's subcommand;
- a plugin/module registry, a dependency-injection container, an `__init__`
  re-export, an event-handler dispatch table.

Treatment is the same everywhere: almost always **Additive** — keep every unit's
registration, dedupe the imports/references. The one thing to watch is two units
claiming the **same key** (route path, command name, registry id) with different
targets; that's **Overlapping** and needs a human decision.

**Dependency manifests** — whatever your ecosystem uses (`requirements.txt`,
`pyproject.toml`, `package.json`, `pom.xml`, `build.gradle`, `go.mod`,
`Cargo.toml`, `Gemfile`, etc.): take the union of dependencies; flag any case
where both sides pin the *same* package to *different* versions. Include both
scripts/tasks; flag name collisions. For other settings, flag differing values
rather than guessing.

**Infrastructure / IaC** (if present): new resources from different units are
additive — include both. The same resource modified on both sides is
Overlapping — flag it and reference the infrastructure-design artifact.

## Silent semantic conflicts — the check git can't do for you

This is the part most merge workflows miss. Git's conflict detection is
line-based and per-file. When unit A changes a shared contract and unit B
consumes it from another file, git sees two non-overlapping edits and merges
them cleanly. No markers, no warning. The merge "succeeds" and then the build
fails — or compiles and breaks at runtime.

Typical shapes, framed by the contract's role rather than any layer — they
apply equally to a web service, a CLI, a data pipeline, a library, or a mobile
app:

- A shared **event or message type** gains/loses a field on one branch; a
  handler on the other branch still reads the old shape.
- A shared **function or service entry point** changes its signature; callers in
  another unit still pass the old arguments.
- A shared **data shape** (API response, serialized record, DTO, file format)
  changes on the producing side; a consumer elsewhere still parses the old one.
- A shared **enum / status set / constant** gains a value one unit handles and
  another doesn't.
- A shared **interface / abstract contract** gains a method one implementation
  provides and another hasn't caught up to.

You cannot find these by reading conflict markers, because there aren't any. To
catch them:

1. From the main workflow's Step 1 you have a **watch-list** of shared contracts.
   For each, locate the producer and *every* consumer (search the codebase for
   the type/function/route name across all units) and confirm they still agree
   after the merge.
2. **Build/compile** the whole project — many of these surface immediately as
   type or import errors.
3. **Run the tests**, and the integration/smoke path if the project documents
   one. Cross-unit contracts only prove out when exercised end-to-end.

Treat any failure here as part of the merge to fix now. A merge that compiles
isn't proven correct until the cross-unit behavior runs green.
