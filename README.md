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

Wachen, Fahrzeuge und Geräte werden zunehmend smarter. Die daraus entstehenden Daten können sinnvoll und effektiv genutzt werden, um Einsätze und Alltag effektiver und automatisierter zu gestalten. Leider gibt es kaum erschwingliche, integrierte Lösungen für die Verwaltung und Steuerung dieser Daten. **HomeAssistant** bietet hier eine kostengünstige Zentrale zur Steuerung und Überwachung von zum Beispiel:

- Beleuchtung, Türen & Toren,
- Monitoren & Sprachausgaben,
- Fahrzeugpositionen, Besatzungen & Status,
- Gerätepositionen & Akkuständen,
- ... (theoretisch) jeder beliebige Anwendung, solange die Daten verarbeitet werden können.

Hier kommt **DiveraControl** ins Spiel: Es stellt die Schnittstelle zur Alarmierungssoftware bereit und ermöglicht so eine nahtlose Integration der Divera-Einheit.

**Für wen ist diese Integration gedacht?**

- **Besitzer** und **Administratoren** einer Divera-Einheit
- **Neugierige Nutzer**, die die Möglichkeiten der Divera-API erkunden wollen

> **Hinweis:** Die Integration funktioniert auch mit eingeschränkten Rechten, dann allerdings mit reduziertem Funktionsumfang. Für reine Nutzer einer Einheit ohne erweiterte Berechtigungen empfiehlt sich die bestehende [Divera 24/7 Integration for Home Assistant](https://github.com/fwmarcel/home-assistant-divera).

---

## ⚠️ Disclaimer

Der Datenschutz ist im BOS-Umfeld besonders wichtig. Wenn du HomeAssistant und diese Integration produktiv einsetzt, prüfe bitte sorgfältig, ob Konfiguration, Berechtigungen und Datenflüsse zu deinen rechtlichen und organisatorischen Anforderungen passen.

Diese Integration ist ein Community-Projekt und wird ohne Zusicherung für Verfügbarkeit, Fehlerfreiheit oder Eignung für einen bestimmten Zweck bereitgestellt. Bitte teste die Einrichtung vor dem produktiven Einsatz umfassend und plane geeignete Fallbacks für den Störungsfall ein.

Für den sicheren und datenschutzkonformen Betrieb deiner HomeAssistant-Instanz bist du als Betreiber selbst verantwortlich – insbesondere, aber nicht ausschließlich, für Datenweitergabe, Zugriffsrechte, Protokollierung und Datensicherheit.

Diese Integration steht in keiner Verbindung zur [DIVERA GmbH](https://www.divera247.com/) und wird von dieser nicht unterstützt.

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

Divera bietet zahlreiche Endpunkte, folgende sind (bisher) nicht für die Umsetzung geplant:

- Setzen von Nutzerstatus bzw. Rückmeldungen
- Löschen & Archivieren von Alarmen, Mitteilungen & Terminen
- Verwaltung von Terminen (Erstellen, Ändern, Löschen)
- Anhänge hinzufügen
- Leitstellen-Funktionen
- Funktionen der PRO-Version (einheitenübergreifende Alarmierung und Verwaltung)

---

## 📂 Installation

### 🏆 **HACS (empfohlen)**

DiveraControl ist via HACS (Home Assistant Community Store) verfügbar.

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

Divera bietet verschiedene Nutzerformen an:

- persönlicher/regulärer Nutzer
- Systembenutzer
- Monitornutzer
- Fahrzeugnutzer

> **Hinweis:** Für eine echte Berechtigungssteuerung sollte ein persönlicher, regulärer Nutzer oder ein Monitornutzer zur Anmeldung verwendet werden. Alle anderen Nutzerformen (auch der Systemnutzer, der scheinbar flexibel berechtigt werden kann, tatsächlich aber Daten für TETRAcontrol (Status3IT) zurückgibt) werden ebenso funktionieren, unterliegen jedoch unterschiedlichen nicht änderbaren Beschränkungen der Berechtigungen, können also nicht alle Daten abfragen.

Falls die Anmeldung mit Benutzername/Passwort fehlschlägt oder es sich um **System-, Schnittstellen-, Monitor- oder Fahrzeugbenutzer** handelt, fragt die Integration direkt nach dem API-Schlüssel.

Eine Einheit kann nur einmal registriert werden. Das gilt auch bei Nutzung abweichender Anmeldedaten oder API-Keys.

### ⏳ **Abfrageintervalle**

Die Intervalle werden immer je Einheit eingestellt. Das entsprechende Intervall wird zur Datenabfrage und -aktualisierung genutzt.

- **Außerhalb von Einsätzen**: längeres Intervall, das außerhalb aktiver Alarme genutzt wird
- **Während eines Einsatzes**: kürzeres Intervall, das im Falle offener Alarme genutzt wird

> **Hinweis:** Die Integration fragt die Daten regelmäßig aktiv bei Divera ab. Auch dann, wenn keine neuen Daten vorliegen. Um die Anzahl der Anfragen nicht unnötig in die Höhe zu treiben, ist die Einstellung eines Wertes niedriger als 5s nicht möglich. Für kürzere Reaktionszeiten kann ein Webhook (siehe unten) eingerichtet werden.

### **Basis-URL**

Die Basis-Adresse, unter der die Divera-Instanz erreichbar ist, kann individualisiert werden. Vorbelegt ist die Standard-URL, wenn der Dienst direkt bei Divera gehostet wird.

### **Webhook**

Die Nutzung eines Webhooks ist optional, aber empfohlen. Mit aktivem Webhook stellt die Integration einen Endpunkt samt URL bereit, der [in Divera als Webhookadresse](https://help.divera247.com/pages/viewpage.action?pageId=44171370) eingegeben werden kann. Der Webhook wird von Divera aufgerufen, sobald ein neuer Alarm erstellt wird. Dies verkürzt die Reaktionszeiten von HomeAssistant auf Alarmierungen deutlich.
Zur Einrichtung in Divera gehe zu "Verwaltung" -> "Schnittstellen" -> "Datenübergabe" -> "Webhooks". Setze dort folgende Einstellungen:

- **URL**: wird während des Setups der Integration einmalig angezeigt
- **Format**: POST application/json
- **Inhalt**: "Ohne Inhalt"

Divera kann über den Webhook Daten übergeben. Diese Daten werden von DiveraControl jedoch nicht verarbeitet. Der Webhook dient ausschließlich als Auslöser einer sofortigen Datenabfrage bei Divera.

> **Hinweis:** Falls in HomeAssistant keine externe URL erreichbar ist, wird die Webhook-Option während der Einrichtung automatisch deaktiviert und die Einrichtung ohne Webhook fortgesetzt.

### 🔁 **Re-Konfiguration**

Über das Drei-Punkte-Menü der Integration kann jederzeit eine Re-Konfiguration gestartet werden. Dabei können folgende Werte angepasst werden:

- API-Schlüssel
- Abfrageintervalle
- Basis-URL
- Webhook-Nutzung

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

Alle Aktionen sind geräteabhängig. Das heißt, dass jeder Ausführung die anzusprechende Einheit mitgegeben werden muss. Über Automationen und im Frontend kann als Auslöser einfach eine Einheit gewählt und die gewünschte Aktion ausgeführt werden. Hier sind viele Felder auch mit Auswahlhilfen versehen.
In den Entwickleroptionen oder bei anderer Implementierung der Aktionen muss ein target in Form der device_id eingegeben werden. Aus technischen Gründen können hier einige Felder nicht mit Auswahlhilfen versorgt werden. Das betrifft alle änderbaren Wertehilfen, z.B. Alarme, Fahrzeuge, Besatzung, Gruppen etc. In diese Felder muss stattdessen die entsprechende ID, bei mehreren IDs durch Komma getrennt, eingegeben werden.

Weitere Details zu den Aktionen, insbesondere zu obligatorischen und optionalen Parametern, können im HomeAssistant unter "Entwicklungswerkzeuge" -> "Aktionen" eingesehen werden. Die Umsetzung umfasst sowohl den "YAML-Modus" als auch den "UI-Modus". Alle Aktionen beginnen mit "DiveraControl: ", gefolgt vom Namen und einer kurzen Beschreibung. Es ist dort außerdem möglich, Aktionen manuell zu testen. Weitere Informationen zur Funktionsweise und dem Einsatz von Aktionen [sind hier zu finden](https://www.home-assistant.io/docs/scripts/perform-actions/).

Aktionen, die bestehende Daten ändern, z.B. eine Fahrzeugposition, tun dies auch bei den lokalen Daten. Somit ist HomeAssistant immer aktuell und muss nicht auf eine Aktualisierung von Divera warten. Dies gilt jedoch nicht für neue Datensätze! So wird z.B. ein neuer Alarm oder eine neue Nachricht immer bei Divera erstellt und erst danach mit HomeAssistant synchronisiert.

> **Hinweis**: Aktionen sind berechtigungsabhängig! Zu jeder Einheit (abgebildet als Gerät) werden nur solche Aktionen angeboten, für die der Nutzer Berechtigungen hat. Unabhängig davon wird vor jeder Aktionsausführung die Berechtigung geprüft und die Aktion ggf. abgebrochen.

#### Technische Service-IDs

Für YAML, Automationen und Entwicklerwerkzeuge sind folgende Service-IDs relevant:

- `diveracontrol.post_vehicle_status`
- `diveracontrol.post_alarm`
- `diveracontrol.put_alarm`
- `diveracontrol.post_close_alarm`
- `diveracontrol.post_message`
- `diveracontrol.post_using_vehicle_property`
- `diveracontrol.post_using_vehicle_crew`
- `diveracontrol.post_news`

### 🧩 **Entitäten (Überblick)**

Die Integration legt je Einheit dynamische Entitäten in mehreren Plattformen an:

- **Sensoren**: u.a. Alarmsensoren, Fahrzeugsensoren, Verfügbarkeitssensoren, Open-Alarms-Zähler, Einheits-/Diagnose-Sensoren
- **Device Tracker**: Alarmpositionen und Fahrzeugpositionen
- **Kalender**: Termine aus Divera

## ⁉️ **Fehleranalyse**

Zur Analyse kann im Menü der Integration das "Debug-Protokoll" aktiviert werden. Damit wird der Loglevel der Integration auf "Debug" gesetzt und entsprechend deutlich mehr Logging ausgegeben.

Zu jeder erstellen Einheit können im Kontextmenü die "Diagnosedaten" heruntergeladen werden. Darin enthalten sind Details zum System, der Integration, sämtliche von Divera abgefragten Daten sowie die Logs der aktuellen Session, welche DiveraControl betreffen.

> **Hinweis:** In den Diagnosedaten werden aktuell nur `api_key` und `accesskey` maskiert. Weitere Daten, inklusive u.a. personenbezogener Daten und Alarminhalte, sind vollständig enthalten. Die Daten sollten daher nie ungefiltert weitergegeben werden!
