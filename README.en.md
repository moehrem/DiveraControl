---
<p align="center">
<a href="https://www.divera247.com">
<img src="https://www.divera247.com/downloads/grafik/divera247_logo_800.png" alt="Divera 24/7">
</a>
</p>
---

[![German](https://img.shields.io/badge/\ud83c\udde9\ud83c\uddea%20-German-red)](README.md)

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

💡 **Found a bug or have a feature request?** Please open an [issue](https://github.com/moehrem/DiveraControl/issues). Thanks! 👍

## 🔍 What is DiveraControl?

**DiveraControl** is an integration of [Divera 24/7](https://www.divera247.com) into [Home Assistant](https://www.home-assistant.io/). It enables local administrators or unit owners to exchange data between Home Assistant and Divera 24/7.

Stations, vehicles, and equipment are becoming increasingly smart. The resulting data can be used meaningfully and effectively to make operations and daily routines more efficient and automated. Unfortunately, there are hardly any affordable, integrated solutions for managing and controlling this data. **Home Assistant** provides a cost-effective hub for controlling and monitoring, for example:

- Lighting, doors & gates,
- Monitors & voice announcements,
- Vehicle positions, crews & status,
- Equipment positions & battery levels,
- ... (theoretically) any application, as long as the data can be processed.

This is where **DiveraControl** comes in: it provides the interface to the alerting software and allows seamless integration.

**Who is this integration for?**

- **Owners** and **administrators** of a Divera unit
- **Curious users** who want to explore the Divera API

> **Note:** The integration also works with limited permissions but with reduced functionality. For regular users of a unit without any additional permissions, the existing [Divera 24/7 Integration for Home Assistant](https://github.com/fwmarcel/home-assistant-divera) is recommended.

---

## ⚠️ Disclaimer

**Data protection** is especially important in public safety (BOS) environments. The use of Home Assistant and this integration in real-world scenarios is **at your own risk**. Ensuring compliance with data protection regulations – particularly with regard to **data transfer, processing, and security** – is entirely the responsibility of the user.

This integration is **not affiliated with** nor **supported by** DIVERA GmbH.

---

## ✅ Features

Communication with Divera is entirely based on APIv2.

### 📥 **Data Retrieval**

- Alarm data
- Unit details
- Availabilities
- Vehicle data and locations
- Custom vehicle attributes
- Permissions
- Message channels
- Calendar entries

### 📤 **Data Submission**

Various Divera endpoints are implemented as actions in Home Assistant, enabling data submission to Divera:

- Alarm creation, update & closure
- Vehicle data & custom attributes
- Response feedback
- Message dispatch
- Create news

---

## 💡 Upcoming Features

Upcoming features are created as issues. You are welcome to comment on existing issues or participate in development!
If you have any ideas please feel free to create an issue.

## ❌ Not included and not planned

Although Divera offers many endpoints, the following are currently **not planned**:

- Setting user status or availability
- Deleting or archiving alarms, messages, or calendar entries
- Managing calendar entries (create, update, delete)
- Adding attachments
- Dispatch center functionality
- PRO version features (cross-unit alerting and administration)

---

## 📂 Installation

### 🏆 **HACS (recommended)**

DiveraControl is available via HACS (Home Assistant Community Store):

1. [Install HACS](https://www.hacs.xyz/docs/use/)
2. [![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=moehrem&repository=diveracontrol&category=Integration)
3. **Installation:** Click "Download" in the bottom-right corner.

### 🔧 **Manual Installation**

- Download the [latest release](https://github.com/moehrem/DiveraControl/releases/latest)
- Extract files to `config/custom_components/diveracontrol`

---

## ⚙️ Configuration

### 🔑 **Authentication**

You can set up authentication using either **username & password** or an **API key**. The method can be selected during setup.
Your personal API key can be found under "Settings" -> "Debug" in your user data. Alternatively, the unit key can be found under "Management" -> "Interfaces" or via the system/monitor user in the admin panel.

Divera offers various user types:

- personal/regular user
- system user
- monitor user
- vehicle user

> **Note:** For proper permission management, a personal or monitor user is recommended. Other user types (including the flexible-looking system user, which in reality is mainly for TETRAcontrol) also work but are limited by fixed restrictions and cannot access all data.

If login with username/password fails or you're using a **system, interface, monitor, or vehicle user**, the integration will prompt for the API key.

It is not possible to log in with a user from a unit that has already been integrated.

### ⏳ **Polling Intervals**

Intervals are set **per unit** and control how often data is retrieved and updated.

- **Outside of deployments:** longer interval
- **During active alarms:** shorter interval

> **Note:** The integration actively polls Divera even when no new data is available. To avoid excessive requests, values below 30s (outside of alarms) or 10s (during alarms) are not allowed.

---

## 🔨 Usage

### 📿 **Actions**

Several Home Assistant actions are implemented for interacting with Divera. They all start with "DiveraControl" and can be used in automations or custom scripts. Implemented actions include:

- Create alarm
- Open/close alarm
- Send message
- Change vehicle crew
- Modify vehicle properties
- Update vehicle status/data
- Modify alarm
- Create news

All actions are device-dependent. This means that every execution must specify the target unit. In automations and the frontend, you can simply select a unit as the trigger and execute the desired action. Many fields here are also equipped with selection aids.

In the developer tools or with other implementations of the actions, a target in the form of the device_id must be entered. For technical reasons, some fields cannot be provided with selection aids. This affects all changeable value aids, e.g., alarms, vehicles, crew, groups, etc. Instead, the corresponding ID must be entered in the fields, separated by commas for multiple IDs.

More details on the parameters (required and optional) can be found in Home Assistant under "Developer Tools" -> "Actions". You may choose "YAML-Mode" or "UI-Mode". All actions start with "DiveraControl: " followed by the name and a short description. You can test them manually there. For more information on how actions work, [see here](https://www.home-assistant.io/docs/scripts/perform-actions/).

Actions that modify existing data (e.g., vehicle position) also update the local state in Home Assistant. This means Home Assistant is always up to date and does not wait for Divera to sync. However, this does **not** apply to new data entries! For example, a new alarm or message is always created on Divera first and then synced to Home Assistant.

---

## ⁉️ **Troubleshooting**

To debug issues, enable the **debug log** in the integration menu. This sets the log level to "debug" and provides much more detailed output.

In the context menu of the created hub, you can also **download diagnostic data**. This includes system details, integration metadata, all data fetched from Divera, and logs from the current session relevant to DiveraControl.

> **Note:** Only the API keys are masked in the log output. All other data, including personal information and alarm content, is included unmasked as received from Divera. These files should **not be shared unfiltered**!
