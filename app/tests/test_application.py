import os
import re
import secrets
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from identity import IAP_ISSUER, IAPVerifier
from storage import MemoryStore, StorageError


def csrf(page):
    return re.search(r'name="csrf_token" value="([^"]+)"', page.get_data(as_text=True))[1]


class RequestWorkflow(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {"RELEASE_ID": "test-release"}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        app = create_app()
        self.staff = app.test_client()
        self.other_staff = app.test_client()

    def test_shared_request_and_stable_id(self):
        form = {"room": "Demo 302", "title": "No audio", "description": "The classroom speakers are silent."}
        page = self.staff.get("/")
        self.assertIn(b"Release: test-release", page.data)
        self.assertEqual(self.staff.get("/health").json, {"release": "test-release", "status": "ok"})
        response = self.staff.post("/requests", data={**form, "csrf_token": csrf(page)})
        self.assertEqual(response.status_code, 303)
        shared = self.other_staff.get("/")
        request_id = re.search(r'data-request-id="([a-f0-9]{32})" data-status="Open"', shared.get_data(as_text=True))[1]
        for status in ("Working", "Resolved"):
            response = self.other_staff.post(
                f"/requests/{request_id}/status", data={"status": status, "csrf_token": csrf(shared)}
            )
            self.assertEqual(response.status_code, 303)
            page = self.staff.get("/")
            self.assertIn(f'data-request-id="{request_id}" data-status="{status}"'.encode(), page.data)
            self.assertIn(f"Request ID: {request_id}".encode(), page.data)

    def test_forms_need_the_sending_sessions_token(self):
        token = csrf(self.staff.get("/"))
        for path in ("/requests", "/requests/" + "0" * 32 + "/status"):
            self.assertEqual(self.staff.post(path).status_code, 400)
            self.assertEqual(self.other_staff.post(path, data={"csrf_token": token}).status_code, 400)

    def test_validation_preserves_the_request_list(self):
        token = csrf(self.staff.get("/"))
        response = self.staff.post("/requests", data={"csrf_token": token, "title": "test", "room": " "})
        self.assertEqual(response.status_code, 400)
        response = self.staff.post("/requests/" + "0" * 32 + "/status", data={"csrf_token": token, "status": "Working"})
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"No requests yet", self.staff.get("/").data)

    def test_title_at_100_characters_is_accepted(self):
        title = "T" * 100
        page = self.staff.get("/")
        response = self.staff.post("/requests", data={
            "csrf_token": csrf(page),
            "room": "Demo 302",
            "title": title,
            "description": "Title boundary test.",
        })
        self.assertEqual(response.status_code, 303)
        self.assertIn(title.encode(), self.staff.get("/").data)

    def test_title_over_100_characters_is_rejected_without_adding_request(self):
        page = self.staff.get("/")
        response = self.staff.post("/requests", data={
            "csrf_token": csrf(page),
            "room": "Demo 302",
            "title": "Existing request",
            "description": "This request should remain saved.",
        })
        self.assertEqual(response.status_code, 303)

        page = self.staff.get("/")
        existing_id = re.search(
            r'data-request-id="([a-f0-9]{32})" data-status="Open"',
            page.get_data(as_text=True),
        )[1]

        response = self.staff.post("/requests", data={
            "csrf_token": csrf(page),
            "room": "Demo 303",
            "title": "T" * 101,
            "description": "This title is too long.",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            b"Please keep the title to 100 characters or fewer.",
            response.data,
        )

        page = self.staff.get("/")
        request_ids = re.findall(
            r'data-request-id="([a-f0-9]{32})"',
            page.get_data(as_text=True),
        )
        self.assertEqual(request_ids, [existing_id])
    def test_storage_failure_shows_retry_message_and_preserves_request(self):
        store = MemoryStore()
        with patch("app.MemoryStore", return_value=store):
            test_app = create_app()
        client = test_app.test_client()

        request_id = store.create_request(
            "Demo 302", "No audio", "Saved before the outage."
        )
        store.update_status(request_id, "Working")

        page = client.get("/")
        with patch.object(
            store, "create_request", side_effect=StorageError("create")
        ):
            response = client.post("/requests", data={
                "csrf_token": csrf(page),
                "room": "Demo 303",
                "title": "Another request",
                "description": "This save should fail temporarily.",
            })

        self.assertEqual(response.status_code, 503)
        self.assertIn(
            b"Requests could not be loaded or saved. Please try again shortly.",
            response.data,
        )
        self.assertNotIn(b"StorageError", response.data)

        page = client.get("/")
        request_ids = re.findall(
            r'data-request-id="([a-f0-9]{32})"',
            page.get_data(as_text=True),
        )
        self.assertEqual(request_ids, [request_id])
        self.assertIn(
            f'data-request-id="{request_id}" data-status="Working"'.encode(),
            page.data,
        )
class ProtectedApplication(unittest.TestCase):
    def setUp(self):
        self.audience = "/projects/123456789/locations/us-central1/services/roomready"
        environment = patch.dict(os.environ, {
            "K_SERVICE": "roomready", "GOOGLE_CLOUD_PROJECT": "example-project",
            "IAP_AUDIENCE": self.audience, "SECRET_KEY": secrets.token_hex(32),
            "RELEASE_ID": "test-release",
        }, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        self.key = ec.generate_private_key(ec.SECP256R1())
        jwks = Mock()
        jwks.get_signing_key_from_jwt.return_value.key = self.key.public_key()
        self.store = MemoryStore()
        factories = (
            patch("app.FirestoreStore", return_value=self.store),
            patch("app.IAPVerifier", return_value=IAPVerifier(self.audience, jwks)),
        )
        for factory in factories:
            factory.start()
            self.addCleanup(factory.stop)

    def signed_headers(self, audience):
        now = int(time.time())
        claims = {"iss": IAP_ISSUER, "aud": audience, "iat": now, "exp": now + 600, "sub": "test-staff"}
        assertion = jwt.encode(claims, self.key, algorithm="ES256", headers={"kid": "test-key"})
        return {"X-Goog-IAP-JWT-Assertion": assertion}

    def test_every_route_requires_the_correct_signed_audience(self):
        client = create_app().test_client()
        for path in ("/", "/health"):
            self.assertEqual(client.get(path).status_code, 403)
            self.assertEqual(client.get(path, headers=self.signed_headers("different-service")).status_code, 403)
            self.assertEqual(client.get(path, headers=self.signed_headers(self.audience)).status_code, 200)
        self.assertEqual(client.post("/requests").status_code, 403)

    def test_startup_requires_hosted_settings(self):
        for settings in ({"REQUIRE_IAP": "false"}, {"ROOMREADY_STORAGE": "memory"},
                         {"IAP_AUDIENCE": ""}, {"SECRET_KEY": ""}, {"RELEASE_ID": ""}):
            with self.subTest(settings=tuple(settings)), patch.dict(os.environ, settings):
                with self.assertRaises(ValueError):
                    create_app()

    def test_a_form_survives_a_new_instance(self):
        base = "https://roomready.example"
        headers = {**self.signed_headers(self.audience), "Referer": base + "/"}
        first = create_app().test_client()
        second = create_app().test_client()
        token = csrf(first.get("/", headers=headers, base_url=base))
        cookie = first.get_cookie("session", domain="roomready.example")
        self.assertTrue(cookie.secure)
        second.set_cookie("session", cookie.value, domain="roomready.example")
        response = second.post("/requests", headers=headers, base_url=base, data={
            "csrf_token": token, "title": "No audio", "room": "Demo 302", "description": "Silent speakers."
        })
        self.assertEqual(response.status_code, 303)
        self.assertIn(b"Silent speakers", first.get("/", headers=headers, base_url=base).data)


if __name__ == "__main__":
    unittest.main()
