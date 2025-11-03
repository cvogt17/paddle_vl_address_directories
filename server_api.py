import os, io, json, tempfile, base64, asyncio, aiohttp
from typing import Optional, List
from fastapi import FastAPI, File, UploadFile, HTTPException
from PIL import Image

try:
    from paddleocr import PaddleOCRVL
except Exception as e:
    PaddleOCRVL = None
    print("PaddleOCRVL not available:", e)

app = FastAPI(title="PaddleOCR-VL API", description="Serverless OCR on GPU")
pipeline = None

@app.on_event("startup")
def load_model():
    global pipeline
    if PaddleOCRVL is None:
        raise RuntimeError("PaddleOCRVL not found in base image.")
    pipeline = PaddleOCRVL(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_layout_detection=False,
    )

@app.get("/")
def health():
    return {"status": "ok" if pipeline else "initializing", "engine": "PaddleOCR-VL"}

@app.post("/ocr/vl")
async def vl_analyze(file: UploadFile = File(...)):
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Model not initialized")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    img = Image.open(io.BytesIO(data)).convert("RGB")
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    img.save(path)
    try:
        outs = pipeline.predict(path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VL pipeline error: {e}")
    return _serialize_outputs(outs)

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

@app.post("/runpod")
async def runpod_entrypoint(payload: dict):
    """
    RunPod serverless entrypoint
    { "input": { "urls": ["https://..."] } } or { "input": { "file_b64": "..." } }
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Model not initialized")

    inp = payload.get("input", {})
    urls: Optional[List[str]] = inp.get("urls")
    b64: Optional[str] = inp.get("file_b64")
    paths = []

    if urls:
        async with aiohttp.ClientSession() as session:
            async def fetch_one(u):
                async with session.get(u, timeout=180) as r:
                    if r.status != 200:
                        raise HTTPException(status_code=400, detail=f"Download failed {r.status} for {u}")
                    data = await r.read()
                fd, path = tempfile.mkstemp(suffix=".png")
                os.close(fd)
                Image.open(io.BytesIO(data)).convert("RGB").save(path)
                return path
            paths = await asyncio.gather(*[fetch_one(u) for u in urls], return_exceptions=True)
    elif b64:
        raw = base64.b64decode(b64)
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        Image.open(io.BytesIO(raw)).convert("RGB").save(path)
        paths = [path]
    else:
        raise HTTPException(status_code=400, detail="Provide input.urls or input.file_b64")

    results = []
    for idx, p in enumerate(paths if isinstance(paths, list) else [paths]):
        if isinstance(p, Exception):
            results.append({"index": idx, "error": str(p)})
            continue
        try:
            outs = pipeline.predict(p)
            packed = _serialize_outputs(outs)
            packed["index"] = idx
            results.append(packed)
        except Exception as e:
            results.append({"index": idx, "error": f"VL error: {e}"})

    return {"count": len(results), "results": results}
