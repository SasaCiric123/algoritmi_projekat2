# ASP Projekat 2 - simulacija drustvene mreze

Konzolna Python aplikacija koja simulira deo drustvene mreze nad usmerenim grafom pracenja. Program ucitava korisnike, follow veze i blokiranja, a zatim omogucava pretragu, rangiranje uticaja, autocomplete, preporuke i obilazak mreze.

## Pokretanje

Podrazumevano se pokrece nad `small` skupom:

```bash
python main.py
```

Za drugi skup podataka proslediti putanju do foldera:

```bash
python main.py data/dataset/dataset/medium
python main.py data/dataset/dataset/full
```

Svaki folder skupa podataka mora da sadrzi:

```text
users.txt
connections.txt
blocked.txt
```

## Format podataka

`users.txt`:

```text
id|username|bio
```

`connections.txt`:

```text
from_id|to_id
```

`from_id` je korisnik koji prati, a `to_id` je korisnik koji je pracen. Graf je usmeren.

`blocked.txt`:

```text
blocker_id|blocked_id
```

Blokiranje se ne brise iz grafa, vec se koristi pri dodavanju novih veza i preporukama.

## Meni

Program nudi sledece opcije:

```text
1. Pretraga korisnika
2. Prikaz najuticajnijih korisnika
3. Dodavanje nove follow veze
4. Prikaz istorije interakcija
5. BFS obilazak mreze
6. Autocomplete username
7. Preporuka korisnika
8. Izlaz
```

## Implementirane funkcionalnosti

- Izgradnja grafa drustvene mreze kroz klase i hash mape.
- Cuvanje izlaznih veza (`following`), ulaznih veza (`followers`) i izlaznog stepena (`out_degree`).
- PageRank sa damping faktorom `0.85`, epsilon `1e-6` i warm start podrskom.
- Prikaz top PageRank korisnika pomocu `heapq.nlargest`.
- Pretraga po username-u i recima iz biografije.
- Obrada teksta biografije i inverted index za brzu bio pretragu.
- Istorija novih follow interakcija tokom jednog pokretanja programa.
- Zabrana dodavanja follow veze ako postoji blokiranje u bilo kom smeru.
- Trie autocomplete za username prefikse, rangiran po PageRank-u.
- BFS obilazak grafa po nivoima.
- Did you mean predlozi za pogresno unet username.
- Hibridne preporuke korisnika:
  - Personalized PageRank iz perspektive zadatog korisnika.
  - Jaccard slicnost biografija.
  - Formula `alpha * PPR + (1 - alpha) * content_similarity`.
  - Filtriranje samog korisnika, vec pracenih i blokiranih korisnika.

Izmene kao sto su dodavanje nove follow veze i istorija interakcija cuvaju se u memoriji tokom trenutnog pokretanja programa. Ne upisuju se nazad u ulazne fajlove.

## Primeri za testiranje

Pretraga po bio reci:

```text
Opcija: 1
Upit: vegan
```

Prikaz top PageRank korisnika:

```text
Opcija: 2
```

Dodavanje nove veze:

```text
Opcija: 3
Korisnik koji prati: 1
Korisnik koji se prati: 2
```

Primer blokirane veze:

```text
Opcija: 3
Korisnik koji prati: 29
Korisnik koji se prati: 644
```

Autocomplete:

```text
Opcija: 6
Prefiks: gui
```

Did you mean:

```text
Opcija: 4
Korisnik: guimnja
```

BFS:

```text
Opcija: 5
Pocetni korisnik: 1
Nivo: 2
```

Preporuke:

```text
Opcija: 7
Korisnik: 1
Alpha: 0.5
```

Alpha odredjuje odnos grafovskog dela i slicnosti biografije:

```text
alpha = 1.0  -> samo Personalized PageRank
alpha = 0.0  -> samo slicnost biografije
alpha = 0.5  -> pola mreza, pola bio slicnost
```

## Struktura koda

```text
main.py              - konzolni meni i interakcija sa korisnikom
social_graph.py      - graf, PageRank, PPR, pretraga, preporuke, BFS
models.py            - dataclass modeli
data_loader.py       - ucitavanje users/connections/blocked fajlova
text_processing.py   - tokenizacija teksta
trie.py              - Trie struktura za autocomplete
string_similarity.py - Levenshtein distance za Did you mean
```

## Performanse

Merenja su izvrsena lokalno na ovom racunaru pomocu prilozenih `small`, `medium` i `full` skupova. Vremena mogu malo da variraju po masini.

| Skup | Korisnici | Follow veze | Ucitavanje |
| --- | ---: | ---: | ---: |
| small | 1,000 | 80,693 | 0.192s |
| medium | 10,000 | 354,503 | 1.288s |
| full | 81,306 | 1,768,135 | 9.444s |

| Operacija | small | medium | full |
| --- | ---: | ---: | ---: |
| PageRank | 0.244s / 23 iteracije | 3.450s / 41 iteracija | 48.656s / 51 iteracija |
| Pretraga `vegan` | 0.0002s | 0.0036s | 0.0219s |
| BFS nivo 3 od korisnika 1 | 0.0080s | 0.0065s | 0.0491s |
| Autocomplete `gui` | 0.0000s | 0.0001s | 0.0003s |
| Did you mean `guimnja` | 0.0335s | 0.3444s | 2.7265s |
| Preporuke za korisnika 1, alpha 0.5 | 0.237s | 3.593s | 53.601s |

Najskuplje operacije su PageRank i hibridne preporuke, jer preporuke racunaju Personalized PageRank za zadatog korisnika. Pretraga, autocomplete i BFS koriste unapred formirane strukture i rade interaktivno.
