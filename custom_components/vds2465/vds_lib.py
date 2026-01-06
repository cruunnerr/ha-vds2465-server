import asyncio
import struct
import logging
import binascii
import os
import datetime
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

VDS_ERRORS = {
    0: "Allgemein: Fehler",
    1: "Nicht bekannt",
    2: "Nicht erfuellbar",
    3: "Negativquittierung",
    4: "Falscher Sicherheitscode",
    0x10: "Adresse nicht vorhanden/ausserhalb Bereich",
    0x18: "Funktion an dieser Adresse nicht moeglich",
    0x20: "Daten ausserhalb des Wertebereichs",
    0x80: "Pruefsumme fehlerhaft"
}

VDS_TRANSPORT_SERVICES = {
    0x10: "Analoge Festverbindung",
    0x20: "Analoge Bedarfsgesteuerte Verbindung",
    0x30: "X.25 bzw. Datex-P",
    0x40: "ISDN, B-Kanal",
    0x50: "ISDN, D-Kanal",
    0x60: "Buendelfunk, Betriebsfunk",
    0x70: "Datenfunk",
    0x80: "Mobilfunk",
    0x90: "TCP/IP-Intranet-Uebertragung"
}

def calculate_checksum_logic(data, check_mode=False):
    crc = 0
    original = 0
    length = len(data)
    for pos in range(0, length, 2):
        temp = data[pos] << 8
        if pos + 1 == length:
            temp |= 0x00
        else:
            temp |= data[pos + 1]
        
        if check_mode and pos == 4:
            original = temp
        else:
            crc += temp
            if crc > 65535:
                crc &= 0xffff
                crc += 1
            
    crc = ~crc & 0xffff
    return crc, original

def check_crc16(data):
    if len(data) < 6:
        return False
    calculated, original = calculate_checksum_logic(data, check_mode=True)
    if calculated != original:
        _LOGGER.debug(f"CRC Mismatch: Rec={original:04X} Calc={calculated:04X} Data={binascii.hexlify(data)}")
    return calculated == original

def set_crc16(data):
    crc, _ = calculate_checksum_logic(data, check_mode=True)
    struct.pack_into('>H', data, 4, crc)
    return data

def pad_data(data):
    length = len(data)
    diff = 16 - (length % 16)
    if length + diff < MIN_LENGTH:
        diff = MIN_LENGTH - length
    return data + (b'\x00' * diff)

def get_time_buffer():
    now = datetime.datetime.now()
    # Satz 50: [Len(9), Typ(0x50), Jahr%100, Jahr//100, Monat, Tag, Stunde, Minute, Sekunde]
    buf = bytearray(9)
    buf[0] = 7 # Len payload only
    buf[1] = 0x50
    buf[2] = now.year % 100
    buf[3] = now.year // 100
    buf[4] = now.month
    buf[5] = now.day
    buf[6] = now.hour
    buf[7] = now.minute
    buf[8] = now.second
    return buf


