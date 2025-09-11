# app.py - Flask App with IoT + JSON predict
import os, json, time, joblib
import paho.mqtt.client as mqtt
import pandas as pd
from pathlib import Path
from flask import Flask, render_template, request, jsonify

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
# Zone model
# -----------------------------
MODEL_DIR_ZONE = Path("model_out_zone")
MODEL_PIPELINE_PATH_ZONE = MODEL_DIR_ZONE / "model_pipeline_zone.pkl"
METADATA_PATH_ZONE = MODEL_DIR_ZONE / "metadata_zone.json"

zone_model = joblib.load(MODEL_PIPELINE_PATH_ZONE)
metadata_zone = load_metadata(METADATA_PATH_ZONE)

# -----------------------------
# MQTT Config
# -----------------------------
MQTT_HOST = "192.168.1.50"  # Change to your broker IP
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

# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def index():
    # Prepare features metadata for sliders
    features = []
    if metadata_zone:
        for col, stats in metadata_zone.get("feature_example_values", {}).items():
            if "min" in stats and "max" in stats:
                features.append({
                    "name": col,
                    "type": "numeric",
                    "min_r": stats["min"],
                    "max_r": stats["max"],
                    "mean_r": stats["mean"],
                })
            else:
                features.append({
                    "name": col,
                    "type": "categorical",
                    "options": stats.get("unique", [])
                })
    return render_template("index.html", features=features)

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json(force=True)
    try:
        # Construct row from incoming JSON
        row = pd.DataFrame([data])
        probability = float(zone_model.predict_proba(row)[0][1])
        label = "RED" if probability > 0.7 else "YELLOW" if probability > 0.3 else "GREEN"
        if label == "RED":
            message = "🚨 High risk! Immediate evacuation required!"
        elif label == "YELLOW":
            message = "⚠ Warning: Potential landslide risk."
        else:
            message = "✅ Safe conditions."
        publish_alert(data.get("zone","Zone-1"), label, probability, message)
        return jsonify({
            "alert": label,
            "probability": probability,
            "message": message,
            "debug": data
        })
    except Exception as e:
        return jsonify({"error": "prediction failed", "detail": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
