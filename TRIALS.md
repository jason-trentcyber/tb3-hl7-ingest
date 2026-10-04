# Trial log

Every Harbor run against this task, in order. Job directories are under
`~/tb3/jobs/` on the build host; `result.json` and `verifier/test-stdout.txt`
in each are the primary evidence. Nothing here is reconstructed from memory.

Harbor 0.23, Docker 29, 4-core / 7.6 GB VPS, one trial at a time.

Model configuration follows the TB3 CI defaults in
`.github/harbor-run-defaults.yml` at the time of the runs (commit #2047,
2026-09-21): `claude-code` / `anthropic/claude-fable-5-1` /
`reasoning_effort=max` / `CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000`, and `codex` /
`openai/gpt-6-astra` / `reasoning_effort=xhigh`. The assignment email names
Opus 5.5 and GPT-6 Sol; see the README for how that discrepancy was handled.

## Task versions

| Version | Commit | What changed |
|---|---|---|
| v1 | `52ec772` | Initial task. Full spec visible. 12 crux groups. |
| v2 | `7032e4a` | Spec 6.5 (recoverable MSH-4/10) added after Codex trial 1 exposed the ambiguity. `ADT^A40` merge + alias resolution (spec 5.7) added. Verifier launches agent daemon with `-E -s` instead of `-I` (verifier bug, see trial 1). |
| v3 | `cdcd1bd` | Spec Section 5 removed from the agent-visible copy; `/app/capture` (recorded day, seed 20260309) shipped instead. `replay_capture.py` tool. Verifier grades the full ACK envelope (MSH-3..6, MSH-9.2), not only MSA. Spec 6.4 clarified. |

## Runs

