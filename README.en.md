<p align="center">
	<a href="https://www.divera247.com">
		<img src="https://www.divera247.com/downloads/grafik/divera247_logo_800.png" alt="Divera 24/7">
	</a>
</p>

---

[![German](https://img.shields.io/badge/🇩🇪%20-German-red)](README.md)

---

![update-badge](https://img.shields.io/github/last-commit/moehrem/diveracontrol?label=last%20update)

[![GitHub Release](https://img.shields.io/github/v/release/moehrem/DiveraControl?sort=semver)](https://github.com/moehrem/DiveraControl/releases)

![GitHub commit activity](https://img.shields.io/github/commit-activity/m/moehrem/DiveraControl)
![GitHub last commit](https://img.shields.io/github/last-commit/moehrem/DiveraControl)
![GitHub issues](https://img.shields.io/github/issues/moehrem/DiveraControl)

![HA Analytics](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fanalytics.home-assistant.io%2Fcustom_integrations.json&query=%24.diveracontrol.total&label=Active%20Installations)
[![hacs](https://img.shields.io/badge/HACS-Integration-blue.svg)](https://github.com/hacs/integration)
[![HASS QS](https://github.com/moehrem/DiveraControl/actions/workflows/hass.yml/badge.svg)](https://github.com/moehrem/DiveraControl/actions/workflows/hass.yml)
[![HACS QS](https://github.com/moehrem/DiveraControl/actions/workflows/hacs.yml/badge.svg)](https://github.com/moehrem/DiveraControl/actions/workflows/hacs.yml)

---

# DiveraControl for Home Assistant

💡 **Found a bug or have a feature request?** Please open an [issue](https://github.com/moehrem/DiveraControl/issues). Thank you! 👍

## 🔍 What is DiveraControl?

**DiveraControl** is an integration of [Divera 24/7](https://www.divera247.com) into [Home Assistant](https://www.home-assistant.io/). It enables local administrators or unit owners to exchange data between Home Assistant and Divera 24/7.

Stations, vehicles, and equipment are becoming increasingly smart. The resulting data can be used effectively to automate and improve operations and day-to-day routines. Unfortunately, there are hardly any affordable, integrated solutions for managing and controlling this data. **Home Assistant** provides a cost-effective central platform to control and monitor, for example:

- Lighting, doors, and gates
- Monitors and voice announcements
- Vehicle positions, crews, and statuses
- Equipment positions and battery levels
- ... (in theory) any use case, as long as data can be processed

This is where **DiveraControl** comes in: it provides the interface to alerting software and enables seamless integration of a Divera unit.

**Who is this integration for?**

- **Owners** and **administrators** of a Divera unit
- **Curious users** who want to explore the possibilities of the Divera API

> **Note:** The integration also works with limited permissions, but with reduced functionality. For regular users of a unit without extended permissions, the existing [Divera 24/7 Integration for Home Assistant](https://github.com/fwmarcel/home-assistant-divera) is recommended.

---

## ⚠️ Disclaimer

Data protection is particularly important in public safety environments. If you use Home Assistant and this integration in production, please carefully verify whether configuration, permissions, and data flows meet your legal and organizational requirements.

This integration is a community project and is provided without guarantees regarding availability, error-free operation, or fitness for a particular purpose. Please test your setup thoroughly before production use and plan suitable fallbacks for failure scenarios.

As the operator, you are responsible for the secure and privacy-compliant operation of your Home Assistant instance, including (but not limited to) data sharing, access control, logging, and data security.

This integration is not affiliated with and not supported by [DIVERA GmbH](https://www.divera247.com/).

---

## ✅ Features

Communication with Divera is fully based on APIv2.

### 📥 **Data retrieval**

- Alarm data
- Unit details
- Availabilities
- Vehicle data and positions
- Custom vehicle attributes
- Permissions
- Message channels
- Calendar entries

### 📤 **Data submission**

Several Divera endpoints are implemented as Home Assistant actions for sending data to Divera:

- Alarm creation, update, and closure
- Vehicle data and custom attributes
- Response feedback
- Message sending
- News creation

---

## 💡 Upcoming features

Upcoming features are tracked in issues. Feel free to join the discussion or contribute development work.
You are also welcome to submit new ideas as issues.

## ❌ Not included and currently not planned

Divera provides many endpoints. The following are currently not planned:

- Setting user status/response
- Deleting and archiving alarms, messages, and calendar entries
- Calendar management (create, update, delete)
- Adding attachments
- Dispatch center functions
- PRO features (cross-unit alerting and administration)

---

## 📂 Installation

### 🏆 **HACS (recommended)**

DiveraControl is available via HACS (Home Assistant Community Store).

1. [Install HACS](https://www.hacs.xyz/docs/use/)
2. [![Add HACS repository](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=moehrem&repository=diveracontrol&category=Integration)
3. **Install:** Click "Download" in the lower right corner.

### 🔧 **Manual installation**

- Download the [latest release](https://github.com/moehrem/DiveraControl/releases/latest)
- Extract files into `config/custom_components/diveracontrol`

---

## ⚙️ Setup

### 🔑 **Authentication**

Setup supports either **username & password** or an **API key**. You can choose the preferred method during setup.
Your personal API key can be found in your user data under "Settings" -> "Debug". Alternatively, you can use the unit key under "Management" -> "Interfaces" or keys from system/monitor users in the respective admin settings.

Divera provides different user types:

- Personal/regular user
- System user
- Monitor user
- Vehicle user

> **Note:** For proper permission control, use a personal regular user or monitor user when possible. Other user types (including system users) can work, but have fixed permission limits and may not be able to access all data.

If login with username/password fails, or if you use a **system, interface, monitor, or vehicle user**, the integration will ask for an API key directly.

A unit can only be registered once, even when using different credentials or API keys.

### ⏳ **Polling intervals**

Intervals are configured per unit and define how often data is fetched and refreshed.

- **Outside active operations:** longer interval
- **During active alarms:** shorter interval

> **Note:** The integration actively polls Divera even if there is no new data. To avoid unnecessary request volume, values below 5 seconds are not allowed. For faster reactions, you can use a webhook (see below).

### **Base URL**

The base address used to reach the Divera instance can be customized. The default URL is prefilled for services hosted directly by Divera.

### **Webhook**

Webhook usage is optional, but recommended. When enabled, the integration provides an endpoint URL that can be configured [as webhook target in Divera](https://help.divera247.com/pages/viewpage.action?pageId=44171370). Divera calls this webhook as soon as a new alarm is created, which improves Home Assistant reaction time.
To configure in Divera: "Management" -> "Interfaces" -> "Data transfer" -> "Webhooks". Use the following settings:

- **URL**: shown once during integration setup
- **Format**: POST application/json
- **Content**: "No content"

Divera can send payload data via webhook. DiveraControl does not process this payload. The webhook is used only as a trigger to perform an immediate data refresh from Divera.

> **Note:** If no external URL is available in Home Assistant, the webhook option is automatically disabled during setup and setup continues without webhook.

### 🔁 **Reconfiguration**

You can start reconfiguration at any time via the integration's three-dot menu. The following settings can be changed:

- API key
- Polling intervals
- Base URL
- Webhook usage

## 🔨 Usage

### 📟 **Actions**

Several actions for interacting with Divera are implemented in Home Assistant. They all start with "DiveraControl" and can be used in automations, the frontend, or custom integrations—anywhere Home Assistant actions are supported. Implemented actions include:

- Create alarm
- Close/open alarm
- Send message
- Change vehicle crew
- Change vehicle properties
- Change vehicle status and data
- Update alarm
- Create news

All actions are device-dependent. This means each execution must include the target unit. In automations and in the frontend, you can select a unit directly and execute the desired action. Many fields include value selectors there.

In developer tools or other technical usage, you must provide a target via `device_id`. For technical reasons, some fields cannot provide selector helpers there (for example alarms, vehicles, crew, groups). In these fields, enter IDs directly; for multiple IDs, separate them by commas.

More details on actions and required/optional parameters are available in Home Assistant under "Developer Tools" -> "Actions". Both YAML mode and UI mode are supported. All actions begin with "DiveraControl:" followed by name and short description. You can also run actions manually there. More information about action usage can be found [here](https://www.home-assistant.io/docs/scripts/perform-actions/).

Actions that modify existing data (for example vehicle position) also update local integration data. This keeps Home Assistant up to date without waiting for the next Divera sync. This does not apply to new records: new alarms or messages are always created in Divera first and then synchronized to Home Assistant.

> **Note:** Actions are subject to permissions granted! Each unit (registered as device) shows only such actions the user is allowed to execute. Despite that a permission check is done every time an action is executed. If permission is not granted, the action will abort.

#### Technical service IDs

For YAML, automations, and developer tools, these service IDs are available:

- `diveracontrol.post_vehicle_status`
- `diveracontrol.post_alarm`
- `diveracontrol.put_alarm`
- `diveracontrol.post_close_alarm`
- `diveracontrol.post_message`
- `diveracontrol.post_using_vehicle_property`
- `diveracontrol.post_using_vehicle_crew`
- `diveracontrol.post_news`

### 🧩 **Entities (overview)**

The integration creates dynamic entities per unit across multiple platforms:

- **Sensors**: including alarm sensors, vehicle sensors, availability sensors, open-alarms counter, unit/diagnostic sensors
- **Device trackers**: alarm positions and vehicle positions
- **Calendar**: appointments from Divera

## ⁉️ **Troubleshooting**

For analysis, you can enable the integration's debug log from the integration menu. This sets the log level to debug and provides more detailed output.

For each configured unit, diagnostic data can be downloaded from the integration context menu. It includes system details, integration details, all data fetched from Divera, and session logs related to DiveraControl.

> **Note:** In diagnostics data, only `api_key` and `accesskey` are currently redacted. Other data, including personal data and alarm content, may be fully included and should never be shared unfiltered.
