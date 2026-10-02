# Design: hl7-feed-recovery

A Terminal-Bench 3 task. Built for the Klavis AI founding-engineer take-home,
October 2026. Public from the first commit; see the root README for results
and `TRIALS.md` for every run.

## The job being simulated

A regional health system upgraded its interface engines. The inbound HL7 v2
ingestion daemon, written years ago against an older contract, now stalls,
drops records and corrupts rows. The vendor is gone and took the part of the
contract that said how each message changes the database. What is left is
the transport/parsing half of the spec, a schema, and one recorded day of
traffic between the engines and the vendor's reference daemon: the exact
bytes in, the exact ACK bytes out, the database it produced, its dead-letter
file.

An integration engineer is told: make the daemon behave like the reference
did. This is a billable, weeks-of-pager-duty kind of job, and it is how this
work actually happens: you rarely get a spec, you get a capture and a
database and a deadline.

## How the task evolved (and why)

The first version shipped the complete spec. gpt-6-astra, given the whole
contract in writing, got 10 of 11 verifier assertions on the first clean
attempt, and the one miss was a clause the spec did not state. A complete
spec turns the task into careful reading, and frontier models are good at
careful reading. Details in `TRIALS.md`.

The third version removes Section 5 (every processing rule: patients,
identifiers, encounters, observations, idempotency, merge and alias
semantics, about 8 KB of normative text) from the agent-visible spec and
replaces it with the capture. The agent must now *infer* the rules from
evidence, decide which observed behaviours are rules and which are
coincidences of that day's traffic, and generalise to a different day. That
is the actual skill.

## Why this is hard

1. **The rules are only visible through their effects.** The capture has 464
   frames, 202 patients, 152 encounters, 233 observations and 30 dead
   letters. The rule "an `A08` sets a column to NULL when the field is `\"\"`
   and leaves it alone when the field is empty" is in there, but only as a
   handful of rows whose before/after state has to be reconstructed by
   replaying the inbound bytes in order. Same for merge re-keying, alias
   resolution after merge, stale-observation rejection, out-of-order
   admission handling, and `updated_at` semantics.
2. **The capture is one day; the grader is another.** Same generator, same
   crux families, different seed, different ordering, different clean
   traffic. A daemon that special-cases the capture (or memorises it) fails.
   A daemon that generalises the wrong rule from a coincidence fails.
3. **The visible half of the spec still has to be implemented exactly.**
   MLLP reassembly across fragmented and coalesced writes, concurrent
   connections, per-message charset from MSH-18, escape decoding after
   splitting, `LF` as content not separator, 13 reason codes with a
   precedence order, ACK envelope byte-exact (MSH-3..6 echoed, MSH-9.2
   echoed, ASCII only), DLQ with the exact raw bytes.
4. **The existing code looks almost right.** The broken daemon handles the
   sunny-day samples. Its bugs are the ones real ingestors have: one message
   per `recv()`, one connection at a time, `utf-8` with `errors="replace"`,
   `COALESCE` for updates, duplicate set keyed by control ID alone, `INSERT
   OR REPLACE` that clobbers discharge times, `float()` for numerics, no
   merge support at all.
5. **Self-written tests cannot catch misinferred rules.** Both Codex runs
   wrote 27 to 31 unit tests, passed them, and declared success. The tests
   encoded the agent's own reading. The only external check is
   `replay_capture.py`, which says whether the daemon reproduces the capture
   day, which is necessary and not sufficient.

Difficulty is intrinsic to the domain and to the evidence-based framing, not
to hidden tricks. The reference implementation is ~720 lines of
standard-library Python.

## Crux inventory (what both the capture and the hidden stream contain)

