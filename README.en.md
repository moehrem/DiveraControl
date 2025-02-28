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
<!-- [![GitHub Release Date](https://img.shields.io/github/release-date/moehrem/DiveraControl)](https://github.com/moehrem/DiveraControl/releases) -->
<!-- ![GitHub Downloads (all assets, latest release)](https://img.shields.io/github/downloads/moehrem/DiveraControl/latest/total?label=Downloads%20latest%20Release)
![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/moehrem/DiveraControl/ci_pipeline.yml?branch=main) -->

![GitHub commit activity](https://img.shields.io/github/commit-activity/m/moehrem/DiveraControl)
![GitHub last commit](https://img.shields.io/github/last-commit/moehrem/DiveraControl)
![GitHub issues](https://img.shields.io/github/issues/moehrem/DiveraControl)

![HA Analytics](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fanalytics.home-assistant.io%2Fcustom_integrations.json&query=%24.diveracontrol.total&label=Active%20Installations)
[![hacs](https://img.shields.io/badge/HACS-Integration-blue.svg)](https://github.com/hacs/integration)

---

# DiveraControl for HomeAssistant

> **Note:** DiveraControl is still under development. Bugs may occur, and some planned features are not yet implemented. Optimization has not been performed yet. If you're curious, you can test the [pre-release versions](https://github.com/moehrem/DiveraControl/releases)!

💡 **Found a bug or have a feature request?** Please create an [issue](https://github.com/moehrem/DiveraControl/issues). Thank you! 👍

## 🔍 What is DiveraControl?

**DiveraControl** is an integration of [Divera 24/7](https://www.divera247.com) into [HomeAssistant](https://www.home-assistant.io/). It enables local administrators or unit owners to facilitate extensive data exchange between HomeAssistant and Divera 24/7.

Fire stations and vehicles collect a vast amount of data that can be used effectively in emergency situations. Unfortunately, there are very few affordable, integrated solutions for managing and controlling this data. **HomeAssistant** offers a cost-effective hub for controlling, for example:
- Lighting, doors & gates
- Monitors & voice outputs
- Vehicle positions, crew members & statuses
- Device locations & battery levels

This is where **DiveraControl** comes in: It provides the interface to the alarm software, enabling seamless integration.

**Who is this integration for?**
- **Administrators** and **interface users** of a unit
- **Curious users** who want to explore the possibilities of the API

> **Note:** This integration also works with limited rights but with a reduced feature set. Unit users can use the existing [Divera 24/7 Integration for Home Assistant](https://github.com/fwmarcel/home-assistant-divera).

---

## ⚠️ Disclaimer

**Data protection** is particularly important in the emergency services sector. The use of HomeAssistant and this integration in real-life situations is **at your own risk**. Ensuring compliance with data protection regulations—especially regarding **data sharing, processing, and security**—is entirely the responsibility of the user.

> This integration is **not affiliated** with Divera 24/7 and is **not supported** by Divera.

---

## ✅ Features

### 📥 **Data Retrieval**
- Alarm data
- Unit details
- Availability
- Vehicle data & custom attributes
- Permissions
- Message channels

### 📤 **Data Submission**
Various Divera endpoints are implemented as services in HomeAssistant, allowing data submission to Divera:
- Alarm creation, modification & closure
- Vehicle data & custom attributes
- Mission responses
- Message dispatch

---

## 💡 Planned Features
The following features are planned for future implementation:
- Adding crew members to vehicles
- Data retrieval only for active alarms
- Automatic creation & deletion of zones for buildings & incident locations
- Triggering data retrieval via Divera webhook to reduce constant polling
- Availability and roles of emergency personnel

## ❌ Not Included and Not Planned
Divera offers numerous endpoints; however, the following will not be implemented:
- Setting user statuses or responses
- Deleting & archiving alarms, messages & events
- Managing events (creating, modifying, deleting)
- Adding attachments
- Control center functions
- PRO version features (cross-unit alerting)

---

## 📂 Installation

### 🏆 **HACS (Recommended)**
DiveraControl is (not yet) available in the HACS store but can already be added manually:

1. [Install HACS](https://www.hacs.xyz/docs/use/)
2. [![Add HACS Repository](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=moehrem&repository=diveracontrol&category=Integration)
3. **Installation:** Click "Download" at the bottom right.

### 🔧 **Manual Installation**
- Download the [latest release](https://github.com/moehrem/DiveraControl/releases/latest)
- Extract the files into `config/custom_components/diveracontrol`

---

## ⚙️ Setup

### 🔑 **Authentication**
To set up the integration, you need **username & password** or directly an **API key**. The initial login always requires **personal credentials**. These credentials are not stored; they are only used to retrieve the user's API key.

If login with username/password fails or if it involves **system, interface, monitor, or vehicle users**, the integration will prompt for an API key instead.

> Note: Divera provides different API keys. Besides the personal key found under **Profile -> Settings -> Debug**, there is also a general interface key under **Administration -> Interfaces**. However, it is recommended to create and use a dedicated interface user under **Administration -> Interfaces -> System Users** as permissions can be properly configured for such users.

### ⏳ **Polling Intervals**
Polling intervals are configured per unit.
- **Outside of incidents**: Longer interval
- **During an incident**: Shorter interval, used to update data when an alarm is active

> Note: The integration actively polls data from Divera at regular intervals, even if no new data is available. To prevent excessive requests, intervals lower than 30s are not allowed.

