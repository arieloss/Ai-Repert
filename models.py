from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Date, Time, Text, TIMESTAMP
from sqlalchemy.orm import relationship
from database import Base

class Utilisateur(Base):
    __tablename__ = 'utilisateur'
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100))
    langue = Column(String(10))
    email = Column(String(100))
    mot_de_passe = Column(String(255))

class Charge(Base):
    __tablename__ = 'charges'
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100))
    type = Column(String(20))  # prioritaire, semi-prioritaire, non-prioritaire
    puissance_nominale = Column(Float)
    etat = Column(Boolean, default=False)

class Consommation(Base):
    __tablename__ = 'consommation'
    id = Column(Integer, primary_key=True, index=True)
    id_charge = Column(Integer, ForeignKey('charges.id'))
    timestamp = Column(TIMESTAMP)
    consommation = Column(Float)
    charge = relationship('Charge')

class Production(Base):
    __tablename__ = 'production'
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(TIMESTAMP)
    production = Column(Float)

class Batterie(Base):
    __tablename__ = 'batterie'
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(TIMESTAMP)
    soc = Column(Float)
    tension = Column(Float)
    courant = Column(Float)

class Calendrier(Base):
    __tablename__ = 'calendrier'
    id = Column(Integer, primary_key=True, index=True)
    id_charge = Column(Integer, ForeignKey('charges.id'))
    date = Column(Date)
    heure_debut = Column(Time)
    heure_fin = Column(Time)
    priorite_temporaire = Column(String(20))
    charge = relationship('Charge')

class Decision(Base):
    __tablename__ = 'decisions'
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(TIMESTAMP)
    action = Column(String(100))
    cible = Column(String(100))
    raison = Column(Text)
    utilisateur = Column(Integer, ForeignKey('utilisateur.id'))
    user = relationship('Utilisateur')