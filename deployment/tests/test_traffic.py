import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import traffic


STABLE = "roomready-00004-td4"
CANDIDATE = "roomready-r544e3ced9f7a-9-1"
PROJECT = "roomready-team-261030"
REGION = "us-central1"


def revision(name):
    return {"metadata": {"name": name, "labels": {"serving.knative.dev/service": "roomready"}},
            "status": {"conditions": [{"type": "Ready", "status": "True"}]}}


def service(allocation, candidate=CANDIDATE):
    return {"status": {"traffic": [
        *[{"revisionName": name, "percent": percent} for name, percent in allocation.items()],
        {"tag": "candidate", "revisionName": candidate},
        {"tag": "local-candidate", "revisionName": "roomready-local-c927fb70-20261112180201"},
    ]}}


class DispatchValidation(unittest.TestCase):
    def test_only_automatic_events_default_to_candidate(self):
        for event in ("push", "pull_request"):
            self.assertEqual(traffic.select_operation(event, "refs/pull/3/merge", ""), "candidate")
        for selected in ("", "unknown", "split; echo unsafe"):
            with self.subTest(selected=selected), self.assertRaises(ValueError):
                traffic.select_operation("workflow_dispatch", "refs/heads/main", selected)
        for event, ref in (("workflow_dispatch", "refs/heads/other"), ("schedule", "refs/heads/main")):
            with self.subTest(event=event, ref=ref), self.assertRaises(ValueError):
                traffic.select_operation(event, ref, "rollback")

    def test_invalid_inputs_make_no_cloud_calls(self):
        invalid = ("", "LATEST", "candidate", "other-valid", "roomready-", "roomready-Bad",
                   "roomready-one;echo unsafe", "roomready-$(id)", "roomready-one,two=100",
                   "roomready-one\n", "roomready-" + "a" * 60)
        with patch("traffic.gcloud_json") as cloud:
            for operation in ("split", "promote"):
                for bad in invalid:
                    for stable, candidate in ((bad, CANDIDATE), (STABLE, bad)):
                        with self.subTest(operation=operation, stable=stable, candidate=candidate):
                            with self.assertRaises(ValueError):
                                traffic.apply_traffic(operation, stable, candidate, PROJECT, REGION)
            for operation in ("split", "promote"):
                with self.assertRaises(ValueError):
                    traffic.apply_traffic(operation, STABLE, STABLE, PROJECT, REGION)
            with self.assertRaises(ValueError):
                traffic.apply_traffic("unknown", STABLE, CANDIDATE, PROJECT, REGION)
            with self.assertRaises(ValueError):
                traffic.apply_traffic("rollback", "", "", PROJECT, REGION)
            cloud.assert_not_called()

    def test_failure_exercise_and_build_inputs_do_not_mix_with_traffic(self):
        for operation in ("split", "promote", "rollback"):
            with self.assertRaises(ValueError):
                traffic.validate_inputs(operation, STABLE, CANDIDATE, exercise_failed_check=True)
        with self.assertRaises(ValueError):
            traffic.validate_inputs("candidate", STABLE, CANDIDATE)
        with self.assertRaises(ValueError):
            traffic.apply_traffic("candidate", "", "", PROJECT, REGION)
        traffic.validate_inputs("candidate", "", "", exercise_failed_check=True)


