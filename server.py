"""
Flask web server for the PA Theorem Prover.

Routes
------
GET  /            → serve index.html
POST /api/run     → execute a command, return new facts + full fact list
POST /api/reset   → clear the session
GET  /api/facts   → return the current fact list
"""
from __future__ import annotations
import os
import sys
import threading
import webbrowser

from flask import Flask, request, jsonify, send_from_directory

sys.path.insert(0, os.path.dirname(__file__))

from theorem_prover.commands import fact_list, reset_session, rewrite_options, record_prop
from theorem_prover.display import display_prop
from theorem_prover.parser import parse_and_run
from theorem_prover.errors import InvalidCommand, InvalidInput, TypeMismatch
from theorem_prover.types import Eq

app = Flask(__name__, static_folder="static", template_folder="templates")


def _facts_payload():
    return [{"id": i + 1, "prop": display_prop(p)} for i, p in enumerate(fact_list)]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory("templates", "index.html")


@app.route("/api/run", methods=["POST"])
def run_command():
    data = request.get_json(silent=True) or {}
    command = data.get("command", "").strip()
    if not command:
        return jsonify({"ok": False, "error": "Empty command", "error_type": "empty"})

    n_before = len(fact_list)
    try:
        parse_and_run(command)
    except InvalidCommand as e:
        return jsonify({"ok": False, "error": str(e), "error_type": "unknown_command"})
    except InvalidInput as e:
        return jsonify({"ok": False, "error": str(e), "error_type": "invalid_input"})
    except TypeMismatch as e:
        return jsonify({"ok": False, "error": str(e), "error_type": "type_mismatch"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "error_type": "error"})

    new_facts = [display_prop(p) for p in fact_list[n_before:]]
    return jsonify({"ok": True, "new_facts": new_facts, "facts": _facts_payload()})


@app.route("/api/reset", methods=["POST"])
def reset():
    reset_session()
    return jsonify({"ok": True, "facts": []})


@app.route("/api/facts", methods=["GET"])
def get_facts():
    return jsonify({"facts": _facts_payload()})


@app.route("/api/rewrite-options", methods=["POST"])
def rewrite_options_route():
    data = request.get_json(silent=True) or {}
    eq_id     = data.get("eq_id")
    target_id = data.get("target_id")

    if not isinstance(eq_id, int) or not isinstance(target_id, int):
        return jsonify({"ok": False, "error": "eq_id and target_id must be integers"})
    if eq_id < 1 or eq_id > len(fact_list):
        return jsonify({"ok": False, "error": f"Fact #{eq_id} does not exist"})
    if target_id < 1 or target_id > len(fact_list):
        return jsonify({"ok": False, "error": f"Fact #{target_id} does not exist"})

    f_a = fact_list[eq_id - 1]
    f_b = fact_list[target_id - 1]

    # Auto-detect which fact is the Eq — try eq_id first, then swap.
    if isinstance(f_a, Eq):
        eq, target = f_a, f_b
        actual_eq_id, actual_target_id = eq_id, target_id
    elif isinstance(f_b, Eq):
        eq, target = f_b, f_a
        actual_eq_id, actual_target_id = target_id, eq_id
    else:
        return jsonify({"ok": False, "error": "Neither selected fact is an equality (Eq)"})

    try:
        options = rewrite_options(eq, target)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

    if not options:
        return jsonify({"ok": False, "error": "No rewrites possible"})

    return jsonify({
        "ok": True,
        "options": [display_prop(p) for p in options],
        "eq_id": actual_eq_id,
        "target_id": actual_target_id,
    })


@app.route("/api/rewrite-apply", methods=["POST"])
def rewrite_apply():
    data = request.get_json(silent=True) or {}
    eq_id      = data.get("eq_id")
    target_id  = data.get("target_id")
    option_idx = data.get("option_idx")

    for name, val in [("eq_id", eq_id), ("target_id", target_id), ("option_idx", option_idx)]:
        if not isinstance(val, int):
            return jsonify({"ok": False, "error": f"{name} must be an integer"})

    if eq_id < 1 or eq_id > len(fact_list):
        return jsonify({"ok": False, "error": f"Fact #{eq_id} does not exist"})
    if target_id < 1 or target_id > len(fact_list):
        return jsonify({"ok": False, "error": f"Fact #{target_id} does not exist"})

    f_eq     = fact_list[eq_id - 1]
    f_target = fact_list[target_id - 1]

    if not isinstance(f_eq, Eq):
        return jsonify({"ok": False, "error": f"Fact #{eq_id} is not an equality (Eq)"})

    try:
        options = rewrite_options(f_eq, f_target)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

    if option_idx < 0 or option_idx >= len(options):
        return jsonify({"ok": False,
                        "error": f"option_idx {option_idx} out of range (0–{len(options) - 1})"})

    n_before = len(fact_list)
    record_prop(options[option_idx])
    new_facts = [display_prop(p) for p in fact_list[n_before:]]
    return jsonify({"ok": True, "new_facts": new_facts, "facts": _facts_payload()})


# ---------------------------------------------------------------------------
# Server entry point
# ---------------------------------------------------------------------------

def run_server(host: str = "127.0.0.1", port: int = 5050, open_browser: bool = True):
    url = f"http://{host}:{port}"
    if open_browser:
        def _open():
            import time
            time.sleep(0.6)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()
    print(f"PA Theorem Prover  →  {url}")
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    run_server()
