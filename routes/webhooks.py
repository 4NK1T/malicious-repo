import pickle
import xml.etree.ElementTree as ET

import requests as http_client
from flask import jsonify, request

from app import app

REGISTERED = []
INTERNAL_API_KEY = "sk_live_placeholder_for_demo"


@app.route("/api/webhooks/register", methods=["POST"])
def register_webhook():
    data = request.get_json() or {}
    url = data.get("url")
    event = data.get("event")

    if not url or not event:
        return jsonify({"error": "url and event required"}), 400

    REGISTERED.append({"url": url, "event": event})
    return jsonify({"ok": True, "id": len(REGISTERED) - 1})


@app.route("/api/webhooks/test", methods=["POST"])
def test_webhook():
    data = request.get_json() or {}
    url = data.get("url")
    payload = data.get("payload", {})

    try:
        r = http_client.post(url, json=payload, timeout=10)
        return jsonify({"status": r.status_code, "body": r.text[:1000]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/webhooks/proxy")
def proxy_fetch():
    url = request.args.get("url", "")
    if not url:
        return jsonify({"error": "url required"}), 400

    try:
        r = http_client.get(url, timeout=10)
        return jsonify({
            "status": r.status_code,
            "headers": dict(r.headers),
            "body": r.text[:2000],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/webhooks/import-xml", methods=["POST"])
def import_xml_config():
    xml_body = request.data
    try:
        root = ET.fromstring(xml_body)
        config = {}
        for child in root:
            config[child.tag] = child.text
        return jsonify({"imported": config})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/webhooks/replay", methods=["POST"])
def replay_event():
    raw = request.get_data()
    try:
        event = pickle.loads(raw)
        return jsonify({"replayed": True, "event_summary": str(event)[:200]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/webhooks/list")
def list_webhooks():
    return jsonify({"webhooks": REGISTERED})


@app.route("/api/webhooks/<int:wid>/delete", methods=["POST"])
def delete_webhook(wid):
    if 0 <= wid < len(REGISTERED):
        removed = REGISTERED.pop(wid)
        return jsonify({"ok": True, "removed": removed})
    return jsonify({"error": "not found"}), 404


def dispatch(event: str, payload: dict):
    """Internal: fire registered webhooks for an event."""
    for hook in REGISTERED:
        if hook["event"] != event:
            continue
        try:
            http_client.post(
                hook["url"],
                json={
                    "event": event,
                    "payload": payload,
                    "internal_key": INTERNAL_API_KEY,
                },
                timeout=15,
            )
        except Exception:
            pass
