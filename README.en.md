<p align="center">
  <a href="https://www.divera247.com">
    <img src="https://www.divera247.com/downloads/grafik/divera247_logo_800.png" alt="Divera 24/7">
  </a>
</p>

---

[![Deutsch](https://img.shields.io/badge/🇩🇪%20-Deutsch-blue)](README.md)

---

![GitHub Release](https://img.shields.io/github/v/release/moehrem/DiveraControl?sort=semver)
![GitHub last commit](https://img.shields.io/github/last-commit/moehrem/DiveraControl)
![GitHub commit activity](https://img.shields.io/github/commit-activity/m/moehrem/DiveraControl)
![GitHub issues](https://img.shields.io/github/issues/moehrem/DiveraControl)
![HA Analytics](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fanalytics.home-assistant.io%2Fcustom_integrations.json&query=%24.diveracontrol.total&label=Active%20Installations)
[![hacs](https://img.shields.io/badge/HACS-Integration-blue.svg)](https://github.com/hacs/integration)
[![HASS QS](https://github.com/moehrem/DiveraControl/actions/workflows/hass.yml/badge.svg)](https://github.com/moehrem/DiveraControl/actions/workflows/hass.yml)
[![HACS QS](https://github.com/moehrem/DiveraControl/actions/workflows/hacs.yml/badge.svg)](https://github.com/moehrem/DiveraControl/actions/workflows/hacs.yml)

---

# DiveraControl for Home Assistant

💡 **Found a bug or have a feature request?** Please create an [Issue](https://github.com/moehrem/DiveraControl/issues). Thank you! 👍

---

## 🔍 What is DiveraControl?

**DiveraControl** is a **[Home Assistant](https://www.home-assistant.io/)** integration for **[Divera 24/7](https://www.divera247.com)**. It provides comprehensive data from connected Divera units and enables bidirectional data exchange through actions – e.g., to change statuses or trigger alarms.

The integration is aimed at **users, administrators, and unit owners**. Depending on individual permissions in Divera, various functions are available.

> **Note:** By popular demand, **v2.0.0** also implements personal functions, making the integration useful for home use.

Fire stations, vehicles, and devices are becoming increasingly smart. The resulting data can be used effectively to make operations and daily routines **more efficient and automated**. However, there are few affordable solutions for managing and controlling this data. **Home Assistant** provides a cost-effective central system for controlling and monitoring:
- Lighting, doors & gates,
- Monitors & voice outputs,
- Vehicle positions, crews & statuses,
- Device positions & battery levels,
- theoretically **any application**, as long as the data can be processed in Home Assistant.

**DiveraControl** bridges this gap: it provides the **interface to Divera** and enables **seamless integration** of the unit into Home Assistant.

---

## ⚠️ Disclaimer & Privacy

This integration is a **community project with no connection to DIVERA GmbH** and is **not supported** by them.

> **Important:** The operator of the Home Assistant instance is **solely responsible** for:
> - **Data protection compliance** (in particular GDPR, BDSG, organizational requirements)
> - **Secure configuration** (access rights, logging, API keys)
> - **Fallback strategies** for production operation

**No warranty** for availability, freedom from errors, or suitability for specific purposes.
**Thoroughly test the setup before production use!**

---

## ✅ Features

Communication with Divera takes place **exclusively via the APIv2**.

---

### 📥 Data Fetching and Provision

| **Data** | **Description** |
|----------|----------------|
| Alarm data | All non-archived alarms |
| Last alarm | Details of the most recent alarm |
| Unit details | Information about the Divera unit |
| User details | User data and information |
| User status | Current status of users |
| Availability | Availability per status |
| Vehicle data & positions | Data and locations of vehicles |
| Vehicle properties | Individual vehicle settings |
| Permissions | User and unit permissions |
| Message channels | Channels for message exchange |
| Calendar entries | Appointments from Divera |

---

### 📤 Data Submission (Actions)

Divera endpoints are implemented as **actions in Home Assistant** and enable sending data to Divera.

| **Action** | **Description** |
|------------|----------------|
| Set user status | Changes a user's status |
| Create/Modify/Close alarm | Alarm management |
| Update vehicle data | Position, status & properties |
| Operation feedback | Feedback on operations |
| Send messages | Sending messages |
| Create notices | Creating notices |

> **Note:** Detailed descriptions of parameters and usage can be found below under [Actions](#-actions).

---
---

## 💡 Roadmap & Contribution

📌 **Planned features** can be found in the [Issues](https://github.com/moehrem/DiveraControl/issues).
**Feel free to participate in discussions or development!**

💡 **New suggestions** can be submitted as an Issue.

---

## ❌ Not Supported

The following Divera endpoints are **not planned**:

| **Feature** | **Reason** |
|-------------|------------|
| Delete/Archive alarms | Not within the scope of the integration |
| Appointment management (CRUD) | Complexity & permission management |
| Add attachments | Technical limitations |
| Control center functions | Target audience is units, not control centers |
| PRO version features | Cross-unit management |

---

## 📂 Installation

### 🏆 **HACS (Recommended)**

1. [Install HACS](https://www.hacs.xyz/docs/use/)
2. [![Add HACS Repository](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=moehrem&repository=diveracontrol&category=Integration)
3. **Install:** Click **"Download"** at the bottom right.

---

### 🔧 **Manual Installation**

1. Download the [latest release](https://github.com/moehrem/DiveraControl/releases/latest)
2. Extract the files to `config/custom_components/diveracontrol`

---
---

## ⚙️ Setup

---

### 🔑 Authentication

For setup, **username & password** or an **API key** is required.

#### 👤 User Types in Divera

| **User Type** | **Description** | **Recommended?** |
|---------------|----------------|-----------------|
| Personal/Regular User | Full permission control | ✅ **Yes** |
| Monitor User | Limited permissions | ✅ **Yes** |
| System User | Technical user, permission-dependent | ⚠️ Limited |
| Vehicle User | Vehicle-specific data | ⚠️ Limited |

> **Note:**
> - For **full permission control**, **personal or monitor users** should be used.
> - System/Vehicle users work **technically**, but are subject to **Divera-internal restrictions** (e.g., returning TETRAcontrol data).
> - If login with username/password fails, the **API key will be requested automatically**.

#### 🔑 API Key

The key can be found in:
- **Personal User:** *"Settings" → "Debug"*
- **Unit:** *"Administration" → "Interfaces"*
- **System/Monitor User:** Respective administration options

> **Important:** Each combination of **user + unit** can **only be registered once**.
> However, a user can be added **multiple times** for different units.

---

### ⏳ Polling Intervals

Intervals are configured **per unit**:

| **Interval** | **Description** | **Recommended Value** |
|--------------|----------------|----------------------|
| **Outside of Operations** | Longer interval for normal requests | 60s |
| **During an Operation** | Shorter interval for active alarms | 30s |

> **Note:**
> - The integration **regularly polls** data from Divera.
> - **Minimum value: 5s** (shorter intervals are not possible to limit server load).
> - For **real-time updates** → Use [Webhooks](#-webhooks-for-real-time-updates).

---

### 🌐 Base URL

The base address of the Divera instance can be **individually adjusted**.
**Default:** `https://api.divera247.com` (for Divera-hosted instances).

---

### 🔁 Re-Configuration

Each unit can be reconfigured via the **gear icon button**.
A distinction is made between:

#### **🏢 Unit Settings** (apply to all users of the unit)
- Polling intervals (outside/during operations)
- Base URL

#### **👤 User Settings** (user-specific)
- **API Key** (for system/monitor/vehicle users)
- **Username/Password** (for personal users)

---
---

## 🔨 Usage

---

### 📟 Actions

The integration offers several actions per device/user, that can be used in **automations, dashboards, or scripts**.

| **Action** | **Parameters** (Examples) | **Description** | **Permission** |
|------------|---------------------------|----------------|----------------|
| **Create alarm** | `title`, `message`, `priority` | Creates a new alarm | Admin/Unit Owner |
| **Modify alarm** | `alarm_id`, `title`, `message` | Edits an existing alarm | Admin |
| **Open/Close alarm** | `alarm_id`, `status` | Changes alarm status | Admin |
| **Set user status** | `status_id` | Changes the user's status | Personal User |
| **Send message** | `channel_id`, `message` | Sends a message | Depends on channel |
| **Create notice** | `title`, `message`, `recipients` | Creates a notice | Admin |
| **Change vehicle crew** | `vehicle_id`, `user_ids` | Changes the crew | Admin/Vehicle User |
| **Change vehicle properties** | `vehicle_id`, `property`, `value` | Updates properties | Admin |
| **Change vehicle status** | `vehicle_id`, `status`, `latitude`, `longitude` | Position & status | Admin/Vehicle User |
| **Request data update** | – | Forces an immediate fetch | All Users |

> **💡 Tips:**
> - Actions are **device-dependent** → Select the **user device** in Home Assistant as the trigger.
> - Buttons can be linked to actions in dashboards (selection aids available).
> - **Testing:** Actions can be manually tested under *"Settings" → "Developer Tools" → "Actions".*
> - [Home Assistant Actions Documentation](https://www.home-assistant.io/docs/scripts/perform-actions/)

---

### 📟 Trigger

The integration creates some triggers. These triggers are also available per device/user, thus can be used in **Automations** very easily.

| **Trigger**               | **condition to trigger**        |
|---------------------------|---------------------------------|
| **New alarm**             | number of "open alarms" raises  |
| **All alarms closed**     | number of "open alarms" is zero |

---

#### ⚠️ Important Notes on Actions
- **Local Update:** Changing existing data (e.g., vehicle position) updates it **immediately locally** in Home Assistant. No waiting for Divera sync!
- **New Data Records:** Are **first created in Divera** and then synchronized with Home Assistant.
- **Permissions:** Actions are **technically available to all users**, but **checked before execution** and aborted if permissions are missing.

---

### 🧩 Entities (Overview)

The integration **dynamically creates entities** per unit:

| **Platform** | **Entities** (Examples) | **Purpose** |
|--------------|-------------------------|-------------|
| **Input Select** | Set user status | Change status with one click |
| **Sensors** | Alarms, vehicles, availability, open alarms counter, last alarm, diagnostic sensors | Data querying & monitoring |
| **Device Tracker** | Alarm positions, vehicle positions | Location tracking on maps |
| **Calendar** | Appointments from Divera | Integration into calendar views |

---
---

## ⁉️ Troubleshooting

| **Method** | **Description** | **Caution** |
|------------|----------------|-------------|
| **Debug Log** | Enables extended logs in Home Assistant | Log level set to *Debug* |
| **Diagnostic Data** | Downloadable in the unit's context menu | Contains **all local data** (including personal data!) |

> **⚠️ Important:**
> - In diagnostic data, **only `accesskey` is masked**.
> - **All other data** (user data, alarm contents, etc.) are **unencrypted**.
> - **Never share unfiltered!**

---
---

## 💡 Practical Tips

---

### 🔄 Webhooks for Real-Time Updates

**Problem:** By default, DiveraControl **polls data at intervals** – not elegant, but approved by Divera.
**Solution:** Use webhooks for **instant updates**.

#### ✅ Prerequisites
- **Administrative rights** for the Divera unit

#### 🔧 Setup
1. Set up a **webhook as a trigger** for an automation in Home Assistant.
2. Select the action: **"DiveraControl: Request data update"**.
3. Register the webhook URL in Divera.

> **Advantage:** No more regular polling required – updates occur **on-demand**.
