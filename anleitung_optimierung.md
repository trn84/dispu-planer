# Anleitung zur Optimierung des Prüfungsplans

Dieses Dokument beschreibt die Funktionsweise und Konfiguration der Optimierungs-Engine, die das Herzstück dieses Planungstools bildet. Das Verständnis dieser Konzepte ermöglicht es Ihnen, den generierten Prüfungsplan genau an Ihre Prioritäten anzupassen.

## Das Grundprinzip: Die "Kostenfunktion"

Ein Computer-Solver versteht keine menschlichen Konzepte wie "Bequemlichkeit" oder "ein guter Zeitplan". Er versteht nur ein einziges Ziel: **Minimiere eine Zahl.**

Unsere Aufgabe ist es, alle unsere Wünsche in eine einzige mathematische Formel – eine sogenannte **Kostenfunktion** – zu übersetzen. Jede Eigenschaft eines Zeitplans, die wir als "schlecht" empfinden, erhöht den Wert dieser Funktion. Der Solver versucht dann, durch intelligentes Ausprobieren von Milliarden von Möglichkeiten, einen gültigen Zeitplan zu finden, bei dem diese "Gesamtkosten"-Zahl so niedrig wie möglich ist.

Die `weights` (Gewichte) in der `config.yaml`-Datei sind die entscheidenden Stellschrauben in dieser Kostenfunktion. Sie legen fest, wie "teuer" eine unerwünschte Eigenschaft ist.

## Die Optimierungsziele und ihre Gewichte

Unser Modell verfolgt zwei Hauptziele, die jeweils mit einem Gewicht versehen sind.

### 1. Hauptziel: `weight_active_days`

-   **Was es bedeutet:** Dieses Gewicht steuert das wichtigste Ziel: Professoren sollen an so wenigen Tagen wie möglich anwesend sein müssen. Es ist die "Strafe" für jeden zusätzlichen Arbeitstag eines Professors.
-   **Wie es funktioniert:** Das Modell zählt für jeden Professor und jeden Tag, ob er mindestens eine Prüfung hat. Jeder dieser "aktiven Professor-Tage" wird mit dem Wert von `weight_active_days` multipliziert und zu den Gesamtkosten addiert.
    -   `Kosten_Tage = (Anzahl aller aktiven Professor-Tage) * weight_active_days`
-   **Wie man den Wert wählt:** Dieser Wert sollte **der mit Abstand größte** in Ihrer Konfiguration sein, da ein zusätzlicher Anreisetag für einen Professor die größte Unannehmlichkeit darstellt.
    -   **Empfehlung:** Wählen Sie eine hohe Zahl, die eine greifbare Bedeutung hat. Ein guter Startwert ist die Anzahl der Minuten eines Arbeitstages, z.B. **`480`** (für 8 Stunden). Das bedeutet: "Ein zusätzlicher Arbeitstag ist so schlimm wie 480 Minuten Leerlaufzeit."
    -   **Wertebereich:** Starten Sie mit Werten zwischen **400 und 1000**. Ein höherer Wert zwingt den Solver noch stärker, Tage zu bündeln, selbst wenn dadurch größere Lücken an den verbleibenden Tagen entstehen.

### 2. Nebenziel: `weight_prof_pair_locality`

-   **Was es bedeutet:** Dieses Gewicht steuert das "Feintuning". Es sorgt dafür, dass Prüfungen, die vom *selben Professorenpaar* abgenommen werden, möglichst kompakt geplant werden – idealerweise direkt hintereinander und im selben Raum.
-   **Wie es funktioniert:** Dieses Gewicht bestraft zwei Dinge:
    1.  **Zeitliche Streuung:** Es berechnet die Gesamtspanne von der ersten bis zur letzten Prüfung einer "Arbeitsgruppe". Je weiter diese auseinanderliegen, desto höher die Kosten.
    2.  **Raumwechsel:** Für jeden Raumwechsel innerhalb einer Arbeitsgruppe wird eine feste "Strafgebühr" (im Code hartcodiert auf 120 Minuten) zu den Kosten addiert.
    -   `Kosten_Lokalität = (Summe aller Zeitspannen + Summe aller Raumwechsel-Strafen) * weight_prof_pair_locality`
-   **Wie man den Wert wählt:** Dieser Wert sollte **deutlich kleiner** sein als `weight_active_days`. Er drückt eine Präferenz aus, keine harte Anforderung.
    -   **Empfehlung:** Starten Sie mit einem kleinen Wert wie **`1`** oder **`5`**.
    -   **Wertebereich:** Experimentieren Sie mit Werten zwischen **1 und 20**.
        -   Ein Wert von `1` sagt dem Solver: "Eine Minute Leerlaufzeit innerhalb einer Gruppe ist eine Kosten-Einheit."
        -   Ein Wert von `10` sagt: "Jede Minute, die du die Prüfungen einer Gruppe auseinanderziehst, ist 10-mal schlimmer als normaler Leerlauf. Versuche es wirklich zu vermeiden!"

## Die kombinierte Kostenfunktion

Die finale Formel, die der Solver minimiert, sieht vereinfacht so aus:

**`Gesamtkosten = (Kosten_Tage) + (Kosten_Lokalität)`**

Der Solver wird also immer eine Lösung bevorzugen, die einen Professor-Tag einspart (`-480` Kosten), selbst wenn er dafür die Prüfungen einer Arbeitsgruppe um ein paar Stunden auseinanderziehen muss (`+120` Kosten).

## Praktische Anleitung zum Tuning: Ein Workflow

Der beste Weg, die Gewichte einzustellen, ist iterativ:

1.  **Schritt 1: Das Fundament legen (Tage minimieren)**
    -   Setzen Sie `weight_active_days` auf einen hohen Wert (z.B. `480`).
    -   Setzen Sie `weight_prof_pair_locality` auf einen niedrigen Wert (z.B. `1`).
    -   Führen Sie die Optimierung aus. Das Ergebnis ist ein Plan, der primär darauf ausgelegt ist, die Anwesenheitstage aller Professoren zu minimieren.

2.  **Schritt 2: Die Bündelung verbessern (Feintuning)**
    -   Schauen Sie sich das interaktive Gantt-Diagramm an. Sind die farbigen Blöcke (die zu einem Prüferpaar gehören) schon gut gebündelt?
    -   Erhöhen Sie nun `weight_prof_pair_locality` auf `5` oder `10`.
    -   Führen Sie die Optimierung erneut aus.

3.  **Schritt 3: Vergleichen und Entscheiden**
    -   Vergleichen Sie das neue Gantt-Diagramm mit dem vorherigen. Die farbigen Blöcke sollten jetzt noch kompakter und seltener über verschiedene Räume verteilt sein.
    -   **Kontrollfrage:** Musste für diese verbesserte Bündelung ein Professor einen zusätzlichen Tag anreisen? Falls ja, ist der "Preis" für das Feintuning zu hoch. Falls nein, haben Sie eine bessere Lösung gefunden.

Wiederholen Sie diesen Prozess, bis Sie den "Sweet Spot" gefunden haben, der die Prioritäten Ihrer Fakultät am besten widerspiegelt. Die Gewichte sind Ihre direkten Kontrollknöpfe, um dem Solver Ihre Wünsche mitzuteilen.