# Struttura Completa del Progetto

## Panoramica
Web Application Flask completa per gestione società discografica con UI/UX responsive mobile-first.

## Tecnologie
- **Backend**: Flask 3.0, SQLAlchemy, Flask-Login
- **Database**: MySQL + PyMySQL
- **Frontend**: HTML5, CSS3 (Mobile-First), JavaScript Vanilla
- **Autenticazione**: Flask-Login con hash password
- **Forms**: Flask-WTF con validazione

## Struttura File

```
MaquetaWeb/
│
├── app/                              # Package applicazione principale
│   ├── __init__.py                   # Factory Flask, configurazione
│   ├── models.py                     # Modelli database (11 tabelle)
│   ├── forms.py                      # Form WTForms per tutti i moduli
│   │
│   ├── blueprints/                   # Blueprints modulari
│   │   ├── __init__.py
│   │   ├── auth.py                   # Autenticazione, login, logout, gestione utenti
│   │   ├── main.py                   # Dashboard principale
│   │   ├── artisti.py                # CRUD artisti
│   │   ├── dischi.py                 # CRUD dischi
│   │   ├── singoli.py                # CRUD singoli
│   │   ├── eventi.py                 # CRUD eventi
│   │   ├── servizi.py                # CRUD servizi (solo admin)
│   │   ├── staff.py                  # CRUD staff (solo admin)
│   │   ├── documenti.py              # Upload/download documenti
│   │   └── news.py                   # CRUD news interne/esterne
│   │
│   ├── templates/                    # Template HTML Jinja2
│   │   ├── base.html                 # Template base con sidebar e header
│   │   ├── index.html                # Homepage
│   │   ├── dashboard.html            # Dashboard con statistiche
│   │   ├── _macros.html              # Macro riutilizzabili
│   │   │
│   │   ├── auth/                     # Template autenticazione
│   │   │   ├── login.html
│   │   │   ├── registrazione.html
│   │   │   └── lista_utenti.html
│   │   │
│   │   ├── artisti/                  # Template artisti
│   │   │   ├── lista.html
│   │   │   ├── dettaglio.html
│   │   │   └── form.html
│   │   │
│   │   ├── dischi/                   # Template dischi
│   │   │   ├── lista.html
│   │   │   ├── dettaglio.html
│   │   │   └── form.html
│   │   │
│   │   ├── singoli/                  # Template singoli
│   │   ├── eventi/                   # Template eventi
│   │   ├── servizi/                  # Template servizi
│   │   ├── staff/                    # Template staff
│   │   ├── documenti/                # Template documenti
│   │   └── news/                     # Template news
│   │
│   └── static/                       # File statici
│       ├── css/
│       │   └── style.css             # CSS completo (900+ righe), mobile-first
│       │
│       ├── js/
│       │   └── main.js               # JavaScript interattivo (200+ righe)
│       │
│       └── uploads/                  # File caricati
│           ├── images/               # Immagini (foto, copertine)
│           │   └── .gitkeep
│           └── documents/            # Documenti (PDF, DOC, etc.)
│               └── .gitkeep
│
├── run.py                            # Entry point applicazione
├── init_db.py                        # Script inizializzazione database
├── requirements.txt                  # Dipendenze Python
├── .env                              # Variabili ambiente (configurazione)
├── .env.example                      # Template variabili ambiente
├── .gitignore                        # File da ignorare in Git
│
├── README.md                         # Documentazione completa
├── ISTRUZIONI_INSTALLAZIONE.md       # Guida rapida installazione
├── STRUTTURA_PROGETTO.md             # Questo file
└── START_APP.bat                     # Script Windows per avvio rapido
```

## Database - Tabelle

1. **users** - Utenti del sistema
2. **artisti** - Artisti musicali
3. **dischi** - Album/Dischi
4. **singoli** - Singoli musicali
5. **artisti_dischi** - Relazione molti-a-molti artisti-dischi
6. **artisti_singoli** - Relazione molti-a-molti artisti-singoli
7. **eventi** - Eventi (concerti, registrazioni, etc.)
8. **servizi** - Servizi offerti
9. **staff** - Membri dello staff
10. **documenti** - Documenti caricati
11. **news** - News/Articoli

## Moduli Funzionali

