# Komponentendiagramm

Auf Basis der Umsetzungsbeschreibungen im Pflichtenheft werden benötigte Komponenten und deren Beziehungen in einem umfassenden Entwurfsmodell dargestellt.

![Happin Component Diagram.jpg](uploads/dc46bab5fe506ac8440cee1cf1bb77c8/Happin_Component_Diagram.jpg){width=834 height=600}

---

## Legende

<table>
<tr>
<th>Farben</th>
<th>Softwarekategorien</th>
</tr>
<tr>
<td>

![image.png](uploads/18bccf51e68c9dcf83b89255e0ff0c79/image.png){width="116" height="426"}
</td>
<td>

A-Software

* befasst sich lediglich mit der Anwendung
* ist frei von Technik

0-Software

* umfasst generische Softwarebibliotheken mit grundlegenden Datenstrukturen und Algorithmen

R-Software

* tranformiert von einer Repräsentation in eine andere

T-Software

* arbeitet mit mindestens einer technisches Schnittstelle

AT-Software

* Vermischung von A- und T-Software → **Sollte vermieden werden!**
</td>
</tr>
</table>

---

## Beschreibung

Im Folgenden soll eine textuelle Erklärung des Komponentendiagramms gegeben werden.

### Frontend

Happin soll in drei grundsätzlichen GUI-Frontends zur Verfügung stehen (Web, iOS und Android). Dies wird durch das gewählte Frontend-Framework _React Native_ ermöglicht.

Diese drei Frontends bieten jeweils diese beiden Schnittstellen an, die von der Präsentation verwendet werden:

* DefinePresentation
    * notwendige Ansichten definieren
* DisplayData
    * Dialogobjekte mit Daten füllen (und ggf. aktualisieren)

Die Präsentation bietet wiederum gegenüber den GUI-Frontends die Schnittstelle _PresentationEvents_ an, über die sie über Präsentationereignisse informiert wird.

Die Präsentation selbst enthält nach **Model-View-ViewModel** Designpattern alle ViewModels, die sich aus dem Pflichtenheft und den Workflows ableiten lassen (z. B. Login-Screen ([M1](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m1--nutzer-authentifizierung:~:text=Prio%203%20\(Kann\)-,%F0%9F%94%B4,M1%20%E2%80%93%20Nutzer%2DAuthentifizierung,-Die%20Plattform%20Happin)), öffentliche Eventliste ([M11](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m1--nutzer-authentifizierung:~:text=M4\)%20erreichbar%20sein.-,%F0%9F%94%B4,M11%20%E2%80%93%20%C3%96ffentliche%20Eventliste,-Alle%20%C3%B6ffentlichen%20Events)), Host Dashboard ([M7](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m1--nutzer-authentifizierung:~:text=den%20G%C3%A4sten%20ausgef%C3%BCllt.-,%F0%9F%94%B4,M7%20%E2%80%93%20Host%2D%C3%9Cbersicht,-Hosts%20ben%C3%B6tigen%20eine)), Ticketkauf ([S2](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m1--nutzer-authentifizierung:~:text=angegebenen%20Adresse%20berechnet.-,%F0%9F%9F%A1,S2%20%E2%80%93%20Zahlungen,-Die%20App%20soll)), etc.).

Sie bietet gegenüber dem Dialogkern die Schnittstelle _Sync_ an, um Dialogdaten aktuell zu halten.

Der Dialogkern, der dafür zuständig ist, was dargestellt wird und wie auf Benutzeraktionen reagiert wird, bietet der Präsentation die Schnittstellen _DialogEvents_ (informieren über Dialogaktionen) und _CurrentData_ (Abfrage der aktuellen Dialogdaten) an.

Der DialogManager erzeugt und konfiguriert die Komponenten bei der Erzeugung eines Dialogs. Er kommuniziert mit der Sitzungssteuerung.

Die Sitzungssteuerung verwaltet alle zur Sitzung gehörenden Dialogkomponenten. Sie interagiert wiederum mit der Sitzungsverwaltung.

Die Sitzungsverwaltung kennt alle angemeldeten Benutzer (also alle Sitzungen).

Sowohl die Sitzungsverwaltung als auch der Dialogkern nutzen entsprechende Schnittstellen des BackendAdapter, der für die Kommunikation mit dem Backend der Anwendung zuständig ist (_AuthBackend_ zur Authentifizierung, _AppBackend_ für Anwendungsdaten).

