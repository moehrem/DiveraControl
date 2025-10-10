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

💡 **Fehler oder Funktionswünsche?** Bitte erstelle ein [Issue](https://github.com/moehrem/DiveraControl/issues). Vielen Dank! 👍

## 🔍 Was ist DiveraControl?

**DiveraControl** ist eine Integration von [Divera 24/7](https://www.divera247.com) in [HomeAssistant](https://www.home-assistant.io/). Sie ermöglicht lokalen Administratoren oder Einheitenbesitzern einen umfangreichen Datenaustausch zwischen HomeAssistant und Divera 24/7.

In Feuerwehrgebäuden und Fahrzeugen sammeln sich zahlreiche Daten an, die im Einsatzfall sinnvoll genutzt werden können. Leider gibt es kaum erschwingliche, integrierte Lösungen für die Verwaltung und Steuerung dieser Daten. **HomeAssistant** bietet hier eine kostengünstige Zentrale zur Steuerung von zum Beispiel:

- Beleuchtung, Türen & Toren
- Monitoren & Sprachausgaben
- Fahrzeugpositionen, Besatzungen & Status
- Gerätepositionen & Akkuständen

Hier kommt **DiveraControl** ins Spiel: Es stellt die Schnittstelle zur Alarmierungssoftware bereit und ermöglicht so eine nahtlose Integration.

**Für wen ist diese Integration gedacht?**

- **Besitzer** und **Administratoren** einer Divera-Einheit
- **Neugierige Nutzer**, die die Möglichkeiten der Divera-API erkunden wollen

> **Hinweis:** Die Integration funktioniert auch mit eingeschränkten Rechten, dann allerdings mit reduziertem Funktionsumfang. Für reine Nutzer einer Einheit empfiehlt sich die bestehende [Divera 24/7 Integration for Home Assistant](https://github.com/fwmarcel/home-assistant-divera).

---

## ⚠️ Disclaimer

Der **Datenschutz** ist im BOS-Bereich besonders wichtig. Jeder Einsatz von HomeAssistant und dieser Integration in realen Lagen erfolgt **auf eigene Verantwortung**. Die Einhaltung der Datenschutzrichtlinien – insbesondere im Hinblick auf **Datenweitergabe, -verarbeitung und -sicherheit** – liegt vollständig beim Nutzer.

> Diese Integration steht in **keiner Verbindung** zu und wird auch **nicht unterstützt** von der DIVERA GmbH.

---

## ✅ Funktionsumfang

Die Kommunikation zu Divera basiert vollständig auf der APIv2.

### 📥 **Datenabfrage**

- Alarmdaten
- Einheitendetails
- Verfügbarkeiten
- Fahrzeugdaten und -positionen
- individuelle Fahrzeugeigenschaften
- Berechtigungen
- Nachrichtenkanäle
- Kalendereinträge

### 📤 **Datenübergabe**

Verschiedene Divera-Endpunkte sind als Aktionen in HomeAssistant umgesetzt und ermöglichen das Übermitteln von Daten an Divera:

- Alarmerstellung, -änderung & -abschluss
- Fahrzeugdaten & individuelle Eigenschaften
- Einsatzrückmeldungen
- Nachrichtenversand
- Erstellung von Mitteilungen

---

## 💡 Weitere geplante Funktionen

Anstehende Funktionen finden sich in den Issues. Beteilige dich gerne an der Diskussion oder auch der Entwicklung!
Neue Vorschläge dürfen gerne als Issue angefragt werden.

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

DiveraControl ist via HACS (Home Assistant COmmunity Store) verfügbar.

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
Der persönliche API-Schlüssel ist in den Nutzerdaten unter "Einstellungen" -> "Debug" zu finden. Alternativ kann der Schlüssel der Einheit unter "Verwaltung" -> "Schnittstellen" genutzt werden oder der Schlüssel des System- oder Monitornutzers aus den jeweiligen Verwaltungsoptionen.

Divera bietet verscheidene Nutzerformen an:

- persönlicher/regulärer Nutzer
- Systembenutzer
- Monitornutzer
- Fahrzeugnutzer

> **Hinweis:** Für eine echte Berechtigungssteuerung sollte ein persönlicher, regulärer Nutzer oder ein Monitornutzer zur Anmeldung verwendet werden. Alle anderen Nutzerformen (auch der Sytemnutzer, der scheinbar flexibel berechtigt werden kann, tatsächlich aber Daten für TETRAcontrol (Status3IT) zurückgibt) werden ebenso funktionieren, unterliegen jedoch unterschiedlichen nicht änderbaren Beschränkungen der Berechtigungen, können also nicht alle Daten abfragen.

Falls die Anmeldung mit Benutzername/Passwort fehlschlägt oder es sich um **System-, Schnittstellen-, Monitor- oder Fahrzeugbenutzer** handelt, fragt die Integration direkt nach dem API-Schlüssel.

Die Anmeldung eines Nutzers einer Einheit, die bereits integriert wurde, ist nicht möglich.

### ⏳ **Abfrageintervalle**

Die Intervalle werden immer je Einheit eingestellt. Das entsprechende Interval wird zur Datenabfrage und -aktualisierung genutzt.

- **Außerhalb von Einsätzen**: längeres Intervall, das außerhalb aktiver Alarme genutzt wird
- **Während eines Einsatzes**: kürzeres Intervall, das im Falle offener Alarme genutzt wird

> **Hinweis:** Die Integration fragt die Daten regelmäßig aktiv bei Divera ab. Auch dann, wenn keine neuen Daten vorliegen. Um die Anzahl der Anfragen nicht unnötig in die Höhe zu treiben, ist die Einstellung eines Wertes niedriger als 30s für "außerhalb von Einsätzen" bzw 10s für "während Einsätzen" nicht möglich.

## 🔨 Benutzung

### 📟 **Aktionen**

Zur Interaktion mit Divera sind verschiedene Aktionen in HomeAssistant implementiert. Sie beginnen alle mit "DiveraControl" und können in Automationen, im Frontend über Buttons, in eigenen Entwicklungen - kurz: überall da, wo in HomeAssistant Aktionen unterstützt werden - aufgerufen werden. Umgesetzte Aktionen sind:

- Alarm erstellen
- Alarm schließen/öffnen
- Nachrichten senden
- Fahrzeugbesatzung ändern
- Fahrzeugeigenschaften ändern
- Fahrzeugstatus und -daten ändern
- Alarm ändern
- Erstellen einer neuen Mitteilung

Alle Aktionen sind geräteabhängig. Das heißt, dass jeder Ausführung die anzusprechende Einheit mitgegeben werden muss. Über Automationen und im Frontend kann als Auslöser einfach eine Einhet gewählt und die gewünschte Aktion ausgeführt werden.
In den Entwickleroptionen oder bei anderer Implementierunt der Aktionen muss ein target in Form der device_id eingegeben werden.

Weitere Details zu den Aktionen, insbesondere zu obligatorischen und optionalen Parametern, können im HomeAssistant unter "Entwicklungswerkzeuge" -> "Aktionen" eingesehen werden. Es ist dort außerdem möglich, Aktionen manuell zu testen. Weitere Informationen zur Funktionsweise und dem Einsatz von Aktionen [sind hier zu finden](https://www.home-assistant.io/docs/scripts/perform-actions/).

Aktionen, die bestehende Daten ändern, z.B. eine Fahrzeugposition, tun dies auch bei den lokalen Daten. Somit ist HomeAssistant immer aktuell und muss nicht auf eine Aktualisierung von Divera warten. Dies gilt jedoch nicht für neue Datensätze! So wird z.B. ein neuer Alarm oder eine neue Nachricht immer bei Divera erstellt und erst danach mit HomeAssistant synchronisiert.

## ⁉️ **Fehleranalyse**

Zur Analyse kann im Menü der Integration das "Debug-Protokoll" aktiviert werden. Damit wird der Loglevel der Integration auf "Debug" gesetzt und entsprechend deutlich mehr Logging ausgegeben.

Im Kontextenü zum erstellen Dienst selbst können die "Diagnosedaten heruntergeladen" werden. Darin enthalten sind Details zum System, der Integration, sämtliche von Divera abgefragten Daten sowie die Logs der aktuellen Session, welche DiveraControl betreffen.

> **Hinweis:** In der Ausgabedatei werden lediglich die API-Schlüssel maskiert. Weitere Daten, inklusive u.a. personenbezogener Daten und Alarminhalte sind vollständig, wie von Divera übergeben, in der Ausgabe enthalten. Die Daten sollten daher nicht ungefiltert weitergegeben werden!