| # | Date (UTC) | Version | Agent / model | Reward | Wall | Exceptions | Job dir | Genuine? | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 10-02 15:23 | v1 | oracle | 1.000 | 43 s | 0 | `2026-10-02__15-23-08` | n/a | |
| 2 | 10-02 15:23 | v1 | nop | 0.000 | 52 s | 0 | `2026-10-02__15-23-55` | n/a | |
| 3 | 10-02 15:26 | v1 | codex / gpt-6-astra / xhigh | 0.000 | 29m 01s | 0 | `2026-10-02__15-26-09` | **No** | Agent daemon failed to start in the verifier: `ModuleNotFoundError: hl7` because the verifier used `python -I`, which drops the script directory from `sys.path`. Verifier bug. Re-running the collected artifact under the fixed verifier: 8/11 pass; the 3 failures were the spec-6.5 ambiguity (agent read MSH-10 as recoverable on `BAD_CHARSET`/`DECODE_ERROR`; a defensible reading). Not counted. |
| 4 | 10-02 16:12 | v2 | oracle | 1.000 | 36 s | 0 | `2026-10-02__16-12-17` | n/a | |
| 5 | 10-02 16:12 | v2 | nop | 0.000 | 32 s | 0 | `2026-10-02__16-12-56` | n/a | |
| 6 | 10-02 16:13 | v2 | codex / gpt-6-astra / xhigh | 0.000 | 38m 26s | 0 | `2026-10-02__16-13-35` | Yes, but weak | 10/11 pass. Only `encounters` differed, and only in `updated_at` on rows re-keyed by a merge, where the spec was silent. The agent's choice (bump `updated_at`) was reasonable; spec and reference were changed to match it. Under the amended spec the submission passes on every seed tried. Conclusion: with the full spec visible the task is a careful-reading exercise and gpt-6-astra does it. Counted as a v2 failure for the record but treated as a signal that v2 is too easy. |
| 7 | 10-02 17:04 | v3 | oracle | 1.000 | 36 s | 0 | `2026-10-02__17-04-54` | n/a | |
| 8 | 10-02 17:05 | v3 | nop | 0.000 | 32 s | 0 | `2026-10-02__17-05-34` | n/a | |
| 9 | 10-02 17:06 | v3 | codex / gpt-6-astra / xhigh | **1.000** | 21m 25s | 0 | `2026-10-02__17-06-12` | n/a (solved) | 15 commands: read spec, read code, six SQL/Python queries over the capture, one 507-line rewrite of `hl7.py`, replay match, own unittest file (299 lines), BEHAVIOR.md documenting the inferred rules including the chain-merge single-alias behaviour. Collected artifact passes the verifier on 8/8 seeds locally. Rule inference from a complete capture is not hard for this model. |
| 10 | 10-02 17:32 | v3 | claude-code / claude-fable-5-1 / max | **1.000** | 26m 56s | 0 | `2026-10-02__17-32-36` | n/a (solved) | Same shape as Codex: SQL over the capture, rewrite of `hl7.py` (736 lines) and `server.py`, replay match, a self-written restart/edge harness, a PROCESSING.md of inferred rules. Both CI-default models solve v3 in under 30 min. The capture plus the visible spec is a complete definition and a local oracle; rule inference from complete evidence is not where these models fail. |
| 11 | 10-02 22:53 | v4 | oracle | 1.000 | 77 s | 0 | `2026-10-02__22-53-08` | n/a | 23 assertions, 4 phases. |
| 12 | 10-02 22:54 | v4 | nop | 0.000 | 6m 50s | 0 | `2026-10-02__22-54-29` | n/a | Bounded by the 120 s replay deadline per phase. |
| 13 | 10-02 23:01 | v4 | codex / gpt-6-astra / xhigh | **1.000** | 37m 28s | 0 | `2026-10-02__23-01-25` | n/a (solved) | 42 commands. Rewrote the daemon on asyncio: commit per frame under WAL/`synchronous=NORMAL`; a write-ahead sidecar (`errors.jsonl.pending`) so the DLQ append and the SQLite commit are atomic across SIGKILL; 1 MiB cap with split-terminator handling; `call_at` frame timer; backpressure via `pause_reading`. Wrote a 600-line contract test with its own 8-engine load generator and a kill test. Passed all 23 assertions on the first verifier run. The durability, throughput and limit requirements were understood and implemented at a level a senior engineer would sign off on. |
| 14 | 10-03 00:35 | v4 | codex / gpt-6-astra / xhigh | **1.000** | 39m 06s | 0 | `2026-10-03__00-35-13` | n/a (solved) | Second Codex run on v4, same result. (A claude-code run launched in the same chain failed immediately on a wrong kwarg and produced no job directory; see trial 15.) |
| 15 | 10-03 22:46 | v4 | claude-code / claude-fable-5-1 / max | **1.000** | 44m 42s | 0 | `2026-10-03__22-46-14` | n/a (solved) | Both CI-default models solve v4. Four framings (spec reading, inference from capture, HL7 semantics, durability/throughput engineering); every one solved on first attempt by every model that ran it. Common factor: each version handed the agent an enumerable acceptance checklist. See `ANALYSIS.md`. |
| 16 | 10-04 02:53 | v5 `hl7-census-drift` @ `89bcaaf` | codex / gpt-6-astra / xhigh | **0.000** | 17m 59s | 0 | `2026-10-04__02-53-09` | 7/9 passed; **census.csv** and **identity.csv** differ | First genuine failure. 25 commands, 23 self-written regression tests, "Friday's census is now 180, matching the nurses' count". Found 8 of 9 planted defects including all three silent ones (sub-id, cross-site dedup, A08-before-A01). Missed: **A40 merge must leave the prior MRN on the survivor as an `MRG`-type identifier** (it stored it as `MR`; 38 identity rows differ); and on A08-before-A01 it let the late A01 overwrite the location the A08 had already set (4 census rows). Both are "which of two reasonable behaviours did the reporting side assume" questions — exactly the un-enumerable kind. The agent's own final message documents "merge-alias formatting assumptions" as a known unknown. **Judged unfair**: the MRG convention was not discoverable from anything in the container. Documented in INTERFACE_SUMMARY.md and the A08 location rule removed from the generator (`bb08d17`). |
| 17 | 10-04 03:29 | v5 @ `bb08d17` | claude-code / claude-fable-5-1 / max | 0.000 | 22m 50s | **1 `ApiRateLimitError`** | `2026-10-04__03-29-11` | n/a | **Does not count** (infrastructure failure under the brief's rules). Subscription window exhausted mid-run. Re-run pending a fresh window. |
| 18 | 10-04 03:52 | v5 @ `bb08d17` | codex / gpt-6-astra / xhigh | **1.000** | 24m 54s | 0 | `2026-10-04__03-52-03` | n/a (solved) | With the MRG convention documented, astra solved it: 18 commands, 21 regression tests, "Friday's census is now 158, matching the floor's count." Found all nine defects by reading the parser against its own HL7 knowledge; symptoms were confirmation, not discovery. |
| 19 | 10-04 09:49 | v5 @ `bb08d17` | codex / **gpt-6-sol** / xhigh | **0.000** | 26m 34s | 0 | `2026-10-04__09-49-18` | 8/9 passed; **labs.csv** differs (51 rows) | Genuine failure. The model named in the brief. Found all nine planted defects and declared done ("Friday's census is 158, matching the supervisor's count; MRN 416502 is discharged Tuesday"). Stored NM values as sent (`15.0`); the reference canonicalises per the HL7 NM data type (`15`). At step 48 the agent fetched and read the spec text "trailing zeros after a decimal point are not significant… 01.20 and 1.2 are identical" and did not act on it. |
| 20 | 10-04 10:17 | v5 @ `bb08d17` | codex / gpt-6-sol / xhigh | **0.000** | 20m 40s | 0 | `2026-10-04__10-17-24` | 8/9 passed; **labs.csv** differs (50 rows) | Same failure, same cause, independent run. **Judged borderline**: the standard says the representations are equivalent, not which to store; a text comparison punishes a representation choice. Canonical-form rule added to INTERFACE_SUMMARY.md so a careful reader can find it; sol re-run against the documented version follows. |
| 21 | 10-04 10:39 | v5 @ `db856f6` | codex / gpt-6-sol / xhigh | **1.000** | 26m 42s | 0 | `2026-10-04__10-39-23` | n/a (solved) | With the NM canonical-form rule documented, sol solved it. Confirms trials 19–20 failed on the representation gotcha, not on the planted defects. Every Codex model that has run a fully documented version of v5 has solved it. |
| 22 | 10-04 10:56 | v5 @ `db856f6` | claude-code / claude-fable-5-1 / max | **0.000** | 22m 51s | 0 | `2026-10-04__10-56-33` | 7/9 passed; **labs.csv** (3 rows) and **identity.csv** (13–14 rows) differ | **Genuine failure, judged fair.** Found all nine planted defects and both documented conventions; its final message enumerates them correctly and adds a real latent `server.py` crash it also fixed. Lost on **A40 merge semantics**: it deleted the prior patient outright ("deleting the prior patient, and recording the MRG alias"), so the prior record's SSN and PI identifiers vanished from the survivor (identity.csv), and where the survivor already had its own encounters, observations were left pointing at the wrong patient (labs.csv). Neither is a formatting convention: nothing in HL7 or the interface summary says a merged patient's other identifiers disappear, and an engineer asking "what happens to the SSN after the merge?" gets the right answer. This is the first fair failure on v5. |

## Observations so far

- Codex reads the whole spec first, then the code, then writes its own
  unittest suite (27 to 31 tests) and iterates against it. Both runs ended
  with a confident summary ("Validation passed ...") that was wrong about
  the hidden stream. The self-written tests encode the agent's own reading
  of the spec, so they cannot catch misreadings.
- ~600k input tokens per Codex run (88% cached), ~38k output.
- Harbor's artifact scrubber replaces every occurrence of the value of any
  env var whose name matches `KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL|AUTH`
  with `[REDACTED]`. `CODEX_FORCE_AUTH_JSON=1` matches `AUTH`, so every
  literal `1` in the collected Codex artifacts is replaced. The verifier ran
  on the real files inside the container; only the copies under `jobs/` are
  mangled. To re-run a Codex artifact locally, `sed 's/\[REDACTED\]/1/g'`
  restores it (confirmed by re-running under the local harness and
  reproducing the in-container result).