class TrafficChanges(unittest.TestCase):
    def run_action(self, operation, before=None, after=None, revisions=None, candidate=CANDIDATE):
        expected = {"split": {STABLE: 50, CANDIDATE: 50}, "promote": {CANDIDATE: 100},
                    "rollback": {STABLE: 100}}[operation]
        answers = revisions if revisions is not None else [revision(STABLE)]
        if revisions is None and operation != "rollback":
            answers.append(revision(CANDIDATE))
        answers = [*answers, before or service({STABLE: 100}), {}, after or service(expected)]
        with patch("traffic.gcloud_json", side_effect=answers) as cloud:
            result = traffic.apply_traffic(operation, STABLE, candidate, PROJECT, REGION)
        return result, [call.args[0] for call in cloud.call_args_list]

    def test_three_exact_allocations_use_only_traffic_update(self):
        for operation, allocation in (("split", f"{STABLE}=50,{CANDIDATE}=50"),
                                      ("promote", f"{CANDIDATE}=100"), ("rollback", f"{STABLE}=100")):
            with self.subTest(operation=operation):
                result, calls = self.run_action(operation)
                updates = [call for call in calls if call[2] != "describe"]
                self.assertEqual(updates, [["run", "services", "update-traffic", "roomready",
                                           f"--project={PROJECT}", f"--region={REGION}",
                                           f"--to-revisions={allocation}"]])
                self.assertEqual(sum(result["traffic"].values()), 100)
                self.assertEqual(result["tags"]["candidate"], CANDIDATE)

    def test_wrong_service_not_ready_or_wrong_name_stops_before_update(self):
        for position in (0, 1):
            for defect in ("service", "ready", "name"):
                records = [revision(STABLE), revision(CANDIDATE)]
                bad = records[position]
                if defect == "service":
                    bad["metadata"]["labels"]["serving.knative.dev/service"] = "another-service"
                elif defect == "ready":
                    bad["status"]["conditions"][0]["status"] = "False"
                else:
                    bad["metadata"]["name"] = "roomready-different"
                with self.subTest(position=position, defect=defect):
                    with patch("traffic.gcloud_json", side_effect=records) as cloud:
                        with self.assertRaises(ValueError):
                            traffic.apply_traffic("split", STABLE, CANDIDATE, PROJECT, REGION)
                        self.assertTrue(all(c.args[0][2] == "describe" for c in cloud.call_args_list))

    def test_missing_revision_stops_before_update(self):
        error = subprocess.CalledProcessError(1, ["gcloud", "run", "revisions", "describe"])
        with patch("traffic.gcloud_json", side_effect=[revision(STABLE), error]) as cloud:
            with self.assertRaises(subprocess.CalledProcessError):
                traffic.apply_traffic("promote", STABLE, CANDIDATE, PROJECT, REGION)
            self.assertEqual(cloud.call_count, 2)

    def test_changed_candidate_tag_blocks_split_and_promotion(self):
        before = service({STABLE: 100}, candidate="roomready-replacement")
        for operation in ("split", "promote"):
            with patch("traffic.gcloud_json", side_effect=[revision(STABLE), revision(CANDIDATE), before]) as cloud:
                with self.assertRaisesRegex(ValueError, "candidate tag changed"):
                    traffic.apply_traffic(operation, STABLE, CANDIDATE, PROJECT, REGION)
                self.assertEqual(cloud.call_count, 3)

    def test_rollback_needs_only_ready_stable_despite_missing_candidate(self):
        before = service({CANDIDATE: 100}, candidate="roomready-replacement")
        after = service({STABLE: 100}, candidate="roomready-replacement")
        for ignored in ("", "roomready-missing", "invalid; ignored"):
            result, calls = self.run_action("rollback", before=before, after=after, candidate=ignored)
            self.assertEqual(result["traffic"], {STABLE: 100})
            self.assertEqual([c[3] for c in calls if c[:3] == ["run", "revisions", "describe"]], [STABLE])

    def test_rollback_rejects_unready_stable(self):
        bad = revision(STABLE)
        bad["status"]["conditions"] = []
        with patch("traffic.gcloud_json", return_value=bad) as cloud:
            with self.assertRaises(ValueError):
                traffic.apply_traffic("rollback", STABLE, "", PROJECT, REGION)
            self.assertEqual(cloud.call_count, 1)

    def test_observed_traffic_and_tags_must_match_after_update(self):
        wrong_traffic = service({STABLE: 100})
        wrong_tags = service({CANDIDATE: 100}, candidate="roomready-replacement")
        for after in (wrong_traffic, wrong_tags):
            with self.subTest(after=after), self.assertRaisesRegex(ValueError, "Observed traffic or tags"):
                self.run_action("promote", after=after)


if __name__ == "__main__":
    unittest.main()
