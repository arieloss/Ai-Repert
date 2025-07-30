import requests
import random
from datetime import datetime
import time
from typing import List
from pydantic import BaseModel

# Configuration
API_URL = "http://localhost:8000/api/mesures"
CHARGE_IDS = [1, 2, 3, 4, 5]  # IDs of charges from create_initial_charges
INTERVAL_SECONDS = 5  # Send data every 5 seconds
NUM_ITERATIONS = 10  # Number of data points to send (adjust as needed)

class ConsommationData(BaseModel):
    charge_id: int
    consommation: float

class MesuresData(BaseModel):
    production: float
    soc_batterie: float
    tension_batterie: float
    courant_batterie: float
    consommations: List[ConsommationData]

def generate_mock_data() -> MesuresData:
    """Generate realistic mock data for measurements."""
    # Simulate solar production (0-1000 W, varies with time of day)
    hour = datetime.now().hour
    production = max(0, random.gauss(500, 200) * (1 - abs(12 - hour) / 12))  # Peak at noon

    # Simulate battery state
    soc_batterie = random.uniform(20.0, 100.0)  # Battery state of charge (20-100%)
    tension_batterie = random.uniform(48.0, 54.0)  # Battery voltage (48-54V for a typical 48V system)
    courant_batterie = random.uniform(-50.0, 50.0)  # Battery current (-50A to +50A)

    # Simulate consumption for each charge
    consommations = []
    for charge_id in CHARGE_IDS:
        # Random consumption based on typical load patterns
        consommation = random.gauss(50, 20) if random.random() > 0.3 else 0  # 70% chance of being ON
        consommations.append(ConsommationData(charge_id=charge_id, consommation=max(0, consommation)))

    return MesuresData(
        production=production,
        soc_batterie=soc_batterie,
        tension_batterie=tension_batterie,
        courant_batterie=courant_batterie,
        consommations=consommations
    )

def send_measurements():
    """Send mock measurements to the /mesures endpoint."""
    for i in range(NUM_ITERATIONS):
        try:
            # Generate mock data
            data = generate_mock_data()
            
            # Send POST request to the API
            response = requests.post(API_URL, json=data.dict())
            
            # Check response
            if response.status_code == 200:
                print(f"[{datetime.now().isoformat()}] Data sent successfully: {response.json()}")
            else:
                print(f"[{datetime.now().isoformat()}] Error sending data: {response.status_code} - {response.text}")
                
        except requests.RequestException as e:
            print(f"[{datetime.now().isoformat()}] Network error: {str(e)}")
        
        # Wait for the specified interval
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    print("Starting simulation of measurement data...")
    send_measurements()
    print("Simulation completed.")