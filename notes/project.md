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

Delivery owner is John Spears Jr. His Week 2 work is to package and test the app in a container. Initial cloud access allows him to find the project and view its access policy. Publishing permissions will be arranged with Security when the registry and publishing account are ready.

Application owner is Brady Schow.

Platform owner is Brayden Grant. His Week 2 setup permissions allow enabling cloud services and creating or configuring the container registry and database. They do not include application data access, billing administration or deployment.

Everyone can read this public repository. GitHub collaborators can push changes after accepting an invitation. Paul has Security setup permissions. Brady has initial project discovery and access policy viewing permissions for his local Week 2 application work. Additional permissions are arranged for each role as its cloud work begins. Keep personal account details in the private team workspace.

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


Delivery: Artifact Registry Docker repository address is us-central1-docker.pkg.dev/roomready-team-261030/roomready.

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
