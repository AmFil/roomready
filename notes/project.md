# Project settings

## Shared workspace

Repository `https://github.com/AmFil/roomready`

Google Cloud project `roomready-team-261030`

Google Cloud project number `386355367659`

Region `us-central1`

This is the team environment. Use it for the team build. The separate rehearsal environment is not part of the team setup.

## People and access

Coordination and billing contact is Kameron Moshier.

Verification owner is Carter Pugh.

Security owner is Paul Christiansen. He handles service accounts, project permissions and secrets in the team project. Platform still enables the application APIs. Additional permissions for a specific resource can be arranged when that resource exists.

Application, Platform and Delivery owners are waiting for Brady Schow, Brayden Grant and John Spears Jr to choose.

Everyone can read this public repository. GitHub collaborators can push changes after accepting an invitation. Paul has Security setup permissions. Brady and Brayden have project discovery and access policy viewing permissions while their roles are undecided. Additional cloud access depends on the role each person chooses. Keep personal account details in the private team workspace.

## Cloud setup handoff

Coordination has created the cloud project, linked billing and set the total project budget alerts. No application or storage resources have been deployed yet.

Platform enables the application services and creates Artifact Registry and Firestore. Security sets up service accounts, permissions and the application secret. Record the resource names here as they are created.

The Cloud Run service, Artifact Registry repository, Firestore database, service accounts, secret name and application address are pending.

## Spending

The approved team limit is $100 for the whole project. It does not reset each month. Rehearsal spending has a separate authorization.

The project budget tracks gross spending from October 30 2026 with no end date. Email alerts are configured at $10, $25, $50, $75, $90 and $100. A separate $10 monthly Cloud Run spending cap is also configured. It resets monthly and does not cover Firestore, Artifact Registry or other services.

Review costs with Kameron each week and before additional testing. At $75 of reported spending, pause new chargeable work and review the remaining allowance. This leaves room for delayed charges and cleanup. Budget alerts do not guarantee a hard spending cutoff.

The Cloud Run cap can also take time to apply. Neither control guarantees an exact $100 maximum bill across the full project.

When Platform creates Cloud Run, use request based billing, zero minimum instances and no more than two instances. These hosting limits are pending until a service exists. Keep scheduled background workloads out of the baseline.
