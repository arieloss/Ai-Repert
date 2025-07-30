# api.py
from fastapi import FastAPI, HTTPException, Depends, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, time, timedelta
import requests
import os
from gtts import gTTS
import io
from pydantic import BaseModel
from typing import List

from database import SessionLocal, engine, get_db, Base
from models import Charge, Consommation, Production, Batterie, Calendrier, Decision, Utilisateur
from optimiseur_robuste import OptimiseurRobuste
from solcast_manager import GestionnaireSolcast

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Repert API", description="API pour le système de relais intelligent")

# Initialize robust optimizer
optimiseur_robuste = OptimiseurRobuste()


class ConsommationData(BaseModel):
    charge_id: int
    consommation: float

class MesuresData(BaseModel):
    production: float
    soc_batterie: float
    tension_batterie: float
    courant_batterie: float
    consommations: List[ConsommationData]

# Endpoints for charges
@app.get("/charges/", response_model=List[dict])
def get_charges(db: Session = Depends(get_db)):
    """Récupérer toutes les charges"""
    charges = db.query(Charge).all()
    return [{"id": c.id, "nom": c.nom, "type": c.type, "puissance_nominale": c.puissance_nominale, "etat": c.etat} for c in charges]

@app.post("/charges/")
def create_charge(nom: str, type: str, puissance_nominale: float, db: Session = Depends(get_db)):
    """Créer une nouvelle charge"""
    charge = Charge(nom=nom, type=type, puissance_nominale=puissance_nominale)
    db.add(charge)
    db.commit()
    db.refresh(charge)
    return {"id": charge.id, "nom": charge.nom, "type": charge.type}

@app.put("/charges/{charge_id}/etat")
def update_charge_state(charge_id: int, etat: bool, db: Session = Depends(get_db)):
    """Modifier l'état d'une charge (ON/OFF)"""
    charge = db.query(Charge).filter(Charge.id == charge_id).first()
    if not charge:
        raise HTTPException(status_code=404, detail="Charge non trouvée")
    charge.etat = etat
    db.commit()
    return {"id": charge.id, "etat": charge.etat}

# Endpoints for measurements (Arduino)
@app.post("/mesures")
@app.post("/mesures/")
def receive_measurements(data: MesuresData, db: Session = Depends(get_db)):
    """Recevoir les mesures d'Arduino"""
    # Save production
    prod = Production(production=data.production, timestamp=datetime.now())
    db.add(prod)
    
    # Save battery state
    bat = Batterie(
        soc=data.soc_batterie, 
        tension=data.tension_batterie, 
        courant=data.courant_batterie, 
        timestamp=datetime.now()
    )
    db.add(bat)
    
    # Save consumptions
    for cons in data.consommations:
        conso = Consommation(
            id_charge=cons.charge_id,
            consommation=cons.consommation,
            timestamp=datetime.now()
        )
        db.add(conso)
    
    db.commit()
    return {"message": "Mesures enregistrées", "status": "success"}

@app.get("/commandes/")
def get_commands(db: Session = Depends(get_db)):
    """Récupérer les commandes pour Arduino (optimisation robuste)"""
    # Get current context
    derniere_production = db.query(Production).order_by(Production.timestamp.desc()).first()
    derniere_batterie = db.query(Batterie).order_by(Batterie.timestamp.desc()).first()
    
    contexte = {
        "production_actuelle": derniere_production.production if derniere_production else 0,
        "soc_batterie": derniere_batterie.soc if derniere_batterie else 0,
        "evenement_special": False  # To be implemented with calendar
    }
    
    # Run robust optimization
    resultat = optimiseur_robuste.optimiser_complet(db, contexte)
    
    return {
        "charges": resultat["decisions"],
        "strategie": resultat["strategie"]["nom"],
        "score": resultat["strategie"]["score"],
        "alerte": resultat["alerte_vocale"],
        "timestamp": datetime.now().isoformat()
    }