Der BackendAdapter nutzt einige API-Schnittstellen, die aus der festgelegten Umsetzung im Pflichtenheft abgeleitet wurden. Sie vollenden bzw. ergänzen die ViewModels der Präsentation, indem sie die Backend-Daten für die Frontend-Dialoge bereitstellen. Für jedes ViewModel gibt es eine passende API (z. B. Authentifizierung ([M1](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m1--nutzer-authentifizierung:~:text=Prio%203%20\(Kann\)-,%F0%9F%94%B4,M1%20%E2%80%93%20Nutzer%2DAuthentifizierung,-Die%20Plattform%20Happin)), RSVP ([M5](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m1--nutzer-authentifizierung:~:text=der%20App%20\(M11\).-,%F0%9F%94%B4,M5%20%E2%80%93%20Teilnahme%20und%20R%C3%BCckmeldung%20\(RSVP\),-Eingeladene%20G%C3%A4ste%20m%C3%BCssen)), öffentliche Liste ([M11](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m1--nutzer-authentifizierung:~:text=M4\)%20erreichbar%20sein.-,%F0%9F%94%B4,M11%20%E2%80%93%20%C3%96ffentliche%20Eventliste,-Alle%20%C3%B6ffentlichen%20Events)), etc.).

### Backend

Alle API-Schnittstellen werden vom API-Adapter im Backend bereitgestellt.

Speziell für die AuthAPI nutzt er wiederum die Schnittstellen _Register_, _Login_, _Logout_ und _Delete_ der Authentication-Komponente, um Benutzerkonten zu verwalten.

Registriert sich ein Nutzer, muss seine Handynummer bestätigt werden ([M1](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m1--nutzer-authentifizierung:~:text=Prio%203%20\(Kann\)-,%F0%9F%94%B4,M1%20%E2%80%93%20Nutzer%2DAuthentifizierung,-Die%20Plattform%20Happin)). Dafür nutzt die Authentication-Komponente die Schnittstelle _SendMessage_, die vom MessagingAdapter zur Verfügung gestellt wird. Dieser kommuniziert mit einem externen Service, Resend, um die Nachricht per E-Mail zu senden. Da Resend potenziell AT-Software sein könnte, wird der MessagingAdapter benötigt.

Des Weiteren verwendet die Authentication-Komponente die Auth-Schnittstelle des DatabaseAdapters. Dieser kann wiederum Nutzer mit der Datenbank authentifizieren (_DBAuth_).

Für alle anderen APIs nutzt der API-Adapter entsprechende Schnittstellen des Anwendungskerns.

Der Anwendungskern besteht aus Komponenten, die für die gleichnamigen Schnittstellen für den APIAdapter zuständig sind. Einige dieser Komponenten nutzen die _Read_- bzw. _Write_-Schnittstelle des DatabaseAdapters. Um diese umzusetzen, nutzt dieser wiederum die _DBData_-Schnittstelle der Datenbank.

Darüber hinaus werden der PaymentAdapter ([S2](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m1--nutzer-authentifizierung:~:text=angegebenen%20Adresse%20berechnet.-,%F0%9F%9F%A1,S2%20%E2%80%93%20Zahlungen,-Die%20App%20soll)), MapsAdapter ([S1](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m1--nutzer-authentifizierung:~:text=ist%20nicht%20vorgesehen-,%F0%9F%9F%A1,S1%20%E2%80%93%20Kartenintegration,-Um%20die%20Location)) sowie WeatherAdapter ([S3](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m1--nutzer-authentifizierung:~:text=nicht%20umgesetzt%20werden.-,%F0%9F%9F%A1,S3%20%E2%80%93%20Wetteranzeige,-F%C3%BCr%20jedes%20Event)) verwendet, die allesamt für die Kommunikation mit einem externen Service (Stripe, MapTiler und WeatherAPI) zuständig sind (potenziell AT-Software).

Zur Generierung von CSV- bzw. PDF-Versionen ([S8](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m1--nutzer-authentifizierung:~:text=definiert%20werden%20k%C3%B6nnen.-,%F0%9F%9F%A1,S8%20%E2%80%93%20RSVP%2DExport,-Hosts%20sollen%20die)) eines Tickets wird von der Ticketing-Komponente (A-Software) ein TicketGenerationAdapter (T-Software) verwendet, der generische Python-Softwarebibliotheken einsetzt.

