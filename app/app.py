import os

from flask import (
    Flask,
    abort,
    redirect,
    render_template_string,
    request,
    url_for,
)

app = Flask(__name__)

# Temporary storage: restarting the app clears this list.
room_requests = []

STATUSES = ["Open", "Working", "Resolved"]
RELEASE_LABEL = "local"

PAGE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>RoomReady</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 850px;
            margin: 2rem auto;
            padding: 0 1rem;
            color: #222;
        }
        label {
            display: block;
            margin-top: 1rem;
            font-weight: bold;
        }
        input, textarea, select, button {
            box-sizing: border-box;
            font: inherit;
            margin-top: .35rem;
            padding: .6rem;
        }
        input, textarea {
            width: 100%;
        }
        textarea {
            min-height: 100px;
        }
        article {
            border: 1px solid #ccc;
            border-radius: 6px;
            margin: 1rem 0;
            padding: 1rem;
        }
        .notice {
            background: #f1f5f9;
            padding: .75rem;
        }
        .error {
            color: #a00;
        }
        .release {
            color: #555;
        }
    </style>
</head>
<body>
    <header>
        <h1>RoomReady</h1>
        <p class="release">Release: {{ release_label }}</p>
    </header>

    <p class="notice">
        Temporary version: requests clear when the app restarts.
    </p>

    {% if error %}
        <p class="error" role="alert">{{ error }}</p>
    {% endif %}

    <h2>Report an equipment problem</h2>
    <form method="post" action="{{ url_for('create_request') }}">
        <label for="room">Room number</label>
        <input id="room" name="room" type="text"
               placeholder="Demo 204" maxlength="40" required>

        <label for="title">Request title</label>
        <input id="title" name="title" type="text"
               placeholder="Projector will not turn on"
               maxlength="100" required>

        <label for="description">Request description</label>
        <textarea id="description" name="description"
                  placeholder="Describe the equipment problem"
                  maxlength="1000" required></textarea>

        <button type="submit">Submit request</button>
    </form>

    <h2>Requests</h2>

    {% for item in room_requests %}
        <article>
            <h3>{{ item.title }}</h3>
            <p><strong>Room:</strong> {{ item.room }}</p>
            <p>{{ item.description }}</p>

            <form method="post"
                  action="{{ url_for('update_status', request_id=item.id) }}">
                <label for="status-{{ item.id }}">Status</label>
                <select id="status-{{ item.id }}" name="status">
                    {% for status in statuses %}
                        <option value="{{ status }}"
                            {% if item.status == status %}selected{% endif %}>
                            {{ status }}
                        </option>
                    {% endfor %}
                </select>
                <button type="submit">Save status</button>
            </form>
        </article>
    {% else %}
        <p>No requests yet.</p>
    {% endfor %}
</body>
</html>
"""


def show_page(error=None, status_code=200):
    page = render_template_string(
        PAGE,
        room_requests=room_requests,
        statuses=STATUSES,
        release_label=RELEASE_LABEL,
        error=error,
    )
    return page, status_code


@app.get("/")
def home():
    return show_page()


@app.post("/requests")
def create_request():
    room = request.form.get("room", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    if not room or not title or not description:
        return show_page(
            "Please fill in the room, title, and description.",
            400,
        )

    room_requests.append({
        "id": len(room_requests) + 1,
        "room": room,
        "title": title,
        "description": description,
        "status": "Open",
    })

    return redirect(url_for("home"))


@app.post("/requests/<int:request_id>/status")
def update_status(request_id):
    new_status = request.form.get("status", "")

    if new_status not in STATUSES:
        return show_page("Please choose a listed status.", 400)

    for item in room_requests:
        if item["id"] == request_id:
            item["status"] = new_status
            return redirect(url_for("home"))

    abort(404)


@app.get("/health")
def health():
    return {"status": "ok", "release": RELEASE_LABEL}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
