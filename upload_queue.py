"""Coda di upload differita verso il NAS.

Schema operativo:

  1. enqueue_upload() salva il file su STAGING_FOLDER (disco locale) e
     inserisce una riga in `pending_uploads` con status='pending'.
     L'utente ottiene la risposta HTTP subito, senza aspettare l'SFTP.

  2. Un thread daemon (_worker_loop) gira in background, pesca le righe
     pending in ordine di creazione, le marca 'uploading', tenta il
     trasferimento SFTP via nas_storage.upload_local_path().
     A successo: status='uploaded', file locale cancellato.
     A errore: attempts++, status torna a 'pending' (riprovato con
     backoff) finche` non si supera UPLOAD_MAX_ATTEMPTS -> 'failed'.

  3. list_pending() viene usato dalla route file-manager per fondere i
     file ancora in transito con quelli gia` presenti sul NAS, cosi`
     l'utente vede subito in lista il file che ha appena caricato con
     un badge "in caricamento".

Il modulo e` thread-safe: il worker e` un singolo thread daemon avviato
una sola volta da start_worker().
"""
import os
import time
import threading
import logging
import uuid
import traceback
from datetime import datetime

from werkzeug.utils import secure_filename

import nas_storage
from config import Config
from database import get_db_connection

logger = logging.getLogger(__name__)

# Stato del worker
_worker_thread = None
_worker_lock = threading.Lock()
_worker_stop = threading.Event()


# ---------------------------------------------------------------------------
# Helper interni
# ---------------------------------------------------------------------------

def _ensure_staging_dir():
    """Crea la cartella di staging se non esiste."""
    os.makedirs(Config.STAGING_FOLDER, exist_ok=True)


def _staging_path_for(username, filename):
    """Genera un path locale univoco nella cartella di staging.

    Il nome reale del file e` preservato in DB; sul disco usiamo un UUID
    per evitare collisioni quando piu` utenti caricano file con lo stesso
    nome contemporaneamente.
    """
    safe_user = secure_filename(username) or 'anon'
    user_dir = os.path.join(Config.STAGING_FOLDER, safe_user)
    os.makedirs(user_dir, exist_ok=True)
    # Mantieni l'estensione per facilitare il debug visivo della cartella
    ext = ''
    if '.' in filename:
        ext = '.' + filename.rsplit('.', 1)[1].lower()
    return os.path.join(user_dir, f"{uuid.uuid4().hex}{ext}")


# ---------------------------------------------------------------------------
# API pubblica
# ---------------------------------------------------------------------------

