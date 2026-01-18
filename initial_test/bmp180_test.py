from machine import I2C, Pin
import time

from bmp180 import BMP180

I2C_SCL_PIN = 22
I2C_SDA_PIN = 32

i2c = I2C(0, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN), freq=100000)

print("I2C scan:", i2c.scan())

bmp = BMP180(i2c)
bmp.oversample_sett = 3       # 0..3 (3 = mejor resolución)
bmp.baseline = 101325.0       # Pa, para altitud (opcional)

print("BMP180 chip_id:", bmp.chip_id)
print("Leyendo cada 2 segundos. Ctrl+C para detener.")

try:
    while True:
        bmp.blocking_read()
        t = bmp.temperature          # °C
        p = bmp.pressure             # Pa (por implementación)
        a = bmp.altitude             # m (depende baseline)
        print("Temp (°C):", t, "Pressure (Pa):", p, "Altitude (m):", a)
        time.sleep(2)
except KeyboardInterrupt:
    print("Stop.")