class VdSConnection:
    def __init__(self, reader, writer, devices_config, event_callback, polling_interval=5):
        self.reader = reader
        self.writer = writer
        self.peer = writer.get_extra_info('peername')
        self.devices_config = devices_config # List of dicts: [{key: "...", identnr: "...", keynr: ...}, ...]
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
        self.polling_interval = polling_interval
        self.vds_request_counter = 0
        
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
            _LOGGER.info(f"Verbindung von {self.peer} zurückgesetzt")
        except Exception as e:
            _LOGGER.error(f"Fehler in Verbindung {self.peer}: {e}", exc_info=True)
        finally:
            await self.disconnect()

    async def disconnect(self):
        if not self._running:
            return
        
        self._running = False
        _LOGGER.info(f"Trenne Verbindung zu {self.peer}")
        if (self.identnr or self.key_nr_rec) and self.event_callback:
             try:
                self.event_callback("disconnected", {"identnr": self.identnr, "keynr": self.key_nr_rec})
             except Exception as e:
                _LOGGER.error(f"Error in disconnect callback: {e}")

        if self.timer_task: self.timer_task.cancel()
        if self.poll_task: self.poll_task.cancel()
        
        try:
            self.writer.close()
            try:
                await asyncio.wait_for(self.writer.wait_closed(), timeout=1.0)
            except asyncio.TimeoutError:
                _LOGGER.warning(f"Timeout beim Schließen der Verbindung zu {self.peer}")
        except (ConnectionResetError, BrokenPipeError, AttributeError, OSError) as e:
            _LOGGER.debug(f"Fehler beim Schließen des Writers ({self.peer}): {e}")
        except Exception as e:
             _LOGGER.warning(f"Unerwarteter Fehler beim Schließen des Writers ({self.peer}): {e}")

    async def send(self, data):
        self.last_send_buffer = data
        _LOGGER.debug(f"TX ({self.peer}): {binascii.hexlify(data).upper()}")
        try:
            self.writer.write(data)
            await self.writer.drain()
        except Exception as e:
             _LOGGER.warning(f"Senden an {self.peer} fehlgeschlagen: {e}")
             await self.disconnect()

    def get_device_by_keynr(self, keynr):
        for dev in self.devices_config:
            if int(dev.get('keynr', 0)) == keynr:
                return dev
        return None

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
        _LOGGER.debug(f"Sende IK1 (Verbindungsaufbau) an {self.peer}")
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
        _LOGGER.debug(f"Sende IK3 (Poll) an {self.peer}")
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
        _LOGGER.debug(f"Sende IK4 (Daten) an {self.peer}, Payload-Länge: {len(payload)}")
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
        _LOGGER.debug(f"Sende IK5 (Ack) an {self.peer}")
        buf = bytearray(13)
        struct.pack_into('>I', buf, 0, self.tc)
        self.tc = (self.tc + 1) & 0xFFFFFFFF
        rc = (self.tc_rec + 1) & 0xFFFFFFFF
        struct.pack_into('>I', buf, 6, rc)
        self.last_sent_rc = rc
        buf[10] = 5; buf[11] = 1; buf[12] = 0
        await self.send(self.prepare_packet(buf))

    async def send_ik6(self):
        _LOGGER.debug(f"Sende IK6 (Nak) an {self.peer}")
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
            while len(self.buffer) >= 4:
                key_nr = struct.unpack('>H', self.buffer[0:2])[0]
                sl = struct.unpack('>H', self.buffer[2:4])[0]
                
                total_len = 4 + sl
                if len(self.buffer) < total_len:
                    break # Warten auf restliche Daten
                
                packet_data = self.buffer[4:total_len]
                _LOGGER.debug(f"RX Header ({self.peer}): KeyNr={key_nr}, Len={sl}")
                
                self.buffer = self.buffer[total_len:]
                self.key_nr_rec = key_nr
                
                if key_nr > 0:
                    dev = self.get_device_by_keynr(key_nr)
                    if dev:
                        _LOGGER.debug(f"Entschlüssele Paket mit KeyNr {key_nr}")
                        self.device_config = dev
                        decrypted = self.decrypt(packet_data)
                    else:
                        _LOGGER.warning(f"Unbekannte KeyNr {key_nr} von {self.peer}")
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
            
            if self.vds_request_counter > 0:
                _LOGGER.debug(f"Burst Mode: {self.vds_request_counter} verbleibend")
                await self.send_ik3()
                self.vds_request_counter -= 1
            else:
                self.poll_task = asyncio.create_task(self.wait_and_poll())

        elif action == ACTION_TIMER_EXPIRED:
            self.send_counter += 1
            _LOGGER.debug(f"Timer abgelaufen für {self.peer}, Wiederholung {self.send_counter}")
            if self.send_counter > 3:
                _LOGGER.warning(f"Timeout nach 3 Wiederholungen ({self.peer})")
                await self.disconnect()
                return
            if self.last_send_buffer:
                await self.send(self.last_send_buffer)
            self.reset_timer()

    async def wait_and_poll(self):
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
            _LOGGER.warning(f"CRC Fehler im Paket von {self.peer}")
            return False
            
        offset = 0
        self.tc_rec = struct.unpack('>I', data[0:4])[0]
        offset += 6 # + CRC
        self.rc_rec = struct.unpack('>I', data[6:10])[0]
        offset += 4
        
        ik = data[10]; pk = data[11]; l = data[12]
        offset += 3
        
        _LOGGER.debug(f"RX Parsed ({self.peer}): TC={self.tc_rec:08X}, RC={self.rc_rec:08X}, IK={ik}, PK={pk}, L={l}")
        
        if pk != 1:
            _LOGGER.warning(f"Ungültige PK {pk} von {self.peer}")
            asyncio.create_task(self.controller(ACTION_IK6))
            return False

        self.send_counter = 0
        
        if ik == 1: 
            if self.send_queue:
                asyncio.create_task(self.controller(ACTION_IK4))
            else:
                asyncio.create_task(self.controller(ACTION_IK3_AFTER_POLL))
            return True
            
        elif ik == 2:
            if self.send_queue:
                asyncio.create_task(self.controller(ACTION_IK4))
            else:
                asyncio.create_task(self.controller(ACTION_IK3))
            return True

        elif ik == 3:
            if self.send_queue:
                asyncio.create_task(self.controller(ACTION_IK4))
            else:
                asyncio.create_task(self.controller(ACTION_IK3_AFTER_POLL))
            return True
        elif ik == 4:
            payload = data[offset:offset+l]
            _LOGGER.debug(f"RX Payload ({self.peer}): {binascii.hexlify(payload).upper()}")
            self.parse_vds_payload(payload)
            if self.send_queue:
                asyncio.create_task(self.controller(ACTION_IK4))
            else:
                asyncio.create_task(self.controller(ACTION_IK3_AFTER_POLL))
            return True
        elif ik == 7:
            expected_tc = (self.last_sent_rc - 1) & 0xFFFFFFFF
            if self.tc_rec != expected_tc:
                _LOGGER.debug(f"IK7: Zaehler TC korrigiert von {self.tc_rec:X} auf {expected_tc:X}")
                self.tc_rec = expected_tc
            
            self.vds_request_counter = 5
            if self.poll_task: self.poll_task.cancel()
            asyncio.create_task(self.send_ik3())
            return True
            
        asyncio.create_task(self.controller(ACTION_IK5))
        return True

    def parse_vds_payload(self, data):
        offset = 0
        records = []
        while offset < len(data):
            if offset + 2 > len(data): break
            sl = data[offset]
            typ = data[offset+1]
            offset += 2
            
            if offset + sl > len(data): break
            content = data[offset : offset+sl]
            records.append((typ, content, sl))
            offset += sl

        packet_context = {}
        for typ, content, sl in records:
            _LOGGER.debug(f"Verarbeite Kontext-Satztyp 0x{typ:02X}, Länge {sl}")
            if typ == 0x56: # Identnummer
                self.identnr = self.decode_ident(content)
                _LOGGER.info(f"Meldungseingang von ({self.peer}): ID: {self.identnr}")
                packet_context["identnr"] = self.identnr
                
                matched_dev_config = None
                matched_keynr = 0
                
                for conf in self.devices_config:
                    if conf.get('identnr') == self.identnr:
                        matched_dev_config = conf
                        matched_keynr = int(conf.get('keynr', 0))
                        break
                
                if matched_dev_config:
                    self.device_config = matched_dev_config
                    if self.key_nr_rec != matched_keynr:
                        _LOGGER.warning(f"Mismatch ({self.identnr}): KeyNr {self.key_nr_rec} empfangen, {matched_keynr} erwartet")
                else:
                     _LOGGER.warning(f"Unbekannte Identnummer {self.identnr} von {self.peer}")
                     asyncio.create_task(self.disconnect())
                     return

                if self.event_callback:
                    self.event_callback("connected", {"identnr": self.identnr, "keynr": self.key_nr_rec})
            
            elif typ == 0x51: # Manufacturer ID
                try:
                    m_str = content.strip(b'\x00').decode('iso-8859-1')
                    packet_context["manufacturer"] = m_str
                except Exception: pass

            elif typ == 0x54: # Area Name
                try:
                    a_str = content.strip(b'\x00').decode('iso-8859-1').replace('\r', ' ').strip()
                    packet_context["area_name"] = a_str
                except Exception: pass

            elif typ == 0x50: # Zeit / Entstehungszeit
                try:
                    if len(content) >= 7:
                        year = content[0] + content[1]*100
                        dt = datetime.datetime(year, content[2], content[3], content[4], content[5], content[6])
                        packet_context["entstehungszeit"] = dt.strftime("%d.%m.%Y, %H:%M:%S")
                except Exception: pass

            elif typ == 0x01: # Priorität
                if len(content) >= 1:
                    packet_context["priority"] = content[0]

            elif typ == 0x61: # Transportdienst
                if len(content) >= 1:
                    service_id = content[0]
                    packet_context["transport_service"] = VDS_TRANSPORT_SERVICES.get(service_id, f"Unbekannt ({service_id})")

            elif typ in [0x10, 0x24, 0x26, 0x55, 0xFF]:
                _LOGGER.debug(f"Ignoriere VdS Satztyp: 0x{typ:02X}")

            elif typ == 0x73: # Telegrammzähler
                try:
                    if len(content) >= 5:
                        counter = struct.unpack('>I', content[1:5])[0]
                        packet_context["telegram_counter"] = counter
                except Exception: pass
            
            elif typ == 0x41: # Quittung Testmeldung
                _LOGGER.debug(f"VdS Quittung Testmeldung empfangen")

        for typ, content, sl in records:
            _LOGGER.debug(f"Verarbeite Aktions-Satztyp 0x{typ:02X}, Länge {sl}")
            if typ == 0x02 or typ == 0x03 or typ == 0x04 or typ == 0x20: # Meldung / Status
                if len(content) >= 5:
                    geraet = (content[0] >> 4) & 0x0F
                    bereich = content[0] & 0x0F
                    adresse = content[1]
                    adr_erw = content[3]
                    meldungsart = content[4]
                    
                    msg_type_text = "Meldung"
                    if typ == 0x20: msg_type_text = "Status"
                    
                    event_data = {
                        "identnr": self.identnr,
                        "keynr": self.key_nr_rec,
                        "geraet": geraet,
                        "bereich": bereich,
                        "adresse": adresse,
                        "code": meldungsart,
                        "text": VDS_MESSAGES.get(meldungsart, f"Unbekannt ({meldungsart})"),
                        "type": msg_type_text,
                        **packet_context
                    }
                    
                    if len(content) > 10: 
                        try:
                            potential_text = content[5:].strip(b'\x00').decode('iso-8859-1')
                            if len(potential_text) > 2 and any(c.isalnum() for c in potential_text):
                                event_data["msg_text"] = potential_text
                        except Exception: pass

                    if adr_erw == 1:
                        event_data["quelle"] = "Eingang"
                        event_data["zustand"] = "Ein" if meldungsart < 128 else "Aus"
                    elif adr_erw == 2:
                        event_data["quelle"] = "Ausgang"
                        event_data["zustand"] = "Ein" if meldungsart < 128 else "Aus"
                    
                    if self.event_callback:
                        self.event_callback("alarm", event_data)

                    if typ == 0x02:
                        ack_record = bytearray([sl, 0x03] + list(content))
                        self.send_queue.append(ack_record)
            
            elif typ == 0x11: # Fehler
                if len(content) >= 2:
                    geraet = (content[0] >> 4) & 0x0F
                    err_code = content[1]
                    err_text = VDS_ERRORS.get(err_code, f"Unbekannter Fehler {err_code}")
                    _LOGGER.warning(f"VdS Fehler ({self.identnr}): {err_text} (Code: {err_code}, Geraet: {geraet})")
                    if self.event_callback:
                        self.event_callback("error", {"identnr": self.identnr, "code": err_code, "text": err_text})

            elif typ == 0x40: # Testmeldung
                if self.event_callback:
                    self.event_callback("status", {"identnr": self.identnr, "keynr": self.key_nr_rec, "msg": "Testmeldung", **packet_context})
                ack_head = bytearray([0, 0x41])
                time_buf = get_time_buffer()
                ack_payload = ack_head + time_buf
                self.send_queue.append(ack_payload)

            elif typ == 0x51 and self.event_callback:
                self.event_callback("manufacturer_update", {"identnr": self.identnr, "manufacturer": packet_context.get("manufacturer")})
            
            elif typ == 0x54 and self.event_callback:
                self.event_callback("area_update", {"identnr": self.identnr, "area_name": packet_context.get("area_name")})

            elif typ == 0x59: # Geraetemerkmale
                sub_offset = 1
                features = {}
                while sub_offset < len(content):
                    if sub_offset + 3 > len(content): break
                    l_sub = content[sub_offset]
                    t_sub = content[sub_offset+1]
                    i_sub = content[sub_offset+2]
                    if sub_offset + l_sub > len(content): break
                    val_bytes = content[sub_offset+3 : sub_offset+l_sub]
                    try:
                        val_str = val_bytes.decode('iso-8859-1').strip('\x00')
                        label = f"Unknown-{t_sub}"
                        if t_sub == 0: label = "MAC"
                        elif t_sub == 1: label = "IMEI"
                        elif t_sub == 2: label = "SIM-Kartennummer"
                        elif t_sub == 3: label = "Rufnummer"
                        elif t_sub == 0xFF: label = "herstellerspezifisch"
                        
                        path = "Erstweg" if i_sub == 1 else "Zweitweg"
                        features[f"{label}-{path}"] = val_str
                    except Exception: pass
                    sub_offset += l_sub
                
                if self.event_callback and features:
                    self.event_callback("features_update", {"identnr": self.identnr, "features": features})

    def decode_ident(self, data):
        res = ""
        for b in data:
            low = b & 0x0F; high = (b >> 4) & 0x0F
            if low != 0xF: res += str(low)
            if high != 0xF: res += str(high)
        return res

    def send_output_command(self, address, state, device=1, area=1):
        payload = bytearray(7)
        payload[0] = 5; payload[1] = 0x02
        gebe = ((device << 4) & 0xF0) | (area & 0x0F)
        payload[2] = gebe
        payload[3] = address & 0xFF
        payload[4] = 0x00; payload[5] = 0x02
        payload[6] = 0x00 if state else 0x80
        self.send_queue.append(payload)

