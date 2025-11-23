import os
import json
import secrets
from uuid import uuid4
from flask import Flask, request, render_template, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
from roboflow import Roboflow

# ----- CONFIG -----
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'static', 'uploads')
DATA_FOLDER = os.path.join(PROJECT_ROOT, 'data')
DETECTIONS_FILE = os.path.join(DATA_FOLDER, 'detections.json')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder='static', template_folder='templates')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['SECRET_KEY'] = secrets.token_hex(16)

# ----- Roboflow model (keeps same as your original) -----
# Keep your real API key here (or move to environment variable for production)
rf = Roboflow(api_key="1D1BZOcqQ1qJRJ91jvfn")
project = rf.workspace("banana-yrnos").project("banana-ripeness-detection-lbydz")
model = project.version(2).model

# ----- Helpers for simple JSON "database" -----
def read_detections():
    if not os.path.exists(DETECTIONS_FILE):
        return []
    try:
        with open(DETECTIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def write_detections(detections):
    with open(DETECTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(detections, f, indent=2, ensure_ascii=False)

def add_detection_record(ripe, unripe, overripe, image_path):
    detections = read_detections()
    record = {
        "id": str(uuid4()),
        "timestamp": __import__('datetime').datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "ripe": int(ripe),
        "unripe": int(unripe),
        "overripe": int(overripe),
        "image_path": image_path
    }
    detections.insert(0, record)  # newest first
    write_detections(detections)
    return record

def delete_detection_record(record_id):
    detections = read_detections()
    updated = []
    removed = None
    for r in detections:
        if r.get("id") == record_id:
            removed = r
        else:
            updated.append(r)
    if removed:
        # try delete image file
        try:
            if removed.get("image_path") and os.path.exists(removed["image_path"]):
                os.remove(removed["image_path"])
        except Exception:
            pass
        write_detections(updated)
        return True
    return False

# ----- Utilities -----
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# ----- Routes -----
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    if 'image' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        # use unique file name to avoid collisions
        unique_name = f"{uuid4().hex}_{original_filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(filepath)

        # Run Roboflow prediction
        try:
            prediction = model.predict(filepath).json()
        except Exception as e:
            # remove saved file if prediction fails
            try:
                os.remove(filepath)
            except Exception:
                pass
            return jsonify({"error": f"Prediction failed: {str(e)}"}), 500

        try:
            # Roboflow response format varies; handle missing fields safely
            preds_outer = prediction.get('predictions') or []
            # If model returns objects directly, `predictions` might be the list of boxes.
            if not preds_outer:
                # no detections
                add_detection_record(0, 0, 0, filepath)
                return jsonify({
                    "prediction": "No banana detected",
                    "confidence": 0,
                    "image_url": filepath
                })

            # Some Roboflow responses are nested (as in your original code). We'll handle both.
            first = preds_outer[0]
            # if nested structure (prediction['predictions'][0]['predictions'])
            inner_list = first.get('predictions') if isinstance(first, dict) and first.get('predictions') else preds_outer
            if not inner_list:
                add_detection_record(0, 0, 0, filepath)
                return jsonify({
                    "prediction": "No banana detected",
                    "confidence": 0,
                    "image_url": filepath
                })

            top = inner_list[0]
            predicted_class = (top.get('class') or '').lower()
            confidence = top.get('confidence', 0)

            # Initialize counts
            counts = {'ripe': 0, 'unripe': 0, 'overripe': 0}
            if predicted_class in counts:
                counts[predicted_class] = 1

            # store record (file-backed)
            add_detection_record(counts['ripe'], counts['unripe'], counts['overripe'], filepath)

            return jsonify({
                "prediction": predicted_class.capitalize() if predicted_class else "Unknown",
                "confidence": confidence,
                "image_url": filepath
            })

        except Exception as e:
            return jsonify({"error": f"Prediction parsing error: {str(e)}"}), 500

    return jsonify({"error": "Invalid file format"}), 400

@app.route('/history')
def history():
    detections = read_detections()
    return render_template('history.html', detections=detections)

@app.route('/delete/<record_id>', methods=['POST'])
def delete_record(record_id):
    if delete_detection_record(record_id):
        return redirect(url_for('history'))
    else:
        return "Error deleting record", 500

# ----- Run -----
if __name__ == '__main__':
    app.run(debug=True)
