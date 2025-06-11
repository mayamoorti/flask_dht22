from flask import Flask, jsonify, render_template, request
import board
import adafruit_dht
import time
import digitalio
import csv
import os
from datetime import datetime

app = Flask(__name__)

# === Constants ===
DHT_PIN = board.D4
LED_PIN = board.D17
LOG_FILE = 'log.csv'
TEMP_RANGE = (18, 27)   # °C
HUM_RANGE = (40, 60)    # %
LED_BLINK_COUNT = 10
LED_BLINK_DELAY = 0.3

# === Setup ===
dht_device = adafruit_dht.DHT22(DHT_PIN)

led = digitalio.DigitalInOut(LED_PIN)
led.direction = digitalio.Direction.OUTPUT
led.value = False

# Ensure log file exists
def initialize_log():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'temperature', 'humidity'])

initialize_log()


# === Sensor Reading ===
def read_sensor(max_retries=3):
    for _ in range(max_retries):
        try:
            temperature = dht_device.temperature
            humidity = dht_device.humidity
            if temperature is not None and humidity is not None:
                return temperature, humidity
        except RuntimeError:
            time.sleep(1)
        except Exception as e:
            app.logger.exception("Sensor read exception")
            raise RuntimeError(f"Sensor error: {e}")
    raise RuntimeError("Sensor read failed after retries")


# === LED Blinking ===
def blink_led(times=LED_BLINK_COUNT, delay=LED_BLINK_DELAY):
    for _ in range(times):
        led.value = True
        time.sleep(delay)
        led.value = False
        time.sleep(delay)


# === Routes ===
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/data')
def data():
    try:
        temperature, humidity = read_sensor()
    except RuntimeError as e:
        return jsonify(error=str(e)), 500

    # Blink LED if out of range
    if not (TEMP_RANGE[0] <= temperature <= TEMP_RANGE[1] and HUM_RANGE[0] <= humidity <= HUM_RANGE[1]):
        blink_led()
    else:
        led.value = False

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    temp_rounded = round(temperature, 1)
    hum_rounded = round(humidity, 1)

    # Log the data
    try:
        with open(LOG_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, temp_rounded, hum_rounded])
    except Exception as e:
        app.logger.error(f"Failed to log data: {e}")

    return jsonify(timestamp=timestamp, temperature=temp_rounded, humidity=hum_rounded)


@app.route('/log')
def log():
    try:
        with open(LOG_FILE, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)[::-1]
        return jsonify(rows)
    except Exception as e:
        app.logger.error(f"Log read error: {e}")
        return jsonify(error="Failed to read log."), 500


@app.route('/clear', methods=['POST'])
def clear_log():
    try:
        with open(LOG_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'temperature', 'humidity'])
        return '', 204
    except Exception as e:
        app.logger.error(f"Failed to clear log: {e}")
        return jsonify(error="Failed to clear log."), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