class VdSAsyncServer:
    def __init__(self, host, port, devices, event_callback, polling_interval=5):
        self.host = host
        self.port = port
        self.devices = devices
        self.event_callback = event_callback
        self.polling_interval = polling_interval
        self.server = None
        self._connections = set()

    async def start(self):
        self.server = await asyncio.start_server(
            self.handle_client, self.host, self.port, reuse_address=True
        )
        _LOGGER.info(f"VdS Server gestartet auf Port {self.port}")
        return self.server

    async def stop(self):
        _LOGGER.debug("VdSAsyncServer.stop() called")
        if self.server:
            _LOGGER.debug("Closing server socket (stop accepting)...")
            self.server.close()
        if self._connections:
            _LOGGER.info(f"Closing {len(self._connections)} active connections")
            for conn in list(self._connections):
                try:
                    await conn.disconnect()
                except Exception: pass
            self._connections.clear()
        if self.server:
            try:
                await asyncio.wait_for(self.server.wait_closed(), timeout=2.0)
                _LOGGER.debug("Server socket closed")
            except Exception: pass

    async def handle_client(self, reader, writer):
        conn = VdSConnection(reader, writer, self.devices, self.event_callback, self.polling_interval)
        self._connections.add(conn)
        try:
            await conn.run()
        finally:
            self._connections.discard(conn)

    def send_output_command(self, identnr, address, state, device=1, area=1):
        for conn in self._connections:
            if conn.identnr == identnr:
                conn.send_output_command(address, state, device, area)
                return True
        return False