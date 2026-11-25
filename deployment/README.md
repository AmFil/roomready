# RoomReady release controls

Open the RoomReady release workflow in GitHub Actions and choose Run workflow on main.

Choose `candidate` to build and test a new private candidate at zero normal traffic. Leave both revision inputs empty. The deliberate failure option is only for testing this candidate release gate.

For the shared traffic exercise, use the exact revision names from the latest reviewed handoff.

* `split` sends 50 percent to stable and 50 percent to candidate. Supply both revisions.
* `promote` sends 100 percent to candidate. Supply both revisions.
* `rollback` sends 100 percent to the exact stable revision. Only stable is required. The candidate input is ignored so an unavailable candidate cannot block recovery.

Traffic actions use existing revisions. They do not build or deploy images. Split and promotion stop if the candidate tag no longer matches the selected revision. Rollback still requires the selected stable revision to belong to RoomReady and be ready.

Wait for each run to finish and check its traffic summary before starting another action. Pause for the team's observations between split, promotion and rollback. All actions share one workflow concurrency group.

A merge to main can deploy a replacement candidate and move its tag. Refresh the revision, image, protected URL and visible release in the handoff, and complete the readiness check before moving traffic.
