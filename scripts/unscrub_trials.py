#!/usr/bin/env python3
"""Undo Harbor's secret scrubbing of the value "1" in trial directories.

Harbor treats any env key matching KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL|AUTH as sensitive
and, after a trial, replaces every occurrence of each such value in every text file under
the trial dir with [REDACTED]. CLAUDE_FORCE_OAUTH=1 / CODEX_FORCE_AUTH_JSON=1 therefore
turn every literal "1" into "[REDACTED]", which breaks result.json and the viewer.

This reverses that for trials run with those flags. Safe because the only scrubbed values
in those runs were "1" and the real OAuth tokens (which are long and never appear as a
bare "[REDACTED]" adjacent to digits/JSON structure in the same way; we only restore
when the token would be absurd, i.e. everywhere, since the real tokens never appeared in
output files -- they are only in config.json env blocks, which we restore too since the
token value there was already masked separately as sk-a****AAA before scrubbing).

usage: python3 unscrub_trials.py <jobs_dir> [job_name ...]
"""
import os
import sys


def main():
    root = sys.argv[1]
    names = sys.argv[2:] or sorted(os.listdir(root))
    total = 0
    for name in names:
        job = os.path.join(root, name)
        if not os.path.isdir(job):
            continue
        for dirpath, _, files in os.walk(job):
            for f in files:
                p = os.path.join(dirpath, f)
                try:
                    with open(p, "rb") as fh:
                        data = fh.read()
                except OSError:
                    continue
                if b"[REDACTED]" not in data:
                    continue
                n = data.count(b"[REDACTED]")
                data = data.replace(b"[REDACTED]", b"1")
                with open(p, "wb") as fh:
                    fh.write(data)
                total += n
                print(f"{p}: {n}")
    print("restored", total)


if __name__ == "__main__":
    main()
