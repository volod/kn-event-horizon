# Contract development within delivery groups

The [forward plan](../impl/plan.md) follows the path from a source record to a durable identity,
a cited claim, a reviewed fact and a reproducible export or dashboard. Each group delivers a
result its consumer can exercise. Read the group's tasks in order and use their explicit
prerequisites when selecting work. Source permissions, live-instance access, budgets and
release approval belong to the human lane.

## Selection rule

MODEL and DELIVERY describe the work and its evidence. The first eligible required task in
written order has priority. An independent group can proceed while another waits for evidence
or authorization. Every group closes with an audit. Consumers require that audit before using
the group's output. Optional extensions have their own audits.

## Model sequence

Define each durable key, contract, unit, time meaning and evidence boundary before its first
writer. Compile the contract, exercise the writer or a representative fixture, then rebuild
the registered models together. For example, identity workflows consume the registered journal
and shared human verification protocol. Claim selection additionally needs evidence contracts
and tested identity resolution. Neither workflow needs GDELT dictionaries or a live counterpart.

## Model ownership and splits

Keep shared objects and histories in identity, claims and review in evidence, source and run
metadata with their registered owners, and common measurements in supply. Domain adapters
extend these contracts. Preserve original SATCOM snapshot keys and cells alongside canonical
space facts. Interchange owns its versioned external schemas, binding ledger and loss reporting.
Each new table must declare [verification coverage](../impl/current/evidence-model.md#coverage-and-target-resolvers)
and provide representative replay fixtures in the
[combined baseline](../impl/current/data-contracts/model-baseline.md#extending-the-checkpoint).
Changes to keys, units, null meanings or ownership require an explicit compatibility decision,
backfill evidence and reruns of affected consumers.

## Integrated baseline and later changes

Run the registered-subset fixture check as each group grows the registry. During development
use the editable ODCS 1.0.0 and single Alembic baseline, explicitly rebuilding and backfilling
with recovery evidence when adopting changes. The full `development-model-baseline` task checks
every core and domain owner together before release approval. Its acceptance retains full
fixture round trips, lossless SATCOM import, repeated rebuilds, decision replay, role checks and
review of the generated diff. Release migration mode still requires the owner's approval.