---

## SAAM-Analyse

Nach dem ersten Entwurf des Architekturmodells wurde eine Variabilitätsanalyse nach SAAM durchgeführt. Anhand der Ergebnisse wurde die Architektur erweitert und angepasst, um sie für potenzielle Änderungen in der Zukunft vorzubereiten.

### Änderungsszenarien

Die Szenarien werden in zwei Kategorien unterteilt: **Fachliche Szenarien** betrachten Änderungen aus Anwendersicht (neue Funktionen, Plattformen oder Formate), **Technische Szenarien** betrachten Änderungen an der technischen Infrastruktur und den eingesetzten Technologien.

#### Fachliche Szenarien

* **Direkte Szenarien**
    * Ein neues GUI-Frontend soll hinzugefügt werden (z. B. iPadOS-App).
        * Die GUI-Engine ist vollständig von den tatsächlich existierenden Frontends entkoppelt. In Kombination mit der einfachen Möglichkeit von React Native, Anwendungen für weitere Endgeräte zu builden, erfordert das Anbinden eines neuen Frontends keine weiteren Änderungen an der Architektur.
    * Es soll ein neues Ticketformat eingebunden werden (z. B. PKPASS).
        * Durch den TicketGenerationAdapter, welcher generische Python-Softwarebibliotheken verwendet, um (aktuell) „Generate CSV” und „Generate PDF” anzubieten, ist eine Architektur-Änderung für weitere Dateiformate lediglich in diesem Adapter nötig. Im TicketingAdapter muss lediglich beim Aufruf der Schnittstelle die Option realisiert werden, das neue Ticketformat anzufordern.
    * Eine weitere Zahlungsmethode soll angeboten werden (z. B. PayPal oder Apple Pay zusätzlich zu Stripe).
        * Da die Zahlungsabwicklung vollständig hinter dem PaymentAdapter gekapselt ist, genügt es, dessen Implementierung um die neue Zahlungsmethode zu erweitern. Die Schnittstelle gegenüber dem Anwendungskern bleibt unverändert.
    * Die App soll ein neues visuelles Design erhalten.
        * Durch die MVVM-Trennung ist die visuelle Darstellung vollständig in den GUI-Frontends und der Präsentation angesiedelt. Dialogkern, Sitzungsverwaltung, BackendAdapter und das gesamte Backend bleiben unberührt. Das Redesign erfordert ausschließlich Anpassungen auf der Ansichtsebene.
* **Indirekte Szenarien**
    * Ein neuer externe Dienst soll eingebunden werden (bspw. Recommendation).
        * Es muss ein neuer Adapter implementiert werden, der die Entkopplung herstellt. Falls die neue API mit einer neuen Funktion einhergeht, müssen ggf. eine Komponente im Anwendungskern, eine neue Schnittstelle im APIAdapter sowie ein neues ViewModel im Frontend umgesetzt werden. Da diese Änderungen so gravierend durch die Architektur ziehen, ist eine Entkopplung nicht möglich.
    * Eine neue Authentifizierungsmethode soll unterstützt werden (z. B. OAuth 2.0 / Social Login via Google oder Apple).
        * Die Authentication-Komponente ist aktuell auf das eigene Register-/Login-Verfahren ausgelegt. Die Integration eines OAuth-Providers erfordert einen neuen Adapter für den externen Identity-Provider sowie Anpassungen in der Authentication-Komponente selbst (neuer Loginpfad, Token-Handling). Auf Frontend-Seite müssen entsprechende ViewModels und Dialog-Flows ergänzt werden.

#### Technische Szenarien

