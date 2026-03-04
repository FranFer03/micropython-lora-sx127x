from machine import SoftSPI, Pin
import time
import sys
import os

sys.path.append("./library")
from sx127x import LoRa

COUNTER_FILE = "tx_counter.txt"

SPI_SCK_PIN = 5  # Pin de reloj SPI (Serial Clock)
SPI_MOSI_PIN = 27  # Pin de datos Master Out Slave In
SPI_MISO_PIN = 19  # Pin de datos Master In Slave Out

LORA_CS_PIN = 18  # Pin Chip Select (CS/NSS)
LORA_RST_PIN = 14  # Pin de Reset del módulo
LORA_DIO0_PIN = 26  # Pin de interrupción DIO0


def load_counter():
    try:
        with open(COUNTER_FILE, "r") as f:
            counter = int(f.read().strip())
            print(f"Contador cargado desde archivo: {counter}")
            return counter
    except (OSError, ValueError):
        print("No se encontró archivo de contador, iniciando desde 0")
        return 0


def save_counter(counter):
    try:
        with open(COUNTER_FILE, "w") as f:
            f.write(str(counter))
    except OSError as e:
        print(f"Error al guardar contador: {e}")


spi = SoftSPI(
    baudrate=3000000,
    polarity=0,
    phase=0,
    sck=Pin(SPI_SCK_PIN),
    mosi=Pin(SPI_MOSI_PIN),
    miso=Pin(SPI_MISO_PIN),
)
lora = LoRa(spi, cs_pin=LORA_CS_PIN, reset_pin=LORA_RST_PIN, dio0_pin=LORA_DIO0_PIN)

counter = load_counter()

try:
    while True:
        message = f"Envio #{counter}"

        print(f"\n[{time.time()}] Enviando: {message}")
        lora.send(message)
        print("Enviado exitosamente")

        counter += 1
        save_counter(counter)

        time.sleep(2)

except KeyboardInterrupt:
    print(f"\n\n{'=' * 50}")
    print("Transmisión detenida")
    print(f"Total de envíos realizados en esta sesión: {counter}")
    print(f"Último número de envío: {counter - 1}")
    print(f"Próximo envío será: {counter}")
    print(f"{'=' * 50}")
