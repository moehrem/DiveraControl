<p align="center">
  <a href="https://www.divera247.com">
    <img src="https://www.divera247.com/downloads/grafik/divera247_logo_800.png" alt="Divera 24/7">
  </a>
</p>

- [🇩🇪 German](README.md)

# DiveraControl for HomeAssistant

> **Note:** DiveraControl is still in development. Errors may occur, and some planned features are still missing. Optimization has not yet taken place. If you're curious, you can test the [pre-release versions](https://github.com/moehrem/DiveraControl/releases)!

💡 **Found a bug or have a feature request?** Please create an [issue](https://github.com/moehrem/DiveraControl/issues). Thank you! 👍

## 🔍 What is DiveraControl?

**DiveraControl** is an integration of [Divera 24/7](https://www.divera247.com) into [HomeAssistant](https://www.home-assistant.io/). It enables local administrators or unit owners to extensively exchange data between HomeAssistant and Divera 24/7.

Fire stations and emergency vehicles collect a lot of data that can be useful in emergency situations. Unfortunately, there are hardly any affordable, integrated solutions for managing and controlling this data. **HomeAssistant** provides a cost-effective central hub for controlling:
- Lighting, doors & gates
- Monitors & voice announcements
- Vehicle locations, crew & statuses
- Device locations & battery levels

This is where **DiveraControl** comes in: It provides the interface to the alarm software and enables seamless integration.

**Who is this integration for?**
- **Administrators** and **interface users** of a unit
- **Curious users** exploring the API capabilities

> **Note:** The integration also works with limited permissions, but with reduced functionality. Unit users can use the existing [Divera 24/7 Integration for Home Assistant](https://github.com/fwmarcel/home-assistant-divera).

---

## ⚠️ Disclaimer

**Data privacy** is particularly important in the emergency services sector. Any use of HomeAssistant and this integration in real-life scenarios is **at your own risk**. Compliance with data protection regulations – especially regarding **data transfer, processing, and security** – is entirely the responsibility of the user.

> This integration is **not affiliated** with Divera 24/7 and is **not supported** by Divera.

---

## ✅ Features

### 📥 **Data Retrieval**
- Alarm data
- User status
- Unit details
- Availability
- Vehicle data & custom attributes
- Permissions
- Message channels

### 📤 **Data Submission**
HomeAssistant services allow sending data to Divera:
- User status (basic & extended)
- Alarm creation, modification & closure
- Vehicle data & custom attributes
- Response to alarms
- Message dispatch

---

## ❌ Not Yet Included
Divera offers numerous endpoints, but not all are integrated:
- Deleting & archiving alarms, messages & events
- Managing events (create, edit, delete)
- Adding attachments
- Assigning crew to vehicles
- Control center functions
- PRO version features (cross-unit alarm management)

**Planned Features:**
- Adding crew to vehicles
- Querying data only for active alarms (via Divera Webhook)
- Automatic creation & deletion of zones for buildings & incident locations

---

## 📂 Installation

### 🏆 **HACS (Recommended)**
DiveraControl is (not yet) available in the HAC-store but can be added manually:

1. [Install HACS](https://www.hacs.xyz/docs/use/)
2. [![Add HACS Repository](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=moehrem&repository=diveracontrol&category=Integration)
3. **Installation:** Click "Download" at the bottom right.

### 🔧 **Manual Installation**
- Download the [latest release](https://github.com/moehrem/DiveraControl/releases/latest)
- Extract files into `config/custom_components/diveracontrol`

---

## ⚙️ Configuration

### 🔑 **Authentication**
To set up the integration, you need **username & password** or the **API key**. The initial login must always be done with **personal credentials**. These are not stored but only used to retrieve the user's API key.

2.  (Recommended for admins) → API key must be entered manually
3.  (Central, permissions not adjustable) → API key can be retrieved under Management → Interfaces

If login with username/password fails or if you are using **system, interface, monitor, or vehicle accounts**, the integration will directly ask for the API key.

### ⏳ **Query Intervals**
Intervals are always set per unit:
- **Outside of emergencies:** Longer interval
- **During an emergency:** Shorter interval for faster updates

---

## 👍 Usage

### 🔍 **Data Retrieval**
Queries run automatically in the background. The following sensors are available:
- **Unit details** (name, address, coordinates)
- **Vehicles** (status, location, crew, attributes)
- **Alarms** (keyword, message, responses)
- **User status** (only for "real" users)
- **Open alarms** (count)
- **Trackers** (for incidents & vehicles)

### 📤 **Data Submission** (HomeAssistant Services)
- Set user status (basic/extended)
- Update vehicle data
- Create, modify & close alarms
- Send messages

### 🔄 **Sensor Handling**
- Sensors update automatically
- Sensors without current data are removed from HomeAssistant

### ⚙️ **Configuration Changes**
Adjustable via HomeAssistant integrations management:
- Query intervals for normal & alarm situations

---