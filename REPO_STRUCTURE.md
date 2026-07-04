# Struttura del repository

Questo repository usa una struttura modulare e ripetibile.

```text
repo/
  README.md
  requirements.txt
  sources_manifest.csv
  scripts/
    config.py
    utils.py
    src/
      build_all_datasets.py
  notebooks/
  output/
    data/
    charts/
```

Alcuni nomi restano stabili tra repository: `scripts/config.py`, `scripts/utils.py`, `scripts/src`, `notebooks`, `output/data` e `output/charts`.

Altri nomi cambiano in base al progetto. In questo repository i moduli specifici per Banca d'Italia, MEF, Eurostat, normalizzazione e controlli qualità restano separati perché riflettono fonti e fasi diverse della pipeline.

`scripts/src/build_all_datasets.py` è l'entry point standard. Carica la pipeline esistente e abilita il salvataggio degli output tabellari sia in CSV sia in JSON.

`output/data` contiene dati scaricati, dati convertiti, dataset finali e report qualità.

`output/charts` è riservata a grafici e immagini generati da notebook o script successivi.

`notebooks` è riservata ad analisi esplorative, controlli e produzione di grafici. Numero e tipologia dei notebook possono cambiare in base all'analisi.

Il codice deve restare basato su funzioni, senza classi. Le configurazioni devono stare in `scripts/config.py`. Non usare YAML, `argparse` o file `__init__.py`.

Ogni funzione deve avere una docstring sintetica. Le funzioni che applicano scelte metodologiche devono spiegare il criterio usato, per esempio filtri, classificazioni, aggregazioni, normalizzazioni, trattamento dei valori mancanti e gestione degli output vuoti.

Il README deve restare leggibile anche per un utente non esperto. Deve spiegare scopo del repository, fonti dati, istruzioni di esecuzione, struttura degli output, definizioni operative, metodologia, assunzioni e limiti.
