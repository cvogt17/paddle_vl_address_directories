# server_api.py
import os
import io
import json
import tempfile
import base64
import runpod
from typing import Optional, List
from PIL import Image

try:
    from paddleocr import PaddleOCRVL
except ImportError as e:
    raise RuntimeError("PaddleOCRVL library not found in base image") from e

# Initialize model once (cold-start)
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

def handler(job):
    inp = job.get("input", {})
    # Support ping for simple test
    if inp.get("ping"):
        return {"pong": True}

    urls: Optional[List[str]] = inp.get("urls")
    b64: Optional[str] = inp.get("file_b64")
    paths: List[str] = []

    if urls:
        import requests
        for u in urls:
            r = requests.get(u, timeout=180)
            if r.status_code != 200:
                return {"error": f"Download failed with status {r.status_code} for URL: {u}"}
            fd, path = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            Image.open(io.BytesIO(r.content)).convert("RGB").save(path)
            paths.append(path)
    elif b64:
        try:
            raw = base64.b64decode(b64)
        except Exception as e:
            return {"error": f"Base64 decode error: {e}"}
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        Image.open(io.BytesIO(raw)).convert("RGB").save(path)
        paths.append(path)
    else:
        return {"error": "Provide input.urls OR input.file_b64"}

    results = []
    for idx, p in enumerate(paths):
        try:
            outs = PIPELINE.predict(p)
            packed = _serialize_outputs(outs)
            packed["index"] = idx
            results.append(packed)
        except Exception as e:
            results.append({"index": idx, "error": f"VL inference error: {e}"})

    return {"count": len(results), "results": results}

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
