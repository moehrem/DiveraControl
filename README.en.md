<p align="center">
  <a href="https://www.divera247.com">
    <img src="https://www.divera247.com/downloads/grafik/divera247_logo_800.png" alt="Divera 24/7">
  </a>
</p>

---

[![German](https://img.shields.io/badge/🇩🇪%20-German-blue)](README.md)

---

![update-badge](https://img.shields.io/github/last-commit/moehrem/diveracontrol?label=last%20update)

[![GitHub Release](https://img.shields.io/github/v/release/moehrem/DiveraControl?sort=semver)](https://github.com/moehrem/DiveraControl/releases)
<!-- [![GitHub Release Date](https://img.shields.io/github/release-date/moehrem/DiveraControl)](https://github.com/moehrem/DiveraControl/releases) -->
<!-- ![GitHub Downloads (all assets, latest release)](https://img.shields.io/github/downloads/moehrem/DiveraControl/latest/total?label=Downloads%20latest%20Release)
![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/moehrem/DiveraControl/ci_pipeline.yml?branch=main) -->

![GitHub commit activity](https://img.shields.io/github/commit-activity/m/moehrem/DiveraControl)
![GitHub last commit](https://img.shields.io/github/last-commit/moehrem/DiveraControl)
![GitHub issues](https://img.shields.io/github/issues/moehrem/DiveraControl)

![HA Analytics](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fanalytics.home-assistant.io%2Fcustom_integrations.json&query=%24.diveracontrol.total&label=Active%20Installations)
[![hacs](https://img.shields.io/badge/HACS-Integration-blue.svg)](https://github.com/hacs/integration)
[![HASS QS](https://github.com/moehrem/DiveraControl/actions/workflows/hass.yml/badge.svg)](https://github.com/moehrem/DiveraControl/actions/workflows/hass.yml)
[![HACS QS](https://github.com/moehrem/DiveraControl/actions/workflows/hacs.yml/badge.svg)](https://github.com/moehrem/DiveraControl/actions/workflows/hacs.yml)

---

# DiveraControl for HomeAssistant

> **Note:** DiveraControl is still in development. All planned features for the release have now been implemented, but optimization and bug fixing are ongoing. If you're curious, you can test the [pre-release versions](https://github.com/moehrem/DiveraControl/releases)!

💡 **Found a bug or have a feature request?** Please create an [issue](https://github.com/moehrem/DiveraControl/issues). Thank you! 👍

## 🔍 What is DiveraControl?

**DiveraControl** is an integration of [Divera 24/7](https://www.divera247.com) into [HomeAssistant](https://www.home-assistant.io/). It enables local administrators or unit owners to exchange data between HomeAssistant and Divera 24/7 seamlessly.

Fire stations and emergency vehicles generate vast amounts of data that can be utilized effectively during an emergency. However, integrated and affordable solutions for managing and controlling this data are scarce. **HomeAssistant** serves as a cost-effective control center for managing:
- Lighting, doors & gates
- Monitors & voice announcements
- Vehicle locations, crews & statuses
- Device locations & battery levels

**DiveraControl** acts as the interface to the alerting software, enabling smooth integration.

**Who is this integration for?**
- **Administrators** and **interface users** of an emergency unit
- **Curious users** exploring the API’s capabilities

> **Note:** The integration also works with limited permissions but with reduced functionality. Unit members may use the existing [Divera 24/7 Integration for Home Assistant](https://github.com/fwmarcel/home-assistant-divera).

---

## ⚠️ Disclaimer

**Data privacy** is crucial in the emergency services sector. Any use of HomeAssistant and this integration in real-life operations is **at your own risk**. Compliance with data protection regulations, particularly regarding **data transmission, processing, and security**, is entirely the user's responsibility.

> This integration is **not affiliated** with Divera 24/7 and is **not officially supported** by Divera.

---

## ✅ Features
The communication with Divera is fully based on APIv2.

### 📥 **Data Retrieval**
- Alarm details
- Unit information
- Availability
- Vehicle data & custom properties
- Permissions
- Messaging channels

### 📤 **Data Submission**
Various Divera endpoints are implemented as services in HomeAssistant, enabling data transmission to Divera:
- Creating, modifying & closing alarms
- Updating vehicle data & properties
- Sending responses to alerts
- Sending messages

> **Note:** Changes made via HomeAssistant are immediately reflected locally and don’t require waiting for a Divera update. However, newly created records, such as alarms, are always first created at Divera and then synchronized with HomeAssistant.

---

## 💡 Planned Features
The following features are planned for future implementation:
- Data retrieval limited to active alarms
- Automatic creation & deletion of zones for buildings & incident locations
- Triggering data retrieval via Divera webhook to reduce polling

## ❌ Excluded Features
Divera offers many endpoints, but the following are not planned for implementation:
- Setting user statuses or responses
- Deleting & archiving alarms, messages & appointments
- Managing appointments (creating, modifying, deleting)
- Adding attachments
- Control center functions
- PRO version features (cross-unit alerting and management)

---

## 📂 Installation

### 🏆 **HACS (Recommended)**
DiveraControl is (not yet) available in the HAC-Store but can be added manually:

1. [Install HACS](https://www.hacs.xyz/docs/use/)
2. [![Add HACS Repo](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=moehrem&repository=diveracontrol&category=Integration)
3. **Installation:** Click "Download" at the bottom right.

### 🔧 **Manual Installation**
- [Download the latest release](https://github.com/moehrem/DiveraControl/releases/latest)
- Extract files to `config/custom_components/diveracontrol`

---

## ⚙️ Setup

### 🔑 **Authentication**
Login requires either **username & password** or an **API key**. The setup process allows you to choose the authentication method.

Divera offers different user types:
- Regular user
- System user
- Monitor user
- Vehicle user

> **Note:** A regular user is recommended for authentication. Other user types may work but have varying access restrictions.

If authentication with username/password fails, or if the account is a **system, interface, monitor, or vehicle user**, the integration will request the API key instead.

### ⏳ **Polling Intervals**
Polling intervals are configured per unit and determine how often data is fetched and updated:
- **Outside of emergencies**: A longer interval when no active alarms exist
- **During an emergency**: A shorter interval for active alarms

> **Note:** The integration actively fetches data from Divera, even if no new data is available. To avoid excessive requests, intervals below 30s are not allowed.

## 🔨 Usage

### 📟 **Services**
DiveraControl implements multiple services in HomeAssistant, all prefixed with "DiveraControl". These can be used in automations or custom scripts. Available services include:
- Create an alarm
- Open/close an alarm
- Modify an alarm
- Update vehicle status & data
- Send messages

More details about each service, including required and optional parameters, can be found in HomeAssistant’s developer tools.

## ⁉️ **Debugging & Logs**
For troubleshooting, enable debug logging and analyze the logs.

Additionally, diagnostic data can be downloaded from the integration menu. These include:
- System and integration details
- All retrieved data from Divera
- Logs of the current session

> **Note:** Only API keys are masked. All other data, including personal information and alarm details, are fully retained. Be cautious when sharing logs!

