from flask import Flask, jsonify, render_template, request
import board
import adafruit_dht
import time
import digitalio
import csv
import os
from datetime import datetime

app = Flask(__name__)

# Sensor and LED setup
DHT_PIN = board.D4
dht_device = adafruit_dht.DHT22(DHT_PIN)

led = digitalio.DigitalInOut(board.D17)
led.direction = digitalio.Direction.OUTPUT
led.value = False

# Log file path
LOG_FILE = 'log.csv'

# Ensure the log file exists with headers
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'temperature', 'humidity'])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def data():
    temperature = None
    humidity = None

    for _ in range(3):
        try:
            temperature = dht_device.temperature
            humidity = dht_device.humidity
            if temperature is not None and humidity is not None:
                break
        except RuntimeError:
            time.sleep(1)
        except Exception as e:
            return jsonify(error=f"Unexpected error: {e}")

    if temperature is None or humidity is None:
        return jsonify(error="Sensor read error: no valid reading after retries")

    # Flash LED if values are out of range
    temp_ok = 18 <= temperature <= 27
    hum_ok = 40 <= humidity <= 60
    if not (temp_ok and hum_ok):
        for _ in range(10):
            led.value = True
            time.sleep(0.3)
            led.value = False
            time.sleep(0.3)
    else:
        led.value = False

    # Timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Append to log file
    with open(LOG_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, round(temperature, 1), round(humidity, 1)])

    return jsonify(
        timestamp=timestamp,
        temperature=round(temperature, 1),
        humidity=round(humidity, 1)
    )

@app.route('/log')
def log():
    try:
        with open(LOG_FILE, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)[::-1]  # Reverse so newest is on top
            return jsonify(rows)
    except Exception as e:
        return jsonify(error=f"Log read error: {e}")

@app.route('/clear', methods=['POST'])
def clear_log():
    try:
        with open(LOG_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'temperature', 'humidity'])
        return '', 204  # No content
    except Exception as e:
        return jsonify(error=f"Failed to clear log: {e}"), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
