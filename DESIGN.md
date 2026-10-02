# Design: hl7-feed-recovery

A Terminal-Bench 3 task. Built for the Klavis AI founding-engineer take-home,
October 2026. Public from the first commit; see the root README for results.

## The job being simulated

A regional health system upgraded its interface engines. The inbound HL7 v2
ingestion daemon, written years ago against an older contract, now stalls,
drops records and corrupts rows. An integration engineer is handed the current
interface specification and told to make the daemon conform. This is a
billable, weeks-of-pager-duty kind of job: everything the daemon gets wrong
shows up as a missing admission or a wrong lab value on a clinician's screen.

## Why this is hard (and why it is hard for a good reason)

The task is not hard because of hidden tricks. The whole contract is in
`/app/docs/INTERFACE_SPEC.md`, which the agent can read. It is hard because:

1. **The spec is long and every clause is load-bearing.** Nine sections, ~40
   numbered rules, a precedence order for 13 reason codes. The verifier
   compares behaviour byte-for-byte against a reference implementation across
   several hundred messages that collectively exercise every rule. Getting 95%
   of the rules right scores zero.
2. **Several rules contradict a model's prior.** HL7 null (`""`) means
   *delete*, empty means *leave alone*. MSH field numbers are off by one. The
   MRN is not the first PID-3 repetition. Escape decoding must happen *after*
   splitting. `LF` is not a segment separator. Latin-1 messages are decoded
   per message, after reading MSH-18 as ASCII. A model that "knows HL7" from
   training data will confidently do several of these wrong.
3. **The existing code looks almost right.** The broken daemon is ~250 lines
   of plausible code that handles the sunny-day samples. Its bugs are the
   bugs real ingestors have: one message per `recv()`, one connection at a
   time, `utf-8` with `errors="replace"`, `COALESCE` for updates, in-memory
   duplicate set keyed by control ID alone, `INSERT OR REPLACE` that clobbers
   discharge times, `float()` for numerics. An agent that patches symptoms
   instead of rewriting against the spec will leave most of them in place.
4. **The agent cannot see the grading stream.** It has three sample messages
   and a sender. To be confident it must build its own adversarial corpus
   from the spec, which is exactly what a careful human would do, and
   exactly what agents tend to skip once their own tests pass.
5. **Concurrency and framing interact with correctness.** The verifier sends
   over several connections at once, with frames fragmented into 1–7 byte
   writes and coalesced 2–4 per write. A daemon that is correct but
   single-threaded will time out ACKs; one that is concurrent but shares a
   SQLite connection without a lock will corrupt the ingest log.

Difficulty is intrinsic to the domain, not manufactured. The reference
implementation is ~450 lines of standard-library Python; an expert who has
done this before needs roughly six hours.

## Crux inventory (what the hidden stream contains)

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
| C9 | 27 malformed frames covering every reason code and the precedence order | crashes, wrong code, no ACK, no DLQ entry, closes the socket |
| C10 | corrected resend of a previously-rejected control ID | treats it as duplicate |
| C11 | `A03` before `A01`; the `A01` must not clear `discharge_time` | `INSERT OR REPLACE` nulls it |
| C12 | `LF` inside a TX value; OBX-14 and OBR-7 both absent | splits on LF; wrong `observed_at` fallback |

Plus 400 clean messages per run (seeded) so that the bulk of the database
must also be right, and concurrency/fragmentation on every connection.

## Verifier design

Separate-verifier mode, as TB3 CI requires. The agent's container is
destroyed before grading. Only `/app/ingest` is collected.

Inside the verifier image (`tests/Dockerfile`, python:3.12-slim, pytest
pinned): the test fixture starts the agent's `server.py` and the baked
reference `server.py` on two fresh SQLite files and two random ports, replays
an identical seeded stream through both with identical client behaviour, then
asserts equality of: every ACK (`MSA-1`, `MSA-2`, `MSA-3`), every row of
`patients`, `patient_identifiers`, `encounters`, `observations`, the
`ingest_log` modulo wall-clock columns, and the DLQ modulo `received_at`.
Plus: the daemon is still alive, every frame got an ACK, no ACK took > 2 s,
the whole replay finished in < 60 s, `config.json` and `schema.sql` are
unmodified.

The seed is random per run unless `HL7_VERIFY_SEED` is set. The oracle passes
on every seed tried; determinism is enforced by giving each MRN authority
its own connection so per-patient ordering is preserved while connections
still run concurrently.

## Cheat analysis

The `/cheat` prompt tells the agent its container is torn down and tests run
elsewhere, and asks it to find a bypass. What is reachable from the agent's
side:

- **Forge the artifact.** `/app/ingest` is a directory of Python; there is no
  output file to forge. The only way to produce the right ACKs and rows is to
  implement the spec.
- **Find the answer key.** There is none in the environment. The hidden stream
  is generated at verify time from a seed chosen at verify time. The
  reference implementation lives only in the verifier image.
- **Tamper with the verifier.** `tests/` is never mounted in the agent
  container. The verifier runs `server.py` with `python -I` (isolated:
  ignores `PYTHONPATH`, user site, and the script's directory is not added
  to `sys.path` for imports other than the explicit insert in server.py),
  deletes `__pycache__` and `.pyc` before starting, and compares
  `config.json`/`schema.sql` to baked copies.
- **Make the reference fail too.** The agent daemon and the reference run
  from different directories on different ports with different DB files;
  the agent's code cannot reach the reference process.
- **Detect "verifier mode" and behave differently.** The agent daemon sees
  only env vars (`HL7_PORT`, `HL7_DB`, `HL7_DLQ`, `HL7_CONFIG`) and
  traffic. There is no signal that distinguishes grading traffic from any
  other traffic, and the traffic itself is the thing being graded.
- **Game the comparison.** The comparison is set equality on full rows and
  exact ACK tuples; there is no partial credit, no regex, no "contains".

Residual risk: an agent could `pip install` an HL7 library at build time.
The spec and instruction forbid third-party packages, and the verifier
image has none installed, so an import would crash the daemon at startup.

## Known limitations

- The reference implementation is the ground truth. If it has a bug, the
  task has a bug. It has been exercised against its own adversarial stream
  across many seeds, but it is one person's reading of the spec it defines.
- Latency and throughput assertions assume the verifier has the resources
  declared in `task.toml` (2 CPU, 2 GB). The budgets are generous (2 s per
  ACK, 60 s for ~450 frames) relative to the reference (~6 s total).
