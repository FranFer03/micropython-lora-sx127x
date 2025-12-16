"""
Simple LoRa Receiver Example

This example demonstrates how to receive messages using LoRa.
The receiver continuously listens for incoming packets and displays them.

Hardware Setup:
- Connect your SX127x module to the microcontroller via SPI
- Adjust the pin numbers according to your hardware configuration

"""

from machine import SoftSPI, Pin
import time
import sys

sys.path.append('./library')
from sx127x import LoRa


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

print("LoRa Receiver Started!")
print("Listening for messages...")
print("Press Ctrl+C to stop")

packet_count = 0
error_count = 0

try:
    while True:
        if lora.is_packet_received():
            packet = lora.get_packet(rssi=True, crc_info=True)
            
            if packet:
                packet_count += 1
                
                print(f"\nPacket #{packet_count} received:")
                print(f"  Message: {packet['payload']}")
                print(f"  RSSI: {packet['rssi']} dBm")
                
                # Check CRC status
                if packet.get('crc_error', False):
                    error_count += 1
                    print("Status: CRC ERROR (corrupted)")
                else:
                    print("Status: OK")
        
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print("Reception stopped")
    print(f"Total packets received: {packet_count}")
    print(f"CRC errors: {error_count}")
    if packet_count > 0:
        success_rate = ((packet_count - error_count) / packet_count) * 100
        print(f"Success rate: {success_rate:.1f}%")
