import paramiko
import stat
import os
import io
import time
import logging
import traceback
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

# Throughput tuning per i transferi SFTP.
# Di default paramiko fa read SFTP da 32 KB per volta: su connessioni a
# latenza non trascurabile (es. NAS su Internet) significa decine di
# round-trip al secondo, ognuno con overhead, che cappa la banda.
# Alzando MAX_REQUEST_SIZE a 256 KB (massimo che la maggioranza dei server
# SFTP accetta senza problemi) ogni read trasporta 8x i dati con la stessa
# latenza, e con set_pipelined(True) molte read vanno in volo in parallelo.
try:
    paramiko.sftp_file.SFTPFile.MAX_REQUEST_SIZE = 256 * 1024
except Exception:
    pass


def _get_sftp():
    """Crea e restituisce una connessione SSH + SFTP al NAS."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        logger.info(f"Connessione SFTP a {Config.NAS_HOST}:{Config.NAS_PORT} come {Config.NAS_USER}")
        ssh.connect(
            hostname=Config.NAS_HOST,
            port=Config.NAS_PORT,
            username=Config.NAS_USER,
            password=Config.NAS_PASSWORD,
            timeout=10
        )
        sftp = ssh.open_sftp()
        logger.info("Connessione SFTP stabilita con successo")
        return ssh, sftp
    except PermissionError as e:
        logger.error(f"PermissionError durante connessione SFTP: {e}")
        logger.error(f"Traceback completo:\n{traceback.format_exc()}")
        raise
    except Exception as e:
        logger.error(f"Errore connessione SFTP ({type(e).__name__}): {e}")
        logger.error(f"Traceback completo:\n{traceback.format_exc()}")
        raise


def diagnose_nas():
    """Diagnostica la connessione NAS: mostra pwd e contenuto root."""
    ssh, sftp = _get_sftp()
    try:
        pwd = sftp.normalize('.')
        logger.info(f"NAS pwd: {pwd}")
        logger.info(f"NAS_BASE_PATH configurato: {Config.NAS_BASE_PATH}")
        # Lista contenuto della home
        items = sftp.listdir(pwd)
        logger.info(f"Contenuto home ({pwd}): {items}")
        # Prova a verificare se il base path esiste
        try:
            sftp.stat(Config.NAS_BASE_PATH)
            logger.info(f"NAS_BASE_PATH '{Config.NAS_BASE_PATH}' ESISTE")
        except Exception:
            logger.warning(f"NAS_BASE_PATH '{Config.NAS_BASE_PATH}' NON ESISTE")
            # Prova con path assoluto
            abs_path = f"{pwd}/{Config.NAS_BASE_PATH}"
            try:
                sftp.stat(abs_path)
                logger.info(f"Path assoluto '{abs_path}' ESISTE")
            except Exception:
                logger.warning(f"Path assoluto '{abs_path}' NON ESISTE")
    finally:
        sftp.close()
        ssh.close()


def _safe_subpath(subpath):
    """Previene path traversal attacks. Restituisce un path sicuro."""
    if not subpath:
        return ''
    # Rimuove componenti pericolosi
    parts = subpath.replace('\\', '/').split('/')
    safe_parts = [p for p in parts if p and p != '..' and p != '.']
    return '/'.join(safe_parts)


def _user_base_path(username):
    """Restituisce il path base per l'utente sul NAS."""
    return f"{Config.NAS_BASE_PATH}/{username}"


def _mkdir_recursive(sftp, path):
    """Crea una directory e tutte le directory intermedie se non esistono."""
    parts = path.replace('\\', '/').split('/')
    current = ''
    for part in parts:
        if not part:
            continue
        current = f"{current}/{part}" if current else part
        try:
            sftp.stat(current)
        except Exception:
            try:
                sftp.mkdir(current)
            except Exception:
                pass


def ensure_user_folder(username):
    """Crea la cartella dell'utente sul NAS se non esiste."""
    ssh, sftp = _get_sftp()
    try:
        path = _user_base_path(username)
        _mkdir_recursive(sftp, path)
    finally:
        sftp.close()
        ssh.close()


