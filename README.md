<p align="center">
  <a href="https://www.divera247.com">
    <img src="https://www.divera247.com/downloads/grafik/divera247_logo_800.png" alt="Divera 24/7">
  </a>
</p>

---

[![English](https://img.shields.io/badge/🇬🇧%20-English-blue)](README.en.md)

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

# DiveraControl für Home Assistant

💡 **Fehler oder Funktionswünsche?** Bitte erstelle ein [Issue](https://github.com/moehrem/DiveraControl/issues). Vielen Dank! 👍

---

## 🔍 Was ist DiveraControl?

**DiveraControl** ist eine **Integration von [Divera 24/7](https://www.divera247.com) in [Home Assistant](https://www.home-assistant.io/)**. Sie stellt umfassende Daten von angebundenen Divera-Einheiten bereit und ermöglicht über Aktionen den bidirektionalen Datenaustausch – z. B. zum Ändern von Status oder Auslösen von Alarmen.

Die Integration richtet sich an **Anwender, Administratoren und Einheitenbesitzer**. Abhängig von den individuellen Berechtigungen in Divera stehen verschiedene Funktionen zur Verfügung.

> **Hinweis:** Auf vielfachen Wunsch wurden mit **v2.0.0** auch persönliche Funktionen umgesetzt, sodass die Integration nun auch für den Heimbedarf sinnvoll einsetzbar ist.

Wachen, Fahrzeuge und Geräte werden zunehmend smarter. Die entstehenden Daten lassen sich nutzbringend einsetzen, um Einsätze und Alltag **effektiver und automatisierter zu gestalten**. Leider gibt es kaum erschwingliche Lösungen für die Verwaltung und Steuerung dieser Daten. **Home Assistant** bietet hier eine kostengünstige Zentrale zur Steuerung und Überwachung von:
- Beleuchtung, Türen & Toren,
- Monitoren & Sprachausgaben,
- Fahrzeugpositionen, Besatzungen & Status,
- Gerätepositionen & Akkuständen,
- theoretisch **jeder beliebigen Anwendung**, solange die Daten in Home Assistant verarbeitbar sind.

**DiveraControl** schließt diese Lücke: Es stellt die **Schnittstelle zu Divera** bereit und ermöglicht eine **nahtlose Integration** der Einheit in Home Assistant.

---

## ⚠️ Haftungsausschluss & Datenschutz

Diese Integration ist ein **Community-Projekt ohne Verbindung zur DIVERA GmbH** und wird von dieser **nicht unterstützt**.

> **Wichtig:** Der Betreiber der Home Assistant-Instanz ist **allein verantwortlich** für:
> - **Datenschutzkonformität** (insb. DS-GVO, BDSG, organisatorische Vorgaben)
> - **Sichere Konfiguration** (Zugriffsrechte, Protokollierung, API-Schlüssel)
> - **Fallback-Strategien** für den Produktivbetrieb

**Keine Gewähr** für Verfügbarkeit, Fehlerfreiheit oder Eignung für bestimmte Zwecke.
**Teste die Einrichtung vor dem Produktiveinsatz umfassend!**

---

## ✅ Funktionsumfang

Die Kommunikation mit Divera erfolgt **ausschließlich über die APIv2**.

---

### 📥 Datenabfrage und -bereitstellung

| **Daten**                     | **Beschreibung**                          |
|-------------------------------|------------------------------------------|
| Alarmdaten                    | Alle nicht archivierten Alarme          |
| Letzter Alarm                 | Details zum aktuellsten Alarm            |
| Einheitendetails              | Informationen zur Divera-Einheit         |
| Nutzerdetails                 | Nutzerdaten und -informationen           |
| Nutzerstatus                  | Aktueller Status der Nutzer               |
| Verfügbarkeiten              | Verfügbarkeit je Status                  |
| Fahrzeugdaten & -positionen   | Daten und Standorte der Fahrzeuge        |
| Fahrzeugeigenschaften         | Individuelle Fahrzeugeinstellungen       |
| Berechtigungen                | Nutzer- und Einheitenberechtigungen      |
| Nachrichtenkanäle             | Kanäle für den Nachrichtenaustausch      |
| Kalendereinträge              | Termine aus Divera                        |

---

### 📤 Datenübergabe (Aktionen)

Divera-Endpunkte sind als **Aktionen in Home Assistant** umgesetzt und ermöglichen das Senden von Daten an Divera.

| **Aktion**                          | **Beschreibung**                          |
|-------------------------------------|------------------------------------------|
| Nutzerstatus setzen                 | Ändert den Status eines Nutzers          |
| Alarm erstellen/ändern/abschließen | Verwaltung von Alarmen                   |
| Fahrzeugdaten aktualisieren         | Position, Status & Eigenschaften          |
| Einsatzrückmeldungen                | Rückmeldungen zu Einsätzen               |
| Nachrichten versenden                | Senden von Nachrichten                    |
| Mitteilungen erstellen              | Erstellung von Mitteilungen               |

> **Hinweis:** Detaillierte Beschreibungen zu Parametern und Nutzung finden sich weiter unten unter [Aktionen](#-aktionen).

---
---
## 💡 Roadmap & Mitwirkung

📌 **Geplante Funktionen** finden sich in den [Issues](https://github.com/moehrem/DiveraControl/issues).
**Beteilige dich gerne an Diskussionen oder der Entwicklung!**

💡 **Neue Vorschläge** können als Issue eingereicht werden.

---
## ❌ Nicht unterstützt

Folgende Divera-Endpunkte sind **nicht geplant**:

| **Funktion**                          | **Begründung**                          |
|---------------------------------------|----------------------------------------|
| Löschen/Archivieren von Alarmen        | Nicht im Scope der Integration          |
| Terminverwaltung (CRUD)               | Komplexität & Berechtigungsmanagement   |
| Anhänge hinzufügen                    | Technische Einschränkungen             |
| Leitstellen-Funktionen                | Zielgruppe sind Einheiten, nicht Leitstellen |
| PRO-Version-Funktionen               | Einheitenübergreifende Verwaltung       |

---

## 📂 Installation

### 🏆 **HACS (empfohlen)**

1. [HACS installieren](https://www.hacs.xyz/docs/use/)
2. [![HACS Repo hinzufügen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=moehrem&repository=diveracontrol&category=Integration)
3. **Installieren:** Unten rechts auf **"Herunterladen"** klicken.

---
### 🔧 **Manuelle Installation**

1. [Letzten Release](https://github.com/moehrem/DiveraControl/releases/latest) herunterladen
2. Dateien nach `config/custom_components/diveracontrol` extrahieren

---
---
## ⚙️ Einrichtung

---
### 🔑 Authentifizierung

Für die Einrichtung werden **Benutzername & Passwort** oder ein **API-Schlüssel** benötigt.

#### 👤 Nutzerformen in Divera
| **Nutzertyp**               | **Beschreibung**                          | **Empfohlen?** |
|-----------------------------|------------------------------------------|----------------|
| Persönlicher/regulärer Nutzer | Volle Berechtigungssteuerung            | ✅ **Ja**       |
| Monitornutzer               | Eingeschränkte Berechtigungen           | ✅ **Ja**       |
| Systembenutzer              | Technischer Nutzer, berechtigungsabhängig | ⚠️ Eingeschränkt |
| Fahrzeugnutzer              | Fahrzeugspezifische Daten                 | ⚠️ Eingeschränkt |

> **Hinweis:**
> - Für eine **volle Berechtigungssteuerung** sollten **persönliche oder Monitornutzer** verwendet werden.
> - System-/Fahrzeugnutzer funktionieren **technisch**, unterliegen aber **Divera-internen Beschränkungen** (z. B. Rückgabe von TETRAcontrol-Daten).
> - Falls die Anmeldung mit Benutzername/Passwort fehlschlägt, wird **automatisch der API-Schlüssel abgefragt**.

#### 🔑 API-Schlüssel
Der Schlüssel findet sich:
- **Persönlicher Nutzer:** *"Einstellungen" → "Debug"*
- **Einheit:** *"Verwaltung" → "Schnittstellen"*
- **System-/Monitornutzer:**Jeweilige Verwaltungsoptionen

> **Wichtig:** Jede Kombination aus **Nutzer + Einheit** kann **nur einmal registriert** werden.
> Ein Nutzer kann jedoch **mehrfach** für verschiedene Einheiten hinzugefügt werden.

---
### ⏳ Abfrageintervalle

Die Intervalle werden **je Einheit** konfiguriert:

| **Intervall**               | **Beschreibung**                          | **Empfohlener Wert** |
|-----------------------------|------------------------------------------|----------------------|
| **Außerhalb von Einsätzen** | Längeres Intervall für normale Abfragen | 60s                |
| **Während eines Einsatzes**| Kürzeres Intervall bei aktiven Alarmen   | 30s                |

> **Hinweis:**
> - Die Integration fragt **regelmäßig aktiv** Daten bei Divera ab.
> - **Minimalwert: 5s** (kürzere Intervalle sind nicht möglich, um die Serverlast zu begrenzen).
> - Für **Echtzeit-Updates** → [Webhooks](#-webhooks-für-echtzeit-updates) nutzen.

---
### 🌐 Basis-URL

Die Basis-Adresse der Divera-Instanz kann **individuell angepasst** werden.
**Standard:** `https://api.divera247.com` (für Divera-gehostete Instanzen).

---
### 🔁 Re-Konfiguration

Jede Einheit kann über den **Zahnradbutton** neu konfiguriert werden.
Es wird unterschieden zwischen:

#### **🏢 Einheiteneinstellungen** (gelten für alle Nutzer der Einheit)
- Abfrageintervalle (außerhalb/während Einsätzen)
- Basis-URL

#### **👤 Benutzereinstellungen** (nutzerindividuell)
- **API-Schlüssel** (für System-/Monitor-/Fahrzeugnutzer)
- **Benutzername/Passwort** (für persönliche Nutzer)

---
---
## 🔨 Benutzung

---
### 📟 Aktionen

Aktionen beginnen mit **"DiveraControl:"** und können in **Automationen, Dashboards oder Skripten** genutzt werden.

| **Aktion**                          | **Parameter** (Beispiele)               | **Beschreibung**                          | **Berechtigung**          |
|-------------------------------------|-----------------------------------------|------------------------------------------|---------------------------|
| **Alarm erstellen**                 | `title`, `message`, `priority`          | Erstellt einen neuen Alarm               | Admin/Einheitenbesitzer    |
| **Alarm ändern**                    | `alarm_id`, `title`, `message`          | Bearbeitet einen bestehenden Alarm       | Admin                     |
| **Alarm öffnen/schließen**          | `alarm_id`, `status`                    | Ändert den Alarmstatus                   | Admin                     |
| **Nutzerstatus setzen**             | `status_id`                             | Ändert den Status des Nutzers            | Persönlicher Nutzer       |
| **Nachricht senden**                | `channel_id`, `message`                 | Sendet eine Nachricht                     | Abhängig vom Kanal         |
| **Mitteilung erstellen**            | `title`, `message`, `recipients`        | Erstellt eine Mitteilung                 | Admin                     |
| **Fahrzeugbesatzung ändern**         | `vehicle_id`, `user_ids`                | Wechselt die Besatzung                   | Admin/Fahrzeugnutzer      |
| **Fahrzeugeigenschaften ändern**   | `vehicle_id`, `property`, `value`       | Aktualisiert Eigenschaften               | Admin                     |
| **Fahrzeugstatus ändern**           | `vehicle_id`, `status`, `latitude`, `longitude` | Position & Status | Admin/Fahrzeugnutzer |
| **Datenaktualisierung anfordern**  | –                                       | Erzwingt einen sofortigen Abruf          | Alle Nutzer               |

> **💡 Tipps:**
> - Aktionen sind **geräteabhängig** → Wähle als Auslöser das **Nutzer-Gerät** in Home Assistant.
> - In Dashboards können Buttons mit Aktionen verknüpft werden (Auswahlhilfen verfügbar).
> - **Testen:** Unter *"Einstellungen" → "Entwicklungswerkzeuge" → "Aktionen"* können Aktionen manuell getestet werden.
> - [Dokumentation zu Aktionen in Home Assistant](https://www.home-assistant.io/docs/scripts/perform-actions/)

---
#### ⚠️ Wichtige Hinweise zu Aktionen
- **Lokale Aktualisierung:** Ändern bestehende Daten (z. B. Fahrzeugposition) diese **sofort lokal** in Home Assistant. Keine Wartezeit auf Divera-Sync!
- **Neue Datensätze:** Werden **zuerst in Divera erstellt** und dann mit Home Assistant synchronisiert.
- **Berechtigungen:** Aktionen sind **technisch für alle Nutzer verfügbar**, werden aber **vor Ausführung geprüft** und bei fehlenden Rechten abgebrochen.

---
### 🧩 Entitäten (Überblick)

Die Integration erzeugt **dynamisch Entitäten** je Einheit:

| **Plattform**       | **Entitäten** (Beispiele)                          | **Zweck**                          |
|---------------------|---------------------------------------------------|------------------------------------|
| **Steuerelemente**  | Nutzerstatus setzen                               | Statusänderung per Klick           |
| **Sensoren**        | Alarme, Fahrzeuge, Verfügbarkeiten, Offene-Alarme-Zähler, Letzter Alarm, Diagnose-Sensoren | Datenabfrage & Monitoring |
| **Device Tracker**  | Alarmpositionen, Fahrzeugpositionen               | Standortverfolgung in Karten        |
| **Kalender**        | Termine aus Divera                                 | Integration in Kalender-Views      |

---
---
## ⁉️ Fehleranalyse

| **Methode**               | **Beschreibung**                          | **Achtung** |
|---------------------------|------------------------------------------|-------------|
| **Debug-Protokoll**       | Aktiviert erweiterte Logs in Home Assistant | Loglevel wird auf *Debug* gesetzt |
| **Diagnosedaten**         | Herunterladbar im Kontextmenü der Einheit | Enthält **alle lokalen Daten** (inkl. personenbezogener Daten!) |

> **⚠️ Wichtig:**
> - In Diagnosedaten werden **nur `api_key` und `accesskey` maskiert**.
> - **Alle anderen Daten** (Nutzerdaten, Alarminhalte, etc.) sind **unverschlüsselt** enthalten.
> - **Nie ungefiltert weitergeben!**

---
---
## 💡 Praxistipps

---
### 🔄 Webhooks für Echtzeit-Updates

**Problem:** Standardmäßig fragt DiveraControl Daten **in Intervallen** ab – wenig elegant, aber von Divera freigegeben.
**Lösung:** Webhooks für **sofortige Updates** nutzen.

#### ✅ Voraussetzungen
- **Verwaltungsberechtigung** für die Divera-Einheit

#### 🔧 Einrichtung
1. **Webhook als Auslöser** einer Automation in Home Assistant einrichten.
2. **Aktion:** *"DiveraControl: Datenaktualisierung anfordern"* auswählen.
3. Webhook-URL in Divera hinterlegen.

> **Vorteil:** Keine regelmäßigen Abfragen mehr nötig – Updates erfolgen **on-demand**.