# Endpoints for dashboard
@app.get("/dashboard/")
def get_dashboard_data(db: Session = Depends(get_db)):
    """Données pour le tableau de bord"""
    # Latest production
    derniere_production = db.query(Production).order_by(Production.timestamp.desc()).first()
    
    # Latest battery state
    derniere_batterie = db.query(Batterie).order_by(Batterie.timestamp.desc()).first()
    
    # Current charges
    charges = db.query(Charge).all()
    
    return {
        "production_actuelle": derniere_production.production if derniere_production else 0,
        "soc_batterie": derniere_batterie.soc if derniere_batterie else 0,
        "charges": [{"id": c.id, "nom": c.nom, "type": c.type, "etat": c.etat} for c in charges]
    }

# Endpoint for weather forecast (Solcast) - Enhanced version
@app.get("/meteo/")
def get_weather_forecast():
    solcast_manager = GestionnaireSolcast()
    return solcast_manager.get_previsions_demain()

# New endpoint for robust optimization
@app.post("/optimisation_robuste/")
def optimisation_robuste(db: Session = Depends(get_db)):
    """Lancer l'optimisation robuste complète"""
    # Get current context
    derniere_production = db.query(Production).order_by(Production.timestamp.desc()).first()
    derniere_batterie = db.query(Batterie).order_by(Batterie.timestamp.desc()).first()
    
    contexte = {
        "production_actuelle": derniere_production.production if derniere_production else 0,
        "soc_batterie": derniere_batterie.soc if derniere_batterie else 0,
        "evenement_special": False
    }
    
    # Run robust optimization
    resultat = optimiseur_robuste.optimiser_complet(db, contexte)
    
    return resultat

# Endpoint for Solcast statistics
@app.get("/statistiques_solcast/")
def get_solcast_statistics():
    """Récupérer les statistiques d'utilisation de l'API Solcast"""
    return optimiseur_robuste.get_statistiques_solcast()

# Endpoint for voice alerts
@app.get("/alerte_vocale/")
def generate_voice_alert(message: str, langue: str = "fr"):
    """Générer une alerte vocale"""
    try:
        tts = gTTS(text=message, lang=langue)
        # For now, just return the message
        # Later, we can save the audio file
        return {"message": message, "langue": langue, "status": "generated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur TTS: {str(e)}")

# Endpoints for calendar
@app.post("/calendrier/")
def add_calendar_event(
    charge_id: int,
    date_event: date,
    heure_debut: time,
    heure_fin: time,
    priorite_temporaire: str,
    db: Session = Depends(get_db)
):
    """Ajouter un événement au calendrier"""
    event = Calendrier(
        id_charge=charge_id,
        date=date_event,
        heure_debut=heure_debut,
        heure_fin=heure_fin,
        priorite_temporaire=priorite_temporaire
    )
    db.add(event)
    db.commit()
    return {"message": "Événement ajouté"}

@app.get("/calendrier/")
def get_calendar_events(db: Session = Depends(get_db)):
    """Récupérer les événements du calendrier"""
    events = db.query(Calendrier).all()
    return [{
        "id": e.id,
        "charge_id": e.id_charge,
        "date": e.date.isoformat(),
        "heure_debut": e.heure_debut.isoformat(),
        "heure_fin": e.heure_fin.isoformat(),
        "priorite_temporaire": e.priorite_temporaire
    } for e in events]

# Endpoint for trend analysis
@app.get("/tendances/")
def analyser_tendances(db: Session = Depends(get_db)):
    """Analyser les tendances de consommation et production"""
    # Last 24 hours of data
    maintenant = datetime.now()
    hier = maintenant.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Production in the last 24 hours
    productions = db.query(Production).filter(
        Production.timestamp >= hier
    ).all()
    
    # Consumptions in the last 24 hours
    consommations = db.query(Consommation).filter(
        Consommation.timestamp >= hier
    ).all()
    
    # Calculate averages
    prod_moyenne = sum(p.production for p in productions) / len(productions) if productions else 0
    conso_moyenne = sum(c.consommation for c in consommations) / len(consommations) if consommations else 0
    
    return {
        "production_moyenne_24h": prod_moyenne,
        "consommation_moyenne_24h": conso_moyenne,
        "efficacite": (prod_moyenne / conso_moyenne * 100) if conso_moyenne > 0 else 0,
        "nombre_mesures_production": len(productions),
        "nombre_mesures_consommation": len(consommations)
    }

