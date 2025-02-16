<p align="center">
  <a href="https://www.divera247.com">
    <img src="https://www.divera247.com/downloads/grafik/divera247_logo_800.png" alt="Divera 24/7">
  </a>
</p>

---

[![English](https://img.shields.io/badge/🇬🇧%20-English-blue)](README.en.md)

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

# DiveraControl für HomeAssistant

> **Hinweis:** DiveraControl befindet sich noch in der Entwicklung. Es können Fehler auftreten, und einige geplante Funktionen fehlen noch. Eine Optimierung hat bislang nicht stattgefunden. Wer trotzdem neugierig ist, kann die [Vorabversionen](https://github.com/moehrem/DiveraControl/releases) testen!

💡 **Fehler oder Funktionswünsche?** Bitte erstelle ein [Issue](https://github.com/moehrem/DiveraControl/issues). Vielen Dank! 👍

## 🔍 Was ist DiveraControl?

**DiveraControl** ist eine Integration von [Divera 24/7](https://www.divera247.com) in [HomeAssistant](https://www.home-assistant.io/). Sie ermöglicht lokalen Administratoren oder Einheitenbesitzern den umfangreichen Datenaustausch zwischen HomeAssistant und Divera 24/7.

In Feuerwehrgebäuden und Fahrzeugen sammeln sich zahlreiche Daten an, die im Einsatzfall sinnvoll genutzt werden können. Leider gibt es kaum erschwingliche, integrierte Lösungen für die Verwaltung und Steuerung dieser Daten. **HomeAssistant** bietet hier eine kostengünstige Zentrale zur Steuerung von:
- Beleuchtung, Türen & Toren
- Monitoren & Sprachausgaben
- Fahrzeugpositionen, Besatzungen & Status
- Gerätepositionen & Akkuständen

Hier kommt **DiveraControl** ins Spiel: Es stellt die Schnittstelle zur Alarmierungssoftware bereit und ermöglicht so eine nahtlose Integration.

**Für wen ist diese Integration gedacht?**
- **Administratoren** und **Schnittstellennutzer** einer Einheit
- **Neugierige Nutzer**, die die Möglichkeiten der API erkunden wollen

> **Hinweis:** Die Integration funktioniert auch mit eingeschränkten Rechten, dann allerdings mit reduziertem Funktionsumfang. Nutzer einer Einheit können die bestehende [Divera 24/7 Integration for Home Assistant](https://github.com/fwmarcel/home-assistant-divera) verwenden.

---

## ⚠️ Disclaimer

Der **Datenschutz** ist im BOS-Bereich besonders wichtig. Jeder Einsatz von HomeAssistant und dieser Integration in realen Lagen erfolgt **auf eigene Verantwortung**. Die Einhaltung der Datenschutzrichtlinien – insbesondere im Hinblick auf **Datenweitergabe, -verarbeitung und -sicherheit** – liegt vollständig beim Nutzer.

> Diese Integration steht in **keiner Verbindung** zu Divera 24/7 und wird von Divera **nicht unterstützt**.

---

## ✅ Funktionsumfang

### 📥 **Datenabfrage**
- Alarmdaten
- Einheitendetails
- Verfügbarkeiten
- Fahrzeugdaten & individuelle Eigenschaften
- Berechtigungen
- Nachrichtenkanäle

### 📤 **Datenübergabe**
HomeAssistant-Services ermöglichen das Übermitteln von Daten an Divera:
- Alarmerstellung, -änderung & -abschluss
- Fahrzeugdaten & individuelle Eigenschaften
- Einsatzrückmeldungen
- Nachrichtenversand

---

## ❌ (Noch) nicht enthalten
Divera bietet zahlreiche Endpunkte, nicht alle sind integriert:
- Löschen & Archivieren von Alarmen, Mitteilungen & Terminen
- Verwaltung von Terminen (Erstellen, Ändern, Löschen)
- Anhänge hinzufügen
- Besatzung zu Fahrzeugen hinzufügen
- Leitstellen-Funktionen
- PRO-Version-Features (einheitenübergreifende Alarmierung)
- Setzen von Nutzerstatus bzw. Rückmeldungen

**Geplante Funktionen:**
- Hinzufügen von Besatzung zu Fahrzeugen
- Datenabfrage nur bei offenen Alarmen
- Automatisches Erstellen & Löschen von Zonen für Gebäude & Einsatzorte

---

## 📂 Installation

### 🏆 **HACS (empfohlen)**
DiveraControl ist (noch) nicht im HAC-Store verfügbar, kann aber bereits manuell hinzugefügt werden:

1. [HACS installieren](https://www.hacs.xyz/docs/use/)
2. [![HACS Repo hinzufügen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=moehrem&repository=diveracontrol&category=Integration)
3. **Installation:** Unten rechts auf "Herunterladen" klicken.

### 🔧 **Manuelle Installation**
- [Letzten Release](https://github.com/moehrem/DiveraControl/releases/latest) herunterladen
- Dateien in `config/custom_components/diveracontrol` extrahieren

---

## ⚙️ Einrichtung

### 🔑 **Authentifizierung**
Zur Einrichtung benötigt man **Benutzername & Passwort** oder direkt den **API-Schlüssel**. Die Anmeldung erfolgt initial immer mit den **persönlichen Zugangsdaten**. Diese Daten werden nicht gespeichert, es wird damit nur der API-Schlüssel des Nutzers abgefragt.

Falls die Anmeldung mit Benutzername/Passwort fehlschlägt oder es sich um **System-, Schnittstellen-, Monitor- oder Fahrzeugbenutzer** handelt, fragt die Integration direkt nach dem API-Schlüssel.

> Hinweis: Divera bietet verschiedene API-Schlüssel zur Nutzung an. Neben dem persönlichen Schlüssel unter **Profil -> Einstellungen -> Debug**, gibt es außerdem einen allgemeinen Schnittstellenschlüssel unter **Verwaltung -> Schnittstellen**. Empfohlen wird jedoch die Einrichtung und Nutzung eines Schnittstellennutzers unter **Verwaltung -> Schnittstellen -> System-Benutzer**. Nur zu diesem lassen sich sinnvoll Berechtigungen einrichten.

### ⏳ **Abfrageintervalle**
Die Intervalle werden immer je Einheit eingestellt.
- **Außerhalb von Einsätzen**: längeres Intervall
- **Während eines Einsatzes**: kürzeres Intervall, das im Falle offener Alarme zur Aktualisierung der Daten genutzt wird

> Hinweis: Die Integration fragt die Daten regelmäßig aktiv bei Divera ab. Auch dann, wenn keine neuen Daten vorliegen. Um die Anzahl der Anfragen nicht unnötig in die Höhe zu treiben, dürfen keine Werte niedriger als 30s eingestellt werden.

---

## 👍 Benutzung

### 🔍 **Datenabfrage**
Die Abfragen laufen automatisiert im Hintergrund. Folgende Sensoren stehen zur Verfügung:
- **Einheitendetails** (Name, Adresse, Koordinaten)
- **Fahrzeuge** (Status, Position, Besatzung, Eigenschaften)
- **Alarme** (Stichwort, Text, Rückmeldungen)
- **Offene Alarme** (Anzahl)
- **Tracker** (für Einsätze & Fahrzeuge)

### 📤 **Datenübergabe** (HomeAssistant-Services)
- Fahrzeugdaten aktualisieren
- Alarme erstellen, ändern & schließen
- Nachrichten senden

### 🔄 **Sensoren-Handling**
- Sensoren werden automatisch aktualisiert
- Sensoren ohne aktuelle Daten werden aus HomeAssistant entfernt

### ⚙️ **Konfigurationsänderungen**
Über die HomeAssistant-Integrationsverwaltung anpassbar:
- Abfrageintervalle
- API-Schlüssel