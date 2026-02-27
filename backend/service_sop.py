import json
import os


def handle_get_sop_content(handler, user: dict) -> bool:
    try:
        sop_path = os.path.join(os.getcwd(), "data", "SOP.md")
        if os.path.exists(sop_path):
            with open(sop_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = ""
        handler.send_json(200, {"content": content})
        return True
    except Exception as e:
        handler.send_json(500, {"error": str(e)})
        return True


def handle_set_sop_content(handler, user: dict) -> bool:
    try:
        sop_path = os.path.join(os.getcwd(), "data", "SOP.md")
        content_length = int(handler.headers.get("Content-Length", "0") or "0")
        post_data = handler.rfile.read(content_length)
        data = json.loads(post_data.decode("utf-8"))
        new_content = data.get("content")
        os.makedirs(os.path.dirname(sop_path), exist_ok=True)
        with open(sop_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        handler.send_json(200, {"status": "success"})
        return True
    except Exception as e:
        handler.send_json(500, {"error": str(e)})
        return True
