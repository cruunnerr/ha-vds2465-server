# VdS 2465 Server for Home Assistant

This Home Assistant custom component implements a **VdS 2465 Server**. It allows your Home Assistant instance to act as a receiver (receiving center/NSL) for alarm systems using the VdS 2465 protocol over IP (e.g., Honeywell/Novar, Telenot, etc.).

---

<details>
<summary>🇬🇧 <b>English Version (Original)</b></summary>

# VdS 2465 Server for Home Assistant

This Home Assistant custom component implements a **VdS 2465 Server**. It allows your Home Assistant instance to act as a receiver (receiving center/NSL) for alarm systems using the VdS 2465 protocol over IP (e.g., Honeywell/Novar, Telenot, etc.).

It supports encrypted communication (AES) and translates VdS messages into Home Assistant events and sensors.

## Features

* **Receives VdS 2465 messages** directly in Home Assistant.
* **AES Encryption support**
* **Entities per Device**:
* `binary_sensor`: Connection Status (Online/Offline).
* `sensor`: Last Message (Readable text).
* `sensor`: Last Test Message (Timestamp).
* `sensor`: Manufacturer ID.


* **Events**: Fires `vds2465_alarm` events for every received packet, allowing for complex automations.
* **Multi-Device Support**: Connect multiple alarm panels to one server instance.
* **Configurable via UI**: Easy setup of keys and device identifiers.

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
3. **Server Port**: Enter the port you want to listen on (Default: `4100`).

### 2. Add Devices (Alarm Panels)

Once the integration is added, you need to register your alarm panels so HA can decrypt their messages.

1. Find the **VdS 2465 Server** integration card.
2. Click **Configure**.
3. Select **Add VdS Device** (Gerät hinzufügen).
4. Enter the details from your alarm panel configuration:
* **Ident number (Identnummer)**: The account number sent by the panel (e.g., `123456`).
* **Key number (Schlüsselnummer)**: The index of the key used (often `1` or matches the VdS-ID).
* **AES Key**: The 32-character hexadecimal key used for encryption.



### 3. Configure your Alarm Panel

Configure your alarm system's IP transmission unit (ÜG) to send to Home Assistant:

* **Protocol**: VdS 2465-S2.
* **Target IP**: The IP address of your Home Assistant.
* **Target Port**: `4100` (or whatever you configured).
* **Encryption**: Enabled (AES).
* **Key**: Must match the key you entered in HA.
* **Ident/Account Number**: Must match the Ident number in HA.

## Usage

### Entities

For each configured device, the following entities are created:

* **`binary_sensor.vds_[ident]_status`**:
* **On**: Device is connected and authenticated.
* **Off**: Device is disconnected.


* **`sensor.vds_[ident]_last_message`**:
* Shows the text of the last received event (e.g., "Einbruch - Ausgelöst").
* Attributes contain raw data (Event code, partition/bereich, detector group/meldegruppe).


* **`sensor.vds_[ident]_last_test_message`**:
* Timestamp of the last successful routine test message (Routine call).


* **`sensor.vds_[ident]_manufacturer_id`**:
* Displays the manufacturer string sent by the device upon connection.



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

## Troubleshooting

* **500 Internal Server Error during config**: Update the integration to the latest version.
* **Devices not connecting**: Check if the AES Key is correct (Hex format) and if the Docker container (if used) maps the port `4100` correctly.
* **"Unknown KeyNr" logs**: You haven't added the device with that specific Key ID in the integration options yet.

## Known Issues

* **Devices not connecting after HA restart**: This is just a frontend error. As soon as a message is being sent from the alarm device to HA it will shown as connected again. May be fixed in the future.
* **Manufactur isn't shown correctly**: Instead of the manufactur code like `DS6700 V7.12` it just shows the ID Number. Will be fixed in the future.

## License

MIT

</details>

---

<details>
<summary>🇩🇪 <b>Deutsche Version (Übersetzung)</b></summary>

# VdS 2465 Server für Home Assistant

Diese Home Assistant Custom Component implementiert einen **VdS 2465 Server**. Sie ermöglicht es deiner Home Assistant Instanz, als Empfänger (Empfangszentrale/NSL) für Alarmanlagen zu fungieren, die das VdS 2465 Protokoll über IP nutzen (z. B. Honeywell/Novar, Telenot, etc.).

Die Integration unterstützt verschlüsselte Kommunikation (AES) und übersetzt VdS-Nachrichten in Home Assistant Events und Sensoren.

## Funktionen

* **Empfang von VdS 2465 Nachrichten** direkt in Home Assistant.
* **Unterstützung für AES-Verschlüsselung**
* **Entitäten pro Gerät**:
* `binary_sensor`: Verbindungsstatus (Online/Offline).
* `sensor`: Letzte Meldung (Lesbarer Text).
* `sensor`: Letzter Routineruf (Zeitstempel).
* `sensor`: Hersteller-ID.


