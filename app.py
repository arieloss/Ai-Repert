from fastapi import FastAPI, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from api import app as api_routes
from database import Base, engine, SessionLocal
from models import Charge
from sqlalchemy.orm import Session
from fastapi import Request
from models import Charge, Consommation, Production, Batterie, Calendrier, Decision, Utilisateur



app = FastAPI()

# Mount the API routes
app.mount("/api", api_routes)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure templates
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def create_initial_charges():
    """Create initial charges in the database on application startup"""
    db = SessionLocal()
    try:
        # Define initial charges
        charges_initiales = [
            {"id": 1, "nom": "Charge 1", "type": "Eclairage", "puissance_nominale": 100.0},
            {"id": 2, "nom": "Charge 2", "type": "Electronique", "puissance_nominale": 80.0},
            {"id": 3, "nom": "Charge 3", "type": "Electromenager", "puissance_nominale": 200.0},
            {"id": 4, "nom": "Charge 4", "type": "Autres", "puissance_nominale": 50.0},
            {"id": 5, "nom": "Charge 5", "type": "Reserve", "puissance_nominale": 150.0},
        ]
        
        for charge_data in charges_initiales:
            # Check if charge already exists
            charge_existante = db.query(Charge).filter(Charge.id == charge_data["id"]).first()
            
            if not charge_existante:
                charge = Charge(
                    id=charge_data["id"],
                    nom=charge_data["nom"],
                    type=charge_data["type"],
                    puissance_nominale=charge_data["puissance_nominale"],
                    etat=False
                )
                db.add(charge)
        db.commit()
    except Exception as e:
        print(f"Error creating initial charges: {e}")
        db.rollback()
    finally:
        db.close()

# Create database tables
Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root(request: Request, db: Session = Depends(get_db)):
    """Render the dashboard"""
    # Get dashboard data
    derniere_production = db.query(Production).order_by(Production.timestamp.desc()).first()
    derniere_batterie = db.query(Batterie).order_by(Batterie.timestamp.desc()).first()
    charges = db.query(Charge).all()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "production_actuelle": derniere_production.production if derniere_production else 0,
        "soc_batterie": derniere_batterie.soc if derniere_batterie else 0,
        "charges": [{"id": c.id, "nom": c.nom, "type": c.type, "etat": c.etat} for c in charges]
    })

@app.get("/charges")
def manage_charges(request: Request, db: Session = Depends(get_db)):
    """Render the charge management page"""
    charges = db.query(Charge).all()
    return templates.TemplateResponse("charges.html", {
        "request": request,
        "charges": [{"id": c.id, "nom": c.nom, "type": c.type, "puissance_nominale": c.puissance_nominale, "etat": c.etat} for c in charges]
    })