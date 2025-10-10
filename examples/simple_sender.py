"""
Simple LoRa Sender Example

This example demonstrates how to send messages using LoRa.
The sender transmits a message every 2 seconds.

Hardware Setup:
- Connect your SX127x module to the microcontroller via SPI
- Adjust the pin numbers according to your hardware configuration

"""

from machine import SPI, Pin
import time
import sys

sys.path.append('../library')
from sx127x import LoRa

spi = SPI(1, 
          baudrate=10000000, 
          polarity=0, 
          phase=0,
          sck=Pin(18),
          mosi=Pin(23),
          miso=Pin(19))

print("Initializing LoRa...")
lora = LoRa(spi, cs_pin=5, reset_pin=14, dio0_pin=26)

# Optional: Configure custom parameters
# lora.set_frequency(915E6)      # 915 MHz (Americas) - default
# lora.set_spreading_factor(7)   # SF7 - default
# lora.set_bandwidth(125000)     # 125 kHz - default
# lora.set_tx_power(17)          # 17 dBm - default

print("LoRa Sender Started!")
print("Sending messages every 2 seconds")
print("Press Ctrl+C to stop")

counter = 0

try:
    while True:
        message = f"Hello LoRa #{counter}"
        
        print(f"Sending: {message}")
        lora.send(message)
        print("Sent successfully!")
        
        counter += 1
        
        time.sleep(2)

except KeyboardInterrupt:
    print(f"Transmission stopped. Total messages sent: {counter}")