def enqueue_upload(username, subpath, file_stream, filename):
    """Salva il file in staging e inserisce una riga pending.

    Ritorna l'id della riga creata, oppure None in caso di errore di
    scrittura locale (errore "duro" che merita di essere riportato
    all'utente, a differenza di un errore SFTP che e` recuperabile).
    """
    _ensure_staging_dir()

    local_path = _staging_path_for(username, filename)

    # Scrittura su disco a chunk (file.save() di werkzeug fa gia` streaming)
    try:
        file_stream.save(local_path)
    except Exception as e:
        logger.error(f"Errore salvataggio in staging di {filename}: {e}", exc_info=True)
        return None

    size = os.path.getsize(local_path)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO pending_uploads
                    (username, subpath, filename, local_path, size_bytes, status, attempts)
                VALUES (%s, %s, %s, %s, %s, 'pending', 0)
                """,
                (username, subpath or '', filename, local_path, size),
            )
            row_id = cursor.lastrowid
        conn.commit()
        logger.info(f"Upload enqueued #{row_id}: {username}/{subpath}/{filename} ({size} bytes)")
        return row_id
    except Exception as e:
        # Se l'insert fallisce, rimuovi il file di staging per non lasciarlo orfano
        logger.error(f"Errore insert pending_uploads per {filename}: {e}", exc_info=True)
        try:
            os.remove(local_path)
        except Exception:
            pass
        return None
    finally:
        conn.close()


def list_pending(username, subpath=''):
    """Ritorna i file ancora da caricare/in upload per (username, subpath).

    Output coerente con nas_storage.list_files() in modo da poter essere
    fuso nella stessa lista mostrata dal template file_manager.html:
    dict con name, size, size_human, modified, is_dir, extension, pending=True.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, filename, size_bytes, status, attempts, error_message, created_at
                FROM pending_uploads
                WHERE username = %s AND subpath = %s
                  AND status IN ('pending', 'uploading', 'failed')
                ORDER BY created_at ASC
                """,
                (username, subpath or ''),
            )
            rows = cursor.fetchall()
    finally:
        conn.close()

    items = []
    for r in rows:
        name = r['filename']
        ext = name.rsplit('.', 1)[1].lower() if '.' in name else ''
        items.append({
            'name': name,
            'size': r['size_bytes'],
            'size_human': nas_storage.format_size(r['size_bytes']),
            'modified': r['created_at'] or datetime.now(),
            'is_dir': False,
            'extension': ext,
            'pending': True,
            'pending_status': r['status'],         # 'pending' | 'uploading' | 'failed'
            'pending_attempts': r['attempts'],
            'pending_error': r['error_message'],
            'pending_id': r['id'],
        })
    return items


# ---------------------------------------------------------------------------
# Worker in background
# ---------------------------------------------------------------------------

def _fetch_next_job():
    """Recupera un job 'pending' marcandolo 'uploading' in modo atomico.

    Usa una transazione + SELECT ... FOR UPDATE per evitare race condition
    nel caso (raro ma possibile) in cui partano piu` worker.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            conn.begin()
            cursor.execute(
                """
                SELECT id, username, subpath, filename, local_path, attempts
                FROM pending_uploads
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT 1
                FOR UPDATE
                """
            )
            row = cursor.fetchone()
            if not row:
                conn.commit()
                return None
            cursor.execute(
                "UPDATE pending_uploads SET status='uploading' WHERE id=%s",
                (row['id'],),
            )
            conn.commit()
            return row
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        logger.error(f"Errore fetch_next_job: {e}", exc_info=True)
        return None
    finally:
        conn.close()


def _mark_uploaded(job_id, local_path):
    """Job concluso con successo: aggiorna stato e cancella il file di staging."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE pending_uploads SET status='uploaded', error_message=NULL WHERE id=%s",
                (job_id,),
            )
        conn.commit()
    finally:
        conn.close()

    try:
        if local_path and os.path.exists(local_path):
            os.remove(local_path)
    except Exception as e:
        logger.warning(f"Impossibile cancellare il file di staging {local_path}: {e}")


def _mark_failed(job_id, attempts, error):
    """Job fallito: incrementa attempts, decide se ritentare o dare per perso."""
    attempts = (attempts or 0) + 1
    error_text = (error or '')[:1000]  # tronca per stare nel TEXT
    new_status = 'failed' if attempts >= Config.UPLOAD_MAX_ATTEMPTS else 'pending'

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE pending_uploads
                SET status=%s, attempts=%s, error_message=%s
                WHERE id=%s
                """,
                (new_status, attempts, error_text, job_id),
            )
        conn.commit()
    finally:
        conn.close()

    if new_status == 'failed':
        logger.error(f"Job #{job_id} marcato FAILED dopo {attempts} tentativi: {error_text}")
    else:
        logger.warning(f"Job #{job_id} fallito (attempt {attempts}), ritentero`: {error_text}")


def _process_one_job():
    """Pesca un job pending e prova a caricarlo. True se ha lavorato."""
    job = _fetch_next_job()
    if not job:
        return False

    job_id = job['id']
    try:
        logger.info(
            f"Upload job #{job_id}: {job['username']}/{job['subpath']}/{job['filename']} "
            f"(tentativo {job['attempts'] + 1})"
        )
        nas_storage.upload_local_path(
            job['username'], job['subpath'], job['local_path'], job['filename']
        )
        _mark_uploaded(job_id, job['local_path'])
        logger.info(f"Upload job #{job_id} OK")
    except Exception as e:
        err = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        _mark_failed(job_id, job['attempts'], err)
    return True


