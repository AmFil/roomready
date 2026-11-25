"""Validate and apply RoomReady traffic changes to existing revisions."""

import argparse
import json
import os
import re
import subprocess
import sys


SERVICE = "roomready"
OPERATIONS = {"candidate", "split", "promote", "rollback"}


def validate_inputs(operation, stable, candidate, exercise_failed_check=False):
    if operation not in OPERATIONS:
        raise ValueError("Choose candidate, split, promote or rollback.")
    if operation == "candidate":
        if stable or candidate:
            raise ValueError("Leave both revision inputs empty when building a candidate.")
        return
    if exercise_failed_check:
        raise ValueError("The deliberate failure option is only for a candidate release.")
    names = (stable,) if operation == "rollback" else (stable, candidate)
    for name in names:
        if len(name) > 63 or not re.fullmatch(r"roomready-[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", name):
            raise ValueError("Supply the exact RoomReady revision names required for this operation.")
    if operation != "rollback" and stable == candidate:
        raise ValueError("Stable and candidate must be different revisions.")


def select_operation(event, ref, selected):
    if event in {"push", "pull_request"}:
        return "candidate"
    if event != "workflow_dispatch" or ref != "refs/heads/main":
        raise ValueError("Manual release actions must run on main.")
    if selected not in OPERATIONS:
        raise ValueError("A manual run needs an explicit valid operation.")
    return selected


def gcloud_json(arguments):
    result = subprocess.run(
        ["gcloud", *arguments, "--format=json", "--quiet"],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout or "{}")


def traffic_percentages(service):
    result = {}
    for target in service.get("status", {}).get("traffic", []):
        percent = target.get("percent", 0)
        if percent:
            name = target["revisionName"]
            result[name] = result.get(name, 0) + percent
    return result


def traffic_tags(service):
    return {target["tag"]: target["revisionName"]
            for target in service.get("status", {}).get("traffic", []) if target.get("tag")}


def apply_traffic(operation, stable, candidate, project, region):
    validate_inputs(operation, stable, candidate)
    if operation == "candidate":
        raise ValueError("The existing release job builds candidates.")
    if not project or not region:
        raise ValueError("The project and region must be configured.")
    target = [f"--project={project}", f"--region={region}"]
    names = (stable,) if operation == "rollback" else (stable, candidate)
    for name in names:
        revision = gcloud_json(["run", "revisions", "describe", name, *target])
        metadata = revision.get("metadata", {})
        belongs = metadata.get("labels", {}).get("serving.knative.dev/service") == SERVICE
        ready = any(c.get("type") == "Ready" and c.get("status") == "True"
                    for c in revision.get("status", {}).get("conditions", []))
        if metadata.get("name") != name or not belongs or not ready:
            raise ValueError(f"Revision {name} must belong to {SERVICE} and be ready.")
    before = gcloud_json(["run", "services", "describe", SERVICE, *target])
    tags = traffic_tags(before)
    if operation != "rollback" and tags.get("candidate") != candidate:
        raise ValueError("The candidate tag changed. Refresh the handoff and readiness check first.")
    expected = {"split": {stable: 50, candidate: 50},
                "promote": {candidate: 100}, "rollback": {stable: 100}}[operation]
    allocation = ",".join(f"{name}={percent}" for name, percent in expected.items())
    gcloud_json(["run", "services", "update-traffic", SERVICE, *target,
                 f"--to-revisions={allocation}"])
    after = gcloud_json(["run", "services", "describe", SERVICE, *target])
    if traffic_percentages(after) != expected or traffic_tags(after) != tags:
        raise ValueError("Observed traffic or tags do not match. Stop and inspect the service before continuing.")
    return {"operation": operation, "project": project, "region": region,
            "service": SERVICE, "traffic": expected, "tags": tags}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    operation = select_operation(os.getenv("GITHUB_EVENT_NAME", ""),
                                 os.getenv("GITHUB_REF", ""), os.getenv("OPERATION", ""))
    stable = os.getenv("STABLE_REVISION", "")
    candidate = os.getenv("CANDIDATE_REVISION", "")
    validate_inputs(operation, stable, candidate,
                    os.getenv("EXERCISE_FAILED_CHECK", "false").lower() == "true")
    if args.validate_only:
        if os.getenv("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as output:
                output.write(f"operation={operation}\n")
        print(f"Validated operation {operation}.")
        return
    result = apply_traffic(operation, stable, candidate,
                           os.getenv("GCP_PROJECT_ID", ""), os.getenv("GCP_REGION", ""))
    print(json.dumps(result, indent=2))
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
            summary.write(f"Completed {operation} for {SERVICE}.\n\n")
            for name, percent in result["traffic"].items():
                summary.write(f"* `{name}` receives {percent} percent of normal traffic.\n")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, subprocess.CalledProcessError) as error:
        print(f"Traffic action stopped. {error}", file=sys.stderr)
        sys.exit(1)
