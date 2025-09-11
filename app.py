# app.py - Updated Flask App with IoT Alerts
import os, json, time, joblib
import paho.mqtt.client as mqtt
from pathlib import Path
from flask import Flask, render_template, request

app = Flask(__name__)

# -----------------------------
# Helper to load metadata safely
# -----------------------------
def load_metadata(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}

# -----------------------------
# Main model
# -----------------------------
MODEL_DIR = Path("model_out")
MODEL_PIPELINE_PATH = MODEL_DIR / "model_pipeline.pkl"
METADATA_PATH = MODEL_DIR / "metadata.json"

model = joblib.load(MODEL_PIPELINE_PATH)

TARGET_COL_MAIN = "Landslide"  # default
if METADATA_PATH.exists():
    metadata = load_metadata(METADATA_PATH)
    if "target_col" in metadata:
        TARGET_COL_MAIN = metadata["target_col"]

# -----------------------------
# Zone model
# -----------------------------
MODEL_DIR_ZONE = Path("model_out_zone")
MODEL_PIPELINE_PATH_ZONE = MODEL_DIR_ZONE / "model_pipeline_zone.pkl"
METADATA_PATH_ZONE = MODEL_DIR_ZONE / "metadata_zone.json"

zone_model = joblib.load(MODEL_PIPELINE_PATH_ZONE)

TARGET_COL_ZONE = "Event_Label"  # default
if METADATA_PATH_ZONE.exists():
    metadata_zone = load_metadata(METADATA_PATH_ZONE)
    if "target_col" in metadata_zone:
        TARGET_COL_ZONE = metadata_zone["target_col"]

# -----------------------------
# MQTT Config
# -----------------------------
MQTT_HOST = "192.168.1.50"  # Change to Raspberry Pi IP
MQTT_PORT = 1883
MQTT_TOPIC_BASE = "mine/alerts/evac"

mqtt_client = mqtt.Client()
try:
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
    print("✅ Connected to MQTT broker")
except Exception as e:
    print("⚠️ MQTT connection failed:", e)

def publish_alert(zone, level, probability, message):
    topic = f"{MQTT_TOPIC_BASE}/{zone}"
    payload = {
        "zone": zone,
        "level": level,
        "probability": float(probability),
        "message": message,
        "ttl": 120,
        "timestamp": int(time.time())
    }
    try:
        mqtt_client.publish(topic, json.dumps(payload), qos=1, retain=False)
        print(f"📡 Alert sent → {payload}")
    except Exception as e:
        print("⚠️ MQTT publish failed:", e)

@app.route("/")
def index():
    return render_template("index.html", prediction=None, probability=None)

@app.route("/predict", methods=["POST"])
def predict():
    data = request.form
    rainfall = float(data.get("rainfall", 0))
    slope = float(data.get("slope_angle", 0))
    saturation = float(data.get("soil_saturation", 0))
    earthquake = float(data.get("earthquake_activity", 0))
    zone = data.get("zone", "Zone-1")

    # Zone-based model prediction
    probability = zone_model.predict_proba([[rainfall, slope, saturation, earthquake]])[0][1]
    label = "RED" if probability > 0.7 else "YELLOW" if probability > 0.3 else "GREEN"

    if label == "RED":
        message = "🚨 High risk! Immediate evacuation required!"
    elif label == "YELLOW":
        message = "⚠ Warning: Potential landslide risk."
    else:
        message = "✅ Safe conditions."

    publish_alert(zone, label, probability, message)
    return render_template("index.html", prediction=label, probability=probability, zone=zone)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
