# Librería MicroPython LoRa SX127x

Esta librería proporciona una implementación simple y eficiente para controlar módulos LoRa basados en el chip SX127x (como el SX1276/77/78/79) usando MicroPython.

## Conexiones Hardware

Conecta el módulo LoRa SX127x a tu microcontrolador usando SPI:

| Módulo LoRa | Microcontrolador |
| ----------- | ---------------- |
| VCC         | 3.3V             |
| GND         | GND              |
| MISO        | MISO (GPIO)      |
| MOSI        | MOSI (GPIO)      |
| SCK         | SCK (GPIO)       |
| NSS/CS      | CS (GPIO)        |
| RESET       | RESET (GPIO)     |
| DIO0        | DIO0 (GPIO)      |

## Configuración de Parámetros

### Frecuencia (`set_frequency`)

- **Valor**: En Hz (ejemplo: `915E6` para 915 MHz)
- **Común**:
  - 915 MHz (América)
  - 868 MHz (Europa)
  - 433 MHz (Asia)

### Spreading Factor (`set_spreading_factor`)

- **Rango**: 6 a 12
- **SF7**: Mayor velocidad, menor alcance
- **SF12**: Menor velocidad, mayor alcance
- **Por defecto**: 7

### Bandwidth (`set_bandwidth`)

- **Valores**: 7800, 10400, 15600, 20800, 31250, 41700, 62500, 125000, 250000 Hz
- **Por defecto**: 125000 Hz

### Coding Rate (`set_coding_rate`)

- **Rango**: 5 a 8 (representa 4/5, 4/6, 4/7, 4/8)
- **Mayor valor**: Mayor protección contra errores, menor velocidad
- **Por defecto**: 5 (4/5)

### TX Power (`set_tx_power`)

- **Rango**: 2 a 20 dBm (con PA_BOOST)
- **Por defecto**: 17 dBm

### Funciones de configuración:

- `set_frequency(frequency)`: Establece la frecuencia de operación
- `set_spreading_factor(sf)`: Establece el spreading factor (6-12)
- `set_bandwidth(bw)`: Establece el ancho de banda
- `set_coding_rate(denom)`: Establece la tasa de codificación (5-8)
- `set_tx_power(power, use_pa_boost)`: Establece la potencia de transmisión

### CRC (Cyclic Redundancy Check)

- **Estado**: Habilitado por defecto
- **Descripción**: Verifica la integridad de los paquetes recibidos
- **Funciones**:
  - `enable_crc()`: Habilita verificación CRC
  - `disable_crc()`: Deshabilita verificación CRC
  - `has_crc_error()`: Verifica si el último paquete tuvo error CRC
  - `get_packet(rssi=False, crc_info=False)`: Obtiene paquete con información de CRC

#### Ejemplo de uso de CRC:

```python
# Recibir paquete con información de CRC
if lora.is_packet_received():
    packet = lora.get_packet(rssi=True, crc_info=True)
    if packet:
        print(f"Payload: {packet['payload']}")
        print(f"RSSI: {packet['rssi']} dBm")

        if packet['crc_error']:
            print("¡Paquete corrupto detectado!")
        else:
            print("Paquete válido")
```

Para más detalles, consulta: `docs/CRC_IMPLEMENTATION.md`

## Solución de Problemas

### Alcance limitado

- Aumenta el Spreading Factor (9-12)
- Aumenta la potencia de transmisión
- Usa antenas adecuadas
- Verifica que no haya obstáculos entre los dispositivos

### Paquetes corruptos (errores CRC)

- Verifica la calidad de las conexiones
- Reduce la distancia entre dispositivos
- Aumenta el Spreading Factor
- Verifica interferencias en el canal
- Asegúrate de que ambos dispositivos tengan CRC habilitado
