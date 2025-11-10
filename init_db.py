#!/usr/bin/env python
"""
Script per inizializzare il database e creare un utente admin
"""

from app import create_app, db
from app.models import User
import sys

def init_database():
    """Inizializza il database e crea le tabelle"""
    app = create_app()

    with app.app_context():
        print("Creazione delle tabelle del database...")
        db.create_all()
        print("Tabelle create con successo!")

        # Verifica se esiste già un admin
        admin_exists = User.query.filter_by(username='admin').first()

        if not admin_exists:
            print("\nCreazione utente amministratore...")
            admin = User(
                username='admin',
                email='admin@discografica.com',
                ruolo='admin',
                attivo=True
            )
            admin.set_password('admin123')  # CAMBIARE IN PRODUZIONE!

            db.session.add(admin)
            db.session.commit()

            print("✓ Utente admin creato con successo!")
            print("\nCredenziali admin:")
            print("  Username: admin")
            print("  Password: admin123")
            print("\n⚠ IMPORTANTE: Cambia la password dopo il primo accesso!")
        else:
            print("\n✓ Utente admin già esistente.")

        # Crea alcuni dati di esempio
        create_sample_data = input("\nVuoi creare dati di esempio? (s/n): ").lower()

        if create_sample_data == 's':
            from app.models import Servizio
            from datetime import datetime

            # Crea servizi di esempio
            servizi = [
                {
                    'nome': 'Produzione Musicale',
                    'descrizione': 'Servizio completo di produzione musicale professionale',
                    'categoria': 'Produzione',
                    'prezzo': 1500.00,
                    'valuta': 'EUR',
                    'durata': '2-4 settimane',
                    'icona': 'music',
                    'attivo': True
                },
                {
                    'nome': 'Distribuzione Digitale',
                    'descrizione': 'Distribuzione su tutte le piattaforme digitali principali',
                    'categoria': 'Distribuzione',
                    'prezzo': 299.00,
                    'valuta': 'EUR',
                    'durata': '1 anno',
                    'icona': 'disc',
                    'attivo': True
                },
                {
                    'nome': 'Marketing & Promozione',
                    'descrizione': 'Campagna marketing completa sui social media',
                    'categoria': 'Marketing',
                    'prezzo': 800.00,
                    'valuta': 'EUR',
                    'durata': '1 mese',
                    'icona': 'speaker',
                    'attivo': True
                }
            ]

            for s in servizi:
                if not Servizio.query.filter_by(nome=s['nome']).first():
                    servizio = Servizio(**s)
                    db.session.add(servizio)

            db.session.commit()
            print("✓ Dati di esempio creati!")

        print("\n" + "="*50)
        print("Database inizializzato con successo!")
        print("="*50)
        print("\nPuoi ora avviare l'applicazione con:")
        print("  python run.py")
        print("\nL'app sarà disponibile su:")
        print("  http://localhost:6000")
        print("="*50)

if __name__ == '__main__':
    try:
        init_database()
    except Exception as e:
        print(f"\n❌ Errore durante l'inizializzazione: {e}")
        print("\nAssicurati che:")
        print("1. MySQL sia in esecuzione")
        print("2. Il database 'discografica_db' sia stato creato")
        print("3. Le credenziali in .env siano corrette")
        sys.exit(1)