def ensure_shared_folder():
    """Crea la cartella condivisa sul NAS se non esiste."""
    ensure_user_folder('__condivisi__')


def list_files(username, subpath=''):
    """Lista file e cartelle nella directory dell'utente.

    Returns:
        list of dict: [{name, size, modified, is_dir, extension}, ...]
    """
    logger.info(f"list_files chiamata per utente={username}, subpath={subpath}")
    ssh, sftp = _get_sftp()
    try:
        subpath = _safe_subpath(subpath)
        base = _user_base_path(username)
        full_path = f"{base}/{subpath}" if subpath else base
        logger.info(f"Accesso a path NAS: {full_path}")

        # Crea la cartella se non esiste
        _mkdir_recursive(sftp, full_path)

        items = []
        for entry in sftp.listdir_attr(full_path):
            is_dir = stat.S_ISDIR(entry.st_mode)
            name = entry.filename
            ext = ''
            if not is_dir and '.' in name:
                ext = name.rsplit('.', 1)[1].lower()

            items.append({
                'name': name,
                'size': entry.st_size if not is_dir else 0,
                'size_human': format_size(entry.st_size) if not is_dir else '-',
                'modified': datetime.fromtimestamp(entry.st_mtime),
                'is_dir': is_dir,
                'extension': ext
            })

        # Ordina: cartelle prima, poi file, in ordine alfabetico
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        return items
    except FileNotFoundError:
        return []
    finally:
        sftp.close()
        ssh.close()


def upload_file(username, subpath, file_obj, filename):
    """Carica un file nella cartella dell'utente."""
    ssh, sftp = _get_sftp()
    try:
        subpath = _safe_subpath(subpath)
        base = _user_base_path(username)
        target_dir = f"{base}/{subpath}" if subpath else base

        _mkdir_recursive(sftp, target_dir)

        # Sanitizza il nome del file
        safe_name = filename.replace('/', '_').replace('\\', '_')
        remote_path = f"{target_dir}/{safe_name}"

        sftp.putfo(file_obj, remote_path)
        return True
    except Exception:
        return False
    finally:
        sftp.close()
        ssh.close()


def upload_local_path(username, subpath, local_path, filename):
    """Carica su NAS un file presente sul filesystem locale, in streaming.

    A differenza di upload_file (che riceve uno stream/BytesIO), questa
    funzione usa sftp.put() che legge a chunk dal disco: indispensabile
    per file di grandi dimensioni (>100 MB) per non saturare la RAM.

    Lancia un'eccezione in caso di errore (gestita dal worker della coda).
    """
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"File locale non trovato: {local_path}")

    ssh, sftp = _get_sftp()
    try:
        subpath = _safe_subpath(subpath)
        base = _user_base_path(username)
        target_dir = f"{base}/{subpath}" if subpath else base

        _mkdir_recursive(sftp, target_dir)

        safe_name = filename.replace('/', '_').replace('\\', '_')
        remote_path = f"{target_dir}/{safe_name}"

        # sftp.put usa lo streaming a chunk dal filesystem locale
        sftp.put(local_path, remote_path)
        return True
    finally:
        sftp.close()
        ssh.close()


def download_file(username, subpath, filename):
    """Scarica un file dalla cartella dell'utente caricandolo INTERAMENTE in RAM.

    DEPRECATED per file grandi: usa iter_remote_file() in streaming.
    Mantenuta per retrocompatibilita` di eventuali altre chiamate.

    Returns:
        BytesIO object con il contenuto del file, o None se errore
    """
    ssh, sftp = _get_sftp()
    try:
        subpath = _safe_subpath(subpath)
        safe_name = filename.replace('/', '_').replace('\\', '_')
        base = _user_base_path(username)
        target_dir = f"{base}/{subpath}" if subpath else base
        remote_path = f"{target_dir}/{safe_name}"

        buffer = io.BytesIO()
        sftp.getfo(remote_path, buffer)
        buffer.seek(0)
        return buffer
    except Exception:
        return None
    finally:
        sftp.close()
        ssh.close()