@app.post("/forcer_charges/")
def forcer_charges(
    charges_forcées: List[int] = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Permet à l'utilisateur de forcer l'activation/coupure de charges.
    Retourne une alerte si l'énergie disponible ne suffira pas.
    """
    solcast_manager = GestionnaireSolcast()
    previsions = solcast_manager.get_previsions_demain()
    production_totale = sum(p["pv_estimate"] for p in previsions["previsions"])
    derniere_batterie = db.query(Batterie).order_by(Batterie.timestamp.desc()).first()
    soc_batterie = derniere_batterie.soc if derniere_batterie else 0
    capacite_batterie = 10  # kWh, adjust according to the actual system

    # Calculate total consumption of forced charges
    charges = db.query(Charge).filter(Charge.id.in_(charges_forcées)).all()
    consommation_forcée = sum(c.puissance_nominale for c in charges) * 24  # over 24h

    # Check feasibility
    energie_disponible = production_totale + soc_batterie * capacite_batterie / 100
    if consommation_forcée > energie_disponible:
        alerte = "Attention, l'énergie disponible ne suffira pas à couvrir toutes les charges forcées."
    else:
        alerte = "OK, les charges forcées pourront être couvertes."

    # Apply commands (ON/OFF) to Arduino (to be implemented)
    return {
        "resultat": alerte,
        "energie_disponible": energie_disponible,
        "consommation_forcée": consommation_forcée,
        "charges_forcées": [c.nom for c in charges]
    }

@app.post("/forcer_prevision/")
def forcer_prevision():
    """
    Force la mise à jour de la prévision IA si le quota le permet.
    """
    solcast_manager = GestionnaireSolcast()
    if solcast_manager.peut_appeler_api():
        previsions = solcast_manager._appel_api_demain()
        solcast_manager._mettre_a_jour_cache(previsions)
        solcast_manager.appels_aujourd_hui += 1
        return {"message": "Prévision mise à jour", "appels_restants": solcast_manager.limite_appels_quotidien - solcast_manager.appels_aujourd_hui}
    else:
        return {"message": "Quota d'appels atteint, prévision non rafraîchie", "appels_restants": 0}

@app.post("/anticipation_batterie/")
def anticipation_batterie(
    charge_ids: List[int] = Body(..., embed=True),
    periode_h: float = Body(6, embed=True),  # Duration to cover in hours (default 6h)
    db: Session = Depends(get_db)
):
    """
    Calcule la durée de tenue de la batterie pour les charges sélectionnées.
    Affiche la durée max possible et l'alerte si la batterie ne tiendra pas.
    """
    # Get battery capacity and current SOC
    capacite_batterie = 10_000  # Wh (10 kWh, adjust according to the actual system)
    derniere_batterie = db.query(Batterie).order_by(Batterie.timestamp.desc()).first()
    soc_batterie = derniere_batterie.soc if derniere_batterie else 0
    energie_disponible = capacite_batterie * soc_batterie / 100

    # Get selected charges
    charges = db.query(Charge).filter(Charge.id.in_(charge_ids)).all()
    puissance_totale = sum(c.puissance_nominale for c in charges)  # in W
    consommation_totale = puissance_totale * periode_h  # in Wh

    # Calculate maximum duration
    if puissance_totale > 0:
        duree_max = energie_disponible / puissance_totale  # in hours
    else:
        duree_max = 0

    # Generate alert
    if consommation_totale > energie_disponible:
        alerte = f"Attention, la batterie ne pourra alimenter ces charges que pendant {duree_max:.2f}h."
    else:
        alerte = f"OK, la batterie pourra alimenter ces charges pendant {periode_h}h."

    return {
        "charges_selectionnees": [c.nom for c in charges],
        "puissance_totale_W": puissance_totale,
        "energie_disponible_Wh": energie_disponible,
        "consommation_totale_Wh": consommation_totale,
        "duree_max_h": round(duree_max, 2),
        "periode_a_couvrir_h": periode_h,
        "alerte": alerte
    }

@app.get("/mesures/dernieres/")
def get_latest_measurements(limit: int = 10, db: Session = Depends(get_db)):
    """Récupérer les dernières mesures reçues"""
    # Latest productions
    productions = db.query(Production).order_by(Production.timestamp.desc()).limit(limit).all()
    
    # Latest battery states
    batteries = db.query(Batterie).order_by(Batterie.timestamp.desc()).limit(limit).all()
    
    # Latest consumptions
    consommations = db.query(Consommation).order_by(Consommation.timestamp.desc()).limit(limit).all()
    
    return {
        "productions": [{
            "id": p.id,
            "production": p.production,
            "timestamp": p.timestamp.isoformat()
        } for p in productions],
        "batteries": [{
            "id": b.id,
            "soc": b.soc,
            "tension": b.tension,
            "courant": b.courant,
            "timestamp": b.timestamp.isoformat()
        } for b in batteries],
        "consommations": [{
            "id": c.id,
            "charge_id": c.id_charge,
            "consommation": c.consommation,
            "timestamp": c.timestamp.isoformat()
        } for c in consommations]
    }

@app.get("/mesures/temps_reel/")
def get_realtime_measurements(db: Session = Depends(get_db)):
    """Récupérer les mesures des 60 dernières secondes"""
    maintenant = datetime.now()
    il_y_a_une_minute = maintenant - timedelta(minutes=1)
    
    # Productions in the last minute
    productions = db.query(Production).filter(
        Production.timestamp >= il_y_a_une_minute
    ).order_by(Production.timestamp.desc()).all()
    
    # Battery states in the last minute
    batteries = db.query(Batterie).filter(
        Batterie.timestamp >= il_y_a_une_minute
    ).order_by(Batterie.timestamp.desc()).all()
    
    # Consumptions in the last minute by charge
    consommations = db.query(Consommation).filter(
        Consommation.timestamp >= il_y_a_une_minute
    ).order_by(Consommation.timestamp.desc()).all()
    
    # Group consumptions by charge
    consommations_par_charge = {}
    for c in consommations:
        if c.id_charge not in consommations_par_charge:
            consommations_par_charge[c.id_charge] = []
        consommations_par_charge[c.id_charge].append({
            "consommation": c.consommation,
            "timestamp": c.timestamp.isoformat()
        })
    
    return {
        "periode": "60 dernières secondes",
        "production_actuelle": productions[0].production if productions else 0,
        "batterie_actuelle": {
            "soc": batteries[0].soc if batteries else 0,
            "tension": batteries[0].tension if batteries else 0,
            "courant": batteries[0].courant if batteries else 0
        },
        "consommations_par_charge": consommations_par_charge,
        "total_mesures": {
            "productions": len(productions),
            "batteries": len(batteries),
            "consommations": len(consommations)
        }
    }

@app.get("/mesures/charge/{charge_id}/")
def get_charge_history(charge_id: int, heures: int = 24, db: Session = Depends(get_db)):
    """Récupérer l'historique de consommation d'une charge"""
    maintenant = datetime.now()
    debut_periode = maintenant - timedelta(hours=heures)
    
    consommations = db.query(Consommation).filter(
        Consommation.id_charge == charge_id,
        Consommation.timestamp >= debut_periode
    ).order_by(Consommation.timestamp.desc()).all()
    
    # Statistics
    if consommations:
        consommations_values = [c.consommation for c in consommations]
        moyenne = sum(consommations_values) / len(consommations_values)
        maximum = max(consommations_values)
        minimum = min(consommations_values)
        total_energie = sum(consommations_values) * (5 / 3600)  # Wh (measurements every 5s)
    else:
        moyenne = maximum = minimum = total_energie = 0
    
    return {
        "charge_id": charge_id,
        "periode_heures": heures,
        "statistiques": {
            "moyenne_watts": round(moyenne, 2),
            "maximum_watts": maximum,
            "minimum_watts": minimum,
            "energie_totale_wh": round(total_energie, 2),
            "nombre_mesures": len(consommations)
        },
        "historique": [{
            "consommation": c.consommation,
            "timestamp": c.timestamp.isoformat()
        } for c in consommations[:100]]  # Limit to 100 measurements for display
    }