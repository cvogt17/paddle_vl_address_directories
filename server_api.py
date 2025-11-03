# server_api.py
import os, io, json, tempfile, base64, asyncio, aiohttp
from typing import Optional, List

# 1) RunPod SDK
import runpod

# 2) Model
from paddleocr import PaddleOCRVL
from PIL import Image

# Load model once at cold start
PIPELINE = PaddleOCRVL(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_layout_detection=False,
)

def _serialize_outputs(outputs):
    results = []
    for i, res in enumerate(outputs):
        outdir = tempfile.mkdtemp(prefix="vl_out_")
        res.save_to_json(save_path=outdir)
        res.save_to_markdown(save_path=outdir)
        item = {"index": i}
        for name in os.listdir(outdir):
            p = os.path.join(outdir, name)
            if name.lower().endswith(".json"):
                item["json"] = json.loads(open(p, "r", encoding="utf-8").read())
            if name.lower().endswith(".md"):
                item["markdown"] = open(p, "r", encoding="utf-8").read()
        results.append(item)
    return {"images_processed": len(results), "results": results}

# 3) The handler that RunPod Jobs will call. `event` = {"input": {...}}
def handler(event):
    inp = (event or {}).get("input", {})
    if inp.get("ping"):
        return {"pong": True}

    urls: Optional[List[str]] = inp.get("urls")
    b64: Optional[str] = inp.get("file_b64")
    paths: List[str] = []

    # Accept either URLs or a base64 image
    if urls:
        # simple synchronous fetch to keep things minimal
        import requests
        for u in urls:
            r = requests.get(u, timeout=180)
            r.raise_for_status()
            fd, path = tempfile.mkstemp(suffix=".png"); os.close(fd)
            Image.open(io.BytesIO(r.content)).convert("RGB").save(path)
            paths.append(path)
    elif b64:
        raw = base64.b64decode(b64)
        fd, path = tempfile.mkstemp(suffix=".png"); os.close(fd)
        Image.open(io.BytesIO(raw)).convert("RGB").save(path)
        paths.append(path)
    else:
        return {"error": "Provide input.urls or input.file_b64 or input.ping"}

    results =
