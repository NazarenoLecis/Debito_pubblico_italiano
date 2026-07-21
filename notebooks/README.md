# Notebook di analisi

I notebook in questa cartella leggono i dati gia' prodotti dalla pipeline sotto `output/data/public/debito-pubblico.json`.

Lo stile dei grafici e' volutamente neutro e da analisi: i grafici riprendono i contenuti principali del sito, non il suo template visuale.

Prima di eseguirli:

```bash
python scripts/build_all_datasets.py
```

Notebook disponibili:

- `01_quadro_generale.ipynb`: stock, debito/PIL e composizione.
- `02_profilo_scadenze.ipynb`: profilo scadenze, quote sul totale e vita media residua stimata.
- `03_costo_e_rendimenti.ipynb`: costo del debito e rendimenti all'emissione.

Ogni figura riporta in basso a sinistra fonte ed elaborazione.
