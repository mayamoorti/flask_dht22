from flask import Flask, jsonify, render_template, request
import board
import adafruit_dht
import time
import digitalio
import csv
import os
from datetime import datetime

# === Flask Setup ===
app = Flask(__name__)

# === Config Constants ===
DHT_PIN = board.D4
LED_PIN = board.D17
LOG_FILE = 'log.csv'
TEMP_RANGE = (18, 27)  # °C
HUM_RANGE = (40, 60)   # %
LED_BLINK_COUNT = 10
LED_BLINK_DELAY = 0.3

# === Hardware Setup ===
def setup_sensor():
    return adafruit_dht.DHT22(DHT_PIN)

def setup_led():
    led_device = digitalio.DigitalInOut(LED_PIN)
    led_device.direction = digitalio.Direction.OUTPUT
    led_device.value = False
    return led_device

# Initialize devices
dht_device = setup_sensor()
led = setup_led()

# === Initialization ===
def initialize_log():
    if not os.path.exists(LOG_FILE):
        write_log_header()

def write_log_header():
    with open(LOG_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'temperature', 'humidity'])

# === Utility Functions ===
def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def read_sensor(max_retries=3):
    for _ in range(max_retries):
        try:
            temperature = dht_device.temperature
            humidity = dht_device.humidity
            if temperature is not None and humidity is not None:
                return round(temperature, 1), round(humidity, 1)
        except RuntimeError:
            time.sleep(1)
        except Exception as e:
            app.logger.exception("Sensor exception")
            raise RuntimeError(f"Sensor read error: {e}")
    raise RuntimeError("Sensor failed after retries")

def blink_led(times=LED_BLINK_COUNT, delay=LED_BLINK_DELAY):
    for _ in range(times):
        led.value = True
        time.sleep(delay)
        led.value = False
        time.sleep(delay)

def is_within_range(value, min_val, max_val):
    return min_val <= value <= max_val

def log_data(timestamp, temperature, humidity):
    try:
        with open(LOG_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, temperature, humidity])
    except Exception as e:
        app.logger.error(f"Log write error: {e}")

def read_log():
    try:
        with open(LOG_FILE, 'r') as f:
            return list(csv.DictReader(f))[::-1]
    except Exception as e:
        app.logger.error(f"Log read error: {e}")
        raise RuntimeError("Failed to read log")

def clear_log():
    try:
        write_log_header()
    except Exception as e:
        app.logger.error(f"Log clear error: {e}")
        raise RuntimeError("Failed to clear log")

# === API Routes ===
@app.route('/')
def serve_ui():
    return render_template('index.html')

@app.route('/api/v1/data', methods=['GET'])
def api_get_data():
    try:
        temperature, humidity = read_sensor()
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 500

    if not is_within_range(temperature, *TEMP_RANGE) or not is_within_range(humidity, *HUM_RANGE):
        blink_led()
    else:
        led.value = False

    timestamp = get_timestamp()
    log_data(timestamp, temperature, humidity)

    return jsonify({
        'timestamp': timestamp,
        'temperature': temperature,
        'humidity': humidity
    }), 200

@app.route('/api/v1/log', methods=['GET'])
def api_get_log():
    try:
        rows = read_log()
        return jsonify(rows), 200
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/clear', methods=['POST'])
def api_clear_log():
    try:
        clear_log()
        return '', 204
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 500

# === Entrypoint ===
def run():
    initialize_log()
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

if __name__ == '__main__':
    run()
