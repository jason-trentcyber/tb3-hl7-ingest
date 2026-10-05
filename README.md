# Can an AI fix a hospital's data feed when nobody can tell it what's wrong?

This repository is a take-home submission for Klavis AI's Founding Engineer role.
The assignment: design one original task for [Terminal-Bench 3](https://www.tbench.ai),
a benchmark that measures how well AI coding agents handle realistic engineering
work, and show that the two strongest agents available today fail it for real
reasons, not because the task is broken.

## The problem in plain language

Hospitals run on messages. Every time a patient is admitted, moved to another bed,
discharged, or has a lab result come back, the hospital's systems send a short
text message in a format called HL7 to every other system that needs to know. A
small program, the *feed daemon*, listens for these messages and writes them into
a database. Reports are built from that database: who is in which bed tonight,
who went home today and how long they stayed, what their lab values were.

If the daemon misreads the messages, the reports are wrong, and nobody finds out
from the daemon. It keeps saying "received, thanks" to every message. The first
sign of trouble is a charge nurse counting heads at midnight and getting a
different number than the report, or a lab value that is ten times too high, or a
patient who was discharged Tuesday still showing as being on the ward on Friday.

That is the situation we hand to the AI agent. Three hospitals upgraded their
message engines. The daemon was written for the old ones. A house supervisor has
sent a memo listing six things the floor has noticed. The reports are correct;
the daemon is not. The agent has to work out *everything* that is wrong, with
only the memo, the HL7 standard, and a week of recorded traffic, and fix it so
that the reports come out right for a week of traffic it has never seen. There
is no partial credit: the midnight census is either right or it is not.

## Why this is hard for an AI

Most coding tasks come with a definition of done: a failing test, a spec, an
expected output. AI agents are very good at those. They read the definition,
work towards it, and check themselves against it until it is satisfied.

Here there is no definition to read. The memo says "here is what we noticed; there
is probably more." The agent has to reason from downstream symptoms ("the census
is high") back to upstream causes ("the daemon treats a Social Security number as
a medical record number"), and then keep going after the visible symptoms are
fixed, because the grading covers things no one on the floor would ever notice.
It has to decide when it is finished with no test turning green to tell it.

That is also, not coincidentally, what the job is actually like.

## What we found

Short version: the task does not meet the bar. On the final version, both
Claude Code (Opus 5.5) and Codex (sol) solve it. The record of how it got there,
seven versions and 33 logged trials, is the most useful part of this repository.
[`RESULTS.md`](RESULTS.md) is the five-minute summary.

Versions 1 through 4 (`tasks/hl7-feed-recovery`) each tried a different way of
making the problem hard: a dense specification, a reference capture to infer
behaviour from, HL7 semantics that need domain knowledge, and demanding
durability and throughput requirements. Both agents solved every one, usually
by writing their own test suite that mirrored the specification and iterating
until it passed.

Analysing the public Terminal-Bench 3 results (`ANALYSIS.md`) showed what the
tasks both models score zero on have in common: the agent cannot enumerate what
it will be graded on. Versions 5 and 6 (`tasks/hl7-census-drift`) were built on
that pattern, and v6 went further by hiding two of the four report scripts.

What happened is the finding. Every run that looked like a genuine failure
traced back to a convention the task relied on but never stated: how a merge
message names the retired record, how numbers are written, whether identifiers
move to the surviving patient after a merge. An independent reviewer reading
only what the agent sees made the same "wrong" choice the models did. Once each
convention was written down, the models passed. They found all nine planted
defects in every run. Hiding information made the task unfair, not hard; a
harder task needs more reasoning with everything stated.
[`PROPOSAL.md`](PROPOSAL.md) sketches one.

Along the way the verifier was hardened so the agent's code runs as an
unprivileged user and cannot read the answers or write its own score, tested
with a deliberately hostile submission. Both adversarial (`/cheat`) trials
scored zero.

## What is in the repository

| Path | What it is |
|---|---|
| `RESULTS.md` | Final-version checks, trials, and failure analysis: start here |
| `tasks/hl7-census-drift/` | The final task (v5–v6.3): broken daemon, memo, recorded traffic, reports, sandboxed verifier, reference solution |
| `tasks/hl7-feed-recovery/` | The previous task (v1–v4), complete and solved by both models; kept as the record of what did not work |
| `TRIALS.md` | Every agent run, with model, configuration, duration, result and what the agent actually did |
| `ANALYSIS.md` | Why v1–v4 were solved and what the leaderboard data says about tasks that are not |
| `DESIGN.md`, `tasks/*/DESIGN.md` | Design notes: planted defects, how each is disguised, how the verifier works |
| `PROPOSAL.md` | A harder sibling task (revocable patient links), proposed and probed, not built |
| `analysis/` | Independent ambiguity review and design-probe outputs |
| `scripts/` | Tooling: static checks, trial summariser, capture builder, verifier isolation test |

## How to run it

The task follows the Terminal-Bench 3 layout and runs under
[Harbor](https://github.com/laude-institute/harbor). From the repository root:

```
harbor run -p tasks/hl7-census-drift --agent oracle --env docker --yes    # reference solution, expect 1.0
harbor run -p tasks/hl7-census-drift --agent nop    --env docker --yes    # do nothing, expect 0.0
scripts/static_checks.sh tasks/hl7-census-drift                           # the TB3 CI static checks
```

Agent trials use the Terminal-Bench 3 CI default configurations; exact commands
and every result are in `TRIALS.md`.

## About the author

Jason Trent is a systems and cloud architect and a former full-stack engineer,
with years in healthcare SaaS and security. He is not an HL7 specialist: his
hands-on HL7 work was integration-engine plumbing in Mirth. He picked this domain
because he knows how these feeds fail downstream. The code was written by AI
coding agents (Claude Code and Codex), as the assignment allowed; he directed the
design, decided what counted as a fair failure, and verified every result.

Contact: jason@jtrent.dev · [jtrent.dev](https://jtrent.dev)
