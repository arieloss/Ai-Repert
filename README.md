# AI Repert Backend - Documentation API

## Schéma de flux général



## Endpoints REST principaux

### 1. Gestion des charges
- `GET /charges/` : Liste toutes les charges (id, nom, type, puissance, état)
- `POST /charges/` : Crée une nouvelle charge (nom, type, puissance_nominale)
- `PUT /charges/{charge_id}/etat` : Modifie l'état (ON/OFF) d'une charge

### 2. Mesures et commandes (Arduino)
- `POST /mesures/` : Reçoit les mesures (production, SOC batterie, consommations...)
- `GET /commandes/` : Récupère les commandes optimisées pour Arduino

### 3. Optimisation énergétique
- `POST /optimisation_robuste/` : Lance l'optimisation complète (décisions, stratégie, alerte)
- `POST /forcer_charges/` : Mode manuel, force l'activation/coupure de charges, retourne une alerte
- `POST /anticipation_batterie/` : Calcule l'autonomie batterie pour charges sélectionnées

### 4. Prévisions météo (Solcast)
- `GET /meteo/` : Récupère la liste brute des prévisions Solcast (jusqu'à 97 créneaux, 48h+)
- `POST /forcer_prevision/` : Force une mise à jour des prévisions si quota disponible
- `GET /statistiques_solcast/` : Statistiques d'utilisation de l'API Solcast

### 5. Dashboard et tendances
- `GET /dashboard/` : Données synthétiques pour le tableau de bord (production, SOC, état des charges)
- `GET /tendances/` : Analyse des tendances de production/consommation sur 24h

### 6. Calendrier
- `POST /calendrier/` : Ajoute un événement de calendrier (charge, date, heure, priorité temporaire)
- `GET /calendrier/` : Liste tous les événements du calendrier

### 7. Alertes vocales
- `GET /alerte_vocale/` : Génère une alerte vocale multilingue (texte -> synthèse)

---

## Exemple de structure de réponse `/meteo/`
```json
{
  "previsions": [
    {
      "period_end": "2025-07-29T00:00:00.0000000Z",
      "pv_estimate10": 0.0,
      "pv_estimate": 0.0,
      "pv_estimate90": 0.0
    },
    ... (jusqu'à 97 créneaux, filtrer 48 pour demain)
  ],
  "source": "api",
  "appels_restants": 8,
  "analyse": { /* analyse avancée, voir code */ }
}
```

---

## Exemple de configuration `.env` pour plusieurs clés Solcast

```
SOLCAST_API_KEY1=cle1
SOLCAST_SITE_ID1=siteid1
SOLCAST_API_KEY2=cle2
SOLCAST_SITE_ID2=siteid2
# Ajouter autant de paires que nécessaire :
# SOLCAST_API_KEY3=cle3
# SOLCAST_SITE_ID3=siteid3
```

## Notes d'intégration
- **Filtrage 48 créneaux** : côté frontend, filtrer les 48 créneaux de demain pour le graphique.
- **Quota Solcast** : rotation automatique entre deux clés/site_id, fallback sur cache si besoin.
- **Endpoints robustes** : tous les cas d'erreur sont gérés (quota, absence de données, etc).
- **Swagger/OpenAPI** : documentation interactive disponible sur `/docs`.

---

## Pour toute question ou évolution, voir le code source ou contacter l'équipe backend. 