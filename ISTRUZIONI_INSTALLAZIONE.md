# Istruzioni Rapide di Installazione

## Step 1: Installazione Dipendenze

```bash
pip install -r requirements.txt
```

## Step 2: Configurazione Database

1. Crea il database MySQL:
```sql
CREATE DATABASE discografica_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. Modifica il file `.env` con le tue credenziali MySQL:
```
DATABASE_URI=mysql+pymysql://root:TUA_PASSWORD@localhost/discografica_db
```

## Step 3: Inizializza Database

```bash
python init_db.py
```

Quando richiesto, scegli 's' per creare dati di esempio.

## Step 4: Avvia l'Applicazione

```bash
python run.py
```

## Step 5: Accedi

Apri il browser e vai su: **http://localhost:6000**

**Credenziali iniziali:**
- Username: `admin`
- Password: `admin123`

⚠ **IMPORTANTE**: Cambia la password dopo il primo accesso!

---

## Risoluzione Problemi Comuni

### Errore "Access denied for user"
→ Verifica le credenziali MySQL in `.env`

### Errore "Unknown database"
→ Assicurati di aver creato il database con il comando CREATE DATABASE

### Porta 6000 già in uso
→ Cambia la porta in run.py: `app.run(port=7000)`

---

## Struttura Permessi

- **Admin**: Accesso completo, gestione utenti
- **Editor**: Crea/modifica contenuti, non gestisce utenti
- **User**: Vede/modifica solo propri contenuti

---

**Per maggiori dettagli consulta il README.md**
