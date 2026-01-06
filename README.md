# VdS 2465 Server for Home Assistant

This Home Assistant custom component implements a **VdS 2465 Server**. It allows your Home Assistant instance to act as a receiver (receiving center/NSL) for alarm systems using the VdS 2465 protocol over IP.

---

<details>
<summary>🇬🇧 <b>English Version</b></summary>

# VdS 2465 Server for Home Assistant

This Home Assistant custom component implements a **VdS 2465 Server**. It allows your Home Assistant instance to act as a receiver (receiving center/NSL) for alarm systems using the VdS 2465 protocol over IP.

The integration supports encrypted communication (AES), persistent and demand-controlled connections, switching of outputs, and translates VdS messages into Home Assistant events and sensors with a wide range of attributes.

## Features

* **Receive VdS 2465 messages** directly in Home Assistant.
* **AES Encryption support**.
* **Switch outputs** on the transmission device (ÜG).
* **Automatic sensor creation** when a new channel (address) is received.
* **State Persistence**: Optional recovery of sensor states and attributes after a Home Assistant restart.
* **Entities per Device**:
    * `binary_sensor`: Connection Status (Online/Offline).
    * `sensor`: Last Message (Readable text).
    * `sensor`: Last Routine Call (Timestamp).
    * `sensor`: Manufacturer ID.
    * `switch`: Outputs.

* **Events**: Fires `vds2465_alarm` events for every valid packet received, allowing for complex automations.
* **Multi-Device Support**: Connect multiple alarm panels or transmission devices to a single server instance. Unique assignment via Ident number and key.
* **Configurable via UI**: Easy setup of keys, device identifiers, polling intervals, and ports.

## How to Install

### Option 1: HACS (Recommended)

1. Open **HACS** in Home Assistant.
2. Go to "Integrations" -> "Custom repositories" (via the 3 dots in the top right corner).
3. Add the URL of this repository: `https://github.com/cruunnerr/ha-vds2465-server`.
4. Select category **Integration**.
5. Click **Add**.
6. Search for **VdS 2465 Server** and install it.
7. **Restart Home Assistant**.

### Option 2: Manual Installation

1. Download the `custom_components/vds2465` folder from this repository.
2. Copy it to your Home Assistant's `config/custom_components/` directory.
3. Restart Home Assistant.

## How to Configure

### 1. Add Integration

1. Go to **Settings** -> **Devices & Services**.
2. Click **Add Integration** and search for **VdS 2465 Server**.
3. **Server Port**: Enter the port you want the server to listen on (Default: `4100`).
4. **Polling Interval**: Set how often the server polls the alarm panel (Default: `5s`). Lower values reduce latency.
5. **Restore States**: Enable to keep the last received sensor values and attributes after a restart.

### 2. Manage Devices (Alarm Panels)

Once the integration is added, you must register your alarm panels so HA can decrypt their messages.

1. Find the **VdS 2465 Server** integration card.
2. Click **Configure** (gear icon).
3. **Global Settings**: Update port, interval, or persistence.
4. **Add VdS Device**: Add a new alarm panel.
5. **Edit VdS Device**: View or modify existing devices (including the AES key in plain text).
6. **Remove VdS Device**: Delete a registered device.

**Device details required:**
* **Ident number (Identnummer)**: The account number sent by the panel (e.g., `123456`).
* **Key number (Schlüsselnummer)**: The index of the key used. Leave blank for unencrypted connections.
* **AES Key**: The 32-character hexadecimal key used for encryption.
* **Device Number**: Important for switching outputs. (Default: 1).
* **Area Number**: Important for switching outputs. (Default: 1).

### 3. Configure your Alarm Panel

Configure your alarm system's IP transmission unit (ÜG) to send to Home Assistant:

* **Protocol**: VdS 2465-S2.
* **Target IP**: The IP address of your Home Assistant.
* **Target Port**: `4100` (or whatever you configured).
* **Encryption**: Enabled/Disabled as needed.
* **AES Key (HEX format, 32 characters)**: Must match the key entered in HA.
* **Ident/Account Number**: Must match the Ident number in HA.

## Usage

### Entities

For each configured device, the following entities are created:

* **`binary_sensor.vds_[ident]_status`**:
    * **On**: Device is connected and authenticated.
    * **Off**: Device is disconnected.
    (For persistent connections, this state should ideally always be "Connected" to allow for quick failure detection.)

