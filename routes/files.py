import os
import shutil

from flask import jsonify, request, send_file

from app import app

UPLOAD_DIR = "/var/storage/uploads"
ALLOWED_EXTS = {"png", "jpg", "jpeg", "gif", "pdf", "txt", "doc", "docx", "zip"}


def _ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def _has_allowed_extension(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext in ALLOWED_EXTS


@app.route("/api/files/upload", methods=["POST"])
def upload_file():
    _ensure_upload_dir()

    if "file" not in request.files:
        return jsonify({"error": "no file part"}), 400

    f = request.files["file"]
    filename = request.form.get("name") or f.filename
    user_id = request.form.get("user_id")

    if not _has_allowed_extension(filename):
        return jsonify({"error": "extension not allowed"}), 400

    save_path = os.path.join(UPLOAD_DIR, filename)
    f.save(save_path)

    return jsonify({
        "ok": True,
        "filename": filename,
        "size": os.path.getsize(save_path),
        "uploaded_by": user_id,
    })


@app.route("/api/files/download")
def download_file():
    filename = request.args.get("name", "")
    if not filename:
        return jsonify({"error": "missing name"}), 400

    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        return jsonify({"error": "not found"}), 404

    return send_file(path)


@app.route("/api/files/list")
def list_files():
    if not os.path.exists(UPLOAD_DIR):
        return jsonify({"files": []})

    files = []
    for name in os.listdir(UPLOAD_DIR):
        full = os.path.join(UPLOAD_DIR, name)
        if os.path.isfile(full):
            files.append({"name": name, "size": os.path.getsize(full)})
    return jsonify({"files": files})


@app.route("/api/files/delete", methods=["POST"])
def delete_file():
    data = request.get_json() or {}
    filename = data.get("filename", "")

    path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
        return jsonify({"ok": True, "deleted": filename})
    return jsonify({"error": "not found"}), 404


@app.route("/api/files/rename", methods=["POST"])
def rename_file():
    data = request.get_json() or {}
    old = data.get("old", "")
    new = data.get("new", "")

    old_path = os.path.join(UPLOAD_DIR, old)
    new_path = os.path.join(UPLOAD_DIR, new)

    if not os.path.exists(old_path):
        return jsonify({"error": "source not found"}), 404
    os.rename(old_path, new_path)
    return jsonify({"ok": True})


@app.route("/api/files/copy", methods=["POST"])
def copy_file():
    data = request.get_json() or {}
    src = data.get("src", "")
    dst = data.get("dst", "")

    src_path = os.path.join(UPLOAD_DIR, src)
    dst_path = os.path.join(UPLOAD_DIR, dst)

    if not os.path.exists(src_path):
        return jsonify({"error": "source not found"}), 404
    shutil.copy(src_path, dst_path)
    return jsonify({"ok": True})
