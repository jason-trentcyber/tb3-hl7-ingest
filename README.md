# HL7 census drift: a realistic debugging environment for AI coding agents

A [Terminal-Bench 3](https://www.tbench.ai) task, built to evaluate how AI coding
agents handle the kind of production problem that has no failing test: a hospital
data feed that quietly writes bad data, and a set of reports that are wrong
without saying why.

This repository contains three things:

- **The environment.** A broken HL7 feed daemon with nine planted defects, a
  supervisor's memo describing symptoms, a week of recorded traffic from three
  hospitals, and the four downstream reports. Traffic is generated, so grading
  uses a week the agent has never seen.
- **A grader that can't be gamed.** The agent's code runs as an unprivileged user
  in a separate container. It cannot read the reference answers or write its own
  score; this was tested with a deliberately hostile submission.
- **A method for telling real AI failures from flawed tests.** Every agent run is
  logged and every failure traced to its cause, with an independent reviewer
  checking whether the task was fair.

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

That is the situation the agent is given. Three hospitals upgraded their message
engines. The daemon was written for the old ones. A house supervisor has sent a
memo listing six things the floor has noticed. The agent has to work out
*everything* that is wrong, with only the memo, the HL7 standard, and a week of
recorded traffic, and fix it so the reports come out right for a week of traffic
it has never seen. There is no partial credit: the midnight census is either right
or it is not.

## What it asks of an agent

Most coding tasks come with a definition of done: a failing test, a spec, an
expected output. Here there is none. The memo says "here is what we noticed; there
is probably more." The agent has to reason from downstream symptoms ("the census
is high") back to upstream causes ("the daemon treats a Social Security number as
a medical record number"), keep going after the visible symptoms are fixed, and
decide when it is finished with no test turning green to tell it.

That is also, not coincidentally, what the job is actually like.

## Real failure or flawed test?

The hardest part of evaluating an AI agent is not running it. It is deciding,
when it gets something wrong, whether the agent failed or the task did.

Over seven versions and 34 logged runs against the leading coding agents (Claude
Code and Codex at their strongest settings), several runs looked like clean
failures. Each was traced to its cause. In every case the task relied on a
convention it never stated: how a merge message names the retired record, how
numbers should be stored, whether identifiers move to the surviving patient after
a merge. An independent reviewer, given only what the agent sees, made the same
choice the agents did. Those runs were not counted as failures; the conventions
were documented and the task re-run.

The lesson applies well beyond benchmarks: an agent working from a spec is only as
reliable as the spec. Once every rule was written down, the agents found all nine
defects and produced correct reports. The full record, including the runs that
went against the task, is in [`RESULTS.md`](RESULTS.md) and
[`TRIALS.md`](TRIALS.md). [`PROPOSAL.md`](PROPOSAL.md) sketches a follow-on task
designed around that lesson.

## What is in the repository

| Path | What it is |
|---|---|
| `RESULTS.md` | Checks, trials, and failure analysis for the final version |
| `tasks/hl7-census-drift/` | The task: broken daemon, memo, recorded traffic, reports, sandboxed verifier, reference solution |
| `tasks/hl7-feed-recovery/` | Earlier versions (v1–v4), kept as the record of the design's evolution |
| `TRIALS.md` | Every agent run, with model, configuration, duration, result and what the agent actually did |
| `ANALYSIS.md` | What the public Terminal-Bench 3 results say about which tasks agents fail |
| `DESIGN.md`, `tasks/*/DESIGN.md` | Design notes: planted defects, how each is disguised, how the verifier works |
| `PROPOSAL.md` | A follow-on task (revocable patient links), proposed and probed, not built |
| `analysis/` | Independent ambiguity review and design-probe outputs |
| `scripts/` | Tooling: static checks, trial summariser, capture builder, verifier isolation test |

## How to run it

The task follows the Terminal-Bench 3 layout and runs under
[Harbor](https://github.com/laude-institute/harbor). From the repository root:

```
harbor run -p tasks/hl7-census-drift --agent oracle --env docker --yes    # reference solution, expect 1.0
harbor run -p tasks/hl7-census-drift --agent nop    --env docker --yes    # do nothing, expect 0.0
scripts/static_checks.sh tasks/hl7-census-drift                           # the TB3 CI static checks
scripts/isolation_test.sh                                                 # hostile submission vs. the real verifier image
```

Agent trials use the Terminal-Bench 3 CI configurations; exact commands and every
result are in `TRIALS.md`.

## About the author

Jason Trent is a systems and cloud architect and a former full-stack engineer,
with years in healthcare SaaS and security. He is not an HL7 specialist: his
hands-on HL7 work was integration-engine plumbing in Mirth. He picked this domain
because he knows how these feeds fail downstream. The code was written by AI
coding agents (Claude Code and Codex); he directed the design, decided what
counted as a fair failure, and verified every result.

Contact: jason@jtrent.dev · [jtrent.dev](https://jtrent.dev)

Licensed under the MIT License (see `LICENSE`).
