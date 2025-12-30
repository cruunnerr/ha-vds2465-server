# VdS 2465 Server for Home Assistant

This Home Assistant custom component implements a **VdS 2465 Server**. It allows your Home Assistant instance to act as a receiver (receiving center/NSL) for alarm systems using the VdS 2465 protocol over IP (e.g., Honeywell/Novar, Telenot, etc.).

It supports encrypted communication (AES) and translates VdS messages into Home Assistant events and sensors.

## Features

- **Receives VdS 2465 messages** directly in Home Assistant.
- **AES Encryption support**
- **Entities per Device**:
  - `binary_sensor`: Connection Status (Online/Offline).
  - `sensor`: Last Message (Readable text).
  - `sensor`: Last Test Message (Timestamp).
  - `sensor`: Manufacturer ID.
- **Events**: Fires `vds2465_alarm` events for every received packet, allowing for complex automations.
- **Multi-Device Support**: Connect multiple alarm panels to one server instance.
- **Configurable via UI**: Easy setup of keys and device identifiers.

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
   - **Ident number (Identnummer)**: The account number sent by the panel (e.g., `123456`).
   - **Key number (Schlüsselnummer)**: The index of the key used (often `1` or matches the VdS-ID).
   - **AES Key**: The 32-character hexadecimal key used for encryption.

### 3. Configure your Alarm Panel

Configure your alarm system's IP transmission unit (ÜG) to send to Home Assistant:
- **Protocol**: VdS 2465-S2.
- **Target IP**: The IP address of your Home Assistant.
- **Target Port**: `4100` (or whatever you configured).
- **Encryption**: Enabled (AES).
- **Key**: Must match the key you entered in HA.
- **Ident/Account Number**: Must match the Ident number in HA.

## Usage

### Entities

For each configured device, the following entities are created:

- **`binary_sensor.vds_[ident]_status`**:
  - **On**: Device is connected and authenticated.
  - **Off**: Device is disconnected.
- **`sensor.vds_[ident]_last_message`**:
  - Shows the text of the last received event (e.g., "Einbruch - Ausgelöst").
  - Attributes contain raw data (Event code, partition/bereich, detector group/meldegruppe).
- **`sensor.vds_[ident]_last_test_message`**:
  - Timestamp of the last successful routine test message (Routine call).
- **`sensor.vds_[ident]_manufacturer_id`**:
  - Displays the manufacturer string sent by the device upon connection.

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

- **500 Internal Server Error during config**: Update the integration to the latest version.
- **Devices not connecting**: Check if the AES Key is correct (Hex format) and if the Docker container (if used) maps the port `4100` correctly.
- **"Unknown KeyNr" logs**: You haven't added the device with that specific Key ID in the integration options yet.

## Known Issues
- **Devices not connecting after HA restart**: This is just a frontend error. As soon as a message is being sent from the alarm device to HA it will shown as connected again. Will be fixed in the future.
- **Encryption is neccessary**: Since this integration is brand new, I couldn't test every constellation yet. So for now the fields for encryption must be filled and used.

## License

MIT