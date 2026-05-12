#!/usr/bin/env bash
# Avvio produzione di MaquetaWeb con gunicorn + HTTPS.
#
# Modalita`:
#   ./start.sh              -> HTTPS su :5000 col cert self-signed in certs/
#   ./start.sh --http       -> HTTP (utile per dev locale, sconsigliato in prod)
#   ./start.sh --port 8080  -> cambia porta
#
# Variabili d'ambiente lette da gunicorn.conf.py:
#   PORT=5000               porta di ascolto
#   WORKERS=N               numero worker (default 2*core+1)
#   WORKER_TIMEOUT=1800     timeout per request (default 30 min)
#   SSL_CERTFILE=path       cert PEM (default certs/cert.pem)
#   SSL_KEYFILE=path        chiave PEM (default certs/key.pem)

set -e

cd "$(dirname "$0")"

# Default: HTTPS
USE_HTTPS=1
PORT_OVERRIDE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --http)   USE_HTTPS=0; shift ;;
        --port)   PORT_OVERRIDE="$2"; shift 2 ;;
        --help|-h)
            grep '^# ' "$0" | sed 's/^# //'
            exit 0
            ;;
        *) echo "Argomento sconosciuto: $1" >&2; exit 1 ;;
    esac
done

if [[ -n "$PORT_OVERRIDE" ]]; then
    export PORT="$PORT_OVERRIDE"
fi

if [[ "$USE_HTTPS" == "1" ]]; then
    : "${SSL_CERTFILE:=$(pwd)/certs/cert.pem}"
    : "${SSL_KEYFILE:=$(pwd)/certs/key.pem}"
    if [[ ! -f "$SSL_CERTFILE" || ! -f "$SSL_KEYFILE" ]]; then
        echo "ERRORE: certificato non trovato. Genera con:" >&2
        echo "  openssl req -x509 -newkey rsa:2048 \\" >&2
        echo "    -keyout certs/key.pem -out certs/cert.pem \\" >&2
        echo "    -days 365 -nodes -subj '/CN=maquetaweb-local'" >&2
        exit 1
    fi
    export SSL_CERTFILE SSL_KEYFILE
    echo "Avvio HTTPS su https://localhost:${PORT:-5000}"
    echo "(cert self-signed in $SSL_CERTFILE, il browser mostrera` un avviso)"
else
    unset SSL_CERTFILE SSL_KEYFILE
    echo "Avvio HTTP su http://localhost:${PORT:-5000}"
fi

# Avvio gunicorn dal venv
exec .venv/bin/gunicorn -c gunicorn.conf.py app:app
