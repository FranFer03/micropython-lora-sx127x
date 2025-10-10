"""
MicroPython LoRa SX127x Library

A MicroPython library for controlling LoRa SX127x (SX1276/77/78/79) radio modules.
Provides simple interface for long-range wireless communication.

Example:
    from sx127x import LoRa
    from machine import SPI, Pin
    
    spi = SPI(1, baudrate=10000000, polarity=0, phase=0,
              sck=Pin(18), mosi=Pin(23), miso=Pin(19))
    lora = LoRa(spi, cs_pin=5, reset_pin=14, dio0_pin=26)
    
    lora.send("Hello LoRa!")
"""

__version__ = "1.0.0"
__author__ = "FranFer03"
__all__ = ["LoRa"]

from .sx127x import LoRa
