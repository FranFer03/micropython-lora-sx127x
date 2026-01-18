"""
LoRa Sensor Sender (DS18B20 + BMP180) - ESP32 MicroPython

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

# --- LoRa lib ---
sys.path.append('./library')
from sx127x import LoRa

# --- DS18B20 libs ---
import onewire
import ds18x20

# --- BMP180 lib (the one you pasted) ---
# Ensure this file is in ./library/bmp180.py (or adjust import accordingly)
from bmp180 import BMP180


# -----------------------------
# Pinout - LoRa (as your example)
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
NODE_ID = "NODE01"
SEND_INTERVAL_S = 10

DS18B20_RETRIES = 3
BMP180_RETRIES  = 3

# Oversampling BMP180: 0..3 (3 = max resolution, more delay)
BMP180_OVERSAMPLE = 3


# -----------------------------
# Sensor read helpers
# -----------------------------
def read_ds18b20(ds, roms, retries=3):
    """
    Returns: (temp_c, rom_hex) or (None, None)
    """
    if not roms:
        return (None, None)

    rom = roms[0]  # first sensor; extend if multiple
    rom_hex = rom.hex()

    for _ in range(retries):
        try:
            ds.convert_temp()
            time.sleep_ms(750)  # 12-bit conversion
            t = ds.read_temp(rom)
            if t is None:
                continue
            if -60.0 <= t <= 130.0:
                return (float(t), rom_hex)
        except Exception:
            time.sleep_ms(100)

    return (None, rom_hex)


def read_bmp180(bmp, retries=3):
    """
    Returns: (temp_c, pressure_pa) or (None, None)

    With this library:
      bmp.temperature -> °C
      bmp.pressure    -> Pa (by implementation, despite docstring saying mbar)
    """
    if bmp is None:
        return (None, None)

    for _ in range(retries):
        try:
            # Ensure raw values are refreshed coherently
            bmp.blocking_read()
            t = bmp.temperature
            p = bmp.pressure
            # basic sanity
            if p is not None and p > 10000:  # Pa
                return (float(t), float(p))
        except Exception:
            time.sleep_ms(100)

    return (None, None)


def build_payload(counter, uptime_s, ds_temp, ds_rom, bmp_temp, bmp_pres_pa):
    """
    Compact JSON payload (manual build to keep it small).
    """
    parts = []
    parts.append('"id":"%s"' % NODE_ID)
    parts.append('"n":%d' % counter)
    parts.append('"up":%d' % uptime_s)

    # DS18B20
    parts.append('"ds_t":%s' % ("null" if ds_temp is None else ("%.2f" % ds_temp)))
    parts.append('"ds_rom":%s' % ("null" if ds_rom is None else ('"%s"' % ds_rom)))

    # BMP180
    parts.append('"bmp_t":%s' % ("null" if bmp_temp is None else ("%.2f" % bmp_temp)))
    parts.append('"bmp_p":%s' % ("null" if bmp_pres_pa is None else ("%d" % int(bmp_pres_pa))))

    return "{" + ",".join(parts) + "}"


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

# Optional fixed radio parameters (uncomment if you want to lock them)
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
    bmp.oversample_sett = BMP180_OVERSAMPLE  # 0..3
    # baseline only needed if you plan to send altitude; keep default otherwise
    # bmp.baseline = 101325.0
except Exception as e:
    bmp = None


# -----------------------------
# Main loop
# -----------------------------
print("LoRa Sensor Sender Started")
print("Node:", NODE_ID)
print("DS18B20 ROMs:", [r.hex() for r in ds_roms] if ds_roms else "NONE")
print("BMP180:", "OK" if bmp else "INIT FAIL")
print("Interval:", SEND_INTERVAL_S, "s")
print("Press Ctrl+C to stop")

counter = 0
t0 = time.ticks_ms()

try:
    while True:
        uptime_s = time.ticks_diff(time.ticks_ms(), t0) // 1000

        ds_temp, ds_rom = read_ds18b20(ds, ds_roms, DS18B20_RETRIES)
        bmp_temp, bmp_pres = read_bmp180(bmp, BMP180_RETRIES)

        payload = build_payload(counter, uptime_s, ds_temp, ds_rom, bmp_temp, bmp_pres)

        print("TX:", payload)
        try:
            lora.send(payload)
            print("TX OK")
        except Exception as e:
            print("TX FAIL:", e)

        counter += 1
        time.sleep(SEND_INTERVAL_S)

except KeyboardInterrupt:
    print("Stopped. Total sent:", counter)
