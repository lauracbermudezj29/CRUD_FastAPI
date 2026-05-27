from typing import Sequence
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from faker import Faker
from datetime import date

from ..models.persona import Persona
from ..views.persona import PersonaCreate, PersonaUpdate
from .errors import PersonaNotFoundError, EmailAlreadyExistsError

import random
dominios = [
    "gmail.com",
    "outlook.com",
    "hotmail.com",
    "yahoo.com"
]

def create_persona(db: Session, payload: PersonaCreate) -> Persona:
    """Create a Persona ensuring unique email."""
    # Optimistic check; DB unique constraint is the final guard
    if db.query(Persona).filter(Persona.email == payload.email).first():
        raise EmailAlreadyExistsError()
    obj = Persona(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        birth_date=payload.birth_date,
        is_active=payload.is_active,
        notes=payload.notes,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        # Catch race conditions on unique email
        raise EmailAlreadyExistsError() from e
    db.refresh(obj)
    return obj


def list_personas(db: Session, skip: int = 0, limit: int = 100) -> Sequence[Persona]:
    """Return paginated list of Personas."""
    return db.query(Persona).offset(skip).limit(limit).all()


def get_persona(db: Session, persona_id: int) -> Persona:
    """Return Persona by ID or raise if not found."""
    obj = db.query(Persona).filter(Persona.id == persona_id).first()
    if not obj:
        raise PersonaNotFoundError()
    return obj


def update_persona(db: Session, persona_id: int, payload: PersonaUpdate) -> Persona:
    """Update Persona partially, enforcing unique email."""
    obj = db.query(Persona).filter(Persona.id == persona_id).first()
    if not obj:
        raise PersonaNotFoundError()

    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"] != obj.email:
        if db.query(Persona).filter(Persona.email == data["email"], Persona.id != persona_id).first():
            raise EmailAlreadyExistsError()

    for field, value in data.items():
        setattr(obj, field, value)

    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise EmailAlreadyExistsError() from e
    db.refresh(obj)
    return obj


def delete_persona(db: Session, persona_id: int) -> None:
    """Delete Persona by ID or raise if not found."""
    obj = db.query(Persona).filter(Persona.id == persona_id).first()
    if not obj:
        raise PersonaNotFoundError()
    db.delete(obj)
    db.commit()

fake = Faker()

def poblar_personas(db: Session, cantidad: int):
    personas = []
    for _ in range(cantidad):
        nombre = fake.first_name()
        apellido = fake.last_name()
        persona = Persona(
            first_name=nombre,
            last_name=apellido,
            email=f"{nombre.lower()}.{apellido.lower()}@{random.choice(dominios)}",
            phone=fake.phone_number(),
            birth_date=fake.date_of_birth(),
            is_active=fake.boolean(),
            notes=fake.sentence() if fake.boolean() else None,
        )
        db.add(persona)
        personas.append(persona)
    db.commit()
    return len(personas)

def reset_personas(db):
    deleted_count = db.query(Persona).count()
    db.query(Persona).delete()
    db.commit()
    return deleted_count

def estadisticas_dominios(db):
    personas = db.query(Persona).all()
    resultado = {}
    for persona in personas:
        dominio = persona.email.split("@")[1]
        if dominio in resultado:
            resultado[dominio] += 1
        else:
            resultado[dominio] = 1
    return resultado

def estadisticas_edad(db):
    personas = db.query(Persona).all()
    edades = []
    for persona in personas:
        if persona.birth_date:
            hoy = date.today()
            edad = hoy.year - persona.birth_date.year
            if (
                (hoy.month, hoy.day)
                < (persona.birth_date.month, persona.birth_date.day)
            ):
                edad -= 1
            edades.append(edad)
    if not edades:
        return {
            "edad_promedio": 0,
            "edad_minima": 0,
            "edad_maxima": 0
        }
    return {
        "edad_promedio": round(sum(edades) / len(edades)),
        "edad_minima": min(edades),
        "edad_maxima": max(edades)
    }

def buscar_personas(db: Session, termino: str, limite: int = 50):
    """Busca por first_name, last_name o email usando OR. Máximo 50 resultados."""
    if not termino or len(termino.strip()) < 2:
        return []
    like = f"%{termino.strip()}%"
    return db.query(Persona).filter(
        (Persona.first_name.ilike(like)) |
        (Persona.last_name.ilike(like)) |
        (Persona.email.ilike(like))
    ).limit(limite).all()


def exportar_csv(db: Session):
    """Retorna todos los registros como string CSV con encoding UTF-8."""
    import csv
    import io
    personas = db.query(Persona).all()
    output = io.StringIO()
    output.write('\ufeff')  # BOM para que Excel reconozca UTF-8
    writer = csv.writer(output)
    writer.writerow(["id", "first_name", "last_name", "email", "phone", "birth_date", "is_active", "notes"])
    if not personas:
        output.seek(0)
        return output
    for p in personas:
        writer.writerow([p.id, p.first_name, p.last_name, p.email, p.phone, p.birth_date, p.is_active, p.notes])
    output.seek(0)
    return output

def reporte_activos(db: Session):
    """Retorna solo usuarios activos con proyección reducida."""
    personas = db.query(Persona).filter(Persona.is_active == True).all()
    return [
        {
            "id": p.id,
            "email": p.email,
            "phone": p.phone,
            "is_active": p.is_active
        }
        for p in personas
    ]
