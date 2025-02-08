<p align="center">
  <a href="https://www.divera247.com">
    <img src="https://www.divera247.com/downloads/grafik/divera247_logo_800.png" alt="Divera 24/7">
  </a>
</p>

- [🇩🇪 Deutsch](README.md)

# DiveraControl

**DiveraControl is still in development and may contain errors. Some planned features are still missing, and no optimization has taken place yet. If you're curious, feel free to test it!**

**If you find any bugs or miss any features, please create an [Issue](https://github.com/moehrem/DiveraControl/issues). Thank you!**

---

**DiveraControl** is an integration of Divera 24/7 into HomeAssistant. The goal of this integration is to enable extensive data exchange with Divera 24/7.

Fire stations, vehicles, and equipment are becoming increasingly smarter. However, there is hardly any (or at least not an affordable) integrative provider for small fire departments that offers a centralized system for managing, controlling, and distributing this data to coordinate smart devices. This is where HomeAssistant comes into play. It can serve as a cost-effective central control for lighting, doors and gates, monitors, voice output, vehicle positions, crew status, device locations, battery levels, custom monitors, etc. However, this requires an interface to alarm software, which this integration aims to provide.

To fully utilize this integration, extensive permissions are required in the connected unit. The target audience of this integration consists of administrators or interface users of a unit.

Since I am a firefighter myself, my primary focus is on fire departments. However, since Divera 24/7 is used in various ways and the interface remains the same for all, this integration could be useful for purposes beyond firefighting as well.

The integration also works with limited permissions but offers reduced functionality. For personal use, the long-existing [Divera 24/7 Integration for Home Assistant](https://github.com/fwmarcel/home-assistant-divera) may be more suitable.

---

## Disclaimer

In the public safety sector (BOS), data protection is of utmost importance. The use of HomeAssistant and this integration in real-world situations is entirely **at your own risk**. Ensuring compliance with data protection regulations, particularly concerning "data sharing with third parties," "data processing," and "data security," is the sole responsibility of the user.
This integration is **not affiliated with Divera 24/7** and is **not supported by Divera 24/7**.

---

## What can DiveraControl do?

- Manage multiple **different** users/units
- Connect multiple units of the same user
- Support parallel alarms

### Data Retrieval
- Alarm data
- User status
- Unit details
- Availability
- Vehicle data, including individual vehicle properties
- Permissions
- Message channels

### Data Submission
With **DiveraControl**, data can be sent to Divera. Corresponding services have been implemented in HomeAssistant. The following endpoints are available:
- User status (advanced and simple)
- Alarm creation
- Alarm modification
- Alarm closure
- Vehicle data, including individual vehicle properties
- Operational feedback
- Messages (Messenger)

---

## What can't DiveraControl do?
Divera provides many endpoints, but not all of them can be accessed via this integration. The following functions are not included:
- Managing multiple users **of the same unit**
- Deleting and archiving alarms, notifications, messages, and events
- Creating, modifying, or deleting events
- Adding attachments
- Adding crew members to vehicles, whether inside or outside of operations
- Features for dispatch centers
- Features of the PRO version (e.g., cross-unit alerting)

## What should DiveraControl be able to do?
- Manage multiple users of the same unit
- Add crew members to vehicles

---

## Installation
Currently, installation is only possible manually. A HACS integration is in progress.

To install manually, download the [latest release](https://github.com/moehrem/DiveraControl/releases/latest) and extract it into the HomeAssistant directory `config/custom_components/diveracontrol`.

## Configuration
The setup is done by entering the username and password. None of this is stored; instead, the integration retrieves the user's API key and stores it in HomeAssistant.
You can log in using personal credentials. If the user is assigned to multiple units, each unit will be added as a separate hub within the integration.

For better permission management, it is recommended to use a system user for the unit. Divera allows the creation of system users under **Management** -> **Interfaces** -> **System Users**. System users cannot log in directly; instead, the integration will prompt for their API key.

Another alternative is to use the unit's central interface user. The API key for this user can be found under **Management** -> **Interfaces**. However, the permissions of the interface user cannot be adjusted.

If login with username and password fails, the integration will directly ask for the API key.

Additionally, two intervals can be set: one for normal operations and one for active alarms. The integration will check whether an alarm is active and update data accordingly.

## Usage
There are two main functions: retrieving data from Divera and submitting data to Divera.

### Data Retrieval
Data retrieval happens at the specified interval, and sensor data is automatically updated. Available sensors include:
- Unit details
    - Name, short name, address, coordinates, etc.
- Vehicles
    - Status, coordinates, crew, position, etc.
    - Individual vehicle properties (if configured in Divera)
- Alarms
    - Keywords, text, time, responses, reports, etc.
- Status
    - Only available for "real" users (i.e., not monitor, system, or vehicle users)
    - Personal user status
    - Possible status IDs
- Open alarms
    - Number of open (not closed) alarms
- Trackers
    - For alarms (if coordinates were provided)
    - For vehicles

### Data Submission
Data can be submitted to Divera through various services, accessible via HomeAssistant’s Developer Tools. Documentation for each service is provided there.
- Set user status (simple)
    - Status per unit but without additional details
- Set user status (advanced)
    - Status **only** for the main unit, but with detailed information
- Set vehicle data
- Create alarm
- Modify alarm
- Close alarm
- Send messages

### Sensors
Various sensors are available, including those that interpret Divera data. Each sensor contains relevant attributes. These include:
- Alarms
- Vehicles
- Unit details
- Number of open alarms
- Personal status
- Trackers for operations
- Trackers for vehicles

### Permissions
TBD

### Configuration Changes
Existing hubs can be adjusted via the integration settings in HomeAssistant. Modifiable settings include the API key, data update interval, and update interval during alarms.

