#!/usr/bin/env bash
# Avvio di MaquetaWeb in produzione con gunicorn.
#
# Architettura: gunicorn ascolta SOLO su localhost (127.0.0.1:5000).
# Il TLS e l'esposizione pubblica li fa nginx davanti, col suo cert.
#
# Modalita`:
#   ./start.sh                    -> gunicorn su 127.0.0.1:5000 (per nginx)
#   ./start.sh --port 8000        -> cambia porta interna
#   ./start.sh --lan              -> bind 0.0.0.0 (raggiungibile da LAN
#                                    senza nginx, utile per test locali)
#
# Variabili d'ambiente:
#   BIND_HOST=127.0.0.1   indirizzo di ascolto (--lan lo cambia in 0.0.0.0)
#   PORT=5000             porta
#   WORKERS=N             numero worker
#   WORKER_TIMEOUT=1800   timeout per request (30 min default)
#   FORWARDED_ALLOW_IPS=127.0.0.1   IP del proxy fidato

set -e

cd "$(dirname "$0")"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)   export PORT="$2"; shift 2 ;;
        --lan)    export BIND_HOST="0.0.0.0"; shift ;;
        --help|-h)
            grep '^# ' "$0" | sed 's/^# //'
            exit 0
            ;;
        *) echo "Argomento sconosciuto: $1" >&2; exit 1 ;;
    esac
done

bind="${BIND_HOST:-127.0.0.1}:${PORT:-5000}"
echo "Avvio gunicorn su http://${bind}"
if [[ "${BIND_HOST:-127.0.0.1}" == "127.0.0.1" ]]; then
    echo "(solo localhost: in produzione metti nginx davanti per TLS + accesso esterno)"
fi

exec .venv/bin/gunicorn -c gunicorn.conf.py app:app
