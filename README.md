# MaquetaWeb

Gestionale Flask con file manager integrato verso un NAS via SFTP.

## Funzionalità principali

- **Upload differiti**: i file caricati dagli utenti vengono salvati subito
  in staging locale e poi trasferiti al NAS in background da un worker.
  L'utente vede subito il file in lista con badge "in caricamento".
- **Download streaming**: niente buffer in RAM, supporta file da GB.
- **Permessi**: admin / artista / utente, con cartelle dedicate per artista.
- **Cestino + file nascosti**: con enforcement lato server (non solo UI).
- **CSRF / rate limit / HTTPS**: configurato di default.

---

## Setup iniziale (una sola volta)

```bash
# 1. Dipendenze di sistema
sudo apt install -y python3-pip python3-venv mariadb-server mariadb-client

# 2. Virtualenv + dipendenze Python
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 3. Database e utente applicativo
sudo mysql < setup_db.sql

# 4. Variabili d'ambiente (credenziali DB e NAS)
cp .env.example .env
# Modifica .env con i tuoi valori

# 5. nginx come reverse proxy (gestisce TLS)
#    Vedi docs/nginx.conf.sample per il template completo.
sudo cp docs/nginx.conf.sample /etc/nginx/sites-available/maquetaweb
# (modifica server_name, ssl_certificate, ecc.)
sudo ln -s /etc/nginx/sites-available/maquetaweb /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## Avvio

### Produzione: gunicorn dietro nginx

```bash
./start.sh
```

gunicorn parte ascoltando **solo su `127.0.0.1:5000`** (porta interna,
non raggiungibile da fuori). Il TLS e l'esposizione pubblica li gestisce
nginx davanti, con il certificato gia` configurato (Let's Encrypt o
equivalente). Vedi `docs/nginx.conf.sample`.

Architettura:
```
[Internet] ──HTTPS──▶ [nginx:443 + cert] ──HTTP 127.0.0.1:5000──▶ [gunicorn]
```

Opzioni:
```bash
./start.sh --port 8000       # cambia porta interna
./start.sh --lan             # bind 0.0.0.0 (test senza nginx)
WORKERS=4 ./start.sh         # più worker (default 2*core+1)
WORKER_TIMEOUT=3600 ./start.sh  # timeout per upload molto lunghi
```

Lo schema reale (https), il vero IP del client e l'host pubblico
arrivano a Flask via header `X-Forwarded-*` impostati da nginx e letti
da `werkzeug ProxyFix` (vedi `app.py`).

### Sviluppo: dev server Werkzeug (con reloader)

```bash
.venv/bin/python app.py
```

Server su `http://localhost:5000`. Reloader attivo (cambi al codice
ricaricano il processo). Non usare in produzione.

---

## Primo login

Alla prima inizializzazione del DB, l'app genera una **password admin
casuale** (24 caratteri). La trovi in:
- console / log di avvio (banner in evidenza)
- file `admin_password.txt` nella root del progetto (chmod 600)

**Cambia la password al primo login**, poi cancella `admin_password.txt`.

---

## Architettura

```
[Browser] ──HTTPS──▶ [nginx] ──HTTP 127.0.0.1──▶ [gunicorn + Flask] ──SFTP──▶ [NAS remoto]
                                                       │
                                                       ├─ MariaDB        (utenti, permessi, news, ...)
                                                       ├─ staging/       (file in transito al NAS)
                                                       └─ static/uploads/ (immagini per articoli)
```

### Upload flow

1. Browser carica → Flask salva in `staging/`
2. Riga `status=pending` in `pending_uploads`
3. Risposta HTTP immediata; il file appare con badge "in coda"
4. Worker background: SFTP put → `status=uploaded`, cancella file locale
5. UI auto-refresh ogni 5s finché ci sono pending

### Download flow

`Browser ◀─HTTP chunked─ Flask ◀─SFTP 256KB pipelined─ NAS`

RAM costante (~4 MB chunk), supporta file da decine di GB.

---

## Sicurezza

| Aspetto | Stato |
|---|---|
| Password hashate (bcrypt) | ✅ |
| CSRF tokens su POST | ✅ (Flask-WTF) |
| Rate limit login | ✅ 10/min, 60/h per IP |
| HTTPS | ✅ (nginx davanti gestisce TLS con cert valido) |
| Admin password random | ✅ |
| Cestino enforced server-side | ✅ |
| File nascosti enforced server-side | ✅ |
| Validazione `artista_id` admin→cartella | ✅ |
| Audit log | ❌ (TODO) |
| 2FA | ❌ (TODO) |

### Configurazione nginx

Vedi `docs/nginx.conf.sample` per il template completo. Punti chiave:

- `client_max_body_size 0` (o un valore alto): senza, nginx rifiuta upload
  oltre 1 MB di default.
- `proxy_buffering off; proxy_request_buffering off`: necessario per
  download/upload in streaming, altrimenti nginx bufferizza tutto.
- `proxy_read_timeout 1800s`: allineato col `WORKER_TIMEOUT` di gunicorn.
- Header `X-Forwarded-Proto $scheme` e `X-Forwarded-For`: letti da
  ProxyFix in Flask per ricostruire schema reale e IP client.

---

## Comandi utili

```bash
# Log live
tail -f /tmp/flask.log              # dev server
journalctl -u maquetaweb -f         # se gestito da systemd

# Controlla la coda upload
mysql -u maqueta -p maquetaweb \
    -e "SELECT id, filename, status, attempts FROM pending_uploads ORDER BY id DESC LIMIT 20;"

# Spazio staging (dovrebbe essere ~vuoto a regime)
du -sh staging/

# Stop tutti i processi dell'app
pkill -f 'gunicorn.*app:app' || pkill -f 'python app.py'
```

---

## Stack

- Flask 3.0 + Flask-Login + Flask-WTF + Flask-Limiter
- gunicorn 23 (prod) / Werkzeug (dev)
- MariaDB 11
- paramiko 3.4 (SFTP verso NAS)
- python-dotenv (config)
- Bootstrap 5.3 (frontend)

---

## TODO / Migliorabili

- HTTP Range request → resume download dopo interruzione
- Cache locale dei file scaricati spesso dal NAS
- Pool persistente di connessioni SFTP (oggi una nuova per ogni operazione)
- Refactor di `app.py` in blueprints Flask
- Test automatici (pytest)
- PWA (manifest.json, service worker)
- Audit log delle operazioni file
- 2FA (Authenticator app)
