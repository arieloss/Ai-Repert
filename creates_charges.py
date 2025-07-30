# create_charges.py
# Script pour créer les charges initiales dans la base de données

from database import SessionLocal, engine
from models import Charge, Base
from sqlalchemy.exc import IntegrityError

# Create database tables if they don't exist
Base.metadata.create_all(bind=engine)

def create_initial_charges():
    db = SessionLocal()
    
    try:
        # Définir les charges correspondant aux capteurs de l'Arduino
        charges_initiales = [
            {"id": 1, "nom": "Charge 1", "type": "Eclairage", "puissance_nominale": 100.0},
            {"id": 2, "nom": "Charge 2", "type": "Electronique", "puissance_nominale": 80.0},
            {"id": 3, "nom": "Charge 3", "type": "Electromenager", "puissance_nominale": 200.0},
            {"id": 4, "nom": "Charge 4", "type": "Autres", "puissance_nominale": 50.0},
            {"id": 5, "nom": "Charge 5", "type": "Reserve", "puissance_nominale": 150.0},
        ]
        
        for charge_data in charges_initiales:
            # Vérifier si la charge existe déjà
            charge_existante = db.query(Charge).filter(Charge.id == charge_data["id"]).first()
            
            if not charge_existante:
                charge = Charge(
                    id=charge_data["id"],
                    nom=charge_data["nom"],
                    type=charge_data["type"],
                    puissance_nominale=charge_data["puissance_nominale"],
                    etat=False  # Initialement éteinte
                )
                db.add(charge)
                print(f"Charge créée: {charge_data['nom']} (ID: {charge_data['id']})")
            else:
                print(f"Charge déjà existante: {charge_existante.nom} (ID: {charge_existante.id})")
        
        db.commit()
        print("✅ Toutes les charges ont été créées avec succès!")
        
        # Afficher toutes les charges
        print("\n📋 Liste des charges dans la base de données:")
        all_charges = db.query(Charge).all()
        for charge in all_charges:
            print(f"  - ID: {charge.id}, Nom: {charge.nom}, Type: {charge.type}, Puissance: {charge.puissance_nominale}W, État: {'ON' if charge.etat else 'OFF'}")
            
    except IntegrityError as e:
        print(f"❌ Erreur d'intégrité: {e}")
        db.rollback()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Création des charges initiales...")
    create_initial_charges()