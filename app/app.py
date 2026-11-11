import os
import re
import secrets

from flask import Flask, abort, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFError, CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

from identity import IAPVerifier, IdentityError
from storage import FirestoreStore, MemoryStore, RequestMissing, STATUSES, StorageError


def create_app():
    app = Flask(__name__)
    on_cloud_run = bool(os.environ.get("K_SERVICE"))
    storage_mode = os.environ.get("ROOMREADY_STORAGE", "firestore" if on_cloud_run else "memory")
    iap_setting = os.environ.get("REQUIRE_IAP", "true" if on_cloud_run else "false").lower()
    if storage_mode not in {"memory", "firestore"} or iap_setting not in {"true", "false"}:
        raise ValueError("Check ROOMREADY_STORAGE and REQUIRE_IAP.")
    protected = iap_setting == "true"
    if on_cloud_run and (storage_mode != "firestore" or not protected):
        raise ValueError("Cloud Run requires Firestore storage and IAP.")
    if on_cloud_run and os.environ.get("FIRESTORE_EMULATOR_HOST"):
        raise ValueError("Cloud Run requires the real Firestore database.")

    secret = os.environ.get("SECRET_KEY")
    if not secret and storage_mode == "memory" and not protected:
        # The local form can run without shared settings. Restarting clears its session.
        secret = secrets.token_hex(32)
    if not secret or len(secret.encode()) < 32:
        raise ValueError("Set SECRET_KEY to a stable secret of at least 32 bytes.")
    release = os.environ.get("RELEASE_ID", "" if on_cloud_run else "local")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", release):
        raise ValueError("Set RELEASE_ID to the source version.")
    app.config.update(
        SECRET_KEY=secret,
        MAX_CONTENT_LENGTH=16_384,
        SESSION_COOKIE_SECURE=protected,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if protected:
        audience = os.environ.get("IAP_AUDIENCE", "")
        if not re.fullmatch(r"/projects/\d+/locations/[a-z0-9-]+/services/[a-z0-9-]+", audience):
            raise ValueError("Set IAP_AUDIENCE to the direct Cloud Run service audience.")
        verify = IAPVerifier(audience)
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=0, x_proto=1, x_host=0, x_port=0, x_prefix=0)

        @app.before_request
        def require_signed_identity():
            try:
                verify(request.headers.get("X-Goog-IAP-JWT-Assertion"))
            except IdentityError:
                abort(403)

    # Run identity checks before accepting any form or looking up stored data.
    CSRFProtect(app)
    if storage_mode == "firestore":
        project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        collection = os.environ.get("FIRESTORE_COLLECTION", "requests")
        if not project or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", collection):
            raise ValueError("Check GOOGLE_CLOUD_PROJECT and FIRESTORE_COLLECTION.")
        store = FirestoreStore(project, collection)
    else:
        store = MemoryStore()

    def render_page(error=None, status=200):
        return render_template(
            "index.html", room_requests=store.list_requests(), statuses=STATUSES,
            release_label=release, temporary_storage=(storage_mode == "memory"), error=error,
        ), status

    @app.after_request
    def identify_release(response):
        response.headers["X-RoomReady-Release"] = release
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/")
    def home():
        return render_page()

    @app.post("/requests")
    def create_request():
        values = {field: request.form.get(field, "").strip() for field in ("room", "title", "description")}
        if not all(values.values()):
            return render_page("Please fill in the room, title, and description.", 400)
        for field, maximum in (("room", 40), ("title", 100), ("description", 1000)):
            if len(values[field]) > maximum:
                return render_page(f"Please keep the {field} to {maximum} characters or fewer.", 400)
        store.create_request(**values)
        return redirect(url_for("home"), 303)

    @app.post("/requests/<request_id>/status")
    def update_status(request_id):
        if not re.fullmatch(r"[a-f0-9]{32}", request_id):
            abort(404)
        new_status = request.form.get("status", "")
        if new_status not in STATUSES:
            return render_page("Please choose a listed status.", 400)
        try:
            store.update_status(request_id, new_status)
        except RequestMissing:
            abort(404)
        return redirect(url_for("home"), 303)

    @app.get("/health")
    def health():
        return {"status": "ok", "release": release}

    @app.errorhandler(StorageError)
    def storage_failure(error):
        app.logger.error("Storage operation failed. Operation %s", error.operation)
        return "Requests could not be loaded or saved. Please try again shortly.", 503

    @app.errorhandler(CSRFError)
    def expired_form(_error):
        return "The form is invalid or expired. Reopen the request page and try again.", 400

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")), debug=False)
