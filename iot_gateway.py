
import json
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO

# GPIO Pins for sirens/LEDs per zone
ZONES = {
    "Zone-1": {"siren": 17, "red": 27, "yellow": 22},
    "Zone-2": {"siren": 5, "red": 6, "yellow": 13},
    "Zone-3": {"siren": 19, "red": 26, "yellow": 21},
}

GPIO.setmode(GPIO.BCM)
for z in ZONES.values():
    GPIO.setup(z["siren"], GPIO.OUT)
    GPIO.setup(z["red"], GPIO.OUT)
    GPIO.setup(z["yellow"], GPIO.OUT)

def reset_alerts():
    for z in ZONES.values():
        GPIO.output(z["siren"], GPIO.LOW)
        GPIO.output(z["red"], GPIO.LOW)
        GPIO.output(z["yellow"], GPIO.LOW)

def handle_alert(zone, level):
    pins = ZONES.get(zone)
    if not pins:
        return
    GPIO.output(pins["siren"], GPIO.LOW)
    GPIO.output(pins["red"], GPIO.LOW)
    GPIO.output(pins["yellow"], GPIO.LOW)
    if level == "RED":
        GPIO.output(pins["siren"], GPIO.HIGH)
        GPIO.output(pins["red"], GPIO.HIGH)
    elif level == "YELLOW":
        GPIO.output(pins["yellow"], GPIO.HIGH)

def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())
    zone = data["zone"]
    level = data["level"]
    print(f"📩 Alert for {zone}: {level}")
    handle_alert(zone, level)

client = mqtt.Client()
client.on_message = on_message
client.connect("0.0.0.0", 1883, 60)
client.subscribe("mine/alerts/evac/#")

print("✅ IoT Gateway running — listening for zone alerts...")
client.loop_forever()
