from app import create_app, db
from app.models import Permesso, Ruolo, User

app = create_app()

def init_permissions():
    """Inizializza tutti i permessi disponibili nel sistema"""
    with app.app_context():
        print("Inizializzazione permessi...")

        # Lista di tutti i moduli e azioni
        moduli = [
            'artisti', 'dischi', 'singoli', 'eventi',
            'servizi', 'staff', 'documenti', 'news', 'utenti'
        ]
        azioni = [
            ('create', 'Creazione'),
            ('read', 'Lettura'),
            ('update', 'Modifica'),
            ('delete', 'Eliminazione')
        ]

        permessi_creati = 0

        for modulo in moduli:
            for azione, azione_nome in azioni:
                codice = f"{modulo}.{azione}"

                # Controlla se il permesso esiste già
                permesso_esistente = Permesso.query.filter_by(codice=codice).first()
                if not permesso_esistente:
                    permesso = Permesso(
                        codice=codice,
                        nome=f"{azione_nome} {modulo.capitalize()}",
                        descrizione=f"Permette di {azione_nome.lower()} i {modulo}",
                        modulo=modulo
                    )
                    db.session.add(permesso)
                    permessi_creati += 1
                    print(f"  - Creato permesso: {codice}")

        # Aggiungi permessi speciali per admin
        permessi_speciali = [
            ('ruoli.manage', 'Gestione Ruoli', 'Permette di creare, modificare ed eliminare ruoli', 'sistema'),
            ('permessi.manage', 'Gestione Permessi', 'Permette di assegnare permessi ai ruoli', 'sistema'),
            ('sistema.manage', 'Gestione Sistema', 'Permette di gestire configurazioni di sistema', 'sistema'),
        ]

        for codice, nome, descrizione, modulo in permessi_speciali:
            permesso_esistente = Permesso.query.filter_by(codice=codice).first()
            if not permesso_esistente:
                permesso = Permesso(
                    codice=codice,
                    nome=nome,
                    descrizione=descrizione,
                    modulo=modulo
                )
                db.session.add(permesso)
                permessi_creati += 1
                print(f"  - Creato permesso speciale: {codice}")

        db.session.commit()
        print(f"\nOK - {permessi_creati} permessi creati!")


def init_default_roles():
    """Inizializza i ruoli di default del sistema"""
    with app.app_context():
        print("\nInizializzazione ruoli di sistema...")

        # Ruolo Admin - tutti i permessi
        admin_role = Ruolo.query.filter_by(nome='admin').first()
        if not admin_role:
            admin_role = Ruolo(
                nome='admin',
                descrizione='Amministratore con tutti i permessi',
                is_system=True
            )
            db.session.add(admin_role)
            db.session.commit()

            # Assegna tutti i permessi all'admin
            tutti_permessi = Permesso.query.all()
            admin_role.permessi = tutti_permessi
            db.session.commit()
            print("  - Creato ruolo: admin (con tutti i permessi)")
        else:
            print("  - Ruolo admin già esistente")

        # Ruolo Editor - permessi di lettura, creazione e modifica (no eliminazione)
        editor_role = Ruolo.query.filter_by(nome='editor').first()
        if not editor_role:
            editor_role = Ruolo(
                nome='editor',
                descrizione='Editor con permessi di lettura, creazione e modifica',
                is_system=True
            )
            db.session.add(editor_role)
            db.session.commit()

            # Assegna permessi specifici all'editor
            permessi_editor = Permesso.query.filter(
                db.or_(
                    Permesso.codice.like('%.read'),
                    Permesso.codice.like('%.create'),
                    Permesso.codice.like('%.update')
                )
            ).all()
            editor_role.permessi = permessi_editor
            db.session.commit()
            print("  - Creato ruolo: editor (con permessi read/create/update)")
        else:
            print("  - Ruolo editor già esistente")

        # Ruolo User - solo lettura
        user_role = Ruolo.query.filter_by(nome='user').first()
        if not user_role:
            user_role = Ruolo(
                nome='user',
                descrizione='Utente base con solo permessi di lettura',
                is_system=True
            )
            db.session.add(user_role)
            db.session.commit()

            # Assegna solo permessi di lettura
            permessi_user = Permesso.query.filter(
                Permesso.codice.like('%.read')
            ).all()
            user_role.permessi = permessi_user
            db.session.commit()
            print("  - Creato ruolo: user (con permessi read)")
        else:
            print("  - Ruolo user già esistente")

        print("\nOK - Ruoli di sistema creati!")


def migrate_existing_users():
    """Migra gli utenti esistenti al nuovo sistema di ruoli"""
    with app.app_context():
        print("\nMigrazione utenti esistenti...")

        users = User.query.all()
        migrati = 0

        for user in users:
            if not user.ruolo_id:
                ruolo = Ruolo.query.filter_by(nome=user.ruolo).first()
                if ruolo:
                    user.ruolo_id = ruolo.id
                    migrati += 1
                    print(f"  - Migrato utente {user.username} al ruolo {ruolo.nome}")

        db.session.commit()
        print(f"\nOK - {migrati} utenti migrati!")


if __name__ == '__main__':
    print("=" * 60)
    print("INIZIALIZZAZIONE SISTEMA PERMESSI")
    print("=" * 60)

    # Crea le nuove tabelle se non esistono
    with app.app_context():
        db.create_all()
        print("OK - Tabelle database create/verificate")

    # Inizializza permessi
    init_permissions()

    # Inizializza ruoli di default
    init_default_roles()

    # Migra utenti esistenti
    migrate_existing_users()

    print("\n" + "=" * 60)
    print("INIZIALIZZAZIONE COMPLETATA!")
    print("=" * 60)
    print("\nOra puoi:")
    print("1. Creare nuovi ruoli personalizzati dalla sezione Admin")
    print("2. Assegnare permessi specifici ai ruoli")
    print("3. Assegnare ruoli personalizzati agli utenti")
