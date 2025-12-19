from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from app import models, schemas
from app.database import get_db
from app.auth import get_current_user, get_password_hash
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/user", tags=["usuario"])

@router.get("/profile", response_model=schemas.UsuarioResponse)
def get_user_profile(current_user: models.Usuario = Depends(get_current_user)):
    """
    Obtener el perfil del usuario autenticado
    """
    return current_user

@router.put("/profile", response_model=schemas.UsuarioResponse)
def update_user_profile(
    user_update: schemas.UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Actualizar el perfil del usuario autenticado
    Puede actualizar username, nombre completo y contraseña
    """
    try:
        # Actualizar username si se proporciona
        if user_update.username is not None and user_update.username.strip() != "":
            # Validar que el username no esté vacío
            if len(user_update.username.strip()) < 3:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El nombre de usuario debe tener al menos 3 caracteres"
                )
            
            # Verificar que el nuevo username no esté en uso por otro usuario
            existing_user = db.query(models.Usuario).filter(
                models.Usuario.username == user_update.username,
                models.Usuario.id != current_user.id
            ).first()
            
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El nombre de usuario ya está en uso"
                )
            
            current_user.username = user_update.username
        
        # Actualizar nombre completo si se proporciona
        if user_update.nombre_completo is not None:
            current_user.nombre_completo = user_update.nombre_completo
        
        # Actualizar contraseña si se proporciona
        if user_update.password is not None and user_update.password.strip() != "":
            if len(user_update.password) < 4:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La contraseña debe tener al menos 4 caracteres"
                )
            current_user.password_hash = get_password_hash(user_update.password)
        
        db.commit()
        db.refresh(current_user)
        
        return current_user
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el perfil: {str(e)}"
        )