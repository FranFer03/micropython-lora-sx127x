from machine import Pin
import time
import onewire
import ds18x20

DS18B20_DATA_PIN = 33

ow = onewire.OneWire(Pin(DS18B20_DATA_PIN))
ds = ds18x20.DS18X20(ow)

roms = ds.scan()
print("DS18B20 scan:", [r.hex() for r in roms])

if not roms:
    print("ERROR: No se detectaron DS18B20.")
else:
    print("Leyendo temperatura cada 2 segundos. Ctrl+C para detener.")
    try:
        while True:
            ds.convert_temp()
            time.sleep_ms(750)  # conversión típica 12-bit
            for rom in roms:
                t = ds.read_temp(rom)
                print("ROM:", rom.hex(), "Temp (°C):", t)
            time.sleep(2)
    except KeyboardInterrupt:
        print("Stop.")
