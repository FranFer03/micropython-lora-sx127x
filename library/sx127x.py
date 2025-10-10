"""
MicroPython LoRa SX127x Library
Supports SX1276/77/78/79 chips for long-range wireless communication
"""

import time
from machine import SPI, Pin #ignore # noqa: F401

class LoRa:
    def __init__(self, spi, cs_pin, reset_pin, dio0_pin):
        """Initialize LoRa module with SPI interface and control pins.
        
        Args:
            spi: Configured SPI object for communication with the module.
            cs_pin: GPIO pin number for chip select (CS/NSS).
            reset_pin: GPIO pin number for hardware reset.
            dio0_pin: GPIO pin number for DIO0 interrupt.
        """
        self.spi = spi
        self.cs = Pin(cs_pin, Pin.OUT)
        self.reset_pin = Pin(reset_pin, Pin.OUT)
        self.dio0 = Pin(dio0_pin, Pin.IN)
        
        # Set up interrupt handler for packet reception
        self.dio0.irq(trigger=Pin.IRQ_RISING, handler=self._irq_recv)
        
        # Packet reception state
        self.packet_received = False
        self.received_payload = None
        self.last_payload = None
        self.received_rssi = None
        self.crc_error = False
        self.last_crc_error = False
        
        self.last_receive_time = 0
        self.receive_delay = 2
        
        # SX127x register addresses
        self.REG_RSSI_VALUE = 0x1A
        self.RSSI_OFFSET = 157
        self.TX_BASE_ADDR = 0x00
        self.RX_BASE_ADDR = 0x00
        self.REG_FIFO = 0x00
        self.REG_OP_MODE = 0x01
        self.REG_FRF_MSB = 0x06
        self.REG_FRF_MID = 0x07
        self.REG_FRF_LSB = 0x08
        self.REG_PA_CONFIG = 0x09
        self.REG_LNA = 0x0c
        self.REG_FIFO_ADDR_PTR = 0x0d
        self.REG_FIFO_TX_BASE_ADDR = 0x0e
        self.REG_FIFO_RX_BASE_ADDR = 0x0f
        self.REG_FIFO_RX_CURRENT_ADDR = 0x10
        self.REG_IRQ_FLAGS = 0x12
        self.REG_RX_NB_BYTES = 0x13
        self.REG_PKT_RSSI_VALUE = 0x1a
        self.REG_PKT_SNR_VALUE = 0x1b
        self.REG_MODEM_CONFIG_1 = 0x1d
        self.REG_MODEM_CONFIG_2 = 0x1e
        self.REG_PREAMBLE_MSB = 0x20
        self.REG_PREAMBLE_LSB = 0x21
        self.REG_PAYLOAD_LENGTH = 0x22
        self.REG_MODEM_CONFIG_3 = 0x26
        self.REG_DETECTION_OPTIMIZE = 0x31
        self.REG_DETECTION_THRESHOLD = 0x37
        self.REG_SYNC_WORD = 0x39
        self.REG_DIO_MAPPING_1 = 0x40
        self.REG_VERSION = 0x42
        self.REG_PA_DAC = 0x4d
        
        # Interrupt flags
        self.IRQ_RX_DONE_MASK = 0x40
        self.IRQ_TX_DONE_MASK = 0x08
        self.IRQ_PAYLOAD_CRC_ERROR_MASK = 0x20
        
        # Operating modes
        self.MODE_RX_SINGLE = 0x06
        self.MODE_LORA = 0x80
        self.MODE_SLEEP = 0x00
        self.MODE_STDBY = 0x01
        self.MODE_TX = 0x03
        self.MODE_RX_CONTINUOUS = 0x05
        
        self.MAX_PKT_LENGTH = 255
        
        self.init_lora()

    def init_lora(self):
        """Initialize LoRa module with default configuration.
        
        Sets up the module with default parameters:
        - Frequency: 915 MHz
        - Bandwidth: 125 kHz
        - Spreading Factor: 7
        - Coding Rate: 4/5
        - TX Power: 17 dBm
        
        Raises:
            Exception: If the chip version is invalid (not 0x12).
        """
        init_try = True
        re_try = 0
        self.cs.value(1)
        self.reset_lora()
        
        # Verify chip version (should be 0x12 for SX127x)
        while init_try and re_try < 5:
            version = self.read_register(self.REG_VERSION)
            re_try = re_try + 1
            if version != 0:
                init_try = False
        if version != 0x12:
            raise Exception('Invalid version.')
        
        # Configure LoRa with default parameters
        self.set_mode_sleep()
        self.set_frequency(915E6)  # 915 MHz for Americas
        self.set_bandwidth(125000)
        self.set_spreading_factor(7)
        self.set_coding_rate(5)
        self.set_tx_power(17, use_pa_boost=True)
        self.enable_crc()  # Enable CRC by default
        # Set FIFO base addresses
        self.write_register(self.REG_FIFO_TX_BASE_ADDR, self.TX_BASE_ADDR)
        self.write_register(self.REG_FIFO_RX_BASE_ADDR, self.RX_BASE_ADDR)
        
        # Enable LNA gain
        self.write_register(self.REG_LNA, self.read_register(self.REG_LNA) | 0x03)
        self.write_register(self.REG_MODEM_CONFIG_3, 0x04)
        self.set_mode_standby()
        self.set_mode_rx_continuous()
        self.write_register(self.REG_DIO_MAPPING_1, 0x00)
        print("Lora Conected")
    
    def send(self, data):
        """Send data string via LoRa.
        
        Args:
            data: String data to transmit (max 255 bytes).
        """
        self.set_mode_standby()
        self.write_register(self.REG_FIFO_ADDR_PTR, self.TX_BASE_ADDR)
        
        # Write payload to FIFO
        for byte in data:
            self.write_register(self.REG_FIFO, ord(byte))
        self.write_register(self.REG_PAYLOAD_LENGTH, len(data))
        self.set_mode_tx()
        
        # Wait for transmission to complete
        while not (self.read_register(self.REG_IRQ_FLAGS) & self.IRQ_TX_DONE_MASK):
            time.sleep(0.01)
        self.write_register(self.REG_IRQ_FLAGS, self.IRQ_TX_DONE_MASK)
        self.set_mode_rx_continuous()

    def _irq_recv(self, pin):
        """Interrupt handler for packet reception.
        
        Args:
            pin: Pin object that triggered the interrupt.
        """
        self.check_for_packet()
        
    def check_for_packet(self):
        """Check and process received packet.
        
        Reads the packet from FIFO if available and updates internal state.
        Checks for CRC errors and marks packets accordingly.
        """
        irq_flags = self.read_register(self.REG_IRQ_FLAGS)
        
        # Check for CRC error
        if irq_flags & self.IRQ_PAYLOAD_CRC_ERROR_MASK:
            self.crc_error = True
            self.last_crc_error = True
            # Clear CRC error flag
            self.write_register(self.REG_IRQ_FLAGS, self.IRQ_PAYLOAD_CRC_ERROR_MASK)
            return
        
        if irq_flags & self.IRQ_RX_DONE_MASK:
            # Check if packet has CRC error (double check)
            if irq_flags & self.IRQ_PAYLOAD_CRC_ERROR_MASK:
                self.crc_error = True
                self.last_crc_error = True
            else:
                self.crc_error = False
                self.last_crc_error = False
            
            # Read packet from FIFO
            current_addr = self.read_register(self.REG_FIFO_RX_CURRENT_ADDR)
            self.write_register(self.REG_FIFO_ADDR_PTR, current_addr)
            packet_length = self.read_register(self.REG_RX_NB_BYTES)
            payload = [self.read_register(self.REG_FIFO) for _ in range(packet_length)]
            payload_string = ''.join([chr(byte) for byte in payload])
            
            self.get_rssi()
            
            # Update reception state (only if no CRC error)
            if not self.crc_error:
                self.packet_received = True
                self.received_payload = payload_string
                self.last_payload = payload_string
            
            # Clear interrupt flags
            self.write_register(self.REG_IRQ_FLAGS, self.IRQ_RX_DONE_MASK)
            self.write_register(self.REG_IRQ_FLAGS, 0xFF)
        
    def set_mode_tx(self):
        """Set transmission mode.
        
        Places the module in transmit mode to send packets.
        """
        self.write_register(self.REG_OP_MODE, self.MODE_LORA | self.MODE_TX)

    def set_mode_rx_continuous(self):
        """Set continuous reception mode.
        
        Places the module in continuous receive mode to listen for packets.
        """
        self.write_register(self.REG_OP_MODE, self.MODE_LORA | self.MODE_RX_CONTINUOUS)

    def set_mode_sleep(self):
        """Set sleep mode for low power consumption.
        
        Places the module in sleep mode to minimize power consumption.
        """
        self.write_register(self.REG_OP_MODE, self.MODE_LORA | self.MODE_SLEEP)

    def set_mode_standby(self):
        """Set standby mode.
        
        Places the module in standby mode, ready for configuration changes.
        """
        self.write_register(self.REG_OP_MODE, self.MODE_LORA | self.MODE_STDBY)

    def set_tx_power(self, power, use_pa_boost=False):
        """Set transmission power in dBm.
        
        Args:
            power: Output power in dBm. Range depends on use_pa_boost:
                - With PA_BOOST: 2 to 20 dBm
                - Without PA_BOOST: 0 to 14 dBm
            use_pa_boost: Enable PA_BOOST pin for higher power output.
        """
        if use_pa_boost:
            # Enable high power mode for +20dBm
            if power > 17:
                power = 20
                self.write_register(self.REG_PA_DAC, 0x87)  # Enable +20dBm
            else:
                self.write_register(self.REG_PA_DAC, 0x84)
            power = max(2, min(power, 20))
            self.write_register(self.REG_PA_CONFIG, 0x80 | (power - 2))
        else:
            power = max(0, min(power, 14))
            self.write_register(self.REG_PA_CONFIG, 0x70 | power)

    def set_frequency(self, frequency):
        """Set carrier frequency in Hz.
        
        Args:
            frequency: Carrier frequency in Hz (e.g., 915E6 for 915 MHz).
                Common values: 433E6, 868E6, 915E6.
        """
        frf = int(frequency / 61.03515625)
        self.write_register(self.REG_FRF_MSB, (frf >> 16) & 0xFF)
        self.write_register(self.REG_FRF_MID, (frf >> 8) & 0xFF)
        self.write_register(self.REG_FRF_LSB, frf & 0xFF)

    def set_bandwidth(self, bw):
        """Set signal bandwidth in Hz.
        
        Args:
            bw: Bandwidth in Hz. Valid values:
                7800, 10400, 15600, 20800, 31250, 41700, 62500, 125000, 250000.
        """
        bws = (7800, 10400, 15600, 20800, 31250, 41700, 62500, 125000, 250000)
        i = 9
        for j in range(len(bws)):
            if bw <= bws[j]:
                i = j
                break
        x = self.read_register(self.REG_MODEM_CONFIG_1) & 0x0f
        self.write_register(self.REG_MODEM_CONFIG_1, x | (i << 4))

    def set_spreading_factor(self, sf):
        """Set spreading factor.
        
        Higher spreading factor provides longer range but lower data rate.
        
        Args:
            sf: Spreading factor (6 to 12).
        
        Raises:
            ValueError: If sf is not between 6 and 12.
        """
        if sf < 6 or sf > 12:
            raise ValueError('Spreading factor must be between 6-12')
        self.write_register(self.REG_DETECTION_OPTIMIZE, 0xc5 if sf == 6 else 0xc3)
        self.write_register(self.REG_DETECTION_THRESHOLD, 0x0c if sf == 6 else 0x0a)
        reg2 = self.read_register(self.REG_MODEM_CONFIG_2)
        self.write_register(self.REG_MODEM_CONFIG_2, (reg2 & 0x0f) | ((sf << 4) & 0xf0))
        # Note: Low data rate optimization disabled (requires bandwidth context)

    def set_coding_rate(self, denom):
        """Set coding rate denominator.
        
        Higher coding rate provides better error correction but lower data rate.
        
        Args:
            denom: Denominator for coding rate (5 to 8).
                5 = 4/5, 6 = 4/6, 7 = 4/7, 8 = 4/8.
        """
        denom = min(max(denom, 5), 8)
        cr = denom - 4
        reg1 = self.read_register(self.REG_MODEM_CONFIG_1)
        self.write_register(self.REG_MODEM_CONFIG_1, (reg1 & 0xf1) | (cr << 1))

    def enable_crc(self):
        """Enable CRC checking on received packets.
        
        When enabled, packets with CRC errors will be rejected.
        """
        reg2 = self.read_register(self.REG_MODEM_CONFIG_2)
        self.write_register(self.REG_MODEM_CONFIG_2, reg2 | 0x04)

    def disable_crc(self):
        """Disable CRC checking on received packets.
        
        When disabled, all packets will be accepted regardless of CRC status.
        """
        reg2 = self.read_register(self.REG_MODEM_CONFIG_2)
        self.write_register(self.REG_MODEM_CONFIG_2, reg2 & 0xFB)

    def has_crc_error(self):
        """Check if the last received packet had a CRC error.
        
        Returns:
            True if the last packet had a CRC error, False otherwise.
        """
        return self.last_crc_error

    def write_register(self, reg, value):
        """Write value to SX127x register.
        
        Args:
            reg: Register address to write to.
            value: Byte value to write.
        """
        self.cs.value(0)
        self.spi.write(bytearray([reg | 0x80, value]))
        self.cs.value(1)

    def read_register(self, reg):
        """Read value from SX127x register.
        
        Args:
            reg: Register address to read from.
        
        Returns:
            Byte value read from the register.
        """
        self.cs.value(0)
        self.spi.write(bytearray([reg & 0x7F]))
        value = self.spi.read(1)
        self.cs.value(1)
        return value[0]

    def reset_lora(self):
        """Hardware reset of the LoRa module.
        
        Performs a hardware reset by toggling the reset pin.
        """
        self.reset_pin.value(0)
        time.sleep(0.01)
        self.reset_pin.value(1)
        time.sleep(0.01)

    def is_packet_received(self):
        """Check if a packet has been received.
        
        Returns:
            True if a packet is available, False otherwise.
        """
        return self.packet_received
    
    def get_rssi(self):
        """Get RSSI value in dBm of last received packet.
        
        Returns:
            RSSI value in dBm (negative number).
        """
        rssi_value = self.read_register(self.REG_RSSI_VALUE)
        self.received_rssi  = rssi_value - self.RSSI_OFFSET  
        return self.received_rssi 

    def get_packet(self, rssi=False, crc_info=False):
        """Retrieve received packet and clear reception state.
        
        Args:
            rssi: If True, include RSSI value in returned dictionary.
            crc_info: If True, include CRC error status in returned dictionary.
        
        Returns:
            Dictionary with 'payload' key (always), 'rssi' key (if requested),
            and 'crc_error' key (if requested).
            Returns None if no packet is available.
        """
        if self.packet_received:
            packet_info = {
                "payload": self.received_payload
            }
            
            if rssi:
                packet_info["rssi"] = self.received_rssi
            
            if crc_info:
                packet_info["crc_error"] = self.last_crc_error
            
            self.packet_received = False
            self.received_payload = None
            self.received_rssi = None
            return packet_info
        else:
            return None