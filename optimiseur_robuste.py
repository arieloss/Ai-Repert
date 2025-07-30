from datetime import datetime, time, timedelta
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from models import Charge, Consommation, Production, Batterie, Calendrier, Decision
from solcast_manager import GestionnaireSolcast
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimiseurRobuste:
    """Optimiseur énergétique robuste avec prévisions Solcast"""
    
    def __init__(self):
        self.seuils = {
            "production_faible": 1000,    # W
            "production_forte": 3000,     # W
            "batterie_critique": 20,      # %
            "batterie_optimale": 80,      # %
            "batterie_securite": 10       # %
        }
        
        # Initialiser le gestionnaire Solcast
        try:
            self.solcast_manager = GestionnaireSolcast()
        except Exception as e:
            logger.error(f"Erreur initialisation Solcast: {e}")
            self.solcast_manager = None
    
    def optimiser_complet(self, db: Session, contexte_actuel: Dict) -> Dict:
        """
        Optimisation complète avec prévisions et contexte actuel
        """
        try:
            # 1. Récupérer les prévisions Solcast
            previsions_data = self._recuperer_previsions()
            
            # 2. Analyser le contexte actuel
            analyse_contexte = self._analyser_contexte_actuel(contexte_actuel)
            
            # 3. Analyser les prévisions
            analyse_previsions = previsions_data.get("analyse", {})
            
            # 4. Calculer la stratégie optimale
            strategie = self._calculer_strategie_optimale(
                contexte_actuel, 
                analyse_contexte, 
                analyse_previsions
            )
            
            # 5. Prendre les décisions
            decisions = self._prendre_decisions(db, strategie)
            
            # 6. Générer l'alerte vocale
            alerte = self._generer_alerte_avancee(strategie, decisions)
            
            # 7. Enregistrer la décision
            self._enregistrer_decision(db, strategie, decisions)
            
            return {
                "strategie": strategie,
                "decisions": decisions,
                "alerte_vocale": alerte,
                "contexte": contexte_actuel,
                "analyse_previsions": analyse_previsions,
                "timestamp": datetime.now().isoformat(),
                "source_previsions": previsions_data.get("source", "inconnue"),
                "appels_restants": previsions_data.get("appels_restants", "inconnu")
            }
            
        except Exception as e:
            logger.error(f"Erreur optimisation: {e}")
            return self._optimisation_fallback(db, contexte_actuel)
    
    def _recuperer_previsions(self) -> Dict:
        """Récupère les prévisions Solcast"""
        if not self.solcast_manager:
            return {"analyse": {}, "source": "erreur"}
        
        try:
            return self.solcast_manager.get_previsions_demain()
        except Exception as e:
            logger.error(f"Erreur récupération prévisions: {e}")
            return {"analyse": {}, "source": "erreur"}
    
    def _analyser_contexte_actuel(self, contexte: Dict) -> Dict:
        """Analyse approfondie du contexte actuel"""
        production_actuelle = contexte.get("production_actuelle", 0)
        soc_batterie = contexte.get("soc_batterie", 0)
        heure_actuelle = datetime.now().time()
        
        # Analyser la production
        niveau_production = "forte" if production_actuelle > self.seuils["production_forte"] else \
                           "faible" if production_actuelle < self.seuils["production_faible"] else "moyenne"
        
        # Analyser la batterie
        niveau_batterie = "critique" if soc_batterie < self.seuils["batterie_critique"] else \
                         "optimale" if soc_batterie > self.seuils["batterie_optimale"] else "normale"
        
        # Analyser l'heure
        periode_journee = "jour" if time(6, 0) <= heure_actuelle <= time(18, 0) else "nuit"
        
        return {
            "niveau_production": niveau_production,
            "niveau_batterie": niveau_batterie,
            "periode_journee": periode_journee,
            "heure_actuelle": heure_actuelle.isoformat(),
            "production_w": production_actuelle,
            "soc_pourcentage": soc_batterie
        }
    
    def _calculer_strategie_optimale(self, contexte: Dict, analyse_contexte: Dict, analyse_previsions: Dict) -> Dict:
        """Calcule la stratégie optimale basée sur tous les facteurs"""
        
        # Facteurs de base
        niveau_production = analyse_contexte["niveau_production"]
        niveau_batterie = analyse_contexte["niveau_batterie"]
        periode_journee = analyse_contexte["periode_journee"]
        
        # Facteurs de prévisions
        risque_previsions = analyse_previsions.get("risque", "INCONNU")
        production_demain = analyse_previsions.get("production", {}).get("totale_kwh", 0)
        
        # Calculer le score de stratégie
        score_strategie = self._calculer_score_strategie(
            niveau_production, niveau_batterie, periode_journee, 
            risque_previsions, production_demain
        )
        
        # Déterminer la stratégie
        if score_strategie > 80:
            strategie = "OPTIMISATION_MAXIMALE"
        elif score_strategie > 60:
            strategie = "OPTIMISATION_NORMALE"
        elif score_strategie > 40:
            strategie = "ECONOMIE"
        else:
            strategie = "PRESERVATION"
        
        return {
            "nom": strategie,
            "score": score_strategie,
            "facteurs": {
                "production_actuelle": niveau_production,
                "batterie": niveau_batterie,
                "periode": periode_journee,
                "risque_previsions": risque_previsions,
                "production_demain_kwh": production_demain
            },
            "priorites": self._determiner_priorites(strategie, analyse_contexte, analyse_previsions)
        }
    
    def _calculer_score_strategie(self, niveau_production: str, niveau_batterie: str, 
                                 periode_journee: str, risque_previsions: str, production_demain: float) -> float:
        """Calcule un score pour la stratégie (0-100)"""
        score = 50  # Score de base
        
        # Facteur production actuelle
        if niveau_production == "forte":
            score += 25
        elif niveau_production == "faible":
            score -= 25
        
        # Facteur batterie
        if niveau_batterie == "optimale":
            score += 15
        elif niveau_batterie == "critique":
            score -= 30
        
        # Facteur période
        if periode_journee == "jour":
            score += 10
        else:
            score -= 10
        
        # Facteur prévisions
        if risque_previsions == "FAIBLE":
            score += 20
        elif risque_previsions == "CRITIQUE":
            score -= 40
        elif risque_previsions == "ELEVE":
            score -= 20
        
        # Facteur production demain
        if production_demain > 30:
            score += 15
        elif production_demain < 10:
            score -= 30
        
        return max(0, min(100, score))
    
    def _determiner_priorites(self, strategie: str, analyse_contexte: Dict, analyse_previsions: Dict) -> Dict:
        """Détermine les priorités selon la stratégie"""
        
        if strategie == "OPTIMISATION_MAXIMALE":
            return {
                "charges_prioritaires": "solaire",
                "charges_semi": "solaire",
                "charges_non_prioritaires": "solaire",
                "charge_batterie": "maximale",
                "mode": "optimisation"
            }
        elif strategie == "OPTIMISATION_NORMALE":
            return {
                "charges_prioritaires": "solaire",
                "charges_semi": "solaire",
                "charges_non_prioritaires": "batterie",
                "charge_batterie": "normale",
                "mode": "equilibre"
            }
        elif strategie == "ECONOMIE":
            return {
                "charges_prioritaires": "batterie",
                "charges_semi": "reseau",
                "charges_non_prioritaires": "couper",
                "charge_batterie": "normale",
                "mode": "economie"
            }
        else:  # PRESERVATION
            return {
                "charges_prioritaires": "reseau",
                "charges_semi": "couper",
                "charges_non_prioritaires": "couper",
                "charge_batterie": "maximale",
                "mode": "preservation"
            }
    
    def _prendre_decisions(self, db: Session, strategie: Dict) -> List[Dict]:
        """Prend les décisions concrètes pour chaque charge"""
        charges = db.query(Charge).all()
        decisions = []
        
        priorites = strategie["priorites"]
        
        for charge in charges:
            if charge.type == "prioritaire":
                action = priorites["charges_prioritaires"]
            elif charge.type == "semi-prioritaire":
                action = priorites["charges_semi"]
            else:  # non-prioritaire
                action = priorites["charges_non_prioritaires"]
            
            decisions.append({
                "charge_id": charge.id,
                "nom": charge.nom,
                "type": charge.type,
                "action": action,
                "raison": f"Stratégie {strategie['nom']} - {action}",
                "puissance_nominale": charge.puissance_nominale
            })
        
        return decisions
    
    def _generer_alerte_avancee(self, strategie: Dict, decisions: List[Dict]) -> str:
        """Génère une alerte vocale avancée"""
        nom_strategie = strategie["nom"]
        score = strategie["score"]
        
        # Compter les actions
        actions_solaire = len([d for d in decisions if d["action"] == "solaire"])
        actions_batterie = len([d for d in decisions if d["action"] == "batterie"])
        actions_reseau = len([d for d in decisions if d["action"] == "reseau"])
        actions_couper = len([d for d in decisions if d["action"] == "couper"])
        
        if nom_strategie == "OPTIMISATION_MAXIMALE":
            return f"Optimisation maximale activée. Score: {score:.0f}. Toutes les charges sur solaire."
        elif nom_strategie == "OPTIMISATION_NORMALE":
            return f"Optimisation normale. Score: {score:.0f}. {actions_solaire} charges sur solaire, {actions_batterie} sur batterie."
        elif nom_strategie == "ECONOMIE":
            return f"Mode économie. Score: {score:.0f}. Charges prioritaires sur batterie, autres coupées."
        else:  # PRESERVATION
            return f"Mode préservation critique. Score: {score:.0f}. Charges prioritaires sur réseau, préservation batterie."
    
    def _enregistrer_decision(self, db: Session, strategie: Dict, decisions: List[Dict]):
        """Enregistre la décision en base de données"""
        try:
            decision = Decision(
                timestamp=datetime.now(),
                action=f"Stratégie: {strategie['nom']}",
                cible=f"Score: {strategie['score']:.1f}",
                raison=f"Optimisation robuste avec {len(decisions)} charges",
                utilisateur=1  # Système automatique
            )
            db.add(decision)
            db.commit()
        except Exception as e:
            logger.error(f"Erreur enregistrement décision: {e}")
    
    def _optimisation_fallback(self, db: Session, contexte: Dict) -> Dict:
        """Optimisation de secours en cas d'erreur"""
        logger.warning("Utilisation de l'optimisation de secours")
        
        return {
            "strategie": {"nom": "FALLBACK", "score": 0},
            "decisions": [{"charge_id": 1, "action": "reseau", "raison": "Mode secours"}],
            "alerte_vocale": "Mode secours activé - optimisation temporairement indisponible",
            "contexte": contexte,
            "timestamp": datetime.now().isoformat(),
            "source": "fallback"
        }
    
    def get_statistiques_solcast(self) -> Dict:
        """Retourne les statistiques d'utilisation Solcast"""
        if not self.solcast_manager:
            return {"erreur": "Gestionnaire Solcast non disponible"}
        
        return self.solcast_manager.get_statistiques_utilisation() 