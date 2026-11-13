# Recherche und Verarbeitung

Dieses Projekt verwendet die öffentliche Wikimedia-Commons-API ohne kostenpflichtige API-Schlüssel.

## Workflow

Auf GitHub unter **Actions → Wikimedia Commons Tifo Research → Run workflow** einen Vereinsnamen und optional die FM27-ID eingeben. Anschließend im Workflow-Ergebnis das Artefakt **tifo-research-candidates** herunterladen. Es enthält Quellenkandidaten mit Fotograf, Lizenz, Datei-URL und Statusfeldern.

**Achtung:** Suchtreffer sind keine bestätigten Choreografien des Vereins. Bild und Lizenz müssen geprüft werden, bevor die Flags `reviewed_club_match` und `reviewed_license` in einer lokalen `output/reviewed.json` gesetzt werden. Erst dann erzeugt `python tools/commons_tifo.py --download-reviewed` lokal PNG-Dateien mit 1600×900 Pixeln.

Ein vollständiger FM27-Katalog kann lokal mit `--catalog clubs_catalog.json --limit 10` verarbeitet werden. Kein Upload der 42.757 Vereins-IDs erforderlich. Keine 42.757 fertigen Bilder vorhanden. Der BepInEx-Renderingfehler wird dadurch nicht gelöst.

Wikimedia stellt Lizenz-/Urhebermetadaten über `imageinfo` und `extmetadata` bereit; die Metadaten können unvollständig sein. Beim Veröffentlichen der bearbeiteten Bilder sind die Bedingungen der jeweiligen Lizenz zu beachten.

GitHub Actions ist in öffentlichen Repositories grundsätzlich innerhalb der geltenden GitHub-Nutzungsbedingungen und Limits verfügbar. Keine kostenpflichtigen APIs eingebaut.
