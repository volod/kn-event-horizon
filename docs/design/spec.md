# Agent Python Project Specification

## Purpose

The project provides a small, production-shaped Python base that a team can copy and immediately
develop with human and coding-agent contributors. It makes product intent, forward work, current
behavior, and quality gates explicit enough that a fresh contributor can select and complete work
without reconstructing unwritten process.

The specification is living. A product need discovered during implementation expands this document
through [Extending This Specification](#extending-this-specification). It is not a fixed scope
fence, but behavior that has no specification, boundary, or evaluation is outside the product until
those are declared.

## Design principles

The trust chain is:

```text
domain problem -> bounded capability -> evaluation -> forward task
               -> code and tests -> current-state documentation
```

The product specification answers what and why. The plan answers what remains. Current-state pages
answer what exists. CI checks the joins so completion is a state transition, not a status note.

## Scope

The starter repository includes:

- a Python 3.12+ `src` layout with an importable package and CLI;
- locked `uv` dependency management and Make entrypoints;
- deterministic tests, formatting, linting, typing, coverage, complexity, shell, and docs checks;
- GitHub Actions using the same CI entrypoint as local development;
- shared instructions for Codex, Claude Code, Cursor, and Gemini;
- a living capability registry and forward-plan/current-state lifecycle.

The starter does not choose a business domain, application framework, persistence layer, deployment
platform, or release policy. Those are product decisions and must enter through a specified
capability when needed. The example identity command proves packaging and execution only; it is not
an application architecture recommendation.

## Architecture

```text
Make and GitHub Actions
        |
        +-> package and CLI under src/agent_py/
        +-> mirrored tests under tests/
        +-> quality checks under src/agent_py/quality/
        `-> design -> plan -> current documentation lifecycle
```

Production behavior belongs below `src/agent_py/`. CLI parsing stays at the boundary and domain
logic moves to focused modules. Runtime artifacts resolve from `DATA_DIR` and never enter source
packages.

## Reproducible environment

The environment is created from `pyproject.toml` and committed `uv.lock`. Local development and
GitHub Actions both call Make targets and use the same locked development extra. Tool caches follow
`DATA_DIR`; the shared environment helper chooses `UV_LINK_MODE=copy` only when uv's cache and the
checkout live on different filesystems.

Boundary: the skeleton controls Python dependencies and checks. It does not install system packages,
provision external services, or guarantee reproducibility for undeclared tools.

Evaluation: a fresh copy reaches `make bootstrap` and `make ci` without manual repair. A negative
result names the missing command, stale lock, unsupported interpreter, or failing gate rather than
silently changing the environment contract.

## Project identity

The package exposes typed distribution, import-package, and version metadata. The `agent-py info`
command provides a minimal installed-path smoke test and a stable seam for replacing the starter
identity with the real product's first interface.

Boundary: the command reports identity only. It does not define configuration, service health,
deployment readiness, or product-domain behavior.

Evaluation: package import and CLI tests verify the same identity, while the build target produces
both source and wheel distributions. A negative result retains the minimal identity seam and records
why the proposed product interface is not yet ready.

## Documentation and planning integrity

`AGENTS.md` defines contributor policy. The specification owns product promises, the plan owns
remaining work, and current pages describe available behavior. Task records preserve the work
contract and acceptance evidence after a task leaves the plan.

The closed-research register, `docs/impl/future-research.md`, owns research questions that were
investigated to a decision and then stopped. Each section is headed by the task id the question
carried in the plan and gives the question, the answer with links to its evidence, a reopening
condition, and the directions not to re-run. A reopening condition states what must become true,
such as a measured threshold or a change in available inputs, rather than further effort. When
reopening waits on an authorization or input, an open plan task can own that path and the section
names it. The register is not a backlog, a changelog, or a second copy of the evidence: open work
stays in the plan, available behavior in current pages, and measurements in task records.

An optional `Requires` field declares open task prerequisites across either lane. Plan summaries
skip tasks waiting on these prerequisites and rank the remaining tasks by required status, then
registry and document order. Contributors verify external or manual prerequisites from the task.

Boundary. The checks establish structural agreement. Product value, the strength of acceptance
criteria, completion evidence, and external prerequisites require contributor judgment. The
register check sees section headings, parts, and task references. Whether a reopening condition is
a number or a change in the world, and whether a direction is closed by measurement rather than by
budget, stay reviewer judgment. The register is history by design, so the plan's forward-language
check does not apply to it.

Evaluation. Fixtures exercise broken links, unknown capabilities, missing fields, wrong lanes,
invalid order, unknown and cyclic prerequisites, and scheduling across lanes. A malformed plan
fails with actionable diagnostics and the summary withholds scheduling suggestions. A valid plan
can report that every task in a lane is waiting. Register fixtures reject malformed headings,
closed questions that are still open tasks, missing or empty parts, and reopening tasks that are
not open. An empty register and a complete register pass. A research task that closes negative
meets its gate when its record holds the evidence and its register section states what would
reopen the question.

## Capability Registry

Every product capability appears here exactly once. Status is `planned` when the capability is
specified and has open plan work, or `shipped` when current-state documentation describes its
available implementation. Capabilities that the starter template provides are described in the
[contributor guide](../guide/README.md) instead, so a new project's current-state area starts empty
and holds only its own product behavior. A shipped capability may still have optional extension
work.

Row order is the implementation line. Hard dependencies come first, then work that changes another
capability's evaluation inputs, then required work before capabilities with only optional work, then
upstream before downstream.

| # | Capability | Status | How it is evaluated | Implementation |
| --- | --- | --- | --- | --- |
| 1 | `reproducible-environment` | shipped | A fresh locked environment reaches the complete CI gate without manual repair | [Development guide](../guide/development.md) |
| 2 | `project-identity` | shipped | Import, CLI, and distribution-build tests agree on the starter identity | [Starter identity](../guide/development.md#starter-identity) |
| 3 | `documentation-integrity` | shipped | Link, registry-plan, task-lane, metadata, ordering, prerequisites, forward-language, and closed-research register checks pass over fixtures and the repository tree | [Documentation checks](../guide/development.md#documentation-checks) |

## Extending This Specification

A capability gap is a product discovery, not an automatic refusal and not permission for silent
scope growth. Use this lifecycle in order:

1. State the problem in operator or domain terms.
2. Amend the owning section of this specification, including what the capability does not do.
3. Declare the measurement, acceptance signal, and valid negative result before implementation.
4. Add a `planned` registry row with that evaluation.
5. Put tasks under the capability in the implementation line; every task declares `Serves`.
6. Build and evaluate, document available behavior under current state, remove finished plan scope,
   and change the registry row to `shipped` with its implementation link. Follow the
   [completion workflow](../guide/planning-workflow.md#completion-transition) for the evidence and
   dependency handoff.

When implementation reveals that an existing capability has the wrong boundary, update its section
instead of creating an implementation workaround that the specification cannot explain.

## Specification and plan integrity

The registry and [implementation plan](../impl/plan.md) are two views of one product. The executable
contract requires:

- every task serves a registered capability and sits in its capability group;
- every capability declares an evaluation;
- every planned capability has at least one open task;
- every shipped capability links to its current-state documentation, or to the contributor guide
  when the template provides it;
- groups follow registry order in each task lane;
- every task declares the required outcome, boundary, execution, and acceptance fields;
- lane statuses match whether an agent can finish independently or a human action gates acceptance;
- required tasks precede optional refinements within a capability;
- explicit task prerequisites identify open tasks, form no cycles, and keep required work
  independent of optional refinements;
- every closed-research section names a task that is no longer open, carries its four parts in
  order, and names only open tasks as reopening paths.

The check is structural by design. Product priority changes are made by editing the registry order,
not by adding heuristics to the checker.

## Success criteria

The skeleton succeeds when a team can copy it, rename it, create a locked environment, run a tested
package, and use any supported agent without duplicating project policy. A maintainer can determine
what the product promises, what work remains, which research questions were closed and what would
reopen them, which task is next in each lane, what behavior exists, and how every capability is
evaluated from repository files alone.