* **Direkte Szenarien**
    * Die Schnittstelle einer externen API (AT-Software-Komponente, bspw. Resend oder MapTiler) ändert sich, gibt fehlerhafte Daten zurück oder fällt aus.
        * In der Architektur sind bereits Adapter-Komponenten vorhanden (T-Software), die für genau solche Fälle die nötige Entkopplung von den externen Schnittstellen herstellen. So können im Adapter ggf. Ausnahmen behandelt werden und Implementierungen geändert werden. Aus Sicht der Komponenten, die die Adapter verwenden, bleiben die Schnittstellen unverändert.
    * Eine externe API soll gewechselt werden (bspw. aus Kostengründen oder weil sie eingestellt wird).
        * Ähnlich wie beim vorigen Punkt ist eine Änderung der konkreten Implementierung aufgrund der Entkopplung ausschließlich im Adapter nötig, im Rest des Backends ändert sich nichts.
    * Die Datenbank soll ausgetauscht werden.
        * Die beiden Komponenten DBAuth und Persistenz müssen an die neue Datenbank angepasst werden, jedoch ist der Rest der Anwendung (Authentication und Komponenten im Anwendungskern) unbetroffen.
    * Das Datenbankschema soll angepasst werden (z. B. neue Indexe oder Schema-Normalisierung).
        * Der DatabaseAdapter kapselt sämtliche Datenbankzugriffe. Schema-Anpassungen betreffen ausschließlich die Persistenz- und DBAuth-Teile des DatabaseAdapters sowie die Datenbank selbst; der Anwendungskern und die Authentication-Komponente bleiben unberührt, da sie nur über die stabilen Adapter-Schnittstellen auf die Datenbank zugreifen.
    * Die Python-Bibliotheken im TicketGenerationAdapter sollen aktualisiert oder durch Alternativen ersetzt werden (z. B. ein anderes PDF-Erzeugungspaket).
        * Da der TicketGenerationAdapter die einzige Komponente ist, die diese Bibliotheken einsetzt, ist die Änderung vollständig auf ihn beschränkt. Die Ticketing-Komponente (A-Software) kennt ausschließlich die Schnittstellen „Generate CSV" und „Generate PDF" und bleibt damit unberührt.
* **Indirekte Szenarien**
    * Das Frontend-Framework soll gewechselt werden (z. B. von React Native auf eine native Implementierung je Plattform).
        * React Native ist die Basis aller drei GUI-Frontends. Ein Wechsel würde bedeuten, dass sämtliche Frontends neu implementiert werden müssen. Zwar ist die GUI-Engine von der Präsentation entkoppelt, sodass Dialogkern und Backend unangetastet bleiben. Der Aufwand im Frontend-Bereich ist jedoch erheblich und betrifft alle ViewModel-Bindungen.
    * Offline-Fähigkeit soll im Frontend ergänzt werden (z. B. lokales Caching von Eventdaten bei fehlender Internetverbindung).
        * Der BackendAdapter kommuniziert aktuell ausschließlich synchron mit dem Backend; ein Offline-Modus erfordert eine lokale Datenhaltung und eine Synchronisationslogik. Dies würde Änderungen am BackendAdapter sowie am Dialogkern (Umgang mit veralteten oder nicht verfügbaren Daten) nach sich ziehen.

Es verbleiben mehrere indirekte Szenarien, d. h. Änderungen, die Umbauten an der Architektur erfordern. Jedoch sind alle identifizierten indirekten Szenarien nicht im aktuellen Projektumfang enthalten (neuer Dienst, neue Authentifizierungsmethode, neues Frontend, oder Offline-Fähigkeit). Demnach sind bei der Entwicklung sowie Instandhaltung nicht zu erwarten. Treten sie dennoch ein, müssen sie nicht ohne konkrete Anpassung des Projektumfangs behandelt werden.

Nach Durchführung der SAAM-Analyse hat sich die entworfene Softwarearchitektur bewährt und bietet eine robuste Grundlage für die Implementationsphase.

## Traceability zu den Anforderungen

Dieser Abschnitt ordnet jeder Komponente die Anforderungen aus dem [Pflichtenheft](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft) zu, die sie umsetzt. Dadurch ist vollständig rückverfolgbar, welche Komponente welche Anforderung realisiert.

Die Anforderungs-IDs verlinken jeweils auf den entsprechenden Abschnitt im Pflichtenheft.

### Frontend

