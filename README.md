# RoomReady

RoomReady is our IT 360 team project. It gives people a simple way to report classroom equipement problems and see what still needs attention

Each request has a room, title and description. The team can recieve requests in one shared list and track them as Open, Working or Resolved

## What we are building

A small Python Flask app with ordinary HTML forms. Docker packages the app for Google Cloud Run. Firestore saves requests, approved Google accounts control access, and GitHub Actions will handle releases.

Use fictional classroom examples. Do not enter personal or sensitive information.

## Where work goes

* `app` holds the application code and its tests.
* `deployment` holds cloud setup notes, configuration and deployment work.
* `notes` holds shared project settings, decisions and handoffs.

Application owns the request workflow. Platform owns cloud resources. Security owns accounts and permissions. Delivery owns packaging and releases. Verification owns testing. Coordination keeps shared setup and handoffs organized.

## Getting started

The repository currently contains the shared workspace. Each role will build its part during the weekly tasks.

Read [project settings](notes/project.md) before creating cloud resources. Send Kameron your GitHub username for editing access and the Google account email you will use for cloud work.

Keep passwords, account keys, real environment files and private logs out of Git. The `.gitignore` covers common filenames. Check the files in each commit before pushing.
