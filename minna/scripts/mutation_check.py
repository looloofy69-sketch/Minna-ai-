#!/usr/bin/env python3
"""Mutation check for the safety-critical branches of core/.

Each mutant is ONE exact-once textual change to a source file. Outcome per mutant:
  KILLED    builds, and at least one test fails      (the tests protect this branch)
  SURVIVED  builds, and every test still passes      (a test gap: fix it, do not ignore it)
  INVALID   does not compile                          (not counted in the score)
Exit status 1 if the baseline is not green or any mutant survived.

usage: mutation_check.py <core_dir> [--jobs N] [--only NAME[,NAME...]]
Uses scripts/sandbox_build_and_test.sh, so it needs the offline toolchain described there.
"""
import concurrent.futures as cf
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "sandbox_build_and_test.sh")
RT = "com/hicham/llmchat/runtime/"

# (name, file under src/main/kotlin/<RT>, exact old text, new text)
MUTANTS = [
    ("replay_guard_removed", "AgentRuntime.kt",
     'EffectReservation.REPLAY_BLOCKED -> return run.copy(status = RunStatus.FAILED, denialReason = "Effect replay blocked; reconciliation required").also(store::saveRun)',
     "EffectReservation.REPLAY_BLOCKED -> Unit"),
    ("consumed_approval_executes", "AgentRuntime.kt",
     'ApprovalConsumption.NOT_PENDING -> run.copy(status = RunStatus.FAILED, denialReason = "Approval already consumed").also(store::saveRun)',
     "ApprovalConsumption.NOT_PENDING -> execute(run.activation, action, currentPlan, run)"),
    ("policy_deny_executes", "AgentRuntime.kt",
     'PolicyDecision.DENY -> Run(activation = request, status = RunStatus.DENIED, action = action, denialReason = "Policy denied Action").also(store::saveRun)',
     "PolicyDecision.DENY -> execute(request, action, action.plan(request.input))"),
    ("denied_approval_executes", "AgentRuntime.kt",
     "if (decision == ApprovalDecision.DENIED) {", "if (false) {"),
    ("approved_plan_drift_unchecked", "AgentRuntime.kt",
     "if (fingerprint(context.requesterIdentity, action, currentPlan) != context.fingerprint || currentPlan != ActionPlan(context.plannedInvocations)) {",
     "if (false) {"),
    ("scope_escalation_unchecked", "AgentRuntime.kt",
     "if (!descriptor.scope.containsAll(spec.scope)) throw", "if (false) throw"),
    ("failed_effect_not_marked_unknown", "AgentRuntime.kt",
     "store.markEffectUnknown(invocation.effectId)", "Unit"),
    ("blank_identity_allowed", "PolicyEngine.kt",
     "if (request.identity.isBlank()) return PolicyDecision.DENY", "if (false) return PolicyDecision.DENY"),
    ("egress_https_unchecked", "EgressPolicy.kt",
     'if (uri.scheme?.lowercase() != "https") {', "if (false) {"),
    ("egress_embedded_credentials_unchecked", "EgressPolicy.kt",
     "if (uri.userInfo != null) {", "if (false) {"),
    ("egress_host_allowlist_unchecked", "EgressPolicy.kt",
     "if (host !in normalizedHosts) {", "if (false) {"),
    ("egress_data_class_unchecked", "EgressPolicy.kt",
     "if (disallowedDataClasses.isNotEmpty()) {", "if (false) {"),
]


def build(project_dir):
    p = subprocess.run(["bash", BUILD, project_dir], capture_output=True, text=True)
    lines = [l for l in p.stdout.splitlines() if l.startswith("RESULT")]
    return lines[-1] if lines else "RESULT NO_OUTPUT " + p.stderr[-200:]


def classify(result):
    m = re.search(r"main_errors=(\d+) test_errors=(\d+) run=(.*)", result)
    if not m:
        return "ERROR"
    main_e, test_e, run = int(m.group(1)), int(m.group(2)), m.group(3).strip()
    if main_e or test_e:
        return "INVALID"
    if "Failures:" in run:
        return "KILLED"
    if run.startswith("OK"):
        return "SURVIVED"
    return "ERROR"


def failing_tests(tmp):
    try:
        text = open(os.path.join(tmp, "out", "run.log"), encoding="utf-8").read()
    except OSError:
        return []
    return re.findall(r"^\d+\) (\S+)\(", text, re.M)


def work_copy(core_dir):
    tmp = tempfile.mkdtemp(prefix="mut-")
    shutil.copytree(os.path.join(core_dir, "src"), os.path.join(tmp, "src"))
    return tmp


def run_mutant(core_dir, mutant):
    name, fname, old, new = mutant
    tmp = work_copy(core_dir)
    try:
        path = os.path.join(tmp, "src", "main", "kotlin", RT, fname)
        text = open(path, encoding="utf-8").read()
        if text.count(old) != 1:
            return name, "ERROR", f"pattern found {text.count(old)}x (need exactly 1)", []
        open(path, "w", encoding="utf-8").write(text.replace(old, new))
        result = build(tmp)
        return name, classify(result), result, failing_tests(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    core_dir = os.path.abspath(args[0])
    jobs, only = 3, None
    if "--jobs" in args:
        jobs = int(args[args.index("--jobs") + 1])
    if "--only" in args:
        only = set(args[args.index("--only") + 1].split(","))
    mutants = [m for m in MUTANTS if only is None or m[0] in only]

    t0 = time.time()
    tmp = work_copy(core_dir)
    try:
        base = build(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("BASELINE:", base)
    if not re.search(r"main_errors=0 test_errors=0 run=OK", base):
        print("baseline is not green; mutation results would be meaningless")
        sys.exit(1)

    with cf.ThreadPoolExecutor(max_workers=jobs) as pool:
        results = list(pool.map(lambda m: run_mutant(core_dir, m), mutants))

    width = max(len(r[0]) for r in results)
    for name, status, detail, tests in results:
        extra = (" <- " + ", ".join(tests[:3])) if tests else (" " + detail if status in ("ERROR", "INVALID") else "")
        print(f"{name:<{width}}  {status:<8}{extra}")
    killed = sum(r[1] == "KILLED" for r in results)
    survived = sum(r[1] == "SURVIVED" for r in results)
    other = len(results) - killed - survived
    score = killed / (killed + survived) if killed + survived else float("nan")
    print(f"killed={killed} survived={survived} invalid_or_error={other}  mutation_score={score:.0%}  elapsed={time.time()-t0:.0f}s")
    sys.exit(1 if survived or other else 0)


if __name__ == "__main__":
    main()
