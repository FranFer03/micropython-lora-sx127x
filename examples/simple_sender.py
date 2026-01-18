"""
Simple LoRa Sender Example

This example demonstrates how to send messages using LoRa.
The sender transmits a message every 2 seconds.

Hardware Setup:
- Connect your SX127x module to the microcontroller via SPI
- Adjust the pin numbers according to your hardware configuration

"""

from machine import SoftSPI, Pin
import time
import sys

sys.path.append('./library')
from sx127x import LoRa


# Pines para comunicación SPI con módulo LoRa
SPI_SCK_PIN = 5     # Pin de reloj SPI (Serial Clock)
SPI_MOSI_PIN = 27   # Pin de datos Master Out Slave In
SPI_MISO_PIN = 19   # Pin de datos Master In Slave Out

# Pines específicos del módulo LoRa
LORA_CS_PIN = 18    # Pin Chip Select (CS/NSS)
LORA_RST_PIN = 14   # Pin de Reset del módulo
LORA_DIO0_PIN = 26  # Pin de interrupción DIO0


spi = SoftSPI(baudrate=3000000, polarity=0, phase=0, 
              sck=Pin(SPI_SCK_PIN), mosi=Pin(SPI_MOSI_PIN), miso=Pin(SPI_MISO_PIN))
lora = LoRa(spi, cs_pin=Pin(LORA_CS_PIN), reset_pin=Pin(LORA_RST_PIN), dio0_pin=Pin(LORA_DIO0_PIN))


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
