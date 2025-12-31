import asyncio
import struct
import logging
import binascii
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

_LOGGER = logging.getLogger(__name__)

# --- KONSTANTEN ---
ACTION_CONNECT = 1
ACTION_DATA = 2
ACTION_DISCONNECT = 3
ACTION_IK3 = 4
ACTION_IK4 = 5
ACTION_IK5 = 6
ACTION_IK6 = 7
ACTION_CHECKSUM_ERROR = 8
ACTION_IK3_AFTER_POLL = 9
ACTION_TIMER_EXPIRED = 10
ACTION_RETRY = 11

MIN_LENGTH = 48

# Mapping der VdS Meldungsarten (Auszug)
VDS_MESSAGES = {
    0: "Meldung - Ein",
    128: "Meldung - Aus",
    1: "Revisionsmeldung - Ausgeloest",
    129: "Revisionsmeldung - Zurueckgesetzt",
    2: "Testmeldung - Ein",
    3: "GPS-Position - Positionsänderung",
    4: "Stechstelle - übermittelt",
    16: "Brandmeldung - Ausgeloest",
    144: "Brandmeldung - Zurueckgesetzt",
    17: "Brand - manueller Melder - Ausgeloest",
    145: "Brand - manueller Melder - Zurueckgesetzt",
    18: "Brand - automatischer Melder - Ausgeloest",
    146: "Brand - automatischer Melder - Zurueckgesetzt",
    19: "Brandmeldung aus Loeschanlage - Ausgeloest",
    147: "Brandmeldung aus Loeschanlage - Zurueckgesetzt",
    20: "Katastrophenalarm - Aufgetreten",
    148: "Katastrophenalarm - Zurueckgesetzt",
    21: "Gefahrstoffalarm - Ausgelöst",
    149: "Gefahrstoffalarm - Zurueckgesetzt",
    32: "Überfall-, Einbruchmeldung - Ausgelöst",
    160: "Überfall-, Einbruchmeldung - Zurückgesetzt",
    33: "Überfall - Ausgelöst",
    161: "Überfall - Zurückgesetzt",
    34: "Einbruch - Ausgeloest",
    162: "Einbruch - Zurueckgesetzt",
    35: "Sabotage - Ausgelöst",
    163: "Sabotage - Zurueckgesetzt",
    36: "Geiselnahmen - Ausgelöst",
    164: "Geiselnahmen - Zurueckgesetzt",
    37: "Amok-Alarm - Ausgelöst",
    165: "Amok-Alarm - Zurueckgesetzt",
    38: "Überfall Funkmelder - Ausgelöst",
    166: "Überfall Funkmelder - Zurueckgesetzt",
    39: "Bedrohung - Ausgelöst",
    167: "Bedrohung - Zurueckgesetzt",
    40: "Belästigung - Ausgelöst",
    168: "Belästigung - Zurueckgesetzt",
    41: "Notfall (NGRS-Notfall) - Ausgelöst",
    169: "Notfall (NGRS-Notfall) - Zurueckgesetzt",
    42: "Notruf (NGRS-Notruf) - Ausgelöst",
    170: "Notruf (NGRS-Notruf) - Zurueckgesetzt",
    47: "Bereichsmeldung Überfall, Einbruch - Ausgelöst",
    175: "Bereichsmeldung Überfall, Einbruch - Zurueckgesetzt",
    48: "Störungsmeldungen - Ausgelöst",
    176: "Störungsmeldungen - Zurückgesetzt",
    49: "Störung Primärleitung - Ausgelöst",
    177: "Störung Primärleitung - Zurückgesetzt",
    50: "Störung Netz - Ausgelöst",
    178: "Störung Netz - Zurückgesetzt",
    51: "Störung Batterie - Ausgelöst",
    179: "Störung Batterie - Zurückgesetzt",
    52: "Störung Übertragungsweg - Ausgelöst",
    180: "Störung Übertragungsweg - Zurückgesetzt",
    53: "Störung Erdschluß - Ausgelöst",
    181: "Störung Erdschluß - Zurückgesetzt",
    54: "Störung Testmeldung - Nicht erhalten",
    182: "Störung Testmeldung - Wieder in Ordnung",
    55: "Störung Energieversorgung ÜG - Ausgelöst",
    183: "Störung Energieversorgung ÜG - Wieder in Ordnung",
    56: "Störung, Pufferüberlauf - Ausgelöst",
    184: "Störung, Pufferüberlauf - Zurückgesetzt",
    57: "Nicht abgesetzte Meldungen - Ausgelöst",
    185: "Nicht abgesetzte Meldungen - Zurückgesetzt",
    58: "Störung Übertragungsweg 1 - Ausgelöst",
    186: "Störung Übertragungsweg 1 - Zurückgesetzt",
    59: "Störung Übertragungsweg 2 - Ausgelöst",
    187: "Störung Übertragungsweg 2 - Zurückgesetzt",
    60: "IT-Sicherheitsvorfall - Ausgelöst",
    188: "IT-Sicherheitsvorfall - Zurückgesetzt",
    61: "Störung GPS - Ausgelöst",
    189: "Störung GPS - Zurückgesetzt",
    62: "Störung Testmeldung Erstweg - Ausgelöst",
    190: "Störung Testmeldung Erstweg - Zurückgesetzt",
    63: "Störung Testmeldung Zweitweg - Ausgelöst",
    191: "Störung Testmeldung Zweitweg - Zurückgesetzt",
    64: "Technische Meldung - Ausgelöst",
    192: "Technische Meldung - Zurückgesetzt",
    65: "Technikalarm - Ausgelöst",
    193: "Technikalarm - Zurückgesetzt",
    72: "Notmeldung allgemeine - Ausgelöst",
    200: "Notmeldung allgemeine - Zurückgesetzt",
    73: "Notmeldung 1 - Ausgelöst",
    201: "Notmeldung 1 - Zurückgesetzt",
    74: "Notmeldung 2 - Ausgelöst",
    202: "Notmeldung 2 - Zurückgesetzt",
    75: "Notmeldung 3 - Ausgelöst",
    203: "Notmeldung 3 - Zurückgesetzt",
    76: "Notmeldung 4 - Ausgelöst",
    204: "Notmeldung 4 - Zurückgesetzt",
    77: "Technische Störung, (GMA fremde Technik) - Ausgelöst",
    205: "Technische Störung, (GMA fremde Technik) - Zurückgesetzt",
    80: "Gerätemeldungen - Aktivieren",
    208: "Gerätemeldungen - Zurücknehmen",
    81: "Abschaltung - Aktivieren",
    209: "Abschaltung - Zurücknehmen",
    82: "Rücksetzen - Aktivieren",
    83: "Wiederanlauf, Neustart - Aktivieren",
    84: "Meldungspufferüberlauf - Aufgetreten",
    85: "Systemstörung - Aufgetreten",
    86: "Deckelkontakt - Offen",
    214: "Deckelkontakt - Geschlossen",
    87: "Batteriewarnung (z. B. Funkmelder) - Aufgetreten",
    215: "Batteriewarnung (z. B. Funkmelder) - Zurückgesetzt",
    96: "Zustandsmeldungen - Ein",
    224: "Zustandsmeldungen - Aus",
    97: "Sicherungsbereich - Scharf",
    225: "Sicherungsbereich - Unscharf",
    98: "Internbereich - Ein",
    226: "Internbereich - Aus",
    99: "Revisionszustand - Ein",
    227: "Revisionszustand - Aus",
    100: "Tagbetrieb - Ein",
    228: "Tagbetrieb - Aus",
    101: "Positionsalarm, unerlaubtes Betreten - Ein",
    229: "Positionsalarm, unerlaubtes Betreten - Aus",
    102: "Positionsalarm, unerlaubtes Verlassen - Ein",
    230: "Positionsalarm, unerlaubtes Verlassen - Aus",
    112: "Firmenspezifische Meldungen - Ein",
    240: "Firmenspezifische Meldungen - Aus"
}

