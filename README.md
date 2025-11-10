# Sistema di Gestione Discografica

Web application completa in Flask per la gestione di una società discografica, con dashboard responsive e mobile-first.

## Caratteristiche

### Moduli Implementati

1. **Autenticazione e Utenti**
   - Sistema di login/logout sicuro
   - Gestione utenti con 3 ruoli (admin, editor, user)
   - Controllo accessi granulare

2. **Artisti**
   - CRUD completo
   - Gestione foto profilo
   - Link ai social media
   - Biografia e discografia

3. **Dischi e Singoli**
   - CRUD completo
   - Upload copertine
   - Associazione con artisti
   - Link streaming (Spotify, Apple Music, YouTube)

4. **Eventi**
   - Gestione calendario eventi
   - Eventi pubblici/privati
   - Informazioni complete su luogo e data

5. **Servizi**
   - Catalogo servizi offerti
   - Gestione prezzi e categorie

6. **Staff**
   - Gestione team interno
   - Ruoli e reparti

7. **Documenti**
   - Upload/download documenti
   - Controllo accessi per documento
   - Gestione visibilità

8. **News**
   - Sistema di pubblicazione news
   - News interne/esterne
   - Gestione pubblicazione

### Tecnologie Utilizzate

- **Backend**: Flask 3.0, SQLAlchemy, Flask-Login
- **Database**: MySQL con PyMySQL
- **Frontend**: HTML5, CSS3 (Mobile-First), JavaScript Vanilla
- **UI/UX**: Design moderno e responsive
- **Sicurezza**: Hashing password, controllo accessi, CSRF protection

## Installazione

### Prerequisiti

- Python 3.8+
- MySQL Server
- pip (package manager Python)

### Setup

1. **Clona il repository o estrai i file**

2. **Crea un virtual environment**
   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # Linux/Mac
   source venv/bin/activate
   ```

3. **Installa le dipendenze**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configura il database MySQL**
   ```sql
   CREATE DATABASE discografica_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

5. **Configura le variabili d'ambiente**
   - Copia `.env.example` in `.env`
   - Modifica `.env` con le tue credenziali MySQL:
   ```
   SECRET_KEY=tua-chiave-segreta
   DATABASE_URI=mysql+pymysql://user:password@localhost/discografica_db
   ```

6. **Inizializza il database**
   ```bash
   python init_db.py
   ```
   Questo script:
   - Crea tutte le tabelle
   - Crea un utente admin (username: admin, password: admin123)
   - Opzionalmente crea dati di esempio

7. **Avvia l'applicazione**
   ```bash
   python run.py
   ```

8. **Accedi all'applicazione**
   - URL: http://localhost:6000
   - Username: admin
   - Password: admin123

   **⚠ IMPORTANTE**: Cambia la password admin dopo il primo accesso!

## Struttura del Progetto

```
MaquetaWeb/
├── app/
│   ├── __init__.py              # Factory app Flask
│   ├── models.py                # Modelli database
│   ├── forms.py                 # Form WTForms
│   ├── blueprints/              # Blueprints per moduli
│   │   ├── auth.py              # Autenticazione
│   │   ├── main.py              # Dashboard
│   │   ├── artisti.py
│   │   ├── dischi.py
│   │   ├── singoli.py
│   │   ├── eventi.py
│   │   ├── servizi.py
│   │   ├── staff.py
│   │   ├── documenti.py
│   │   └── news.py
│   ├── templates/               # Template HTML
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── auth/
│   │   ├── artisti/
│   │   ├── dischi/
│   │   └── ...
│   └── static/                  # File statici
│       ├── css/
│       │   └── style.css
│       ├── js/
│       │   └── main.js
│       └── uploads/             # File caricati
│           ├── images/
│           └── documents/
├── run.py                       # Entry point
├── init_db.py                   # Script inizializzazione DB
├── requirements.txt             # Dipendenze Python
├── .env                         # Variabili ambiente (non committare!)
└── README.md                    # Questo file
```

## Permessi e Ruoli

### Admin
- Accesso completo a tutti i moduli
- Gestione utenti e staff
- Può vedere e modificare tutto

### Editor
- Può creare e modificare contenuti (artisti, dischi, eventi, news)
- Può vedere tutti i contenuti
- Non può gestire utenti

### User
- Può vedere solo i contenuti che ha creato
- Può modificare solo i propri contenuti
- Accesso limitato

## Features UI/UX

- ✅ Design mobile-first e completamente responsive
- ✅ Sidebar collassabile su mobile
- ✅ Animazioni fluide e transizioni
- ✅ Card moderne con hover effects
- ✅ Sistema di notifiche toast
- ✅ Preview immagini prima dell'upload
- ✅ Validazione form lato client
- ✅ Icone Font Awesome
- ✅ Palette colori moderna
- ✅ Dashboard con statistiche

## Sicurezza

- Password hashate con Werkzeug
- CSRF protection su tutti i form
- Controllo accessi basato su ruoli
- Protezione contro SQL injection (SQLAlchemy ORM)
- Validazione input lato server
- Gestione sicura upload file

## API Endpoints Principali

- `/` - Homepage/Login
- `/dashboard` - Dashboard principale
- `/artisti` - Lista artisti
- `/artisti/<id>` - Dettaglio artista
- `/dischi` - Lista dischi
- `/singoli` - Lista singoli
- `/eventi` - Lista eventi
- `/servizi` - Lista servizi
- `/staff` - Lista staff
- `/documenti` - Gestione documenti
- `/news` - Lista news

## Sviluppo Futuro

Possibili miglioramenti:

- [ ] API REST per app mobile
- [ ] Export dati in PDF/Excel
- [ ] Sistema di notifiche email
- [ ] Calendario integrato per eventi
- [ ] Statistiche avanzate e analytics
- [ ] Ricerca avanzata con filtri
- [ ] Sistema di commenti/note
- [ ] Backup automatico database
- [ ] Multi-lingua
- [ ] Tema scuro

## Troubleshooting

### Errore connessione database
- Verifica che MySQL sia in esecuzione
- Controlla le credenziali in `.env`
- Verifica che il database sia stato creato

### Errore import moduli
- Assicurati di aver attivato il virtual environment
- Reinstalla le dipendenze: `pip install -r requirements.txt`

### Porta 6000 già in uso
- Cambia porta in `run.py`: `app.run(port=ALTRA_PORTA)`

## Licenza

Progetto sviluppato per uso interno società discografica.

## Supporto

Per problemi o domande, contatta l'amministratore di sistema.

---

**Versione**: 1.0.0
**Data**: 2025
**Autore**: Claude Code
