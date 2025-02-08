<p align="center">
  <a href="https://www.divera247.com">
    <img src="https://www.divera247.com/downloads/grafik/divera247_logo_800.png" alt="Divera 24/7">
  </a>
</p>

- [🇬🇧 English](README.en.md)

# DiveraControl

**DiveraControl ist noch in der Entwicklung und kann daher Fehler aufweisen. Es fehlen noch ein paar geplante Funktionen. Eine Optimierung hat bisher nicht stattgefunden. Wer trotzdem neugierig ist, darf gerne testen!**

**Wer Fehler findet oder Funktionen Vermisst, erstellt bitte einen [Issue](https://github.com/moehrem/DiveraControl/issues). Vielen Dank!**

---

**DiveraControl** ist eine Integration von Divera 24/7 in den HomeAssistant. Ziel dieser Integration ist es, einen umfangreichen Datenaustausch mit Divera 24/7 zu ermöglichen.

Feuerwehrgebäude, Fahrzeuge und Gerätschaften werden zunehmend smarter. Jedoch gibt es kaum einen (oder zumindest für kleine Feuerwehren kaum einen erschwinglichen) integrativen Anbieter für eine zentrale Verwaltung, Steuerung und Verteilung dieser Daten mit dem Ziel, smarte Geräte zu koordinieren. Hier kommt HomeAssistant ins Spiel. Dieser kann als kostengünstige zentrale Steuerung für zB Beleuchtung, Türen und Tore, Monitore, Sprachausgaben, Fahrzeugpositionen, -besatzungen und -status, Gerätepositionen, Ladestand von Akkus, individuelle Monitore usw. eingesetzt werden. Vorausgesetzt es gibt eine Anbindung zur Alarmierungssoftware - und hier soll diese Integration helfen.

Um die Integration voll ausschöpfen zu können, sind umfangreiche Berechtigungen in der anzubindenden Einheit nötig. Zielgruppe der Integration sind Administratoren bzw Schnittstellennutzer einer Einheit.

Da ich selbst Feuerwehrmann bin, habe ich für die Anwendung klar die Feuerwehr im Fokus. Da Divera 24/7 jedoch vielfältig genutzt wird, die Schnittstelle aber für alle gleich ist, kann diese Integration sicher auch für Zwecke außerhalb der Feuerwehr eingesetzt werden.

Die Integration funktioniert auch mit eingeschränkten Rechten, bietet dann aber nicht denselben Umfang. Für den persönlichen Einsatz bietet sich die schon länger existierende Integration [Divera 24/7 Integration for Home Assistant](https://github.com/fwmarcel/home-assistant-divera) an.

---

## Disclaimer

Im BOS-Bereich besitzt das Thema Datenschutz bekanntermaßen eine besondere Bedeutung. Jeder Einsatz von HomeAssistant und dieser Integration in realen Lagen erfolgt auf **eigene Verantwortung**. Die Berücksichtigung der Datenschutzbestimmungen, insbesondere, jedoch nicht beschränkt auf "Weitergabe von Daten an Dritte", "Datenverarbeitung" und "Datensicherheit", liegt vollständig in der Verantwortung des Nutzers.
Diese Integration steht in **keiner Verbindung** zu Divera 24/7 und wird von Divera 24/7 auch **nicht unterstützt**.

---

## Was kann DiveraControl?

- Verwaltung mehrerer **unterschiedlicher** Nutzer/Einheiten
- Anbindung mehrerer Einheiten desselben Nutzers
- Unterstützt parallele Alarme

### Datenabfrage
- Alarmdaten
- Nutzerstatus
- Einheitendetails
- Verfügbarkeit
- Fahrzeugdaten inkl der individuellen Fahrzeugeigenschaften
- Berechtigungen
- Nachrichtenkanäle

### Datenübergabe
Mit **DiveraControl** können Daten an Divera übergeben werden. Dazu wurden in HomeAssistant entsprechende Services implementiert. Umgesetzt sind folgende Endpunkte:
- Nutzerstatus (erweitert und einfach)
- Alarmerstellung
- Alarmänderung
- Alarmabschluss
- Fahrzeugdaten inkl der individuellen Fahrzeugeigenschaften
- Einsatzrückmeldung
- Nachrichten (Messenger)

---

## Was kann DiveraControl nicht?
Von Divera werden sehr viele Endpunkte bereit gestellt. Nicht alle davon können über diese Integration angesprochen werden. Nicht enthaltene Funktionen sind:
- Verwaltung mehrerer Nutzer **derselben** Einheit
- Löschen und Archivieren von Alarmen, Mitteilungen, Nachrichten, Terminen
- Anlegen, Ändern, Löschen von Terminen
- Hinzufügen von Anhängen
- Hinzufügen von Besatzung zu Fahrzeugen, weder außerhalb noch innerhalb von Einsätzen
- Funktionen für Leitstellen
- Funktionen der PRO-Version (zB einheitenübergreifende Alarmierung)

## Was sollte DiveraControl können?
- Umgang mit mehreren Nutzern derselben Einheit
- Hinzufügen von Besatzung zu Fahrzeugen

---

## Installation
Die Installation ist aktuell nur manuell möglich. Eine HACS-Integration ist in Arbeit.

Zur manuellen Installation den [letzten Release](https://github.com/moehrem/DiveraControl/releases/latest) herunterladen und in den HomeAssistant-Ordner `config/custom_components/diveracontrol` extrahieren.


## Einrichtung
Die Einrichtung erfolgt durch Eingabe des Nutzernamens und des Passwortes. Nichts davon wird gespeichert, stattdessen wird mit der Initialisierung der Integration der API-Schlüssel des Nutzers abgefragt und in HomeAssistant abgelegt.
Für die Anmeldung können die persönlichen Zugangsdaten genutzt werden. In diesem Fall werden, falls der Nutzer mehreren Einheiten zugewiesen ist, die einzelnen Einheiten als Hubs zur Integration angelegt.

Es bietet sich jedoch an, für eine zentrale Rechteverwaltung einen Systembenutzer der Einheit zu verwenden. Hierfür bietet Divera die Möglichkeit der Anlage unter **Verwaltung** -> **Schnittstellen** -> **System-Benutzer**. Systembenutzer können nicht angemeldet werden, stattdessen wird die Integration nach dem API-Schlüssel des Nutzers fragen.

Eine weitere Alternative besteht darin, den zentralen Schnittstellenbenutzer der Einheit zu verwenden. Der API-Schlüssel ist unter **Verwaltung** -> **Schnittstellen** zu finden. Allerdings lassen sich die Berechtigungen des Schnittstellennutzers nicht anpassen.

Im Falle einer gescheiterten Anmeldung mit Nutzername und Passwort fragt die Integration direkt nach dem API-Schlüssel.

In jedem Fall können außerdem zwei Intervalle eingegeben werden: Ein Interval außerhalb von Einsätzen und ein Interval bei laufenden Einsätzen. Die Integration wertet die Situation aus (Alarm offen oder nicht) und aktualisiert die Daten im entsprechenden Interval.


## Benutzung
Es gibt zwei Grundfunktionen: Das Abfrgen von und das Übergeben von Daten an Divera.

### Abfragen
Die Abfragen werden entsprechend dem eingestellten Intervall wiederholt, die Sensordaten automatisch aktualisiert. Zu den Sensoren gehören:
- Einheitendetails
    - Name, Kurzname, Adresse, Koordinaten etc.
- Fahrzeuge
    - Status, Koordinaten, Besatzung, Position etc.
    - individuelle Fahrzeugeigenschaften (wenn in Divera eingestellt)
- Alarme
    - Stichwort, Text, Zeit, Rückmeldungen, Bericht etc.
- Status
    - wird nur für "echte" Benutzer (also keine Monitor-, System-, Fahrzeugnutzer) bereitgestellt
    - persönlicher Nutzerstatus
    - mögliche Status-IDs
- Offene Alarme
    - Anzahl offener (nicht geschlossener) Alarme
- Tracker
    - für Alarme, wenn Koordinaten übergeben wurden
    - für Fahrzeuge

### Übergabe
Für die Übergabe von Daten werden Services bereitgestellt. Damit werden die entsprechenden Endpunkte in Divera angesprochen. Jeder Service kann in den HomeAssistant-Entwicklerwerkzeugen getestet werden. Dort findet sich auch eine Doku zu den notwendigen Daten.
- Setzen des Nutzerstatus, einfach
    - Status je Einheit, jedoch ohne Details
- Setzen des Nutzerstatus, erweitert
    - Status **nur** für Haupteinheit, jedoch mit vielen Details
- Setzen von Fahrzeugdaten
- Erstellung Alarm
- Änderung Alarm
- Schließen Alarm
- Senden von Nachrichten

### Sensoren
Es werden verschiedene Sensoren bereitgestellt, auch solche, die Daten von Divera bereits interpretieren. Jeder Sensor enthält die entsprechenden Daten als Attribute. Dazu gehören:
- Alarme
- Fahrzeuge
- Einheitendetails
- Anzahl offener Alarme
- persönlicher Status
- Tracker für Einsätze
- Tracker für Fahrzeuge

### Berechtigung
tbd

### Änderung der Konfiguration
Bestehende Hubs können über die Integrationsverwaltung im HomeAssistant angepasst werden. Änderbar sind der API-Schlüssel, das Abfrageinterval für Daten und das Abfrageinterval im Alarmfall.