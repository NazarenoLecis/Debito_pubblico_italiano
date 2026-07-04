# Aggiornamento workflow mensile

Il workflow mensile deve eseguire l'entry point standard:

```bash
python scripts/src/build_all_datasets.py
```

Gli output generati devono essere presi da:

```text
output/data/
```

La logica attesa è:

1. installare le dipendenze da `requirements.txt`;
2. eseguire `python -m pytest`;
3. eseguire `python scripts/src/build_all_datasets.py`;
4. conservare o pubblicare i file CSV e JSON prodotti sotto `output/data`.

Il branch contiene già `scripts/src/build_all_datasets.py`, che produce un file JSON records per ogni CSV tabellare generato dalla pipeline.
