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

# 5. Certificato HTTPS self-signed (per LAN/dev)
mkdir -p certs
openssl req -x509 -newkey rsa:2048 \
    -keyout certs/key.pem -out certs/cert.pem \
    -days 365 -nodes \
    -subj "/CN=maquetaweb-local" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
chmod 600 certs/key.pem
```

---

## Avvio

### Produzione (raccomandato): gunicorn + HTTPS

```bash
./start.sh
```

L'app diventa raggiungibile su `https://localhost:5000` (e dal LAN
usando l'IP della macchina). Il browser mostrerà un avviso per il
certificato self-signed: clicca "Avanzate → Procedi comunque".

Opzioni:

```bash
./start.sh --port 8443       # cambia porta
./start.sh --http            # avvia senza TLS (sconsigliato)
WORKERS=4 ./start.sh         # più worker per più concorrenza
WORKER_TIMEOUT=3600 ./start.sh  # timeout per upload molto lunghi
```

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
[Browser] ──HTTPS──▶ [gunicorn + Flask] ──SFTP──▶ [NAS remoto]
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
| HTTPS | ✅ (cert self-signed di default; per produzione usare Let's Encrypt) |
| Admin password random | ✅ |
| Cestino enforced server-side | ✅ |
| File nascosti enforced server-side | ✅ |
| Validazione `artista_id` admin→cartella | ✅ |
| Audit log | ❌ (TODO) |
| 2FA | ❌ (TODO) |

### Per HTTPS in produzione vera (no self-signed)

Mettere nginx davanti a gunicorn:

```
[Browser] ──443 HTTPS──▶ [nginx + Let's Encrypt] ──127.0.0.1:5000 HTTP──▶ [gunicorn]
```

Vantaggi: certificati validi (no warning browser), buffering uploads,
serving statici efficiente, supporto HTTP/2.

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
