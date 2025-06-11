import adafruit_dht as dht
import RPi.GPIO as GPIO

import time
import board



pin = dht.DHT22(board.D4)
counter = 1;

while True:
   
    try:
        humidity = pin.humidity
        temperature = pin.temperature
        print('Temp = {0:0.1f}*C Humidity = {0:0.1f}%'.format(temperature, humidity))
        
        time.sleep(1)
        
        

    except RuntimeError as error:
        print(f"Something is wrong: {error}")
        time.sleep(3)
                     
