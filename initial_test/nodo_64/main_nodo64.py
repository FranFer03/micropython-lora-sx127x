"""
LoRa Sensor Sender (DS18B20 + BMP180) - ESP32 MicroPython (Robust)

DS18B20:
  DATA -> GPIO33

BMP180 (I2C):
  SCL -> GPIO22
  SDA -> GPIO32

LoRa (SoftSPI): same as your working example.
"""

from machine import SoftSPI, Pin, I2C
import time
import sys
import gc
import machine
import ujson

# --- LoRa lib ---
sys.path.append('./library')
from sx127x import LoRa

# --- DS18B20 libs ---
import onewire
import ds18x20

# --- BMP180 lib ---
from bmp180 import BMP180


# -----------------------------
# Pinout - LoRa
# -----------------------------
SPI_SCK_PIN   = 5
SPI_MOSI_PIN  = 27
SPI_MISO_PIN  = 19
LORA_CS_PIN   = 18
LORA_RST_PIN  = 14
LORA_DIO0_PIN = 26

# -----------------------------
# Pinout - Sensors
# -----------------------------
DS18B20_DATA_PIN = 33
I2C_SCL_PIN = 22
I2C_SDA_PIN = 32

# -----------------------------
# Config
# -----------------------------
# Si querés fijo:
NODE_ID = "64"


SEND_INTERVAL_S = 10

DS18B20_RETRIES = 3
BMP180_RETRIES  = 3
BMP180_OVERSAMPLE = 3

# Calidad de envío / mantenimiento
GC_EVERY_N_SENDS = 10

# Watchdog (OPCIONAL para campo)
# WDT_TIMEOUT_MS = 15000
# wdt = machine.WDT(timeout=WDT_TIMEOUT_MS)

# LED (OPCIONAL)
# LED_PIN = 2
# led = Pin(LED_PIN, Pin.OUT)
# def blink(n=1, on_ms=60, off_ms=80):
#     for _ in range(n):
#         led.value(1); time.sleep_ms(on_ms)
#         led.value(0); time.sleep_ms(off_ms)


# -----------------------------
# Helpers
# -----------------------------
def valid_ds_temp(t):
    # 85.0 = default after power-up / conversion issue
    # -127.0 = typical error value
    if t is None:
        return False
    if t == 85.0 or t == -127.0:
        return False
    return (-60.0 <= t <= 130.0)


def read_ds18b20(ds, roms, retries=3):
    """
    Returns: (temp_c, rom_hex) or (None, rom_hex/None)
    """
    if not roms:
        return (None, None)

    rom = roms[0]
    rom_hex = rom.hex()

    for _ in range(retries):
        try:
            ds.convert_temp()
            time.sleep_ms(750)
            t = ds.read_temp(rom)
            if valid_ds_temp(t):
                return (float(t), rom_hex)
        except Exception:
            time.sleep_ms(100)

    return (None, rom_hex)


def read_bmp180(bmp, retries=3):
    """
    Returns: (temp_c, pressure_pa) or (None, None)
    """
    if bmp is None:
        return (None, None)

    for _ in range(retries):
        try:
            bmp.blocking_read()
            t = bmp.temperature
            p = bmp.pressure  # Pa (por implementación)
            if p is not None and p > 10000:
                return (float(t), float(p))
        except Exception:
            time.sleep_ms(100)

    return (None, None)


def build_payload(counter, uptime_s, ds_temp, ds_rom, bmp_temp, bmp_pres_pa):
    # JSON manual compacto
    parts = []
    parts.append('"id":"%s"' % NODE_ID)
    parts.append('"n":%d' % counter)
    parts.append('"up":%d' % uptime_s)

    parts.append('"ds_t":%s' % ("null" if ds_temp is None else ("%.2f" % ds_temp)))
    parts.append('"ds_rom":%s' % ("null" if ds_rom is None else ('"%s"' % ds_rom)))

    parts.append('"bmp_t":%s' % ("null" if bmp_temp is None else ("%.2f" % bmp_temp)))
    parts.append('"bmp_p":%s' % ("null" if bmp_pres_pa is None else ("%d" % int(bmp_pres_pa))))

    return "{" + ",".join(parts) + "}"


def build_measurement(node_id, sensor_type_id, value, uptime_ms):
    msg = {
        "node_id": node_id,
        "sensor_type_id": sensor_type_id,
        "value": value,
        "timestamp": uptime_ms  # <-- útil para orden y debug
    }
    return ujson.dumps(msg)



# -----------------------------
# Init LoRa
# -----------------------------
spi = SoftSPI(
    baudrate=3000000,
    polarity=0,
    phase=0,
    sck=Pin(SPI_SCK_PIN),
    mosi=Pin(SPI_MOSI_PIN),
    miso=Pin(SPI_MISO_PIN),
)

lora = LoRa(
    spi,
    cs_pin=Pin(LORA_CS_PIN),
    reset_pin=Pin(LORA_RST_PIN),
    dio0_pin=Pin(LORA_DIO0_PIN),
)

# Parámetros opcionales (si querés estandarizar)
# lora.set_frequency(915E6)
# lora.set_spreading_factor(7)
# lora.set_bandwidth(125000)
# lora.set_tx_power(17)


# -----------------------------
# Init DS18B20
# -----------------------------
ow = onewire.OneWire(Pin(DS18B20_DATA_PIN))
ds = ds18x20.DS18X20(ow)

try:
    ds_roms = ds.scan()
except Exception:
    ds_roms = []


# -----------------------------
# Init BMP180 (I2C)
# -----------------------------
i2c = I2C(0, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN), freq=100000)

bmp = None
try:
    bmp = BMP180(i2c)
    bmp.oversample_sett = BMP180_OVERSAMPLE
except Exception:
    bmp = None


# -----------------------------
# Main loop
# -----------------------------
print("LoRa Sensor Sender Started")
print("Node:", NODE_ID)
print("DS18B20 ROMs:", [r.hex() for r in ds_roms] if ds_roms else "NONE")
print("BMP180:", "OK" if bmp else "INIT FAIL")
print("Interval:", SEND_INTERVAL_S, "s")

counter = 0
t0 = time.ticks_ms()

while True:
    uptime_ms = time.ticks_ms()

    ds_temp, ds_rom = read_ds18b20(ds, ds_roms, DS18B20_RETRIES)
    bmp_temp, bmp_pres = read_bmp180(bmp, BMP180_RETRIES)

    # TEMPERATURA (1)
    if ds_temp is not None:
        payload_t = build_measurement(NODE_ID, 1, round(ds_temp, 2), uptime_ms)
        print("TX TEMP:", payload_t)
        try:
            lora.send(payload_t)
            print("TX TEMP OK")
        except Exception as e:
            print("TX TEMP FAIL:", e)

    # PRESION (3)
    if bmp_pres is not None:
        payload_p = build_measurement(NODE_ID, 3, int(bmp_pres), uptime_ms)
        print("TX PRES:", payload_p)
        try:
            lora.send(payload_p)
            print("TX PRES OK")
        except Exception as e:
            print("TX PRES FAIL:", e)

    counter += 1

    if (counter % GC_EVERY_N_SENDS) == 0:
        gc.collect()

    time.sleep(SEND_INTERVAL_S)

