# Project settings

## Shared workspace

Repository `https://github.com/AmFil/roomready`

Google Cloud project `roomready-team-261030`

Google Cloud project number `386355367659`

Region `us-central1`

This is the team environment. Use it for the team build. The separate rehearsal environment is not part of the team setup.

## People and access

Kameron Moshier owns Coordination and Delivery. As project owner he manages billing and team access and can upload the first container image to the team registry.

Paul Christiansen owns Security. His setup permissions let him manage service accounts, access policies and the form protection secret.

Brayden Grant owns Platform. His setup permissions let him enable cloud services and configure the container registry and Firestore database.

Brady Schow owns Application. He can find the project and view its access policy while building the app.

Carter Pugh owns Verification. He can find the project and view its access policy while checking the app and container.

Everyone can read this public repository. GitHub collaborators can push changes after accepting an invitation. Keep personal account details in the private team workspace.

## Enabled APIs

Cloud Run API (run.googleapis.com)

Artifact Registry API (artifactregistry.googleapis.com)

Firestore API (firestore.googleapis.com)

Secret Manager API (secretmanager.googleapis.com)

Cloud Build API (cloudbuild.googleapis.com)

Status: Verified

## Artifact Registry

Repository Name: roomready

Format: Docker

Location: us-central1

Image Repository Address: us-central1-docker.pkg.dev/roomready-team-261030/roomready

Status: Verified

## Infrastructure Details

Application: Firestore database is (default) in project roomready-team-261030, region us-central1.

Security:
- Project ID: roomready-team-261030 (Project Number: 386355367659, Region: us-central1)
- App Service Account: roomready-app@roomready-team-261030.iam.gserviceaccount.com
- Publishing Service Account: roomready-publisher@roomready-team-261030.iam.gserviceaccount.com
- Denied Test Service Account: roomready-denied-test@roomready-team-261030.iam.gserviceaccount.com
- Form Protection Secret Name: roomready-form-secret (Version: 1, Resource Path: projects/386355367659/secrets/roomready-form-secret/versions/1)

The app account can read and write RoomReady requests in Firestore and read the form protection secret. Use version `1` when connecting the app to the secret.

The publishing account can upload images to the `roomready` registry repository and act as the app account for updates. In Week 3, once the Cloud Run service exists, grant the publishing account Cloud Run Developer on that service.

The denied test account has no project role or access to the app or database. It is used to check that an unapproved account cannot open RoomReady.

Delivery: Artifact Registry Docker repository address is us-central1-docker.pkg.dev/roomready-team-261030/roomready.

## Cloud setup handoff

Coordination linked billing and set the project budget alerts. The project APIs are enabled, the registry and Firestore database are ready, and Security created the three service accounts and the form protection secret listed above.

In Week 3, Delivery will publish the image and Platform will create the Cloud Run service and share its address.

## Spending

The approved team limit is $100 for the whole project. It does not reset each month. Rehearsal spending has a separate authorization.

The project budget tracks gross spending from October 30 2026 with no end date. Email alerts are configured at $10, $25, $50, $75, $90 and $100. A separate $10 monthly Cloud Run spending cap is also configured. It resets monthly and does not cover Firestore, Artifact Registry or other services.

Review costs with Kameron each week and before additional testing. At $75 of reported spending, pause new chargeable work and review the remaining allowance. This leaves room for delayed charges and cleanup. Budget alerts do not guarantee a hard spending cutoff.

The Cloud Run cap can also take time to apply. Neither control guarantees an exact $100 maximum bill across the full project.

When Platform creates Cloud Run, use request based billing, zero minimum instances and no more than two instances. These hosting limits are pending until a service exists. Keep scheduled background workloads out of the baseline.