def _recover_orphan_jobs():
    """Recovery all'avvio: job lasciati in 'uploading' da un crash precedente.

    Se Flask viene ucciso mentre un trasferimento e` a meta`, la riga
    resta in 'uploading' e nessuno la riprende. Al boot del worker la
    rimettiamo a 'pending' cosi` viene ritentata.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE pending_uploads SET status='pending' WHERE status='uploading'"
            )
            recovered = cursor.rowcount
        conn.commit()
        if recovered:
            logger.warning(f"Recovery: {recovered} job orfani rimessi in coda")
    except Exception as e:
        logger.error(f"Errore recovery job orfani: {e}", exc_info=True)
    finally:
        conn.close()


def _cleanup_old_uploaded(days=7):
    """Cancella le righe 'uploaded' piu` vecchie di N giorni.

    La tabella non deve crescere all'infinito. I file gia` trasferiti
    sul NAS non hanno valore informativo dopo qualche giorno.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM pending_uploads "
                "WHERE status='uploaded' AND updated_at < (NOW() - INTERVAL %s DAY)",
                (days,),
            )
            deleted = cursor.rowcount
        conn.commit()
        if deleted:
            logger.info(f"Cleanup: rimosse {deleted} righe uploaded piu` vecchie di {days} giorni")
    except Exception as e:
        logger.error(f"Errore cleanup: {e}", exc_info=True)
    finally:
        conn.close()


# Numero di cicli idle (coda vuota) tra una cleanup e l'altra.
# Con UPLOAD_WORKER_INTERVAL=2s, 1800 cicli ≈ 1 ora di idle prima della cleanup.
_CLEANUP_EVERY_N_IDLE = 1800


def _worker_loop():
    """Loop principale del thread daemon.

    All'avvio: recovery dei job orfani.
    Poi pesca job pending finche` ce ne sono; quando la coda e` vuota
    aspetta UPLOAD_WORKER_INTERVAL secondi prima del prossimo polling.
    Ogni _CLEANUP_EVERY_N_IDLE cicli idle, esegue cleanup tabella.
    Il flag _worker_stop permette di terminare in modo pulito.
    """
    logger.info("Upload worker avviato")
    _recover_orphan_jobs()
    _cleanup_old_uploaded()

    idle_cycles = 0
    while not _worker_stop.is_set():
        try:
            worked = _process_one_job()
        except Exception as e:
            # Non far morire il thread per nessun motivo
            logger.error(f"Errore inatteso nel worker loop: {e}", exc_info=True)
            worked = False

        if worked:
            idle_cycles = 0
        else:
            idle_cycles += 1
            if idle_cycles >= _CLEANUP_EVERY_N_IDLE:
                _cleanup_old_uploaded()
                idle_cycles = 0
            # Coda vuota: aspetta prima di ripollare. wait() e` interrompibile.
            _worker_stop.wait(Config.UPLOAD_WORKER_INTERVAL)
    logger.info("Upload worker terminato")


def start_worker():
    """Avvia il worker daemon. Idempotente: chiamate successive sono no-op."""
    global _worker_thread
    with _worker_lock:
        if _worker_thread and _worker_thread.is_alive():
            return
        _worker_stop.clear()
        _ensure_staging_dir()
        _worker_thread = threading.Thread(
            target=_worker_loop, name='upload-queue-worker', daemon=True
        )
        _worker_thread.start()


def stop_worker(timeout=5):
    """Ferma il worker (utile per test o shutdown puliti)."""
    global _worker_thread
    _worker_stop.set()
    t = _worker_thread
    if t and t.is_alive():
        t.join(timeout=timeout)
