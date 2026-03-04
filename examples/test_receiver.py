from machine import SoftSPI, Pin
import time
import sys
import os

sys.path.append("./library")
from sx127x import LoRa

try:
    import ujson as json
except ImportError:
    import json

SPI_SCK_PIN = 5  # Pin de reloj SPI (Serial Clock)
SPI_MOSI_PIN = 27  # Pin de datos Master Out Slave In
SPI_MISO_PIN = 19  # Pin de datos Master In Slave Out

LORA_CS_PIN = 18  # Pin Chip Select (CS/NSS)
LORA_RST_PIN = 14  # Pin de Reset del módulo
LORA_DIO0_PIN = 26  # Pin de interrupción DIO0


def get_next_ensayo_number():
    """Encuentra el siguiente número de ensayo disponible."""
    n = 0
    while True:
        filename = f"ensayo_{n}.txt"
        try:
            # Intentar abrir el archivo, si existe continuamos buscando
            with open(filename, "r") as f:
                pass
            n += 1
        except OSError:
            # El archivo no existe, este es el número a usar
            return n


def format_datetime():
    """Formatea la fecha y hora actual en formato ISO-like."""
    t = time.localtime()
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        t[0], t[1], t[2], t[3], t[4], t[5]
    )


def save_packet_data(filename, mensaje, rssi):
    """Guarda los datos del paquete recibido en el archivo JSON."""
    try:
        data = {"fecha": format_datetime(), "mensaje_recibido": mensaje, "rssi": rssi}

        with open(filename, "a") as f:
            f.write(json.dumps(data))
            f.write("\n")

        return True
    except Exception as e:
        print(f"Error al guardar datos: {e}")
        return False


ensayo_num = get_next_ensayo_number()
ensayo_filename = f"ensayo_{ensayo_num}.txt"

# Configurar SPI y LoRa
spi = SoftSPI(
    baudrate=3000000,
    polarity=0,
    phase=0,
    sck=Pin(SPI_SCK_PIN),
    mosi=Pin(SPI_MOSI_PIN),
    miso=Pin(SPI_MISO_PIN),
)
lora = LoRa(spi, cs_pin=LORA_CS_PIN, reset_pin=LORA_RST_PIN, dio0_pin=LORA_DIO0_PIN)

packet_count = 0
error_count = 0
save_error_count = 0

try:
    while True:
        if lora.is_packet_received():
            packet = lora.get_packet(rssi=True, crc_info=True)

            if packet:
                packet_count += 1
                payload = packet["payload"]
                rssi = packet["rssi"]

                print(f"\n[Paquete #{packet_count}]")
                print(f"  Mensaje: {payload}")
                print(f"  RSSI: {rssi} dBm")
                print(f"  Fecha: {format_datetime()}")

                if packet.get("crc_error", False):
                    error_count += 1
                    print("  Estado: ERROR CRC (corrupto)")
                else:
                    print("  Estado: OK")

                if save_packet_data(ensayo_filename, payload, rssi):
                    print(f"  Guardado en: {ensayo_filename} ✓")
                else:
                    save_error_count += 1
                    print("Error al guardar ✗")

        time.sleep(0.1)

except KeyboardInterrupt:
    print(f"\n\n{'=' * 50}")
    print("Recepción detenida")
    print(f"Archivo generado: {ensayo_filename}")
    print(f"Total de paquetes recibidos: {packet_count}")
    print(f"Errores CRC: {error_count}")
    print(f"Errores al guardar: {save_error_count}")
    if packet_count > 0:
        success_rate = ((packet_count - error_count) / packet_count) * 100
        print(f"Tasa de éxito: {success_rate:.1f}%")
    print(f"{'=' * 50}")
