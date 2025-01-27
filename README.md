# DiveraControl

---

**DiveraControl ist noch in der Entwicklung und kann daher Fehler aufweisen. Ausserdem fehlen noch ein paar geplante Funktionen. Falls Fehler gefunden werden oder Funktionen gewünscht sind, erstellt bitte einen Issue. Vielen Dank!**

---

**DiveraControl** ist eine Integration von Divera 24/7 in den HomeAssistant. Ziel dieser Integration ist es, einen umfangreichen Datenaustausch mit Divera 24/7 zu ermöglichen.

Feuerwehrgebäude, Fahrzeuge und Gerätschaften werden zunehmend smarter. Jedoch gibt es kaum einen (oder zumindest für kleine Feuerwehren kaum einen erschwinglichen) integrativen Anbieter für eine zentrale Verwaltung, Steuerung und Verteilung dieser Daten mit dem Ziel, smarte Geräte zu koordinieren. Hier kommt HomeAssistant ins Spiel. Dieser kann als kostenfreie zentrale Steuerung für zB Beleuchtung, Türen und Tore, Monitore, Sprachausgaben, Fahrzeugpositionen, -besatzungen und -status, Gerätepositionen, Ladestand von Akkus, individuelle Monitore usw. eingesetzt werden. Vorausgesetzt es gibt eine Anbindung zur Alarmierungssoftware - und hier soll diese Integration helfen.

Um die Integration voll ausschöpfen zu können, sind umfangreiche Berechtigungen in der angebundenen Einheit nötig. Zielgruppe der Integration sind Administratoren bzw Schnittstellennutzer einer Einheit. Die Integration funktioniert auch mit eingeschränkten Rechten, bietet dann aber nicht denselben Umfang.
Für den persönlichen Einsatz bietet sich die schon länger existierende Integration [Divera 24/7 Integration for Home Assistant](https://github.com/fwmarcel/home-assistant-divera) an.

---

## Disclaimer

Im BOS-Bereich besitzt das Thema Datenschutz bekanntermaßen eine besondere Bedeutung. Jeder Einsatz von HomeAssistant und dieser Integration in realen Lagen erfolgt auf **eigene Verantwortung**. Die Berücksichtigung der Datenschutzbestimmungen, insbesondere, jedoch nicht beschränkt auf "Weitergabe von Daten an Dritte", "Datenverarbeitung" und "Datensicherheit", liegt vollständig in der Verantwortung des Nutzers.
Diese Integration steht in **keiner Verbindung** zu Divera 24/7 und wird von Divera 24/7 auch **nicht unterstützt**.

---

## Was kann DiveraControl?

- Verwaltung mehrerer **unterschiedlicher** Nutzer/Einheiten
- Anbindung mehrerer Einheiten desselben Nutzers
- Unterstützt parallele Alarme
- Erstellen und Bearbeiten von Alarmen
- Setzen des Nutzerstatus pro Einheit
- Setzen von Fahrzeugdaten, wie zB Status oder Position

### Datenabfrage
Die Abfragen erfolgen in einem regelmäßigen Turnus, der bei der Einrichtung der Integration eingestellten wird. Abgefragt werden:
- Alarmdaten
- Nutzerstatus
- Einheitendetails
- Verfügbarkeit
- Fahrzeugdaten
- Berechtigungen

### Datenübergabe
Mit **DiveraControl** können Daten an Divera übergeben werden. Dazu wurden in HomeAssistant entsprechende Services implementiert. Umgesetzt sind folgende Endpunkte:
- Nutzerstatus (erweitert und einfach)
- Alarmerstellung
- Alarmänderung
- Alarmabschluss
- Fahrzeugdaten (zB. Status, Position)
- Einsatzrückmeldung
- Nachrichten (Messenger)

### Sensoren
Es werden verschiedene Sensoren bereitgestellt, auch solche, die über die reinen Diveradaten hinausgehen. Jeder Sensor enthält die entsprechenden Daten als Attribute. Dazu gehören:
- Alarme
- Fahrzeuge
- Einheitendetails
- Anzahl offener Alarme
- persönlicher Status
- Tracker für Einsätze
- Tracker für Fahrzeuge

---

## Was kann DiveraControl nicht?
Von Divera werden sehr viele Endpunkte bereit gestellt. Nicht alle davon können über diese Integration angesprochen werden. Nicht enthaltene Funktionen sind:

- Verwaltung mehrerer Nutzer **derselben** Einheit
- Löschen und Archivieren von Alarmen, Mitteilungen, Nachrichten, Terminen
- Anlegen, Ändern, Löschen von Terminen
- Hinzufügen von Anhängen in irgendeiner Form
- Hinzufügen von Besatzung zu Fahrzeugen, weder außerhalb noch innerhalb von Einsätzen
- Lesen und Schreiben der Fahrzeugeigenschaften (betrifft die fahrzeugspezifischen Felder, die im Divera-Backend angelegt sind, NICHT den Status oder die Position des Fahrzeugs!)
- Funktionen für Leitstellen
- Funktionen der PRO-Version (zB einheitenübergreifende Alarmierung)

## Was sollte DiveraControl können?
- Umgang mit mehreren Nutzern derselben Einheit
- Hinzufügen von Besatzung zu Fahrzeugen
- Lesen und Schreiben von individuellen Fahrzeugzusatzdaten

---

## Installation
Die Installation ist aktuell nur manuell möglich. Eine HACS-Integration ist zukünftig geplant.

Zur manuellen Installation den [letzten Release](https://github.com/moehrem/DiveraControl/releases/latest) herunterladen und in den HomeAssistant-Ordner `config/custom_components/diveracontrol` extrahieren.


## Einrichtung
Die Einrichtung erfolgt durch Eingabe des Nutzernamens und des Passwortes. Nichts davon wird gespeichert, stattdessen wird mit der Initialisierung der Integration der API-Schlüssel des Nutzers abgefragt und in HomeAssistant abgelegt.
Für die Anmeldung können die persönlichen Zugangsdaten genutzt werden. In diesem Fall werden, falls der Nutzer mehreren Einheiten zugewiesen ist, die einzelnen Einheiten als Hubs zur Integration angelegt.<br>
Es bietet sich jedoch an, für eine zentrale Rechteverwaltung einen Systembenutzer der Einheit zu verwenden. Hierfür bietet Divera die Möglichkeit der Anlage unter **Verwaltung** -> **Schnittstellen** -> **System-Benutzer**. Systembenutzer können nicht angemeldet werden, stattdessen wird die Integration nach dem API-Schlüssel des Nutzers fragen.<br>
Eine weitere Alternative besteht darin, den zentralen Schnittstellenbenutzer der Einheit zu verwenden. Der API-Schlüssel ist unter **Verwaltung** -> **Schnittstellen** zu finden. Allerdings lassen sich die Berechtigungen des Schnittstellennutzers nicht anpassen.


## Benutzung
tbd
- Sensoren
    - Einheitendetails
    - Fahrzeuge
    - Alarme
    - Status
    - Offene Alarme
    - Tracker
- Dienste
    - Setzen des Nutzerstatus, einfach
    - Setzen des Nutzerstatus, erweitert
    - Setzen von Fahrzeugdaten
    - Erstellung Alarm
    - Änderung Alarm
    - Schließen Alarm
    - Senden von Nachrichten