* **Events**: Feuert `vds2465_alarm` Events für jedes empfangene Paket, was komplexe Automatisierungen ermöglicht.
* **Multi-Geräte-Unterstützung**: Verbinde mehrere Alarmanlagen mit einer Server-Instanz.
* **Konfigurierbar über die Benutzeroberfläche**: Einfache Einrichtung von Schlüsseln und Gerätekennungen.

## Installation

### Option 1: HACS (Empfohlen)

1. Öffne **HACS** in Home Assistant.
2. Gehe zu "Integrationen" -> "Benutzerdefinierte Repositories" (über die 3 Punkte in der oberen rechten Ecke).
3. Füge die URL dieses Repositories hinzu: `https://github.com/cruunnerr/ha-vds2465-server`.
4. Wähle die Kategorie **Integration**.
5. Klicke auf **Hinzufügen**.
6. Suche nach **VdS 2465 Server** und installiere ihn.
7. **Starte Home Assistant neu**.

### Option 2: Manuelle Installation

1. Lade den Ordner `custom_components/vds2465` aus diesem Repository herunter.
2. Kopiere ihn in das Verzeichnis `config/custom_components/` deines Home Assistant.
3. Starte Home Assistant neu.

## Konfiguration

### 1. Integration hinzufügen

1. Gehe zu **Einstellungen** -> **Geräte & Dienste**.
2. Klicke auf **Integration hinzufügen** und suche nach **VdS 2465 Server**.
3. **Server Port**: Gib den Port ein, auf dem der Server lauschen soll (Standard: `4100`).

### 2. Geräte hinzufügen (Alarmanlagen)

Sobald die Integration hinzugefügt wurde, musst du deine Alarmanlagen registrieren, damit HA deren Nachrichten entschlüsseln kann.

1. Suche die **VdS 2465 Server** Integrationskarte.
2. Klicke auf **Konfigurieren**.
3. Wähle **Add VdS Device** (Gerät hinzufügen).
4. Gib die Details aus der Konfiguration deiner Alarmanlage ein:
* **Identnummer (Ident number)**: Die von der Anlage gesendete Kontonummer (z. B. `123456`).
* **Schlüsselnummer (Key number)**: Der Index des verwendeten Schlüssels (oft `1` oder passend zur VdS-ID).
* **AES Key**: Der 32-stellige Hexadezimal-Schlüssel, der für die Verschlüsselung verwendet wird.



### 3. Alarmanlage konfigurieren

Konfiguriere das IP-Übertragungsgerät (ÜG) deiner Alarmanlage für den Versand an Home Assistant:

* **Protokoll**: VdS 2465-S2.
* **Ziel-IP**: Die IP-Adresse deines Home Assistant.
* **Ziel-Port**: `4100` (oder was auch immer konfiguriert wurde).
* **Verschlüsselung**: Aktiviert (AES).
* **Schlüssel**: Muss mit dem in HA eingegebenen Schlüssel übereinstimmen.
* **Ident/Kontonummer**: Muss mit der Identnummer in HA übereinstimmen.

## Verwendung

### Entitäten

Für jedes konfigurierte Gerät werden die folgenden Entitäten erstellt:

* **`binary_sensor.vds_[ident]_status`**:
* **An (On)**: Gerät ist verbunden und authentifiziert.
* **Aus (Off)**: Verbindung zum Gerät ist getrennt.


* **`sensor.vds_[ident]_last_message`**:
* Zeigt den Text des zuletzt empfangenen Ereignisses (z. B. "Einbruch - Ausgelöst").
* Attribute enthalten Rohdaten (Ereigniscode, Partition/Bereich, Meldegruppe).


* **`sensor.vds_[ident]_last_test_message`**:
* Zeitstempel der letzten erfolgreichen Routinetestmeldung (Routineruf).


* **`sensor.vds_[ident]_manufacturer_id`**:
* Zeigt die Herstellerkennung an, die das Gerät beim Verbindungsaufbau sendet.



### Events

Die Integration feuert ein `vds2465_alarm` Event für **jedes** empfangene gültige Paket. Dies kann für Automatisierungen genutzt werden.

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

## Fehlerbehebung

* **500 Internal Server Error während der Konfiguration**: Aktualisiere die Integration auf die neueste Version.
* **Geräte verbinden sich nicht**: Überprüfe, ob der AES-Key korrekt ist (Hex-Format) und ob der Docker-Container (falls verwendet) den Port `4100` korrekt weiterleitet.
* **"Unknown KeyNr" Logs**: Du hast das Gerät mit dieser spezifischen Schlüssel-ID (Key ID) noch nicht in den Integrationsoptionen hinzugefügt.

## Bekannte Probleme

* **Geräte verbinden sich nach HA-Neustart nicht**: Dies ist lediglich ein Anzeige-Fehler im Frontend. Sobald eine Nachricht von der Alarmanlage an HA gesendet wird, wird der Status wieder als verbunden angezeigt. Dies wird eventuell in Zukunft behoben.
* **Hersteller wird nicht korrekt angezeigt**: Anstelle des Herstellercodes wie `DS6700 V7.12` wird nur die ID-Nummer angezeigt. Dies wird in Zukunft behoben.

## Lizenz

MIT

</details>

---