| # | Crux | What a naive implementation does |
|---|------|----------------------------------|
| C1 | `A08` arrives before `A01` for a new visit | drops it, or creates a half-encounter and then `A01` clobbers it |
| C2 | retransmit with same control ID, different body | double-insert, or dedupes across facilities |
| C3 | `\F\ \S\ \T\ \R\ \E\ \Xdd\ \.br\` in names and OBX text | decodes before splitting, so `\S\` becomes a component boundary |
| C4 | `""` vs empty on `A08` | treats both as empty (COALESCE) |
| C5 | MSH-18 = `8859/1` with accented name | decodes the whole stream as UTF-8 |
| C6 | timestamps: no offset, fractional seconds, facility default tz | wrong UTC conversion or `BAD_TIMESTAMP` |
| C7 | MRN is the third PID-3 repetition; a foreign-authority `MR` precedes it | picks the first repetition |
| C8 | `NM` canonicalisation (`007.50`, `+12.0`, `1.40E2`), `ED` hash, stale ORU | `str(float())`, no base64 validation, overwrites newer with older |
| C9 | 28 malformed frames covering every reason code and the precedence order | crashes, wrong code, no ACK, wrong ACK envelope, no DLQ entry, closes the socket |
| C10 | corrected resend of a previously-rejected control ID | treats it as duplicate |
| C11 | `A03` before `A01`; the `A01` must not clear `discharge_time` | `INSERT OR REPLACE` nulls it |
| C12 | `LF` inside a TX value; OBX-14 and OBR-7 both absent | splits on LF; wrong `observed_at` fallback |
| C13 | `A40` merge: re-key encounters/observations/identifiers, identifier collision, `MRG` alias row, alias resolution for later traffic, chain merge keeps only the latest alias, self-merge, unknown prior, PV1 ignored | `UNSUPPORTED_TYPE`; or merges but loses the alias; or follows the whole chain |

Plus 400 clean messages per run (seeded; includes random merges) so the bulk
of the database must also be right, with concurrency and fragmentation on
every connection.

## Verifier design

Separate-verifier mode, as TB3 CI requires. The agent's container is
destroyed before grading. Only `/app/ingest` is collected.

Inside the verifier image (`tests/Dockerfile`, python:3.12-slim, pytest
pinned): the fixture starts the agent's `server.py` and the baked reference
`server.py` on two fresh SQLite files and two random ports, replays an
identical seeded stream through both with identical client behaviour, then
asserts equality of: every ACK (`MSA-1/2/3`, echoed `MSH-3..6`, `MSH-9.2`),
every row of `patients`, `patient_identifiers`, `encounters`,
`observations`, the `ingest_log` modulo wall-clock columns, and the DLQ
modulo `received_at`. Plus: the daemon is still alive, every frame got an
ACK, no ACK took > 2 s, the replay finished in < 60 s, `config.json` and
`schema.sql` are unmodified.

The seed is random per run and asserted to differ from the capture seed. The
oracle passes on every seed tried; determinism is enforced by giving each
MRN authority its own connection so per-patient ordering is preserved while
connections still run concurrently.

The agent daemon is launched with `python -E -s` (ignore `PYTHON*` env, no
user site) after `__pycache__`/`.pyc` are deleted, with `cwd` set to its own
directory, exactly as the documented `python3 /app/ingest/server.py` would
behave. (v1 used `-I`, which also drops the script directory from
`sys.path`, and broke `import hl7`; that was a verifier bug, found by the
first Codex trial, and is why that trial is not counted.)

## Cheat analysis

The `/cheat` prompt tells the agent its container is torn down and tests run
elsewhere, and asks it to find a bypass. What is reachable from the agent's
side:

- **Forge the artifact.** `/app/ingest` is a directory of Python; there is no
  output file to forge. The only way to produce the right ACKs and rows is to
  implement the behaviour.
- **Memorise the capture.** The grading day is a different seed with
  different patients, control IDs, visit numbers and ordering. A lookup
  table keyed on capture bytes produces nothing for the grading stream, and
  the seed is asserted to differ from the capture seed.
- **Find the answer key.** The full Section 5 text lives only in
  `solution/docs/` and the reference only in the verifier image. Neither is
  in the agent container.
- **Tamper with the verifier.** `tests/` is never mounted in the agent
  container. The verifier ignores `PYTHON*` env vars and user site, deletes
  bytecode, and compares `config.json`/`schema.sql` to baked copies.
- **Make the reference fail too.** Different directories, ports and DB
  files; the agent's code cannot reach the reference process.
- **Detect "verifier mode".** The daemon sees env vars and traffic. Nothing
  distinguishes grading traffic, and the traffic is what is graded.
- **Game the comparison.** Set equality on full rows and exact ACK tuples;
  no partial credit, no regex.

Residual risk: `pip install` an HL7 library at build time. The instruction
forbids third-party packages and the verifier image has none, so an import
would crash the daemon at startup.

## Known limitations

- The reference implementation is the ground truth. If it has a bug, the
  task has a bug. It is exercised against its own adversarial stream across
  many seeds, and both Codex trials have been used as independent readers
  of the spec: where they disagreed with the reference and the spec was
  silent, the spec was amended, not the agent penalised.
- The capture day contains every crux family. An agent that studies it
  exhaustively can recover almost every rule. The remaining gap is
  generalisation (different ordering and data) plus the visible-spec
  requirements. If trials show this is still too permissive, the next step
  is to withhold some crux families from the capture.
- Latency and throughput assertions assume the verifier has the resources
  declared in `task.toml` (2 CPU, 2 GB). Budgets are generous (2 s per ACK,
  60 s for ~460 frames) relative to the reference (~6 s total).