def _resolve_remote_path(username, subpath, filename):
    """Risolve in modo sicuro il path remoto sul NAS per (user/subpath/filename)."""
    subpath = _safe_subpath(subpath)
    safe_name = filename.replace('/', '_').replace('\\', '_')
    base = _user_base_path(username)
    target_dir = f"{base}/{subpath}" if subpath else base
    return f"{target_dir}/{safe_name}"


def remote_file_size(username, subpath, filename):
    """Ritorna la dimensione in bytes di un file remoto, o None se non esiste."""
    ssh, sftp = _get_sftp()
    try:
        remote_path = _resolve_remote_path(username, subpath, filename)
        try:
            attrs = sftp.stat(remote_path)
            return attrs.st_size
        except FileNotFoundError:
            return None
        except IOError:
            return None
    finally:
        sftp.close()
        ssh.close()


def iter_remote_file(username, subpath, filename, chunk_size=4 * 1024 * 1024):
    """Generator: legge un file dal NAS via SFTP e yielda chunk in streaming.

    A differenza di download_file() (che bufferizza tutto in RAM), questo
    streamma direttamente dal NAS al chiamante: RAM costante ~chunk_size,
    indipendente dalla dimensione del file. Indispensabile per file >100 MB.

    Default chunk_size = 4 MB: bilancia overhead Python (chunk piu` grandi
    = meno cicli) e responsivita` del flush HTTP verso il browser (chunk
    troppo grandi = la barra di progresso del browser scatta a salti).

    La connessione SSH+SFTP viene aperta all'inizio e chiusa solo quando il
    generator si esaurisce o viene garbage-collected. Se il client HTTP
    chiude la connessione a meta` download, il generator si interrompe,
    Python lo GC, e le risorse SFTP vengono rilasciate dal finally.

    Usage in Flask:
        return Response(iter_remote_file(user, sub, name), mimetype=...)
    """
    ssh, sftp = _get_sftp()
    bytes_sent = 0
    t_start = time.monotonic()
    try:
        remote_path = _resolve_remote_path(username, subpath, filename)
        logger.info(f"Stream download START: {remote_path}")
        remote_file = sftp.open(remote_path, 'rb')
        # Suggerisce a paramiko di pipeline-are le richieste di read; con
        # set_pipelined() le read vanno in volo in parallelo invece di
        # serializzate, migliorando di parecchio la throughput.
        try:
            remote_file.set_pipelined(True)
        except Exception:
            pass
        try:
            while True:
                chunk = remote_file.read(chunk_size)
                if not chunk:
                    break
                bytes_sent += len(chunk)
                yield chunk
        finally:
            try:
                remote_file.close()
            except Exception:
                pass
    finally:
        elapsed = time.monotonic() - t_start
        if elapsed > 0 and bytes_sent > 0:
            mb = bytes_sent / 1024 / 1024
            mbps = mb / elapsed
            logger.info(
                f"Stream download END: {mb:.1f} MB in {elapsed:.1f}s "
                f"= {mbps:.2f} MB/s ({mbps*8:.1f} Mbit/s)"
            )
        try:
            sftp.close()
        except Exception:
            pass
        try:
            ssh.close()
        except Exception:
            pass


def delete_file(username, subpath, filename):
    """Elimina un file dalla cartella dell'utente."""
    ssh, sftp = _get_sftp()
    try:
        subpath = _safe_subpath(subpath)
        safe_name = filename.replace('/', '_').replace('\\', '_')
        base = _user_base_path(username)
        target_dir = f"{base}/{subpath}" if subpath else base
        remote_path = f"{target_dir}/{safe_name}"

        sftp.remove(remote_path)
        return True
    except Exception:
        return False
    finally:
        sftp.close()
        ssh.close()


