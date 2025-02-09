<p align="center">
  <a href="https://www.divera247.com">
    <img src="https://www.divera247.com/downloads/grafik/divera247_logo_800.png" alt="Divera 24/7">
  </a>
</p>

- [🇩🇪 Deutsch](README.md)

# DiveraControl

**DiveraControl is still under development and may contain bugs. Some planned features are still missing, and optimization has not yet been performed. However, if you're curious, feel free to test it!**

**If you find any bugs or are missing a feature, please create an [Issue](https://github.com/moehrem/DiveraControl/issues). Thank you!**

---

**DiveraControl** is an integration of Divera 24/7 into Home Assistant. The goal of this integration is to enable extensive data exchange with Divera 24/7.

Fire stations, vehicles, and equipment are becoming increasingly smarter. However, there is hardly any integrative provider (at least an affordable one for small fire departments) for central management, control, and distribution of this data with the aim of coordinating smart devices. This is where Home Assistant comes in. It can serve as a cost-effective central control for lighting, doors and gates, monitors, voice output, vehicle positions, crews, vehicle statuses, equipment locations, battery levels, custom monitors, etc. However, it requires a connection to the alerting software – and this is where this integration helps.

To fully utilize this integration, extensive permissions are required in the connected unit. The target group of this integration is administrators or interface users of a unit.

As a firefighter myself, my focus for this application is the fire department. However, since Divera 24/7 is widely used and the interface is the same for all, this integration can certainly be used for purposes outside of firefighting as well.

The integration also works with limited permissions but will not provide the same range of features. For personal use, the existing [Divera 24/7 Integration for Home Assistant](https://github.com/fwmarcel/home-assistant-divera) might be a better fit.

---

## Disclaimer

In the BOS (public safety) sector, data protection is of particular importance. Any use of Home Assistant and this integration in real-world scenarios is at **your own risk**. Compliance with data protection regulations, especially but not limited to "data sharing with third parties," "data processing," and "data security," is entirely the user's responsibility.

This integration is **not affiliated** with Divera 24/7 and is **not supported** by Divera 24/7.

---

## What can DiveraControl do?

- Manage multiple users within the same unit
- Connect multiple units for the same user
- Receive and process alarms
- Read and update vehicle data

### Data Retrieval
- Alarm data
- User status
- Unit details
- Availability
- Vehicle data including custom properties
- Permissions
- Messaging channels

### Data Submission
With **DiveraControl**, data can be sent to Divera. Corresponding services have been implemented in Home Assistant. The following endpoints are available:
- User status (simple and advanced)
- Alarm creation
- Alarm modification
- Alarm closure
- Vehicle data including custom properties
- Incident feedback
- Messages (Messenger)

---

## What can't DiveraControl do (yet)?
Divera provides many endpoints. Not all of them can be accessed through this integration. Missing features include:
- Deleting and archiving alarms, messages, notifications, appointments
- Creating, modifying, deleting appointments
- Adding attachments
- Adding crew members to vehicles, neither inside nor outside of incidents
- Control center functions
- PRO version features (e.g., cross-unit alerting)

## What should DiveraControl be able to do?
- Adding crew members to vehicles

---

## Installation
Currently, installation is only possible manually. A HACS integration is in progress.

For manual installation, download the [latest release](https://github.com/moehrem/DiveraControl/releases/latest) and extract it into the Home Assistant folder `config/custom_components/diveracontrol`.


## Setup
The setup is done by entering a username and password. None of this information is stored; instead, the API key of the user is retrieved during the initialization of the integration and stored in Home Assistant.

For login, personal credentials can be used. In this case, if the user is assigned to multiple units, each unit will be added as a hub in the integration.

However, it is advisable to use a system user of the unit for centralized rights management. Divera allows this under **Administration** -> **Interfaces** -> **System Users**. System users cannot log in directly, instead, the integration will ask for the user’s API key.

Another alternative is to use the central interface user of the unit. The API key can be found under **Administration** -> **Interfaces**. However, the permissions of the interface user cannot be adjusted.

If login with a username and password fails, the integration will directly ask for the API key.

Additionally, two intervals can be configured: one for non-emergency mode and one for active emergency situations. The integration evaluates the situation (whether an alarm is active or not) and updates the data accordingly.


## Usage
There are two main functions: retrieving and submitting data to Divera.

### Retrieval
Retrieval happens according to the configured interval, and sensor data is automatically updated. The sensors include:
- Unit details
    - Name, short name, address, coordinates, etc.
- Vehicles
    - Status, coordinates, crew, position, etc.
    - Custom vehicle properties (if set in Divera)
- Alarms
    - Keyword, text, time, feedback, report, etc.
- Status
    - Available only for "real" users (not monitor, system, or vehicle users)
    - Personal user status
    - Possible status IDs
- Active Alarms
    - Number of open (not closed) alarms
- Trackers
    - For alarms, if coordinates have been provided
    - For vehicles

### Submission
Data submission is done through Home Assistant services. These interact with Divera's respective endpoints. Each service can be tested in the Home Assistant developer tools, where documentation for the required data is also available.
- Set user status (simple)
    - Status per unit, but without details
- Set user status (advanced)
    - Status **only** for the main unit, but with additional details
- Update vehicle data
- Create alarm
- Modify alarm
- Close alarm
- Send messages

### Sensors
Various sensors are provided, including those that interpret Divera's data. Each sensor contains corresponding data as attributes, including:
- Alarms
- Vehicles
- Unit details
- Number of active alarms
- Personal status
- Incident trackers
- Vehicle trackers

Sensors that no longer receive data from Divera will be removed from Home Assistant.

### Configuration Changes
Existing hubs can be modified via Home Assistant's integration management. The API key, data retrieval interval, and emergency mode retrieval interval can be adjusted.