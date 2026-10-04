#!/usr/bin/env python3
"""Condense a Harbor trial into a readable play-by-play: one line per command, the final
agent message, and the verifier's pass/fail list. Works for codex and claude-code trials.

usage: python3 trial_summary.py <trial_dir_or_job_dir> [--full]
"""
import glob
import json
import os
import re
import sys


def find_trial(path):
    if os.path.exists(os.path.join(path, "agent")):
        return path
    hits = sorted(glob.glob(os.path.join(path, "*", "agent")))
    if not hits:
        sys.exit(f"no trial under {path}")
    return os.path.dirname(hits[0])


def steps_from_trajectory(path):
    """trajectory.json is agent-neutral (ATIF)."""
    with open(path) as f:
        tj = json.load(f)
    out = []
    for s in tj.get("steps", []):
        src = s.get("source")
        if src == "agent":
            for tc in s.get("tool_calls", []) or []:
                fn = tc.get("function_name") or tc.get("name") or ""
                args = tc.get("arguments") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {"raw": args}
                cmd = args.get("command") or args.get("cmd") or args.get("file_path") or args.get("path") or ""
                if isinstance(cmd, list):
                    cmd = " ".join(cmd)
                out.append(("tool", fn, str(cmd).replace("\n", " ")[:140]))
            if s.get("message") and not s.get("tool_calls"):
                out.append(("msg", "", s["message"]))
        elif src == "user" and out:
            pass
    return out


def verifier_lines(trial):
    p = os.path.join(trial, "verifier", "test-stdout.txt")
    if not os.path.exists(p):
        return []
    txt = open(p, errors="replace").read()
    res = re.findall(r"^(PASSED|FAILED) (\S+)", txt, re.M)
    if not res:
        res = re.findall(r"(test_\w+(?:\[[^\]]*\])?) (PASSED|FAILED)", txt)
        res = [(b, a) for a, b in res]
    tail = txt.strip().splitlines()[-1] if txt.strip() else ""
    return res, tail


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    full = "--full" in sys.argv
    trial = find_trial(args[0])
    print(f"trial: {trial}")
    r = json.load(open(os.path.join(trial, "result.json")))
    ai = r.get("agent_info") or {}
    mi = ai.get("model_info") or {}
    print(f"agent: {ai.get('name')} / {mi.get('name') or mi.get('model_name')}   reward: {(r.get('verifier_result') or {}).get('rewards')}")
    tj = os.path.join(trial, "agent", "trajectory.json")
    steps = steps_from_trajectory(tj) if os.path.exists(tj) else []
    n = 0
    print("\n== commands ==")
    for kind, fn, body in steps:
        if kind == "tool":
            n += 1
            print(f"{n:3d}. [{fn}] {body}")
    msgs = [b for k, _, b in steps if k == "msg"]
    if msgs:
        print("\n== final agent message ==")
        print(msgs[-1][: (None if full else 2500)])
    vl = verifier_lines(trial)
    if vl:
        res, tail = vl
        print("\n== verifier ==")
        for status, name in res:
            print(f"  {status:6s} {name}")
        print("  " + tail)


if __name__ == "__main__":
    main()
