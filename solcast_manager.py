# solcast_manager.py
import os
import requests
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional
import json
from dataclasses import dataclass
from fastapi import HTTPException
from database import charger_cles_solcast

@dataclass
class PrevisionSolcast:
    """Structure pour les prévisions Solcast"""
    period_start: datetime
    period_end: datetime
    pv_estimate: float  # kWh
    pv_estimate10: float
    pv_estimate90: float
    cloud_opacity: float
    temp: float
    ghi: float
    dhi: float
    dni: float

class GestionnaireSolcast:
    """Gestionnaire intelligent pour l'API Solcast"""
    
    def __init__(self):
        self.api_keys_sites = charger_cles_solcast()
        if not self.api_keys_sites:
            raise ValueError("Aucune clé/site_id Solcast trouvée dans .env (SOLCAST_API_KEY1, SOLCAST_SITE_ID1, ...)")
        self.limite_appels_quotidien = 10 * len(self.api_keys_sites)
        self.appels_aujourd_hui = 0
        self.derniere_mise_a_jour = None
        self.cache_previsions = None
        self.duree_validite_cache = 3600  # 1 heure
        self.api_key_index = 0
    
    def peut_appeler_api(self) -> bool:
        """Vérifie si on peut encore appeler l'API aujourd'hui"""
        aujourd_hui = datetime.now().date()
        
        # Reset du compteur si nouveau jour
        if self.derniere_mise_a_jour and self.derniere_mise_a_jour.date() != aujourd_hui:
            self.appels_aujourd_hui = 0
        
        return self.appels_aujourd_hui < self.limite_appels_quotidien
    
    def get_previsions_demain(self) -> Dict:
        """
        Récupère les prévisions complètes de demain
        Optimise les appels API avec cache intelligent
        """
        # Check cache first
        if self.cache_valide():
            return self.analyser_previsions_cachees()
        
        # Check if we can call the API
        if not self.peut_appeler_api():
            if self.cache_previsions:
                return {
                    "previsions": self.cache_previsions,
                    "source": "cache",
                    "appels_restants": 0,
                    "warning": "Utilisation du cache - limite API atteinte"
                }
            else:
                raise HTTPException(
                    status_code=503, 
                    detail="Limite API atteinte et pas de cache disponible"
                )
        
        # Call API for tomorrow
        try:
            previsions = self._appel_api_demain()
            self._mettre_a_jour_cache(previsions)
            self.appels_aujourd_hui += 1
            
            return {
                "previsions": previsions,
                "source": "api",
                "appels_restants": self.limite_appels_quotidien - self.appels_aujourd_hui,
                "analyse": self.analyser_previsions(previsions)
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur API Solcast: {str(e)}")
    
    def _appel_api_demain(self) -> List[Dict]:
        """Appel API pour les prévisions de demain avec rotation clé/site_id si quota ou 404"""
        demain = datetime.now().date() + timedelta(days=1)
        for i in range(len(self.api_keys_sites)):
            api_key, site_id = self.api_keys_sites[self.api_key_index]
            url = f"https://api.solcast.com.au/rooftop_sites/{site_id}/forecasts"
            params = {
                "format": "json",
                "api_key": api_key,
                "start": f"{demain}T00:00:00Z",
                "end": f"{demain}T23:59:59Z"
            }
            try:
                response = requests.get(url, params=params)
                if response.status_code in (429, 404):
                    # Quota reached or site not found, try next key
                    self.api_key_index = (self.api_key_index + 1) % len(self.api_keys_sites)
                    continue
                response.raise_for_status()
                data = response.json()
                return data.get("forecasts", [])
            except requests.HTTPError as e:
                if response.status_code in (429, 404):
                    self.api_key_index = (self.api_key_index + 1) % len(self.api_keys_sites)
                    continue
                else:
                    raise
        raise HTTPException(status_code=429, detail="Toutes les clés API Solcast ont atteint leur quota journalier ou aucun site_id valide.")
    
    def cache_valide(self) -> bool:
        """Vérifie si le cache est encore valide"""
        if not self.cache_previsions or not self.derniere_mise_a_jour:
            return False
        
        age_cache = (datetime.now() - self.derniere_mise_a_jour).seconds
        return age_cache < self.duree_validite_cache
    
    def _mettre_a_jour_cache(self, previsions: List[Dict]):
        """Met à jour le cache avec les nouvelles prévisions"""
        self.cache_previsions = previsions
        self.derniere_mise_a_jour = datetime.now()
    
    def analyser_previsions(self, previsions: List[Dict]) -> Dict:
        """Analyse approfondie des prévisions Solcast"""
        if not previsions or len(previsions) == 0:
            raise HTTPException(status_code=500, detail=f"Prévisions IA invalides ou vides. Réponse brute: {previsions}")
        
        # Calculate key metrics
        production_totale = sum(p.get("pv_estimate", 0) for p in previsions)
        production_max = max(p.get("pv_estimate", 0) for p in previsions)
        production_min = min(p.get("pv_estimate", 0) for p in previsions)
        
        # Analyze by periods
        heures_pointe = [p for p in previsions if p.get("pv_estimate", 0) > 2.0]  # > 2 kWh/30min
        heures_faible = [p for p in previsions if p.get("pv_estimate", 0) < 0.5]  # < 0.5 kWh/30min
        heures_normales = [p for p in previsions if 0.5 <= p.get("pv_estimate", 0) <= 2.0]
        
        # Calculate variability
        productions = [p.get("pv_estimate", 0) for p in previsions]
        variabilite = (max(productions) - min(productions)) / max(productions) if max(productions) > 0 else 0
        
        # Analyze clouds
        opacite_moyenne = sum(p.get("cloud_opacity", 0) for p in previsions) / len(previsions)
        
        # Identify critical periods
        periode_debut = datetime.fromisoformat(previsions[0]["period_end"].replace("Z", "+00:00"))
        periode_fin = datetime.fromisoformat(previsions[-1]["period_end"].replace("Z", "+00:00"))
        
        return {
            "periode": {
                "debut": periode_debut.isoformat(),
                "fin": periode_fin.isoformat(),
                "duree_heures": (periode_fin - periode_debut).total_seconds() / 3600
            },
            "production": {
                "totale_kwh": production_totale,
                "moyenne_kwh_par_30min": production_totale / len(previsions),
                "max_kwh_par_30min": production_max,
                "min_kwh_par_30min": production_min,
                "variabilite": variabilite
            },
            "repartition": {
                "heures_pointe": len(heures_pointe),
                "heures_normales": len(heures_normales),
                "heures_faible": len(heures_faible)
            },
            "meteo": {
                "opacite_nuages_moyenne": opacite_moyenne,
                "qualite_ensoleillement": "excellent" if opacite_moyenne < 0.3 else "bon" if opacite_moyenne < 0.6 else "mauvais"
            },
            "risque": self._calculer_niveau_risque(production_totale, variabilite, len(heures_faible)),
            "recommandations": self._generer_recommandations(production_totale, variabilite, heures_faible)
        }
    
    def _calculer_niveau_risque(self, production_totale: float, variabilite: float, heures_faible: int) -> str:
        """Calcule le niveau de risque selon les prévisions"""
        if production_totale < 10:  # Very low production
            return "CRITIQUE"
        elif production_totale < 20 or heures_faible > 12:
            return "ELEVE"
        elif production_totale < 30 or variabilite > 0.7:
            return "MODERE"
        else:
            return "FAIBLE"
    
    def _generer_recommandations(self, production_totale: float, variabilite: float, heures_faible: List) -> List[str]:
        """Génère des recommandations basées sur l'analyse"""
        recommandations = []
        
        if production_totale < 15:
            recommandations.append("Charger la batterie à 100% aujourd'hui")
            recommandations.append("Préparer le basculement sur réseau")
        
        if len(heures_faible) > 8:
            recommandations.append(f"Prévoir {len(heures_faible)}h de faible production")
            recommandations.append("Optimiser la charge de la batterie")
        
        if variabilite > 0.8:
            recommandations.append("Production très variable - surveillance renforcée")
        
        if production_totale > 40:
            recommandations.append("Production excellente - optimisation maximale possible")
        
        return recommandations
    
    def analyser_previsions_cachees(self) -> Dict:
        """Analyse les prévisions du cache"""
        if not self.cache_previsions:
            return {"erreur": "Pas de cache disponible"}
        
        return {
            "previsions": self.cache_previsions,
            "source": "cache",
            "age_cache_minutes": int((datetime.now() - self.derniere_mise_a_jour).seconds / 60),
            "analyse": self.analyser_previsions(self.cache_previsions)
        }
    
    def get_statistiques_utilisation(self) -> Dict:
        """Retourne les statistiques d'utilisation de l'API"""
        return {
            "appels_aujourd_hui": self.appels_aujourd_hui,
            "limite_quotidien": self.limite_appels_quotidien,
            "appels_restants": self.limite_appels_quotidien - self.appels_aujourd_hui,
            "derniere_mise_a_jour": self.derniere_mise_a_jour.isoformat() if self.derniere_mise_a_jour else None,
            "cache_valide": self.cache_valide()
        }