# Project settings

## Shared workspace

Repository `https://github.com/AmFil/roomready`

Google Cloud project `roomready-team-261030`

Region `us-central1`

This is the team environment. Use it for the team build. The separate rehearsal environment is not part of the team setup.

## People and access

Coordination and billing contact is Kameron Moshier.

Application, Platform, Security, Delivery and Verification owners are waiting for the team to choose. The cloud setup operator will be recorded once that role is chosen.

Everyone can read this public repository. GitHub collaborators can push changes after accepting an invitation. Cloud permissions will be granted to each confirmed Google account for its assigned work. Keep personal account details in the private team workspace.

## Cloud setup handoff

Coordination creates the cloud project, links billing and sets the total project budget alerts.

Platform enables the application services and creates Artifact Registry and Firestore. Security sets up service accounts, permissions and the application secret. Record the resource names here as they are created.

The Cloud Run service, Artifact Registry repository, Firestore database, service accounts, secret name and application address are pending.

## Spending

The approved team limit is $100 for the whole project. It does not reset each month. Rehearsal spending has a separate authorization.

Review costs with Kameron each week and before additional testing. At $75 of reported spending, pause new chargeable work and review the remaining allowance. This leaves room for delayed charges and cleanup. Budget alerts do not guarantee a hard spending cutoff.

When Platform creates Cloud Run, use request based billing, zero minimum instances and no more than two instances. These hosting limits are pending until a service exists. Keep scheduled background workloads out of the baseline.
