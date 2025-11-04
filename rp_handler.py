import runpod
import os
import base64
import tempfile
from paddleocr import PaddleOCRVL
from PIL import Image
import io

# --- 1. Model Singleton Initialization ---
# Load the PaddleOCRVL model pipeline globally.
# This ensures the model is loaded only ONCE when the worker starts,
# not on every single request. This is critical for performance.
# Sources: [9, 13, 37]
try:
    print("Initializing PaddleOCRVL pipeline...")
    # For PaddleOCR-VL, it auto-detects 109 languages 
    OCR_PIPELINE = PaddleOCRVL()
    print("PaddleOCRVL pipeline initialized successfully.")
except Exception as e:
    print(f"Error initializing PaddleOCRVL pipeline: {e}")
    # If the model fails to load, set it to None to handle errors gracefully
    OCR_PIPELINE = None

# --- 2. The Serverless Handler Function ---
# This function is the entrypoint for all jobs sent to the endpoint 
def handler(job):
    """
    Process an incoming job containing a base64-encoded image for OCR.
    """
    if OCR_PIPELINE is None:
        return {"error": "Model pipeline failed to initialize."}

    job_input = job.get('input', {})
    image_b64 = job_input.get('image_base64')

    if not image_b64:
        return {"error": "No 'image_base64' key found in input."}

    # --- 3. Base64 to Temporary File ---
    # PaddleOCR-VL's predict() method expects a file path , not raw bytes.
    # We must decode the base64 string and write it to a temporary file.
    # Sources: [36, 39, 40]
    try:
        # Decode the base64 string
        img_data = base64.b64decode(image_b64)
        
        # Create a named temporary file
        # Using a suffix helps paddleocr identify the file type
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_f:
            temp_f.write(img_data)
            img_path = temp_f.name
    
    except Exception as e:
        print(f"Failed to decode or save base64 image: {e}")
        return {"error": f"Failed to decode or save base64 image: {e}"}

    # --- 4. Run Inference ---
    try:
        print(f"Running prediction on temporary file: {img_path}")
        # Run the prediction
        output = OCR_PIPELINE.predict(img_path)
        
        # The 'output' from predict() is a list of result objects.
        # We need to format this into a JSON-serializable response.
        # The 'res' object has methods and attributes 
        
        results_list =
        if output:
            for res in output:
                # 'prunedResult' and 'markdown' are JSON-serializable
                results_list.append({
                    "markdown": res.markdown['text'],
                    "layout": res.prunedResult 
                })
        
        print(f"Prediction successful. Found {len(results_list)} results.")
        return {"status": "success", "results": results_list}

    except Exception as e:
        print(f"Error during model prediction: {e}")
        return {"error": f"Model prediction failed: {e}"}

    finally:
        # --- 5. Cleanup ---
        # Always ensure the temporary file is deleted
        if 'img_path' in locals() and os.path.exists(img_path):
            os.remove(img_path)
            print(f"Cleaned up temporary file: {img_path}")

# --- 6. Start the RunPod Worker ---
# This line starts the worker process and registers the 'handler' function
# as the job processor [12, 23]
if __name__ == "__main__":
    print("Starting RunPod serverless worker...")
    runpod.serverless.start({"handler": handler})
