from typing import List
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..views.persona import PersonaCreate, PersonaUpdate, PersonaRead, PoblarRequest
from ..services import persona_service

router = APIRouter(prefix="/personas", tags=["personas"])


@router.post("", response_model=PersonaRead, status_code=status.HTTP_201_CREATED)
def create_persona(persona_in: PersonaCreate, db: Session = Depends(get_db)):
    """Create a new Persona delegating to service layer."""
    # Let domain errors bubble up to global handlers
    return persona_service.create_persona(db, persona_in)


@router.get("", response_model=List[PersonaRead])
def list_personas(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List Personas with pagination via service layer."""
    return persona_service.list_personas(db, skip=skip, limit=limit)

@router.get("/estadisticas/dominios")
def estadisticas_dominios(db: Session = Depends(get_db)):
    return persona_service.estadisticas_dominios(db)

@router.get("/estadisticas/edad")
def estadisticas_edad(db: Session = Depends(get_db)):
    return persona_service.estadisticas_edad(db)

@router.get("/buscar/{termino}")
def buscar_personas(termino: str, db: Session = Depends(get_db)):
    """Busca personas por nombre, apellido o email."""
    return persona_service.buscar_personas(db, termino)


@router.get("/exportar/csv")
def exportar_csv(db: Session = Depends(get_db)):
    """Exporta todos los registros en formato CSV."""
    output = persona_service.exportar_csv(db)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=personas.csv"}
    )

@router.get("/{persona_id}", response_model=PersonaRead)
def get_persona(persona_id: int, db: Session = Depends(get_db)):
    """Retrieve a Persona by ID via service layer."""
    return persona_service.get_persona(db, persona_id)


@router.put("/{persona_id}", response_model=PersonaRead)
def update_persona(persona_id: int, persona_in: PersonaUpdate, db: Session = Depends(get_db)):
    """Update an existing Persona (partial) via service layer."""
    return persona_service.update_persona(db, persona_id, persona_in)

@router.delete("/reset", status_code=200)
def reset_personas(db: Session = Depends(get_db)):
    deleted_count = persona_service.reset_personas(db)

    return {
        "message": "Base de datos limpiada. Se eliminaron todos los registros.",
        "deleted_count": deleted_count
    }

@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_persona(persona_id: int, db: Session = Depends(get_db)):
    """Delete a Persona by ID via service layer."""
    persona_service.delete_persona(db, persona_id)
    return None

@router.post("/poblar", status_code=201)
def poblar_personas(data: PoblarRequest, db: Session = Depends(get_db)):
    persona_service.poblar_personas(db, data.cantidad)
    return {
        "message": f"{data.cantidad} usuarios creados exitosamente",
        "status": 201
    }

