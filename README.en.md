<p align="center">
  <a href="https://www.divera247.com">
    <img src="https://www.divera247.com/downloads/grafik/divera247_logo_800.png" alt="Divera 24/7">
  </a>
</p>

---

[![Deutsch](https://img.shields.io/badge/🇩🇪%20-Deutsch-red)](README.md)

---

![update-badge](https://img.shields.io/github/last-commit/moehrem/diveracontrol?label=last%20update)

[![GitHub Release](https://img.shields.io/github/v/release/moehrem/DiveraControl?sort=semver)](https://github.com/moehrem/DiveraControl/releases)

![GitHub commit activity](https://img.shields.io/github/commit-activity/m/moehrem/DiveraControl)
![GitHub last commit](https://img.shields.io/github/last-commit/moehrem/DiveraControl)
![GitHub issues](https://img.shields.io/github/issues/moehrem/DiveraControl)

![HA Analytics](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fanalytics.home-assistant.io%2Fcustom_integrations.json&query=%24.diveracontrol.total&label=Active%20Installations)
[![hacs](https://img.shields.io/badge/HACS-Integration-blue.svg)](https://github.com/hacs/integration)

---

# DiveraControl for HomeAssistant

> **Note:** DiveraControl is still in development. Bugs may occur, and some planned features are not yet implemented. No optimization has taken place so far. If you're curious, you can test the [pre-release versions](https://github.com/moehrem/DiveraControl/releases)!

💡 **Found a bug or have a feature request?** Please create an [issue](https://github.com/moehrem/DiveraControl/issues). Thanks! 👍

## 🔍 What is DiveraControl?

**DiveraControl** is an integration of [Divera 24/7](https://www.divera247.com) into [HomeAssistant](https://www.home-assistant.io/). It allows local administrators or unit owners to exchange data between HomeAssistant and Divera 24/7.

Fire stations and emergency vehicles generate a vast amount of data that can be useful during operations. However, there are few affordable, integrated solutions for managing and controlling this data. **HomeAssistant** provides a cost-effective central system to control:
- Lighting, doors & gates
- Monitors & voice outputs
- Vehicle locations, crew members & statuses
- Device locations & battery levels

This is where **DiveraControl** comes in: It serves as the interface to the alerting software, enabling seamless integration.

**Who is this integration for?**
- **Administrators** and **interface users** of a unit
- **Curious users** who want to explore the API's capabilities

> **Note:** The integration also works with limited user permissions, but with reduced functionality. Regular users of a unit can use the existing [Divera 24/7 Integration for Home Assistant](https://github.com/fwmarcel/home-assistant-divera).

---

## ⚠️ Disclaimer

**Data privacy** is especially important in the emergency services sector. Any use of HomeAssistant and this integration in real-world scenarios is **at your own risk**. The user is solely responsible for ensuring compliance with data protection regulations—especially regarding **data transmission, processing, and security**.

> This integration is **not affiliated** with Divera 24/7 and is **not supported** by Divera.

---

## ✅ Features

### 📥 **Data Retrieval**
- Alarm data
- Unit details
- Availability statuses
- Vehicle data & individual attributes
- Permissions
- Message channels

### 📤 **Data Submission**
Various Divera endpoints are implemented as services in HomeAssistant, allowing data transmission to Divera:
- Creating, modifying & closing alarms
- Updating vehicle data & individual attributes
- Sending response messages
- Sending messages

---

## 💡 Planned Features
The following features are still to be implemented:
- Adding crew members to vehicles
- Querying data only for active alarms
- Automatically creating & deleting zones for buildings & incident locations
- Triggering data retrieval via Divera webhook to reduce constant polling
- Fetching availability and roles of responders

## ❌ Excluded and Not Planned
Divera offers many API endpoints, but the following are not planned for implementation:
- Setting user statuses or responses
- Deleting & archiving alarms, messages & events
- Managing events (creating, modifying, deleting)
- Uploading attachments
- Dispatch center functions
- PRO version features (cross-unit alerting)

---

## 📂 Installation

### 🏆 **HACS (Recommended)**
DiveraControl is (not yet) available in the HACS store but can be added manually:

1. [Install HACS](https://www.hacs.xyz/docs/use/)
2. [![Add HACS Repo](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=moehrem&repository=diveracontrol&category=Integration)
3. **Installation:** Click "Download" at the bottom right.

### 🔧 **Manual Installation**
- Download the [latest release](https://github.com/moehrem/DiveraControl/releases/latest)
- Extract the files into `config/custom_components/diveracontrol`

---

## ⚙️ Configuration

### 🔑 **Authentication**
To set up the integration, you need **a username & password** or directly an **API key**. The initial login is always done using **personal credentials**. These credentials are not stored; they are only used to retrieve the user's API key.

If logging in with a username/password fails or if the user is a **system, interface, monitor, or vehicle account**, the integration will prompt for an API key.

> Note: Divera offers different API keys. Besides the personal key found under **Profile -> Settings -> Debug**, there is also a general interface key under **Administration -> Interfaces**. However, it is recommended to create and use a dedicated system user under **Administration -> Interfaces -> System Users**, as this allows better permission control.

### ⏳ **Polling Intervals**
The intervals are set per unit.
- **Outside of incidents**: longer interval
- **During an incident**: shorter interval, used to update data in case of active alarms

> Note: The integration actively polls Divera for data, even if no new data is available. To avoid unnecessary requests, values below 30s are not allowed.

### 🔍 **Diagnostics**
Each unit, represented as a service in the integration, allows downloading diagnostic data via the context menu (3 dots). These diagnostics include all retrieved data from Divera, which can be used for completeness and content verification.

> Note: The output only masks API keys. Other data, including personal data and alarm details, are included as retrieved from Divera.