### 1. AUTENTICAZIONE (auth.py)
- Login/Logout sicuro
- Registrazione nuovi utenti (solo admin)
- Gestione utenti esistenti
- 3 ruoli: admin, editor, user
- Decoratori per controllo permessi

### 2. DASHBOARD (main.py)
- Statistiche totali (artisti, dischi, singoli, eventi, documenti, news)
- Ultimi artisti aggiunti
- Ultimi dischi aggiunti
- Prossimi eventi
- Ultime news pubblicate
- Azioni rapide per editor/admin

### 3. ARTISTI (artisti.py)
- Lista artisti (griglia 3 colonne)
- Dettaglio artista con biografia
- Foto profilo
- Link social media (Instagram, Facebook, Twitter, Spotify)
- Sito web
- Discografia completa
- Upload foto

### 4. DISCHI (dischi.py)
- Lista dischi con copertine
- Dettaglio disco
- Associazione con artisti (molti a molti)
- Link streaming (Spotify, Apple Music, YouTube)
- Upload copertina
- Informazioni tecniche (formato, etichetta, tracce, codice catalogo)

### 5. SINGOLI (singoli.py)
- Lista singoli
- Dettaglio singolo
- Associazione con artisti
- Link streaming
- Upload copertina
- Durata, ISRC

### 6. EVENTI (eventi.py)
- Lista eventi in tabella
- Dettaglio evento
- Gestione data/ora inizio e fine
- Luogo completo (indirizzo, città, paese)
- Visibilità pubblico/privato
- Tipologie (Concerto, Festival, Registrazione, etc.)

### 7. SERVIZI (servizi.py)
- Catalogo servizi (solo admin)
- Prezzi in diverse valute
- Categorie (Produzione, Distribuzione, Marketing, etc.)
- Icone per UI
- Stato attivo/inattivo

### 8. STAFF (staff.py)
- Gestione team (solo admin)
- Foto membro
- Ruolo e reparto
- Contatti (email, telefono)
- Biografia
- Data assunzione

### 9. DOCUMENTI (documenti.py)
- Upload documenti (PDF, DOC, XLS, ZIP, etc.)
- Download sicuro
- Visibilità privato/pubblico
- Controllo accessi granulare
- Tipologie (Contratto, Fattura, Report, etc.)
- Informazioni file (dimensione, tipo MIME)

### 10. NEWS (news.py)
- Creazione news
- Pubblicazione/bozza
- Data pubblicazione programmabile
- Tipo interna/esterna
- Categorie (Lancio, Evento, Comunicato, etc.)
- Upload immagine
- Sommario e contenuto completo

## Funzionalità UI/UX

### Design System
- Palette colori moderna e professionale
- Typography chiara e leggibile
- Spacing consistente
- Ombre e depth per elevazione
- Animazioni fluide

### Componenti
- **Sidebar**: Navigazione principale, collassabile su mobile
- **Header**: Ricerca, user menu, logout
- **Cards**: Per contenuti visuali
- **Tables**: Per liste dati strutturati
- **Forms**: Con validazione e feedback
- **Buttons**: 6 varianti (primary, success, danger, warning, info, secondary)
- **Badges**: Per stati e categorie
- **Alerts**: Sistema notifiche con auto-dismiss
- **Pagination**: Per liste lunghe
- **Stats Cards**: Per dashboard

### Responsività
- **Mobile First**: Ottimizzato prima per smartphone
- **Breakpoint**: 768px per tablet/desktop
- **Sidebar**: Overlay su mobile con animazione slide
- **Grid**: Adattivo da 1 a 4 colonne
- **Tables**: Scrollabile orizzontalmente su mobile
- **Forms**: Layout a colonna singola su mobile

### Interattività JavaScript
- Toggle sidebar mobile
- Preview immagini prima upload
- Validazione form client-side
- Conferma eliminazione
- Auto-hide alerts
- Link attivo evidenziato
- Ricerca in tempo reale tabelle
- Formattazione automatica durata (MM:SS)
- Notifiche toast animate
- Animazioni on scroll

## Sicurezza

