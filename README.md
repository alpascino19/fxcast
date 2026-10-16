# FXcast

**Estimarea riscului unei mișcări mari a cursului EUR/RON în ziua următoare, pe baza cursurilor BNR și a știrilor economice și politice din presa românească.**

Aplicația spune, în fiecare zi lucrătoare după publicarea cursului BNR, dacă riscul ca euro să se miște cu peste 0,25% a doua zi este **scăzut**, **mediu** sau **ridicat**, împreună cu frecvența istorică a unor astfel de mișcări pentru acel nivel de risc.

> ⚠️ Proiect educațional. Nu reprezintă sfat financiar sau de investiții.

---

## Cuprins

1. [Ideea proiectului](#ideea-proiectului)
2. [Rezultate principale](#rezultate-principale)
3. [Arhitectura](#arhitectura)
4. [Datele](#datele)
5. [Metodologia](#metodologia)
6. [Ce am aflat despre știri și curs](#ce-am-aflat-despre-știri-și-curs)
7. [Limitări](#limitări)
8. [Cum se rulează](#cum-se-rulează)
9. [Structura proiectului](#structura-proiectului)
10. [Pașii următori](#pașii-următori)

---

## Ideea proiectului

Cursul EUR/RON este gestionat de BNR printr-un regim de flotare controlată. Explorarea datelor din 2015 încoace arată un tipar clar: perioade lungi în care cursul este aproape fix, întrerupte de **salturi bruște**. Dintre cele 15 cele mai mari mișcări zilnice din 2015–2026, cel puțin 10 coincid cu evenimente politice identificabile: alegeri, căderi de guvern, moțiuni de cenzură.

| Data cursului | Mișcare EUR/RON | Context |
|---|---|---|
| 19 mai 2025 | −1,41% | Rezultatul turului 2 al alegerilor prezidențiale |
| 2 oct. 2026 | +1,27% | Eșecul învestirii guvernului, scăderea rezervelor BNR, evaluarea S&P |
| 6–7 mai 2025 | +1,21%, +1,22% | Primul tur al alegerilor prezidențiale reluate |
| 4 mai 2026 | +1,13% | Criza guvernamentală, înaintea moțiunii de cenzură |
| 6 mai 2026 | +0,97% | Căderea guvernului prin moțiune de cenzură |
| 16 ian. 2018 | +0,74% | Demisia premierului |
| 29 iun. 2015 | +0,79% | Criza Greciei (eveniment extern) |

**Ipoteza de lucru:** dacă salturile vin din politică, atunci volumul și tipul știrilor ar trebui să ajute la anticiparea lor, acolo unde istoricul cursului singur nu poate.

---

## Rezultate principale

**1. Riscul unei mișcări mari poate fi estimat util.** Evaluat walk-forward pe 2019–2026, pe date nevăzute la antrenare:

| Metrică | Model | Aleator |
|---|---|---|
| AUC | **0,842** | 0,500 |
| Average Precision | **0,263** | 0,032 |

Nivelurile de risc separă clar zilele:

| Nivel de risc | Ponderea zilelor | Zile urmate de o mișcare > 0,25% |
|---|---|---|
| scăzut | 50% | **0,5%** |
| mediu | 40% | **3,1%** |
| ridicat | 10% | **17,4%** |

Între nivelul „scăzut” și „ridicat”, frecvența mișcărilor mari diferă de aproximativ **35 de ori**.

**2. Știrile, în forma actuală, nu îmbunătățesc modelul peste volatilitatea recentă.**

| Model (C = 0,1, test 2019 – iun. 2026) | AUC | AP |
|---|---|---|
| doar features de curs | **0,868** | **0,257** |
| curs + 2 features de știri | 0,859 | 0,249 |
| curs + toate features de știri | 0,848 | 0,250 |

**3. Concluzia economică:** știrile politice mișcă leul **doar atunci când BNR îl lasă să se miște**. Detalii în secțiunea [Ce am aflat](#ce-am-aflat-despre-știri-și-curs).

---

## Arhitectura

```
 BNR (XML anual)        Google News RSS
       │                       │
 fetch_bnr.py       fetch_news_history.py
       │                       │
 bnr_rates.csv      news_history/AAAA.csv ── sources.csv (listă albă)
       │                       │              source_aliases.csv
       └──────────┬────────────┘
           build_features.py
                  │
            features.csv
                  │
            train_model.py ──► models/model.pkl + model_meta.json
                  │
         api.py (FastAPI) ◄── pipeline.py, programat zilnic la 13:30 (APScheduler)
                  │
       frontend (Next.js + Recharts)
```

| Componentă | Tehnologii |
|---|---|
| Colectare și prelucrare date | Python, pandas, requests, feedparser |
| Model | scikit-learn (regresie logistică), joblib |
| API | FastAPI, uvicorn |
| Actualizare automată | APScheduler, subprocess |
| Interfață | Next.js, React, TypeScript, Tailwind CSS, Recharts |

---

## Datele

### Cursuri valutare

Cursurile de referință publicate zilnic de **Banca Națională a României** (fișiere XML anuale de pe `curs.bnr.ro`), pentru EUR și USD, din ianuarie 2015 până azi: aproximativ 2.950 de zile lucrătoare.

### Știri

Colectate din **Google News RSS** cu filtre de dată (`after:` / `before:`), pe 23 de căutări grupate în 6 categorii:

| Categorie | Exemple de căutări |
|---|---|
| politic | alegeri prezidențiale, moțiune de cenzură, vot de învestitură, criză politică |
| fiscal | deficit bugetar, rectificare bugetară, datoria publică |
| banca_centrala | dobânda de politică monetară, rezervele valutare BNR |
| rating | rating România S&P / Fitch / Moody's (comasată cu fiscal în model) |
| ue | fonduri europene, PNRR, procedura de deficit excesiv |
| extern | dobânzile BCE și Fed |

- **79.458** de rânduri colectate (2015–2026), **58.275** de articole unice;
- după lista albă de surse și eliminarea dublurilor: **~35.000** de articole folosite.

**Colectarea istorică** folosește o împărțire adaptivă a ferestrelor de timp: dacă o căutare returnează 40 de articole sau mai multe, fereastra este împărțită recursiv în două până la nivel de zi. Testele au arătat că Google News are limite ascunse, diferite de la o căutare la alta (de exemplu ~47 de rezultate pentru unele căutări), iar o lună întreagă putea pierde aproape jumătate din articole.

### Selecția surselor

Se folosește o **listă albă** (`data/sources.csv`): un articol intră în analiză doar dacă sursa a fost verificată și aprobată. Criteriile sunt obiective și explicabile, nu politice:

| Nivel | Tip | Exemple |
|---|---|---|
| 1 | agenții de presă și presă publică | Agerpres, Mediafax, News.ro, Radio România, TVR |
| 2 | presă economică | Ziarul Financiar, Economica.net, Profit.ro, bursa.ro |
| 3 | presă generalistă cu redacție stabilită | Digi24, Știrile ProTV, HotNews, Adevărul, Libertatea |
| 4 | surse comerciale (pondere redusă) | site-uri ale firmelor de investiții |
| 0 | excluse | rețele sociale, site-uri de partide, presă străină, nișe fără legătură |

Pentru clasificare au fost folosite și evaluări externe: scorurile de încredere din **Reuters Institute Digital News Report 2026** și informațiile despre proprietarii publicațiilor. Publicațiile cu același proprietar (de exemplu Mediafax, Gândul și G4Media) sunt marcate în același grup, pentru că nu reprezintă voci independente.

Numele alternative ale aceleiași surse (`Agerpres` / `agerpres.ro`, `RFI` / `rfi.fr`) sunt unificate prin `data/source_aliases.csv`. Fără această corespondență s-ar fi pierdut aproape 900 de articole doar în 2025.

---

## Metodologia

### Ținta

```
target_big = 1 dacă |schimbarea EUR/RON de mâine| > 0,25%
```

Pragul de 0,25% marchează 158 de zile din 2015–2026 (5,4%) și 3,2% din zilele din 2019 încoace. Modelul estimează **riscul unei mișcări mari, nu direcția ei**: analiza a arătat că volumul de știri anticipă mărimea mișcărilor, nu sensul lor.

### Alinierea în timp

BNR stabilește cursul în jurul orei **13:00**. Fiecare zi de curs primește știrile apărute **între ora 13:00 a zilei lucrătoare anterioare și ora 13:00 a acelei zile**, cu conversie corectă a fusului orar (UTC → Europe/Bucharest, inclusiv ora de vară). Știrile din weekend și din zilele de sărbătoare sunt atribuite automat primei zile BNR următoare (`pandas.merge_asof`).

Fără această aliniere, modelul ar folosi știri publicate **după** stabilirea cursului, adică informație din viitor (*look-ahead bias*).

### Features

**Din curs:** schimbarea de azi, volatilitatea pe 5 și 20 de zile, cea mai mare mișcare din ultimele 5 zile, raportul dintre volatilitatea recentă și cea lunară, plus aceleași măsuri pentru USD/RON.

**Din știri:** doar măsuri **relative**, pentru că numărul absolut de articole este distorsionat de arhivă (vezi [Limitări](#limitări)):
- `*_ratio`: articolele de azi pe categorie față de mediana ultimelor 20 de zile lucrătoare;
- `*_ratio_3d`: suma ultimelor 3 zile față de aceeași mediană;
- `*_share`: ponderea fiecărei categorii în știrile zilei.

### Validarea

**Walk-forward pe ani:** pentru fiecare an din 2019 încoace, modelul este antrenat doar pe anii anteriori și testat pe anul respectiv. Nicio zi de test nu este văzută la antrenare.

Acuratețea nu este folosită: un model care spune mereu „nu urmează nicio mișcare mare” ar avea dreptate în ~97% din zile. Se folosesc **AUC** și **Average Precision**, potrivite pentru evenimente rare.

### Modelul final

Regresie logistică cu standardizare și regularizare (`C = 0,1`), doar pe features de curs. Nivelurile de risc sunt definite prin percentile (sub mediană = scăzut, mediană–percentila 90 = mediu, peste = ridicat), iar frecvențele afișate în aplicație provin din predicțiile walk-forward, nu din datele de antrenare.

---

## Ce am aflat despre știri și curs

### 1. Volatilitatea recentă este cel mai bun predictor

În cele mai agitate 20% dintre zile (după volatilitatea pe 5 zile), o mișcare mare urmează în 14,6% din cazuri. În cele mai liniștite 20%, în 0,2%. Este fenomenul cunoscut drept **gruparea volatilității**: după zile agitate urmează de obicei tot zile agitate.

### 2. Știrile au semnal, dar doar în extreme

În 2019–2026, în zilele cu cel mai mare volum relativ de știri, mișcările mari sunt mult mai frecvente:

| Zile (după `total_ratio_3d`) | Urmate de mișcare mare |
|---|---|
| toate | 3,2% |
| top 10% | 9,7% |
| top 5% | 15,9% |
| top 2% | 22,5% |

Aceste zile sunt însă aproape mereu și zile cu volatilitate mare, așa că modelul nu câștigă informație nouă adăugându-le.

### 3. Modelul prinde „replicile”, nu „cutremurul”

Toate variantele de model pun pe primele locuri zilele **de după** un șoc (de exemplu 6 mai 2025, după primul salt), dar niciuna nu anticipează **primul** șoc. Pe 5 mai 2025, cu 147 de articole politice într-o singură zi, modelul a estimat un risc scăzut, pentru că aprilie fusese foarte calm.

### 4. Lecția din 2024: politica mișcă leul doar când BNR permite

Ponderea învățată pentru știrile politice a ieșit **negativă**. Explicația este anul **2024**: patru rânduri de alegeri și cele mai mari explozii de știri politice din istoric, dar **zero** mișcări mari ale cursului, pentru că BNR a menținut leul practic fix. În 2025 și 2026, crize politice comparabile au produs cele mai mari salturi din istorie.

**Diferența nu a fost în știri, ci în decizia băncii centrale de a apăra sau nu cursul.** Modelul nu are această informație. Un indiciu concret: pe 1 octombrie 2026, creșterea euro a început la aproximativ o oră și jumătate după ce BNR a anunțat scăderea rezervelor valutare cu circa 4,8 miliarde de euro.

---

## Limitări

**Arhiva Google News se „subțiază” cu vechimea.** Numărul de articole găsite scade continuu pentru perioadele vechi:

| An | Articole unice | Pe zi, aproximativ |
|---|---|---|
| 2015 | 1.041 | 3 |
| 2018 | 1.462 | 4 |
| 2021 | 2.667 | 7 |
| 2024 | 6.141 | 17 |
| 2025 | 9.560 | 26 |
| 2026 (9,5 luni) | 23.648 | 82 |

De aceea modelul nu folosește numere absolute de articole, iar comparațiile se fac doar cu zilele din jur. Ultimele 3 luni sunt cele mai afectate (o rampă continuă din iulie până în octombrie 2026) și au fost excluse din comparațiile dintre modele.

**Puține exemple pentru ipoteza principală.** Situația „curs calm, apoi salt politic” apare de 1–2 ori în date. Mecanismul este plauzibil, dar nu poate fi demonstrat statistic cu atât de puține cazuri.

**Zgomot în rezultate.** Căutările prind și știri despre alte țări (de exemplu alegerile parlamentare din Republica Moldova, 28 septembrie 2025, apar ca un vârf de știri „politice”), despre subiecte locale sau articole fără legătură. Lista albă de surse elimină o parte, dar nu poate filtra după conținut.

**Zile saturate.** În zilele de criză, chiar și o fereastră de o zi atinge limita Google News, deci volumul real este subestimat.

**Schimbări de regim.** Între 2023 și 2024, cursul EUR/RON a fost practic fix, fără nicio mișcare peste 0,25% în 2024. Comportamentul cursului depinde de politica BNR, care se poate schimba oricând.

**Ce nu poate face modelul:** să anticipeze un șoc provocat de un eveniment care nu a avut loc încă (de exemplu rezultatul unor alegeri), sau prima zi a unei crize dacă piața era calmă înainte.

---

## Cum se rulează

### Cerințe

- Python 3.12+ (testat pe 3.14)
- Node.js 20+ (testat pe 22)
- Git

### Instalare

```bash
git clone https://github.com/alpascino19/fxcast.git
cd fxcast

python -m venv venv
venv\Scripts\activate          # Windows (PowerShell: .\venv\Scripts\Activate.ps1)
pip install -r requirements.txt

cd frontend
npm install
cd ..
```

### Datele

Datele colectate nu sunt incluse în repository. Se generează astfel:

```bash
python backend/fetch_bnr.py                                        # cursuri BNR, ~1 minut
python backend/fetch_news_history.py --start 2015-01 --end 2026-10 # istoric știri, ~10-12 ore, repornibil
python backend/build_features.py                                   # tabelul de features
python backend/train_model.py                                      # antrenare și evaluare
```

Colectarea istorică salvează progresul după fiecare lună, deci poate fi oprită oricând (Ctrl+C) și reluată cu aceeași comandă.

### Aplicația

Sunt necesare două terminale:

```bash
# terminalul 1 - API, din folderul proiectului
uvicorn backend.api:app --reload

# terminalul 2 - interfața
cd frontend
npx next dev
```

- interfața: http://localhost:3000
- API: http://127.0.0.1:8000, cu documentație interactivă la http://127.0.0.1:8000/docs

### Actualizarea automată

Cât timp API-ul rulează, `pipeline.py` este pornit automat **luni–vineri la 13:30** (ora României): descarcă cursul zilei, colectează știrile din ultimele 3 zile, recalculează features-urile și reantrenează modelul. API-ul reîncarcă datele noi fără repornire. Dacă API-ul este pornit după 13:30 și datele nu sunt la zi, actualizarea rulează imediat. Jurnalul este în `data/pipeline.log`.

Pipeline-ul poate fi rulat și manual:

```bash
python backend/pipeline.py
```

### Endpoint-uri

| Endpoint | Descriere |
|---|---|
| `GET /risk/latest` | Nivelul de risc pentru ziua următoare și indicatorii care îl explică |
| `GET /history?days=90` | Cursul și nivelul de risc pe ultimele N zile |
| `GET /model` | Informații despre model: features, evaluare, praguri |
| `GET /status` | Data ultimelor date, data antrenării, următoarea actualizare |

---

## Structura proiectului

```
fxcast/
├── backend/
│   ├── fetch_bnr.py             # descarcă cursurile BNR
│   ├── fetch_news.py            # colector inițial de știri recente (explorare)
│   ├── fetch_news_history.py    # colectare istorică și zilnică (--recent N)
│   ├── build_features.py        # aliniere știri-curs, features, țintă
│   ├── train_model.py           # evaluare walk-forward și model final
│   ├── pipeline.py              # rulează toți pașii, cu jurnal
│   └── api.py                   # API FastAPI + programarea zilnică
├── data/
│   ├── bnr_rates.csv            # cursuri BNR
│   ├── events.csv               # cele mai mari mișcări și contextul lor
│   ├── sources.csv              # lista albă de surse
│   ├── source_aliases.csv       # nume alternative ale surselor
│   └── news_history/            # știri pe ani (generat, neinclus în Git)
├── models/
│   └── model_meta.json          # evaluarea și pragurile modelului
├── notebooks/
│   ├── 01_explorare.ipynb       # cursuri, randamente, baseline
│   ├── 02_stiri.ipynb           # primele știri, clasificarea surselor
│   ├── 03_gdelt.ipynb           # testarea surselor istorice (GDELT, Google News)
│   ├── 04_news_history.ipynb    # verificarea colectării, alinierea cu BNR
│   ├── 05_features.ipynb        # semnalul fiecărui feature
│   └── 06_model.ipynb           # comparația modelelor, ponderi, evenimente
├── frontend/                    # interfața Next.js
└── requirements.txt
```

---

## Pașii următori

- [x] Descărcarea cursurilor BNR (2015 – prezent)
- [x] Explorarea datelor și baseline
- [x] Colectarea istorică a știrilor, cu listă albă de surse
- [x] Features aliniate la ora de publicare a cursului BNR
- [x] Model evaluat walk-forward, cu niveluri de risc calibrate
- [x] API (FastAPI)
- [x] Interfață web (Next.js)
- [x] Actualizare automată zilnică
- [ ] Știrile zilei afișate în interfață, ca context
- [ ] Publicarea online
- [ ] **Model v2:** rezervele valutare BNR (lunar), calendarul evenimentelor cunoscute (alegeri, decizii de rating, ședințe BNR), clasificarea conținutului știrilor cu un model de limbaj (despre România sau nu, gravitate, ton)

---

## Disclaimer

Acest proiect are scop educațional și de portofoliu. Estimările nu reprezintă recomandări de tranzacționare, investiții sau orice altă formă de sfat financiar. Cursurile valutare sunt influențate de factori pe care niciun model nu îi poate anticipa.

Sursa cursurilor: Banca Națională a României. Știrile sunt folosite doar sub formă de titluri, date de publicare și link-uri, pentru analize statistice agregate.