def create_folder(username, subpath, folder_name):
    """Crea una sottocartella nella cartella dell'utente."""
    ssh, sftp = _get_sftp()
    try:
        subpath = _safe_subpath(subpath)
        safe_name = folder_name.replace('/', '_').replace('\\', '_').strip()
        if not safe_name:
            return False
        base = _user_base_path(username)
        target_dir = f"{base}/{subpath}" if subpath else base
        new_folder = f"{target_dir}/{safe_name}"

        _mkdir_recursive(sftp, new_folder)
        return True
    except Exception:
        return False
    finally:
        sftp.close()
        ssh.close()


def rename_item(username, subpath, old_name, new_name):
    """Rinomina un file o una cartella nella cartella dell'utente."""
    ssh, sftp = _get_sftp()
    try:
        subpath = _safe_subpath(subpath)
        safe_old = old_name.replace('/', '_').replace('\\', '_')
        safe_new = new_name.replace('/', '_').replace('\\', '_').strip()
        if not safe_new or safe_old == safe_new:
            return False
        base = _user_base_path(username)
        target_dir = f"{base}/{subpath}" if subpath else base
        old_path = f"{target_dir}/{safe_old}"
        new_path = f"{target_dir}/{safe_new}"

        # Verifica che il nuovo nome non esista già
        try:
            sftp.stat(new_path)
            return False  # Esiste già
        except FileNotFoundError:
            pass

        sftp.rename(old_path, new_path)
        return True
    except Exception:
        return False
    finally:
        sftp.close()
        ssh.close()


def delete_folder(username, subpath, folder_name):
    """Elimina una cartella vuota dalla cartella dell'utente."""
    ssh, sftp = _get_sftp()
    try:
        subpath = _safe_subpath(subpath)
        safe_name = folder_name.replace('/', '_').replace('\\', '_')
        base = _user_base_path(username)
        target_dir = f"{base}/{subpath}" if subpath else base
        folder_path = f"{target_dir}/{safe_name}"

        # Verifica che sia vuota
        contents = sftp.listdir(folder_path)
        if contents:
            return False

        sftp.rmdir(folder_path)
        return True
    except Exception:
        return False
    finally:
        sftp.close()
        ssh.close()


def format_size(size_bytes):
    """Formatta una dimensione in bytes in formato leggibile."""
    if size_bytes == 0:
        return '0 B'
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    if i == 0:
        return f"{int(size)} B"
    return f"{size:.1f} {units[i]}"


def get_file_icon(extension):
    """Restituisce l'icona Bootstrap per un tipo di file."""
    icons = {
        # Immagini
        'jpg': 'bi-file-image', 'jpeg': 'bi-file-image', 'png': 'bi-file-image',
        'gif': 'bi-file-image', 'webp': 'bi-file-image', 'svg': 'bi-file-image',
        'bmp': 'bi-file-image', 'ico': 'bi-file-image', 'tiff': 'bi-file-image',
        # Documenti
        'pdf': 'bi-file-pdf', 'doc': 'bi-file-word', 'docx': 'bi-file-word',
        'xls': 'bi-file-excel', 'xlsx': 'bi-file-excel', 'csv': 'bi-file-excel',
        'ppt': 'bi-file-ppt', 'pptx': 'bi-file-ppt',
        'txt': 'bi-file-text', 'rtf': 'bi-file-text',
        # Archivi
        'zip': 'bi-file-zip', 'rar': 'bi-file-zip', '7z': 'bi-file-zip',
        'tar': 'bi-file-zip', 'gz': 'bi-file-zip',
        # Audio
        'mp3': 'bi-file-music', 'wav': 'bi-file-music', 'flac': 'bi-file-music',
        'aac': 'bi-file-music', 'ogg': 'bi-file-music', 'wma': 'bi-file-music',
        # Video
        'mp4': 'bi-file-play', 'avi': 'bi-file-play', 'mkv': 'bi-file-play',
        'mov': 'bi-file-play', 'wmv': 'bi-file-play', 'flv': 'bi-file-play',
        # Codice
        'html': 'bi-file-code', 'css': 'bi-file-code', 'js': 'bi-file-code',
        'py': 'bi-file-code', 'json': 'bi-file-code', 'xml': 'bi-file-code',
    }
    return icons.get(extension, 'bi-file-earmark')