| Komponente | Umgesetzte Anforderungen |
|---|---|
| **LoginViewModel** | [M1](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m1--nutzer-authentifizierung) (Nutzer-Authentifizierung: Eingabe Telefonnummer/E-Mail, OTP-Eingabe, Registrierungs- und Login-Workflow) |
| **EventListViewModel** | [M11](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m11--öffentliche-eventliste) (Öffentliche Eventliste: sortierte Listenansicht, Titelbild/Titel/Ort/Datum), [S6](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s6--kartensuche) (Kartensuche: Kartenansicht mit Pins, Filterfunktion), [S7](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s7--event-kategorien) (Kategoriefilter in der Liste) |
| **EventDetailViewModel** | [M4](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m4--einladungslinks) (Eventseite über Einladungslink), [M5](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m5--teilnahme-und-rückmeldung-rsvp) (Teilnahme/Absage/Unsicher anzeigen und auslösen), [M10](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m10--sichtbarkeit-von-events) (Sichtbarkeitsanzeige privat/öffentlich), [M12](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m12--kalenderintegration) (ICS-Download-Button), [S1](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s1--kartenintegration) (Kartenanzeige der Location), [S3](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s3--wetteranzeige) (Wetteranzeige), [S5](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s5--datenschutz-und-privatsphäre) (Adresse erst nach Zusage sichtbar), [S9](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s9--fotoalbum) (Fotoalbum-Anzeige und Upload), [S11](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s11--event-meldungen) (Meldefunktion) |
| **RSVPViewModel** | [M5](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m5--teilnahme-und-rückmeldung-rsvp) (RSVP-Formular: Zusage/Absage/Unsicher, nachträgliche Änderung), [M6](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m6--individuelle-rsvp-formulare) (Individuelle Felder dynamisch anzeigen), [S4](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s4--erweitertes-rsvp-formular) (Erweiterte Feldtypen: Ja/Nein, Abstimmung, Mehrfachwahl), [S10](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s10--warteliste) (Wartelisten-Button und Platzanzeige), [S12](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s12--plus-eins-begleiter) (Plus-Eins-Felder im Formular), [K1](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#green_circle-k1--terminfinder) (Terminauswahl als RSVP-Feld) |
| **TicketPurchaseViewModel** | [M8](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m8--ticketversand) (Ticket-Anzeige in der App mit QR-Code, Download), [S2](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s2--zahlungen) (Ticketkauf-Flow: Preisanzeige, Weiterleitung Stripe, Bestätigung) |
| **NotificationViewModel** | [M7](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m7--host-übersicht) (Benachrichtigung bei Entfernung aus Gästeliste), [S10](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s10--warteliste) (Nachrücken-Benachrichtigung), [K4](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#green_circle-k4--erinnerungen) (Erinnerungsbenachrichtigungen: Einstellungen, Standardwert 1 h) |
| **CreateEventViewModel** | [M2](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m2--erstellung-und-verwaltung-von-events) (Event erstellen: Pflichtfelder, Formular), [M3](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m3--eventdetails-und-bearbeitung) (Eventdetails bearbeiten: vorausgefülltes Formular, Validierung), [M6](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m6--individuelle-rsvp-formulare) (RSVP-Felder definieren), [M10](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m10--sichtbarkeit-von-events) (Öffentlich/Privat-Auswahl), [S2](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s2--zahlungen) (Bepreisung aktivieren), [S4](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s4--erweitertes-rsvp-formular) (Erweiterte RSVP-Felder anlegen/löschen), [S7](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s7--event-kategorien) (Kategorien auswählen), [S10](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s10--warteliste) (Warteliste aktivieren), [S12](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s12--plus-eins-begleiter) (Plus-Eins aktivieren), [K1](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#green_circle-k1--terminfinder) (Terminvorschläge eintragen), [K2](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#green_circle-k2--event-design) (Design-Ansicht: Farben, Schriftarten, Hintergrund, Vorschau), [K3](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#green_circle-k3--bild--und-gif-explorer) (Mediathek-Auswahl für Titelbild), [K5](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#green_circle-k5--co-host-funktion) (Co-Hosts hinzufügen) |
| **HostDashboardViewModel** | [M3](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m3--eventdetails-und-bearbeitung) (Einstiegspunkt „Event bearbeiten"), [M7](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m7--host-übersicht) (Gästeübersicht: Zusagen/Absagen/Unsicher, Gäste entfernen), [S2](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s2--zahlungen) (Einnahmen-Dashboard, Auszahlung anfordern), [S8](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s8--rsvp-export) (Export-Button CSV/PDF), [S11](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s11--event-meldungen) (Meldungs-Einsicht für Moderationsteam), [K5](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#green_circle-k5--co-host-funktion) (Co-Host-Verwaltung) |
| **ScanTicketViewModel** | [M9](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m9--ticket-scanning) (QR-Scanner öffnen, Scan-Ergebnis groß/deutlich anzeigen grün/rot, Mehrfachnutzungskontrolle) |
| **Sitzungssteuerung** | [M1](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m1--nutzer-authentifizierung) (Dialoge der Nutzersitzung nach Login verwalten), [M7](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m7--host-übersicht)/[M9](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m9--ticket-scanning) (Rollenkontrolle: Host-Zugriff auf Dashboard und Scanner), [K5](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#green_circle-k5--co-host-funktion) (Co-Host-Sitzung) |
| **Sitzungsverwaltung** | [M1](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m1--nutzer-authentifizierung) (Kenntnis aller angemeldeten Nutzer, ein Account pro Telefonnummer/E-Mail) |

### Backend

| Komponente | Umgesetzte Anforderungen |
|---|---|
| **Authentication** | [M1](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m1--nutzer-authentifizierung) (Passwortlose Authentifizierung: Register, Login, Logout, Delete, OTP-Generierung und -Validierung, Account-Erstellung) |
| **EventInfo** | [M4](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m4--einladungslinks) (Eindeutige, nicht erratbare Einladungslinks), [M5](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m5--teilnahme-und-rückmeldung-rsvp) (Eventdaten für Gastansicht liefern), [M10](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m10--sichtbarkeit-von-events) (Sichtbarkeitsprüfung: privat nur per Link erreichbar), [M12](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m12--kalenderintegration) (ICS-Datei generieren), [S1](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s1--kartenintegration) (Koordinaten aus Adresse berechnen via MapsAdapter), [S3](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s3--wetteranzeige) (Wetterdaten abrufen via WeatherAdapter), [S5](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s5--datenschutz-und-privatsphäre) (Adresse erst nach Zusage freigeben), [S7](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s7--event-kategorien) (Kategorie in Eventdaten liefern) |
| **EventAdmin** | [M2](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m2--erstellung-und-verwaltung-von-events) (Event erstellen: alle Pflichtfelder persistieren), [M3](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m3--eventdetails-und-bearbeitung) (Eventdetails bearbeiten und validieren), [M6](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m6--individuelle-rsvp-formulare) (RSVP-Formularschema speichern), [M10](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m10--sichtbarkeit-von-events) (Sichtbarkeit setzen), [S2](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s2--zahlungen) (Ticketpreis konfigurieren), [S4](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s4--erweitertes-rsvp-formular) (Erweiterte RSVP-Feldtypen speichern), [S7](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s7--event-kategorien) (Kategorie zuweisen), [S9](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s9--fotoalbum) (Fotoalbum verwalten: Upload, Speicherung, Größenbegrenzung), [S10](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s10--warteliste) (Warteliste konfigurieren), [S12](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s12--plus-eins-begleiter) (Plus-Eins-Einstellung), [K1](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#green_circle-k1--terminfinder) (Terminvorschläge speichern), [K2](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#green_circle-k2--event-design) (Design-Einstellungen persistieren), [K3](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#green_circle-k3--bild--und-gif-explorer) (Medien-Referenz speichern), [K5](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#green_circle-k5--co-host-funktion) (Co-Hosts persistieren) |
| **RSVP** | [M5](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m5--teilnahme-und-rückmeldung-rsvp) (RSVP speichern/ändern, freie Plätze anpassen, Race-Condition-Behandlung, eine Teilnahme pro Nutzer), [M6](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m6--individuelle-rsvp-formulare) (Dynamische Felder validieren und speichern), [S4](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s4--erweitertes-rsvp-formular) (Erweiterte Feldtypen verarbeiten), [S10](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s10--warteliste) (Warteliste FIFO-Logik, automatisches Nachrücken), [S12](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s12--plus-eins-begleiter) (Plus-Eins-Anmeldungen verarbeiten), [K1](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#green_circle-k1--terminfinder) (Terminabstimmung auswerten, meistgewähltes Datum setzen) |
| **HostDashboard** | [M7](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m7--host-übersicht) (Teilnehmerübersicht: Zusagen/Absagen/Unsicher, RSVP-Antworten darstellen, Gäste entfernen), [S2](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s2--zahlungen) (Einnahmen berechnen, Auszahlung über PaymentAdapter auslösen), [S8](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s8--rsvp-export) (CSV/PDF-Export über TicketGenerationAdapter), [S11](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s11--event-meldungen) (Meldungen entgegennehmen und bereitstellen), [K5](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#green_circle-k5--co-host-funktion) (Co-Host-Rechte verwalten) |
| **Notification** | [M3](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m3--eventdetails-und-bearbeitung) (Teilnehmer über Eventänderungen benachrichtigen), [M7](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m7--host-übersicht) (Benachrichtigung bei Entfernung aus Gästeliste), [S10](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s10--warteliste) (Nachrücken-Benachrichtigung via MessagingAdapter), [S11](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s11--event-meldungen) (Meldungen weiterleiten), [K4](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#green_circle-k4--erinnerungen) (Erinnerungen versenden via MessagingAdapter), [K5](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#green_circle-k5--co-host-funktion) (Co-Host-Einladung versenden) |
| **PublicList** | [M11](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m11--öffentliche-eventliste) (Öffentliche Events nach Datum sortiert liefern, robots.txt/X-Robots-Tag setzen), [S6](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s6--kartensuche) (Geo-Filterung und Kartensuche), [S7](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s7--event-kategorien) (Kategoriefilterung) |
| **Ticketing** | [M8](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m8--ticketversand) (Digitale Tickets mit eindeutigem QR-Code generieren, Mehrfachnutzungseinstellung), [M9](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m9--ticket-scanning) (QR-Code validieren, Mehrfachnutzung prüfen und sperren, Rollenkontrolle), [S2](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s2--zahlungen) (Ticket nach Zahlung ausstellen) |
| **MessagingAdapter** | [M1](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m1--nutzer-authentifizierung) (OTP-Versand: einheitliche Versandschnittstelle für E-Mail/SMS), [M3](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m3--eventdetails-und-bearbeitung)/[M7](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m7--host-übersicht)/[S10](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s10--warteliste)/[K4](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#green_circle-k4--erinnerungen) (Benachrichtigungsversand über Resend: Änderungen, Entfernung, Nachrücken, Erinnerungen) |
| **DatabaseAdapter** | [M1](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m1--nutzer-authentifizierung) (DBAuth: Nutzer authentifizieren), [M2](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m2--erstellung-und-verwaltung-von-events)–[M12](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m12--kalenderintegration), [S1](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s1--kartenintegration)–[S12](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s12--plus-eins-begleiter), [K1](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#green_circle-k1--terminfinder)–[K5](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#green_circle-k5--co-host-funktion) (DBData Read/Write für alle Anwendungskern-Komponenten) |
| **PaymentAdapter** | [S2](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s2--zahlungen) (Stripe-Anbindung: Pay Zahlung einziehen, Withdraw Auszahlung an Host) |
| **MapsAdapter** | [S1](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s1--kartenintegration) (Koordinaten aus Adresse via MapTiler), [S6](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s6--kartensuche) (Geodaten für Kartensuche) |
| **WeatherAdapter** | [S3](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s3--wetteranzeige) (Wetterdaten abrufen via WeatherAPI, mind. alle 6 h aktualisieren) |
| **TicketGenerationAdapter** | [M8](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m8--ticketversand) (Ticket als PDF generieren via PDFGenerator), [S8](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s8--rsvp-export) (Gästeliste als CSV via CSVGenerator oder PDF via PDFGenerator exportieren) |
| **CSVGenerator** | [S8](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s8--rsvp-export) (CSV-Format für Gästelisten-Export) |
| **PDFGenerator** | [M8](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#red_circle-m8--ticketversand) (PDF-Ticket generieren), [S8](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft#yellow_circle-s8--rsvp-export) (PDF-Format für Gästelisten-Export) |

---

## Zusammenfassung

Dieses Komponentendiagramm dient als zentrale Grundlage für den weiteren Architekturentwurf des Systems. Es schafft ein gemeinsames Verständnis über Struktur, Verantwortlichkeiten und Abhängigkeiten der einzelnen Komponenten. Auf dieser Basis können Detailentscheidungen zur technischen Umsetzung konsistent getroffen werden.

Im weiteren Verlauf bildet das Diagramm zudem einen wichtigen Referenzpunkt für Implementierung, Erweiterung und Wartung des Systems.