* **`sensor.vds_[ident]_last_message`**:
    * Shows the text of the last received event (e.g., "Einbruch - Ausgelöst").
    * Attributes contain all raw data sent with the message, for example:
        - Identnr
        - Keynr
        - Geraetenummer (Device number)
        - Bereichsnummer (Area number)
        - Adresse (Channel number)
        - Code (VdS2465 event code)
        - Text (VdS2465 event text)
        - Type (Message type)
        - Priority (0 = high, 50 = medium, 100 = low)
        - Entstehungszeit (Timestamp from the panel)
        - Manufacturer (Manufacturer-specific ID)
        - Area name (Custom area/partition label)
        - Quelle (Input or Output)
        - Zustand (On or Off)
        - Msg (e.g., "Testmeldung")
        - Transport service (Type of transmission, e.g., TCP/IP Intranet)

* **`sensor.vds_[ident]_last_test_message`**:
    * Timestamp of the last successful routine test message (Routine call).

* **`sensor.vds_[ident]_manufacturer_id`**:
    * Displays the manufacturer identification string.

* **Auto-generated Sensors**:
    * Sensors for individual channels (addresses) and output acknowledgments are created automatically upon reception and survive restarts.
    * When switching outputs, the transmission device sends feedback upon success. A sensor is generated for this "Acknowledgement message".

### Events

The integration fires a `vds2465_alarm` event for **every** valid packet received. You can use this for automations.

**Event Data Example:**

```json
{
    "event_type": "vds2465_alarm",
    "data": {
        "identnr": "123456",
        "keynr": 1,
        "geraet": 1,
        "bereich": 1,
        "adresse": 5,
        "code": 34,
        "text": "Einbruch - Ausgeloest",
        "quelle": "Eingang",
        "zustand": "Ein"
    }
}
```

### Example Automation

```yaml
alias: VdS Alarm Trigger
trigger:
  - platform: event
    event_type: vds2465_alarm
    event_data:
      identnr: "123456"
      code: 34  # 34 = Burglary / Einbruch
condition: []
action:
  - service: notify.mobile_app_myphone
    data:
      message: "Alarm triggered in area {{ trigger.event.data.bereich }}!"
```

</details>

---

<details>

<summary>🇩🇪 <b>Deutsche Version</b></summary>

# VdS 2465 Server für Home Assistant

Diese Home Assistant Custom Component implementiert einen **VdS 2465 Server**. Sie ermöglicht es deiner Home Assistant Instanz, als Empfänger (Empfangszentrale/NSL) für Alarmanlagen zu fungieren, die das VdS 2465 Protokoll über IP nutzen.

Die Integration unterstützt verschlüsselte Kommunikation (AES), stehende und bedarfsgesteuerte Verbindungen, Schalten von Ausgängen und übersetzt VdS-Nachrichten in Home Assistant Events und Sensoren mit einer Vielzahl an Attributen.

## Funktionen

* **Empfang von VdS 2465 Nachrichten** direkt in Home Assistant.
* **Unterstützung für AES-Verschlüsselung**.
* **Schalten von Ausgängen am Übertragungsgerät**.
* **Automatisches Anlegen von neuen Sensoren** bei Empfang eines neuen Kanals.
* **Zustandsspeicherung**: Optionale Wiederherstellung von Sensorwerten und Attributen nach einem Home Assistant Neustart.
* **Entitäten pro Gerät**:
    * `binary_sensor`: Verbindungsstatus (Online/Offline).
    * `sensor`: Letzte Meldung (Lesbarer Text).
    * `sensor`: Letzter Routineruf (Zeitstempel).
    * `sensor`: Hersteller-ID.
    * `switch`: Ausgänge.

* **Events**: Feuert `vds2465_alarm` Events für jedes empfangene Paket, was komplexe Automatisierungen ermöglicht.
* **Multi-Geräte-Unterstützung**: Verbinde mehrere Alarmanlagen/Übertragungsgeräte mit einer Server-Instanz.
* **Konfigurierbar über die Benutzeroberfläche**: Einfache Einrichtung von Schlüsseln, Intervallen und Ports.

## Installation

### Option 1: HACS (Empfohlen)

1. Öffne **HACS** in Home Assistant.
2. Gehe zu "Integrationen" -> "Benutzerdefinierte Repositories" (über die 3 Punkte in der oberen rechten Ecke).
3. Füge die URL dieses Repositories hinzu: `https://github.com/cruunnerr/ha-vds2465-server`.
4. Wähle die Kategorie **Integration** und klicke auf **Hinzufügen**.
5. Suche nach **VdS 2465 Server** und installiere ihn.
6. **Starte Home Assistant neu**.

### Option 2: Manuelle Installation

1. Lade den Ordner `custom_components/vds2465` aus diesem Repository herunter.
2. Kopiere ihn in das Verzeichnis `config/custom_components/` deines Home Assistant.
3. Starte Home Assistant neu.

## Konfiguration

### 1. Integration hinzufügen

