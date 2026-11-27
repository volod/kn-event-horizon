# Closed Research Register

This register records research questions that were investigated to a decision and then stopped,
with the conditions that would make each worth reopening. Check it before opening a research task.
It is not a backlog or a changelog. Open work belongs in the [forward plan](plan.md), available
behavior in [current-state documentation](current.md), and measurements in
[task records](records/README.md). Each section links that evidence instead of restating it.

Every `##` section below this header is one closed question and follows these rules:

1. **Heading.** The task id the question carried in the plan, in backticks, then ` -- ` and the
   question in a few words. The id is no longer an open task.
2. **Question.** What was asked, in operator terms.
3. **Answer.** The decision, usually "no" or "not at this scale", what was measured, and what
   closed it. Link the task record and current-state pages that hold the evidence.
4. **Reopening condition.** What would have to be true, not merely attempted, for the question to
   be worth reopening. State a number or a change in the world, never more effort. When the
   condition waits on an authorization or an input nobody has yet, an open plan task can own the
   reopening path. Name it on a `- Reopening task:` line.
5. **Do not re-run.** Each direction already shown not to work, with a one-line reason it is closed
   by measurement rather than by budget, so a reopening does not repeat it.

```markdown
## `task-id` -- the question in a few words

### Question

### Answer

### Reopening condition

- Reopening task: `open-task-id`

### Do not re-run

- A dead direction -- the measurement that closed it.
```

The [planning workflow](../guide/planning-workflow.md#closed-research) covers adding, reopening,
and removing sections. `make lint-spec-plan` checks section structure and task references.

## `verify-official-taxonomies` -- full official status for mixed seeds

### Question

Can every supplied scheme be presented as a verified official taxonomy after publication comparison?

### Answer

No. Four schemes or scoped subsets verify, but twelve schemes stay unverified: three contain label
mismatches, three mix normalized or local categories, and six are local vocabularies. The OECD
PDF was subsequently supplied by the user, inspected and checksum-pinned, resolving the initial
HTTP 403 access limitation. The [separate OECD scheme and crosswalks](current/ontology-taxonomy/oecd.md)
now provide the official Figure 9 categories; its original mixed product tree still contains local
codes and extensions and remains normalized.
GCAM publication examples were checked without importing a scheme.
The [review decisions](current/ontology-taxonomy/verification.md) and
[initial task record](records/0022-ontology-taxonomy-verify-official-taxonomies.md) and
[OECD scheme record](records/0023-ontology-taxonomy-oecd-official-product-scheme.md) preserve evidence.
The original task's negative-result rule is satisfied; these findings do not block unrelated work.

### Reopening condition

An affected scheme has reviewed codes and labels matching a specific official publication with
retrievable checksum-pinned bytes, or a publisher issues an authoritative correction resolving its
recorded discrepancy. The OECD byte-checksum and separate official-subset path are satisfied.
Other local mixtures require a separately identified official subset before official status can apply.

### Do not re-run

- Promoting an entire mixed GPT, product or application tree because some labels match -- the
  comparison found explicit local extensions and local codes.
- Treating an expanded NASA acronym, a differing CAMEO verb or ECS web navigation as the canonical
  publication heading -- the recorded root labels and PDF chapter heading disagree.
- Promoting the normalized OECD product tree merely because its PDF checksum is available --
  Figure 9 has no source code strings and omits the seed engineering extensions.
- Importing full GDELT dictionaries to settle this review -- publication examples were sufficient;
  dictionary ingestion belongs to `gdelt-source-dictionaries`.

## `raw-archive-format-selection` -- Avro and Iceberg for the raw archive

### Question

Would Avro or Iceberg improve capture fidelity, schema migration or recovery enough to replace
WARC and the initial Parquet fetch index?

### Answer

Keep WARC for HTTP evidence and stream large files into content-addressed blobs. Version the
capture metadata separately and keep the Parquet index rebuildable. The documented format
capabilities and KN replay requirements support this decision. Target-host performance remains
to be measured. See the [storage design review](records/0054-adhoc-raw-archive-storage-design.md).

### Reopening condition

Revisit Iceberg for the index if the [performance gate](plan.md#performance-gate) shows file
planning, lookup or recovery exceeding an agreed budget after partitioning and batching, or a
deployment requires independent hosts to commit to a shared metadata table. Revisit Avro for
capture metadata if a required consumer needs interoperable Avro writer/reader schema resolution
or a representative workload shows the current metadata encoding exceeding its budget.

### Do not re-run

- Replacing WARC to migrate the schema of an opaque source body. Avro schema resolution applies to
  fields in the Avro envelope. The parser and data contracts interpret the original source bytes.
- Using Iceberg snapshot history as the only evidence retention mechanism. Snapshot expiry can
  release the files those snapshots alone protect.
