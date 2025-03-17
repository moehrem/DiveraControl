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
[![HASS QS](https://github.com/moehrem/DiveraControl/actions/workflows/hass.yml/badge.svg)](https://github.com/moehrem/DiveraControl/actions/workflows/hass.yml)
[![HACS QS](https://github.com/moehrem/DiveraControl/actions/workflows/hacs.yml/badge.svg)](https://github.com/moehrem/DiveraControl/actions/workflows/hacs.yml)

---

# DiveraControl für HomeAssistant

> **Hinweis:** DiveraControl befindet sich noch in der Entwicklung. Es können Fehler auftreten, und einige geplante Funktionen fehlen noch. Eine Optimierung hat bislang nicht stattgefunden. Wer trotzdem neugierig ist, kann die [Vorabversionen](https://github.com/moehrem/DiveraControl/releases) testen!

💡 **Fehler oder Funktionswünsche?** Bitte erstelle ein [Issue](https://github.com/moehrem/DiveraControl/issues). Vielen Dank! 👍

## 🔍 Was ist DiveraControl?

**DiveraControl** ist eine Integration von [Divera 24/7](https://www.divera247.com) in [HomeAssistant](https://www.home-assistant.io/). Sie ermöglicht lokalen Administratoren oder Einheitenbesitzern den umfangreichen Datenaustausch zwischen HomeAssistant und Divera 24/7.

In Feuerwehrgebäuden und Fahrzeugen sammeln sich zahlreiche Daten an, die im Einsatzfall sinnvoll genutzt werden können. Leider gibt es kaum erschwingliche, integrierte Lösungen für die Verwaltung und Steuerung dieser Daten. **HomeAssistant** bietet hier eine kostengünstige Zentrale zur Steuerung von zum Beispiel:
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
Die Kommunikation zu Divera basiert vollständig auf der APIv2.

### 📥 **Datenabfrage**
- Alarmdaten
- Einheitendetails
- Verfügbarkeiten
- Fahrzeugdaten & individuelle Eigenschaften
- Berechtigungen
- Nachrichtenkanäle

### 📤 **Datenübergabe**
Verschiedene Divera-Endpunkte sind als Services in HomeAssistant umgesetzt und ermöglichen das Übermitteln von Daten an Divera:
- Alarmerstellung, -änderung & -abschluss
- Fahrzeugdaten & individuelle Eigenschaften
- Einsatzrückmeldungen
- Nachrichtenversand

> Hinweis: Mit dem Aufruf eines Services zur Änderung von Daten werden auch die lokalen Daten geändert, sodass HA immer aktuell ist und nicht auf eine Aktualisierung von Divera warten muss. Dies gilt nicht für die Neuanlage von Daten, z.B. einem Alarm! Neue Datensätze werden immer bei Divera angelegt und anschließend mit HA synchronoisiert.

---

## 💡 Weitere geplante Funktionen
Folgende Funktionen sollen noch integriert werden:
- Hinzufügen von Besatzung zu Fahrzeugen
- Datenabfrage nur bei offenen Alarmen
- Automatisches Erstellen & Löschen von Zonen für Gebäude & Einsatzorte
- Start der Datenabfrage durch Divera-Webhook, um ständiges Polling bei Divera zu reduzieren
- Verfügbarkeit der Einsatzkräft sowie der Rollen


## ❌ Nicht enthalten und bisher nicht geplant
Divera bietet zahlreiche Endpunkte, folgende sind nicht für die Umsetzung geplant:
- Setzen von Nutzerstatus bzw. Rückmeldungen
- Löschen & Archivieren von Alarmen, Mitteilungen & Terminen
- Verwaltung von Terminen (Erstellen, Ändern, Löschen)
- Anhänge hinzufügen
- Leitstellen-Funktionen
- Funktionen der PRO-Version (einheitenübergreifende Alarmierung und Verwaltung)

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
Zur Einrichtung werden entweder **Benutzername & Passwort** oder der **API-Schlüssel** benötigt. Die entsprechende Einrichtungsform kann vom Nutzer gewählt werden.

Falls die Anmeldung mit Benutzername/Passwort fehlschlägt oder es sich um **System-, Schnittstellen-, Monitor- oder Fahrzeugbenutzer** handelt, fragt die Integration direkt nach dem API-Schlüssel.

> Hinweis: Divera bietet verschiedene API-Schlüssel zur Nutzung an. Neben dem persönlichen Schlüssel unter **Profil -> Einstellungen -> Debug**, gibt es außerdem einen allgemeinen Schnittstellenschlüssel unter **Verwaltung -> Schnittstellen**. Dessen Berechtigungen sind jedoch nicht änderbar, weswegen von Divera die Einrichtung und Nutzung eines Schnittstellennutzers unter **Verwaltung -> Schnittstellen -> System-Benutzer** empfohlen wird.

### ⏳ **Abfrageintervalle**
Die Intervalle werden immer je Einheit eingestellt. Das entsprechende Interval wird zur Datenabfrage und -aktualisierung genutzt.
- **Außerhalb von Einsätzen**: längeres Intervall, das außerhalb aktiver Alarme genutzt wird
- **Während eines Einsatzes**: kürzeres Intervall, das im Falle offener Alarme genutzt wird

> Hinweis: Die Integration fragt die Daten regelmäßig aktiv bei Divera ab. Auch dann, wenn keine neuen Daten vorliegen. Um die Anzahl der Anfragen nicht unnötig in die Höhe zu treiben, ist die Einstellung eines Wertes niedriger als 30s nicht möglich.


## Benutzung

### **Services**
Zur Interaktion mit Divera sind verschiedene Services in HomeAssistant implementiert. Sie beginnen alle mit "DiveraControl" und können in Automationen oder eigenen Entwicklungen aufgerufen werden. Umgesetzte Services sind:
- Alarm erstellen
- Alarm schließen/öffnen
- Alarm ändern
- Fahrzeugstatus und -daten ändern
- Fahrzeugeigenschaften ändern
- Nachrichten senden

Weitere Details zu den Services, insbesondere zu obligatorischen und optionalen Parametern, sind in den Entwicklerwerkzeugen des HomeAssistant zu finden.

Services, die bestehende Daten ändern, z.B. eine Fahrzeugposition, tun dies auch bei den lokalen Daten. Somit ist HomeAssistant immer aktuell und muss nicht auf eine Aktualisierung von Divera warten. Dies gilt jedoch nicht für neue Datensätze! So wird z.B. ein neuer Alarm oder eine neue Nachricht immer bei Divera erstellt und erst danach mit HomeAssistant synchronisiert.


## 🔍 **Fehleranalyse**
Bei Fehler ist eine Aktivierung des Debug-Logs und eine Auswertung der Ergebnisse hilfreich.

Außerdem können über das Kontextmenü der Integration sowie im Dienst selbst Diagnosedaten heruntergeladen werden. Darin enthalten sind Details zum System, der Integration, sämtliche von Divera abgefragten Daten sowie die Logs der aktuellen Session, welche DiveraControl betreffen.
> Hinweis: In den Ausgabe werden lediglich die API-Schlüssel maskiert. Weitere Daten inkl personenbezogener Daten oder Alarminhalte sind vollständig, wie von Divera übergeben, in der Ausgabe enthalten. Die Daten sollten daher nicht ungefiltert weitergegeben werden!