1. Gehe zu **Einstellungen** -> **Geräte & Dienste**.
2. Klicke auf **Integration hinzufügen** und suche nach **VdS 2465 Server**.
3. **Server Port**: Port für den VdS-Server (Standard: `4100`).
4. **Polling-Intervall**: Legt fest, wie oft der Server die EMA abfragt (Standard: `5s`). Kleinere Werte reduzieren die Latenz.
5. **Zustände wiederherstellen**: Aktivieren, um die letzten Sensordaten nach einem Neustart zu behalten.

### 2. Geräte verwalten (Alarmanlagen)

Sobald die Integration hinzugefügt wurde, musst du deine Alarmanlagen registrieren.

1. Suche die **VdS 2465 Server** Integrationskarte und klicke auf **Konfigurieren**.
2. **Globale Einstellungen**: Port, Intervall oder Speicherung anpassen.
3. **Gerät hinzufügen**: Eine neue EMA registrieren.
4. **Gerät bearbeiten**: Vorhandene Geräte ansehen (inkl. AES-Key im Klartext) oder ändern.
5. **Gerät entfernen**: Ein registriertes Gerät löschen.

**Benötigte Gerätedaten:**
* **Identnummer**: Die Kontonummer der Anlage (z. B. `123456`).
* **Schlüsselnummer**: Der Index des verwendeten Schlüssels.
* **AES Key**: Der 32-stellige Hexadezimal-Schlüssel für die Verschlüsselung.
* **Gerätenummer / Bereichsnummer**: Wichtig für das Schalten von Ausgängen.

### 3. Alarmanlage konfigurieren

Konfiguriere das IP-Übertragungsgerät (ÜG) deiner Alarmanlage für den Versand an Home Assistant:

* **Protokoll**: VdS 2465-S2.
* **Ziel-IP**: Die IP-Adresse deines Home Assistant.
* **Ziel-Port**: `4100` (oder konfigurierten Port).
* **AES-Schlüssel (HEX-Format)**: Muss mit dem in HA eingegebenen Schlüssel übereinstimmen.
* **Ident/Kontonummer**: Muss mit der Identnummer in HA übereinstimmen.

## Verwendung

### Entitäten

* **`binary_sensor.vds_[ident]_status`**: Online/Offline-Status der Verbindung.
* **`sensor.vds_[ident]_last_message`**: Zeigt den Text des zuletzt empfangenen Ereignisses (z. B. "Einbruch - Ausgelöst").
Attribute enthalten Rohdaten , welche mit der Nachricht geschickt wurden - zum Beispiel:
    - Identnr
    - Keynr
    - Geraetenummer
    - Bereichsnummer
    - Adresse (Kanalnummer)
    - Code (VdS2465 Ereigniscode)
    - Text (VdS2465 Ereignistext)
    - Type (Typ der Meldung)
    - Priority (0 = hoch, 50 = mittel, 100 = niedrig)
    - Entstehungszeit (Entstehungszeit der Meldung)
    - Manufacturer (Herstellerspezifische Gerätekennung)
    - Area name (individueller Meldungstext)
    - Quelle (Eingang oder Ausgang)
    - Zustand (An oder Aus)
    - Msg (z.B. Testmeldung)
    - Transport service (Art der Übertragung, z.B. TCP/IP-Intranet-Uebertragung)
* **`sensor.vds_[ident]_last_test_message`**: Zeitstempel des letzten erfolgreichen Routinerufs.
* **`sensor.vds_[ident]_manufacturer_id`**: Herstellerkennung des Geräts.
* **Automatisch generierte Sensoren**: Sensoren für einzelne Kanäle (Adressen) und Ausgangs-Rückmeldungen werden automatisch erstellt und bleiben über Neustarts hinweg erhalten.
Beim Schalten von Ausgängen schickt das Übertragungsgerät eine Rückmeldung über den erfolgreichen Schaltvorgang. Es wird ein Sensor für diese "Quittiermeldung" generiert.

### Events

Die Integration feuert ein `vds2465_alarm` Event für jedes empfangene Paket.

**Beispiel für Event-Daten:**

```json
{
    "event_type": "vds2465_alarm",
    "data": {
        "identnr": "123456",
        "keynr": 1,
        "geraet": 1,
        "bereich": 1,
        "adresse": 5,
        "code": 34,
        "text": "Einbruch - Ausgeloest",
        "quelle": "Eingang",
        "zustand": "Ein"
    }
}
```

### Beispiel Automatisierung

```yaml
alias: VdS Alarm Auslöser
trigger:
  - platform: event
    event_type: vds2465_alarm
    event_data:
      identnr: "123456"
      code: 34  # 34 = Einbruch
condition: []
action:
  - service: notify.mobile_app_meinhandy
    data:
      message: "Alarm im Bereich {{ trigger.event.data.bereich }} ausgelöst!"
```

</details>

---

<details>
<summary>📊 <b>VdS2465 Event Codes List</b></summary>

```text
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
```

</details>


# License

MIT