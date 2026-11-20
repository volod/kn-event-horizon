# Specification and plan audit

The [forward plan](../plan.md) had 71 open tasks before and after review. Tracing prerequisites
back from release approval exposed two missing required outcomes, taxonomy verification and SKOS
export. Release approval now depends on both. Microelectronics comparison marts also depend on
the task that establishes the shared dbt project.

The [specification](../../design/spec.md#replay-and-publication-boundaries) defines the archive
commit and SQL checkpoint boundary, publication from eligible evidence, and domain-specific
counting and comparison fixtures. The owning tasks carry replay, withdrawal, and restore checks.
Product acceptance remains open until those tasks run.

The repository tests check five proposal manifests covering 47 sheets and 1,173 rows and exercise
wrapped plan prerequisites. Source publication verification and the owner's origin policy remain
open. The converted JSON was checked against its manifests. Original workbooks were unavailable
in this checkout.

The owner subsequently required origin eligibility for comparisons and a first-release analyst
fact explanation. The plan grew from 71 to 72 open tasks. The shared explanation view gates space
dashboard delivery and is reused by the later domains. Jurisdictions, decision criteria, and
exception authority remain open in the human-assisted origin policy task.

The owner subsequently replaced the origin gate with an informational target-market dimension.
A policy observation task replaces the human origin-policy decision. Technical comparison marts
can proceed independently. Dashboard delivery includes a market-switch regression fixture.
The revised plan has 72 tasks, comprising 64 agent tasks and eight human-assisted tasks.