- ✅ Password hashate (Werkzeug)
- ✅ CSRF protection (Flask-WTF)
- ✅ SQL Injection protection (SQLAlchemy ORM)
- ✅ Controllo accessi basato su ruoli
- ✅ Validazione input server-side
- ✅ Validazione file upload
- ✅ Limite dimensione file (16MB)
- ✅ Sanitizzazione path upload
- ✅ Controllo permessi su ogni route

## Permessi per Ruolo

| Funzionalità | User | Editor | Admin |
|-------------|------|--------|-------|
| Login | ✅ | ✅ | ✅ |
| Dashboard | ✅ | ✅ | ✅ |
| Visualizza propri contenuti | ✅ | ✅ | ✅ |
| Visualizza tutti i contenuti | ❌ | ✅ | ✅ |
| Crea artisti/dischi/singoli | ❌ | ✅ | ✅ |
| Modifica propri contenuti | ✅ | ✅ | ✅ |
| Modifica tutti i contenuti | ❌ | ✅ | ✅ |
| Elimina contenuti | ❌ | ✅ | ✅ |
| Gestisci servizi | ❌ | ❌ | ✅ |
| Gestisci staff | ❌ | ❌ | ✅ |
| Gestisci utenti | ❌ | ❌ | ✅ |

## API Routes Principali

```
/ ...................... Homepage
/login ................. Login
/logout ................ Logout
/dashboard ............. Dashboard

/artisti ............... Lista artisti
/artisti/nuovo ......... Nuovo artista
/artisti/<id> .......... Dettaglio artista
/artisti/<id>/modifica . Modifica artista
/artisti/<id>/elimina .. Elimina artista

/dischi ................ Lista dischi
/dischi/nuovo .......... Nuovo disco
/dischi/<id> ........... Dettaglio disco
/dischi/<id>/modifica .. Modifica disco
/dischi/<id>/elimina ... Elimina disco

/singoli ............... Lista singoli
/eventi ................ Lista eventi
/servizi ............... Lista servizi
/staff ................. Lista staff
/documenti ............. Lista documenti
/documenti/<id>/download Download documento
/news .................. Lista news

[... e molti altri endpoint per CRUD completo di ogni modulo]
```

## Configurazione

### Variabili Ambiente (.env)
```
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=chiave-segreta-cambiare
DATABASE_URI=mysql+pymysql://user:pass@localhost/discografica_db
```

### Porta Applicazione
Default: 6000 (configurabile in run.py)

## Dipendenze Python

```
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Flask-WTF==1.2.1
WTForms==3.1.1
PyMySQL==1.1.0
cryptography==41.0.7
python-dotenv==1.0.0
Werkzeug==3.0.1
email-validator==2.1.0
```

## Performance & Ottimizzazioni

- Query database ottimizzate con relazioni lazy
- Paginazione su liste lunghe
- Immagini con dimensioni ottimizzate
- CSS minimalista (no framework pesanti)
- JavaScript vanilla (no jQuery)
- File statici serviti efficientemente
- Session management ottimizzato

## Estensibilità

Il progetto è strutturato per facile estensione:

1. **Nuovi moduli**: Crea nuovo blueprint in app/blueprints/
2. **Nuove tabelle**: Aggiungi modello in models.py
3. **Nuovi form**: Aggiungi form in forms.py
4. **Nuove rotte**: Registra blueprint in __init__.py
5. **Nuovi template**: Crea in app/templates/[modulo]/
6. **Nuovo styling**: Estendi style.css
7. **Nuove funzionalità JS**: Estendi main.js

## Testing Suggerito

```bash
# Test manuale consigliato:
1. Creare utenti con diversi ruoli
2. Testare upload immagini/documenti
3. Verificare permessi per ogni ruolo
4. Testare CRUD di ogni modulo
5. Verificare responsività mobile
6. Testare ricerca e filtri
7. Verificare paginazione
8. Testare relazioni molti-a-molti (artisti-dischi)
```

## Manutenzione

### Backup Database
```bash
mysqldump -u root -p discografica_db > backup.sql
```

### Update Dipendenze
```bash
pip install --upgrade -r requirements.txt
```

### Log Errors
Flask in development mode mostra errori dettagliati.
Per produzione, configurare logging in app/__init__.py

---

**Versione**: 1.0.0
**Ultima Modifica**: 2025
**Sviluppato con**: Claude Code