def calculate_checksum_logic(data, skip_offset_4=False):
    crc = 0
    length = len(data)
    for pos in range(0, length, 2):
        if skip_offset_4 and pos == 4:
            continue
            
        temp = data[pos] << 8
        if pos + 1 == length:
            temp |= 0x00
        else:
            temp |= data[pos + 1]
        
        crc += temp
        if crc > 65535:
            crc &= 0xffff
            crc += 1
            
    crc = ~crc & 0xffff
    return crc

def check_crc16(data):
    if len(data) < 6:
        return False
    original = (data[4] << 8) | data[5]
    calculated = calculate_checksum_logic(data, skip_offset_4=True)
    return calculated == original

def set_crc16(data):
    crc = calculate_checksum_logic(data, skip_offset_4=True)
    struct.pack_into('>H', data, 4, crc)
    return data

def pad_data(data):
    length = len(data)
    diff = 16 - (length % 16)
    if length + diff < MIN_LENGTH:
        diff = MIN_LENGTH - length
    return data + (b'\x00' * diff)


class VdSConnection:
    def __init__(self, reader, writer, devices_config, event_callback):
        self.reader = reader
        self.writer = writer
        self.peer = writer.get_extra_info('peername')
        self.devices_config = devices_config # Dict: {keynr: {key: "...", identnr: "..."}}
        self.event_callback = event_callback # Funktion(event_type, data)
        
        self.tc = int.from_bytes(os.urandom(4), 'big')
        self.rc_rec = 0
        self.tc_rec = 0
        
        self.send_counter = 0
        self.last_send_buffer = None
        
        self.device_config = None 
        self.key_nr_rec = 0
        self.identnr = None
        
        self.buffer = b""
        self.timer_task = None
        self.poll_task = None
        self.polling_interval = 5
        
        self.last_sent_rc = 0
        self.send_queue = []
        self._running = True

    async def run(self):
        _LOGGER.info(f"Verbindung von {self.peer}")
        try:
            await self.controller(ACTION_CONNECT)
            
            while self._running:
                data = await self.reader.read(4096)
                if not data:
                    break
                self.buffer += data
                await self.controller(ACTION_DATA)
                
        except ConnectionResetError:
            _LOGGER.info("Verbindung zurückgesetzt")
        except Exception as e:
            _LOGGER.error(f"Fehler in Verbindung: {e}", exc_info=True)
        finally:
            await self.disconnect()

    async def disconnect(self):
        self._running = False
        _LOGGER.info(f"Trenne Verbindung zu {self.peer}")
        if (self.identnr or self.key_nr_rec) and self.event_callback:
             self.event_callback("disconnected", {"identnr": self.identnr, "keynr": self.key_nr_rec})

        if self.timer_task: self.timer_task.cancel()
        if self.poll_task: self.poll_task.cancel()
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except (ConnectionResetError, BrokenPipeError, AttributeError):
            pass

    async def send(self, data):
        self.last_send_buffer = data
        # _LOGGER.debug(f"TX: {binascii.hexlify(data)}")
        try:
            self.writer.write(data)
            await self.writer.drain()
        except Exception as e:
             _LOGGER.warning(f"Senden fehlgeschlagen: {e}")
             await self.disconnect()

    def get_device_by_keynr(self, keynr):
        return self.devices_config.get(keynr)

    def encrypt(self, data):
        if not self.device_config or not self.device_config.get('key'):
            return data
        
        key_hex = self.device_config['key']
        key = binascii.unhexlify(key_hex)
        iv = b'\x00' * 16
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        return encryptor.update(data) + encryptor.finalize()

    def decrypt(self, data):
        if not self.device_config or not self.device_config.get('key'):
            return data
            
        key_hex = self.device_config['key']
        key = binascii.unhexlify(key_hex)
        iv = b'\x00' * 16
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        return decryptor.update(data) + decryptor.finalize()

    def prepare_packet(self, payload):
        payload = pad_data(payload)
        payload = bytearray(payload)
        set_crc16(payload)
        payload = bytes(payload)
        
        if self.key_nr_rec > 0:
            payload = self.encrypt(payload)
            
        sl = len(payload)
        header = struct.pack('>HH', self.key_nr_rec, sl)
        return header + payload

    async def send_ik1(self):
        buf = bytearray(14)
        struct.pack_into('>I', buf, 0, self.tc)
        self.tc = (self.tc + 1) & 0xFFFFFFFF
        struct.pack_into('>I', buf, 6, 0)
        self.last_sent_rc = 0
        buf[10] = 1 # IK
        buf[11] = 1 # PK
        buf[12] = 1 # L
        buf[13] = 1 # Window
        await self.send(self.prepare_packet(buf))

    async def send_ik3(self):
        buf = bytearray(13)
        struct.pack_into('>I', buf, 0, self.tc)
        self.tc = (self.tc + 1) & 0xFFFFFFFF
        rc = (self.tc_rec + 1) & 0xFFFFFFFF
        struct.pack_into('>I', buf, 6, rc)
        self.last_sent_rc = rc
        buf[10] = 3 # IK
        buf[11] = 1 # PK
        buf[12] = 0 # L
        await self.send(self.prepare_packet(buf))

    async def send_ik4(self, payload):
        l_byte = len(payload)
        buf = bytearray(13)
        struct.pack_into('>I', buf, 0, self.tc)
        self.tc = (self.tc + 1) & 0xFFFFFFFF
        rc = (self.tc_rec + 1) & 0xFFFFFFFF
        struct.pack_into('>I', buf, 6, rc)
        self.last_sent_rc = rc
        buf[10] = 4 # IK
        buf[11] = 1 # PK
        buf[12] = l_byte # L
        await self.send(self.prepare_packet(buf + payload))

    async def send_ik5(self):
        buf = bytearray(13)
        struct.pack_into('>I', buf, 0, self.tc)
        self.tc = (self.tc + 1) & 0xFFFFFFFF
        rc = (self.tc_rec + 1) & 0xFFFFFFFF
        struct.pack_into('>I', buf, 6, rc)
        self.last_sent_rc = rc
        buf[10] = 5; buf[11] = 1; buf[12] = 0
        await self.send(self.prepare_packet(buf))

    async def send_ik6(self):
        buf = bytearray(13)
        struct.pack_into('>I', buf, 0, self.tc)
        self.tc = (self.tc + 1) & 0xFFFFFFFF
        rc = (self.tc_rec + 1) & 0xFFFFFFFF
        struct.pack_into('>I', buf, 6, rc)
        self.last_sent_rc = rc
        buf[10] = 6; buf[11] = 1; buf[12] = 0
        await self.send(self.prepare_packet(buf))

    async def controller(self, action):
        if not self._running: return

        if action == ACTION_CONNECT:
            await self.send_ik1()
            self.reset_timer()
            
        elif action == ACTION_DATA:
            if len(self.buffer) < 4: return
            
            key_nr = struct.unpack('>H', self.buffer[0:2])[0]
            sl = struct.unpack('>H', self.buffer[2:4])[0]
            
            total_len = 4 + sl
            if len(self.buffer) < total_len: return
            
            packet_data = self.buffer[4:total_len]
            # _LOGGER.debug(f"RX Header: KeyNr={key_nr}, Len={sl}")
            
            self.buffer = self.buffer[total_len:]
            self.key_nr_rec = key_nr
            
            if key_nr > 0:
                dev = self.get_device_by_keynr(key_nr)
                if dev:
                    self.device_config = dev
                    decrypted = self.decrypt(packet_data)
                else:
                    _LOGGER.warning(f"Unbekannte KeyNr: {key_nr}")
                    await self.disconnect()
                    return
            else:
                self.device_config = None
                decrypted = packet_data
                
            if self.process_packet(decrypted):
                if self.timer_task: self.timer_task.cancel()

        elif action == ACTION_IK3:
            await self.send_ik3()
            self.reset_timer()
        
        elif action == ACTION_IK4:
            if self.send_queue:
                payload = self.send_queue.pop(0)
                await self.send_ik4(payload)
                self.reset_timer()
            else:
                await self.controller(ACTION_IK3)
        
        elif action == ACTION_IK5:
            await self.send_ik5()
            await self.controller(ACTION_IK3)
            
        elif action == ACTION_IK6:
            await self.send_ik6()
            await self.controller(ACTION_IK3)

        elif action == ACTION_IK3_AFTER_POLL:
            if self.poll_task: self.poll_task.cancel()
            self.poll_task = asyncio.create_task(self.wait_and_poll())

        elif action == ACTION_TIMER_EXPIRED:
            self.send_counter += 1
            if self.send_counter > 3:
                _LOGGER.warning("Timeout: Zu viele Wiederholungen, trenne Verbindung")
                await self.disconnect()
                return
            if self.last_send_buffer:
                await self.send(self.last_send_buffer)
            self.reset_timer()

    async def wait_and_poll(self):
        # Nur Pollen wenn konfiguriert
        if self.device_config and not self.device_config.get("stehend", True):
            return
        await asyncio.sleep(self.polling_interval)
        await self.controller(ACTION_IK3)

    def reset_timer(self):
        if self.timer_task: self.timer_task.cancel()
        self.timer_task = asyncio.create_task(self.timer_expired())

    async def timer_expired(self):
        await asyncio.sleep(self.polling_interval + 1)
        await self.controller(ACTION_TIMER_EXPIRED)

    def process_packet(self, data):
        if not check_crc16(data):
            _LOGGER.warning("CRC Error")
            return False
            
        offset = 0
        self.tc_rec = struct.unpack('>I', data[0:4])[0]
        offset += 6 # + CRC
        self.rc_rec = struct.unpack('>I', data[6:10])[0]
        offset += 4
        
        ik = data[10]; pk = data[11]; l = data[12]
        offset += 3
        
        # _LOGGER.debug(f"RX Parsed: TC={self.tc_rec}, RC={self.rc_rec}, IK={ik}")
        
        if pk != 1:
            asyncio.create_task(self.controller(ACTION_IK6))
            return False

        self.send_counter = 0
        
        if ik == 1: return True
        elif ik == 2:
            asyncio.create_task(self.controller(ACTION_IK3))
            return True
        elif ik == 3:
            asyncio.create_task(self.controller(ACTION_IK3_AFTER_POLL))
            return True
        elif ik == 4:
            payload = data[offset:offset+l]
            self.parse_vds_payload(payload)
            if self.send_queue:
                asyncio.create_task(self.controller(ACTION_IK4))
            else:
                asyncio.create_task(self.controller(ACTION_IK3_AFTER_POLL))
            return True
        elif ik == 7:
            expected_tc = (self.last_sent_rc - 1) & 0xFFFFFFFF
            if self.tc_rec != expected_tc:
                self.tc_rec = expected_tc
            asyncio.create_task(self.send_ik3())
            asyncio.create_task(self.controller(ACTION_IK3_AFTER_POLL))
            return True
            
        asyncio.create_task(self.controller(ACTION_IK5))
        return True

    def parse_vds_payload(self, data):
        offset = 0
        while offset < len(data):
            if offset + 2 > len(data): break
            sl = data[offset]
            typ = data[offset+1]
            offset += 2
            
            if offset + sl > len(data): break
            content = data[offset : offset+sl]
            
            if typ == 0x56: # Identnummer
                ident_str = self.decode_ident(content)
                _LOGGER.info(f"Gerät Identifiziert: {ident_str}")
                self.identnr = ident_str
                # Callback: Gerät hat sich gemeldet
                if self.event_callback:
                    self.event_callback("connected", {"identnr": ident_str, "keynr": self.key_nr_rec})
                
            elif typ == 0x02: # Meldung
                if len(content) >= 5:
                    geraet = (content[0] >> 4) & 0x0F
                    bereich = content[0] & 0x0F
                    adresse = content[1]
                    adr_erw = content[3]
                    meldungsart = content[4]
                    
                    event_data = {
                        "identnr": self.identnr,
                        "keynr": self.key_nr_rec,
                        "geraet": geraet,
                        "bereich": bereich,
                        "adresse": adresse,
                        "code": meldungsart,
                        "text": VDS_MESSAGES.get(meldungsart, f"Unbekannt ({meldungsart})")
                    }
                    
                    if adr_erw == 1:
                        event_data["quelle"] = "Eingang"
                        event_data["zustand"] = "Ein" if meldungsart < 128 else "Aus"
                    elif adr_erw == 2:
                        event_data["quelle"] = "Ausgang"
                    
                    _LOGGER.info(f"Alarm: {event_data}")
                    if self.event_callback:
                        self.event_callback("alarm", event_data)

                    # Quittung
                    ack_record = bytearray(data[offset-2 : offset+sl])
                    ack_record[1] = 0x03 
                    self.send_queue.append(ack_record)

            elif typ == 0x40: # Testmeldung
                if self.event_callback:
                    self.event_callback("status", {"identnr": self.identnr, "keynr": self.key_nr_rec, "msg": "Testmeldung"})

                # Quittung
                ack_record = bytearray(data[offset-2 : offset+sl])
                ack_record[1] = 0x41
                self.send_queue.append(ack_record)
            
            offset += sl

    def decode_ident(self, data):
        res = ""
        for b in data:
            low = b & 0x0F; high = (b >> 4) & 0x0F
            if low != 0xF: res += str(low)
            if high != 0xF: res += str(high)
        return res

class VdSAsyncServer:
    def __init__(self, host, port, devices, event_callback):
        self.host = host
        self.port = port
        self.devices = devices # {keynr: config_dict}
        self.event_callback = event_callback
        self.server = None

    async def start(self):
        self.server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        _LOGGER.info(f"VdS Server gestartet auf {self.port}")
        return self.server

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            _LOGGER.info("VdS Server gestoppt")

    async def handle_client(self, reader, writer):
        conn = VdSConnection(reader, writer, self.devices, self.event_callback)
        await conn.run()
