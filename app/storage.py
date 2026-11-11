"""Small storage boundary shared by Firestore and the explicit local memory mode."""

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from google.api_core.exceptions import GoogleAPICallError, NotFound, RetryError
from google.api_core.retry import Retry
from google.cloud import firestore

STATUSES = ("Open", "Working", "Resolved")
LIST_LIMIT = 100
RETRY = Retry(initial=0.1, maximum=1.0, multiplier=2.0, timeout=5.0)


class StorageError(Exception):
    def __init__(self, operation):
        self.operation = operation
        super().__init__(operation)


class RequestMissing(Exception):
    pass


@dataclass(frozen=True)
class RoomRequest:
    id: str
    room: str
    title: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime


class MemoryStore:
    """Development only. State is deliberately lost when the process exits."""

    def __init__(self):
        self._items = {}
        self._lock = Lock()

    def list_requests(self):
        with self._lock:
            return sorted(self._items.values(), key=lambda item: item.created_at, reverse=True)[:LIST_LIMIT]

    def create_request(self, room, title, description):
        now = datetime.now(timezone.utc)
        item = RoomRequest(uuid4().hex, room, title, description, "Open", now, now)
        with self._lock:
            self._items[item.id] = item
        return item.id

    def update_status(self, request_id, status):
        with self._lock:
            if request_id not in self._items:
                raise RequestMissing()
            self._items[request_id] = replace(
                self._items[request_id], status=status, updated_at=datetime.now(timezone.utc)
            )


class FirestoreStore:
    def __init__(self, project, collection="requests", client=None):
        self.client = client or firestore.Client(project=project)
        self.collection = self.client.collection(collection)

    def list_requests(self):
        try:
            snapshots = (
                self.collection.order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(LIST_LIMIT)
                .stream(retry=RETRY, timeout=5)
            )
            result = []
            for snapshot in snapshots:
                data = snapshot.to_dict()
                if (
                    not isinstance(data, dict)
                    or any(not isinstance(data.get(key), str) for key in ("room", "title", "description"))
                    or data.get("status") not in STATUSES
                    or not isinstance(data.get("created_at"), datetime)
                ):
                    raise StorageError("read_invalid_record")
                result.append(RoomRequest(
                    snapshot.id, data["room"], data["title"], data["description"],
                    data["status"], data["created_at"], data.get("updated_at", data["created_at"]),
                ))
            return result
        except (GoogleAPICallError, RetryError) as exc:
            raise StorageError("list") from exc

    def create_request(self, room, title, description):
        request_id = uuid4().hex
        try:
            self.collection.document(request_id).create(
                {
                    "room": room,
                    "title": title,
                    "description": description,
                    "status": "Open",
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                },
                retry=RETRY,
                timeout=5,
            )
            return request_id
        except (GoogleAPICallError, RetryError) as exc:
            raise StorageError("create") from exc

    def update_status(self, request_id, status):
        try:
            # update requires an existing document, so a stale form cannot create one.
            self.collection.document(request_id).update(
                {"status": status, "updated_at": firestore.SERVER_TIMESTAMP},
                retry=RETRY,
                timeout=5,
            )
        except NotFound as exc:
            raise RequestMissing() from exc
        except (GoogleAPICallError, RetryError) as exc:
            raise StorageError("update") from exc
