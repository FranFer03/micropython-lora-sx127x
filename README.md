# MicroPython LoRa SX127x Library

This library provides a simple and efficient implementation to control LoRa modules based on the SX127x chip (such as SX1276/77/78/79) using MicroPython.

### Diagrama de Secuencia de Envío

```mermaid
sequenceDiagram
    participant User
    participant LoRa as LoRa Library
    participant SX127x as Hardware SX127x

    User->>LoRa: send("Hello")
    LoRa->>SX127x: write_register(REG_OP_MODE, MODE_STDBY)
    Note right of LoRa: Set mode to Standby
    LoRa->>SX127x: write_register(REG_FIFO_ADDR_PTR, TX_BASE_ADDR)
    Note right of LoRa: Set FIFO pointer
    loop For each byte in "Hello"
        LoRa->>SX127x: write_register(REG_FIFO, byte)
    end
    LoRa->>SX127x: write_register(REG_PAYLOAD_LENGTH, 5)
    LoRa->>SX127x: write_register(REG_OP_MODE, MODE_TX)
    Note right of LoRa: Set mode to TX (Transmit)
    activate SX127x
    Note right of SX127x: Hardware transmits packet...
    deactivate SX127x
    loop Poll TX_DONE flag
        LoRa->>SX127x: read_register(REG_IRQ_FLAGS)
        SX127x-->>LoRa: IRQ_FLAGS value
        Note right of LoRa: Wait until TX_DONE flag is set
    end
    LoRa->>SX127x: write_register(REG_IRQ_FLAGS, TX_DONE_MASK)
    Note right of LoRa: Clear TX_DONE flag
    LoRa->>SX127x: write_register(REG_OP_MODE, MODE_RX_CONTINUOUS)
    Note right of LoRa: Return to RX mode
    LoRa-->>User: Return (transmission complete)
```

### Diagrama de Secuencia de Recepción

```mermaid
sequenceDiagram
    participant User
    participant LoRa as LoRa Library
    participant DIO0 as Pin DIO0
    participant SX127x as Hardware SX127x

    Note over SX127x: Packet arrives via radio
    activate SX127x
    Note right of SX127x: Hardware receives packet
    SX127x->>DIO0: Set DIO0 pin HIGH
    deactivate SX127x
    DIO0->>LoRa: Trigger IRQ_RISING interrupt
    activate LoRa
    LoRa->>LoRa: _irq_recv(pin) called
    LoRa->>LoRa: check_for_packet()
    LoRa->>SX127x: read_register(REG_IRQ_FLAGS)
    SX127x-->>LoRa: irq_flags value

    alt CRC Error detected
        LoRa->>LoRa: Set crc_error = True
        LoRa->>SX127x: write_register(REG_IRQ_FLAGS, CRC_ERROR_MASK)
        Note right of LoRa: Clear CRC error flag and return
    else RX_DONE flag is set (no CRC error)
        LoRa->>SX127x: read_register(REG_FIFO_RX_CURRENT_ADDR)
        SX127x-->>LoRa: current_addr
        LoRa->>SX127x: write_register(REG_FIFO_ADDR_PTR, current_addr)
        LoRa->>SX127x: read_register(REG_RX_NB_BYTES)
        SX127x-->>LoRa: packet_length
        loop For each byte in packet
            LoRa->>SX127x: read_register(REG_FIFO)
            SX127x-->>LoRa: byte
        end
        LoRa->>LoRa: Convert bytes to payload string
        LoRa->>SX127x: read_register(REG_PKT_RSSI_VALUE)
        SX127x-->>LoRa: rssi_value
        LoRa->>LoRa: Store payload, RSSI, set packet_received = True
        LoRa->>SX127x: write_register(REG_IRQ_FLAGS, RX_DONE_MASK)
        LoRa->>SX127x: write_register(REG_IRQ_FLAGS, 0xFF)
        Note right of LoRa: Clear all interrupt flags
    end
    deactivate LoRa

    Note over User: Later, user checks for packet
    User->>LoRa: is_packet_received()
    LoRa-->>User: True
    User->>LoRa: get_packet(rssi=True, crc_info=True)
    LoRa->>LoRa: Build packet_info dict
    LoRa->>LoRa: Clear packet_received flag
    LoRa-->>User: {"payload": "data", "rssi": -50, "crc_error": False}
```

## Hardware Connections

Connect the LoRa SX127x module to your microcontroller using SPI:

| LoRa Module | Microcontroller |
| ----------- | --------------- |
| VCC         | 3.3V            |
| GND         | GND             |
| MISO        | MISO (GPIO)     |
| MOSI        | MOSI (GPIO)     |
| SCK         | SCK (GPIO)      |
| NSS/CS      | CS (GPIO)       |
| RESET       | RESET (GPIO)    |
| DIO0        | DIO0 (GPIO)     |

## Parameter Configuration

### Frequency (`set_frequency`)

- **Value**: In Hz (example: `915E6` for 915 MHz)
- **Common**:
  - 915 MHz (Americas)
  - 868 MHz (Europe)
  - 433 MHz (Asia)

### Spreading Factor (`set_spreading_factor`)

- **Range**: 6 to 12
- **SF7**: Higher speed, shorter range
- **SF12**: Lower speed, longer range
- **Default**: 7

### Bandwidth (`set_bandwidth`)

- **Values**: 7800, 10400, 15600, 20800, 31250, 41700, 62500, 125000, 250000 Hz
- **Default**: 125000 Hz

### Coding Rate (`set_coding_rate`)

- **Range**: 5 to 8 (represents 4/5, 4/6, 4/7, 4/8)
- **Higher value**: Better error protection, lower speed
- **Default**: 5 (4/5)

### TX Power (`set_tx_power`)

- **Range**: 2 to 20 dBm (with PA_BOOST)
- **Default**: 17 dBm

## Configuration Functions

- `set_frequency(frequency)`: Set operating frequency
- `set_spreading_factor(sf)`: Set spreading factor (6-12)
- `set_bandwidth(bw)`: Set bandwidth
- `set_coding_rate(denom)`: Set coding rate (5-8)
- `set_tx_power(power, use_pa_boost)`: Set transmission power
- `enable_crc()`: Enable CRC verification
- `disable_crc()`: Disable CRC verification
- `has_crc_error()`: Check if the last packet had a CRC error
- `get_packet(rssi=False, crc_info=False)`: Get packet with CRC information
