import os
from flask import Flask, request, render_template, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
from roboflow import Roboflow
from flask_mysqldb import MySQL
import secrets

app = Flask(__name__, static_folder='static', template_folder='templates')

# Configuration
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['SECRET_KEY'] = secrets.token_hex(16)

# MySQL Configuration (XAMPP Default)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'banana_ripeness'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

# Initialize Roboflow model
rf = Roboflow(api_key="1D1BZOcqQ1qJRJ91jvfn")
project = rf.workspace("banana-yrnos").project("banana-ripeness-detection-lbydz")
model = project.version(2).model

def init_db():
    """Initialize the database tables"""
    try:
        with mysql.connection.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS detections (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ripe INT DEFAULT 0,
                    unripe INT DEFAULT 0,
                    overripe INT DEFAULT 0,
                    image_path VARCHAR(255)
            ''')
        mysql.connection.commit()
    except Exception as e:
        print(f"Database initialization error: {e}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def add_detection(ripe, unripe, overripe, image_path):
    """Add a new detection record to the database"""
    try:
        with mysql.connection.cursor() as cursor:
            cursor.execute('''
                INSERT INTO detections 
                (ripe, unripe, overripe, image_path) 
                VALUES (%s, %s, %s, %s)
            ''', (ripe, unripe, overripe, image_path))
        mysql.connection.commit()
        return True
    except Exception as e:
        print(f"Insert error: {e}")
        return False

def get_all_detections():
    """Retrieve all detection records from the database"""
    try:
        with mysql.connection.cursor() as cursor:
            cursor.execute('''
                SELECT id, 
                       DATE_FORMAT(timestamp, '%Y-%m-%d %H:%i:%s') as timestamp, 
                       ripe, 
                       unripe, 
                       overripe, 
                       image_path 
                FROM detections 
                ORDER BY timestamp DESC
            ''')
            return cursor.fetchall()
    except Exception as e:
        print(f"Fetch error: {e}")
        return []

def delete_detection(id):
    """Delete a detection record from the database"""
    try:
        # First get the image path
        with mysql.connection.cursor() as cursor:
            cursor.execute('SELECT image_path FROM detections WHERE id = %s', (id,))
            detection = cursor.fetchone()
            
            if detection and detection['image_path']:
                try:
                    os.remove(detection['image_path'])
                except OSError:
                    pass
            
            # Then delete the record
            cursor.execute('DELETE FROM detections WHERE id = %s', (id,))
            mysql.connection.commit()
            return True
    except Exception as e:
        print(f"Delete error: {e}")
        return False

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
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        prediction = model.predict(filepath).json()
        
        try:
            # Check if predictions exist
            if not prediction['predictions'] or not prediction['predictions'][0]['predictions']:
                return jsonify({
                    "prediction": "No banana detected",
                    "confidence": 0,
                    "image_url": filepath
                })
                
            predicted_class = prediction['predictions'][0]['predictions'][0]['class'].lower()
            confidence = prediction['predictions'][0]['predictions'][0]['confidence']
            
            # Initialize counts
            counts = {'ripe': 0, 'unripe': 0, 'overripe': 0}
            if predicted_class in counts:
                counts[predicted_class] = 1
            
            # Store in database only if banana is detected
            add_detection(counts['ripe'], counts['unripe'], counts['overripe'], filepath)
            
            return jsonify({
                "prediction": predicted_class.capitalize(),
                "confidence": confidence,
                "image_url": filepath
            })
            
        except Exception as e:
            return jsonify({"error": f"Prediction error: {str(e)}"}), 500

    return jsonify({"error": "Invalid file format"}), 400

@app.route('/history')
def history():
    detections = get_all_detections()
    return render_template('history.html', detections=detections)

@app.route('/delete/<int:id>', methods=['POST'])
def delete_record(id):
    if delete_detection(id):
        return redirect(url_for('history'))
    else:
        return "Error deleting record", 500

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    with app.app_context():
        init_db()
    app.run(debug=True)