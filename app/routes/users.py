from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime
from app import models, schemas
from app.database import get_db
from app.auth import get_current_user, get_password_hash
from pydantic import BaseModel, EmailStr
from typing import Optional, List

router = APIRouter(prefix="/users", tags=["administracion-usuarios"])

# Middleware para verificar que sea SUPERADMIN
def verify_superadmin(current_user: models.Usuario = Depends(get_current_user)):
    if current_user.rol.upper() != "SUPERADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a esta funcionalidad"
        )
    return current_user

@router.get("/", response_model=schemas.UsersListResponse)
def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    busqueda: Optional[str] = None,
    rol: Optional[str] = None,
    activo: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(verify_superadmin)
):
    """
    Obtener listado de todos los usuarios
    Solo accesible para SUPERADMIN
    """
    query = db.query(models.Usuario)
    
    # Filtro de búsqueda
    if busqueda:
        search_filter = f"%{busqueda}%"
        query = query.filter(
            (models.Usuario.username.ilike(search_filter)) |
            (models.Usuario.email.ilike(search_filter)) |
            (models.Usuario.nombre_completo.ilike(search_filter))
        )
    
    # Filtro por rol
    if rol and rol != "todos":
        query = query.filter(models.Usuario.rol == rol.upper())
    
    # Filtro por estado activo
    if activo is not None:
        query = query.filter(models.Usuario.activo == activo)
    
    # Contar total
    total = query.count()
    
    # Obtener usuarios con paginación
    usuarios = query.order_by(models.Usuario.fecha_creacion.desc()).offset(skip).limit(limit).all()
    
    return {
        "usuarios": usuarios,
        "total": total
    }

@router.get("/{user_id}", response_model=schemas.UserListResponse)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(verify_superadmin)
):
    """
    Obtener un usuario por su ID
    Solo accesible para SUPERADMIN
    """
    user = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    return user

@router.post("/", response_model=schemas.UserListResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(verify_superadmin)
):
    """
    Crear un nuevo usuario
    Solo accesible para SUPERADMIN
    """
    # Validar que el username no exista
    existing_user = db.query(models.Usuario).filter(
        models.Usuario.username == user_data.username
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya está en uso"
        )
    
    # Validar que el email no exista
    existing_email = db.query(models.Usuario).filter(
        models.Usuario.email == user_data.email
    ).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está en uso"
        )
    
    # Validar rol
    valid_roles = ["SUPERADMIN", "ADMIN", "CAJERO"]
    if user_data.rol.upper() not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rol inválido. Debe ser uno de: {', '.join(valid_roles)}"
        )
    
    # Validar contraseña
    if len(user_data.password) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener al menos 4 caracteres"
        )
    
    # Crear usuario
    new_user = models.Usuario(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        nombre_completo=user_data.nombre_completo,
        rol=user_data.rol.upper(),
        activo=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.put("/{user_id}", response_model=schemas.UserListResponse)
def update_user(
    user_id: int,
    user_data: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(verify_superadmin)
):
    """
    Actualizar un usuario existente
    Solo accesible para SUPERADMIN
    """
    # Buscar usuario
    user = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Actualizar username si se proporciona
    if user_data.username is not None:
        # Verificar que no esté en uso por otro usuario
        existing_user = db.query(models.Usuario).filter(
            models.Usuario.username == user_data.username,
            models.Usuario.id != user_id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre de usuario ya está en uso"
            )
        user.username = user_data.username
    
    # Actualizar email si se proporciona
    if user_data.email is not None:
        # Verificar que no esté en uso por otro usuario
        existing_email = db.query(models.Usuario).filter(
            models.Usuario.email == user_data.email,
            models.Usuario.id != user_id
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está en uso"
            )
        user.email = user_data.email
    
    # Actualizar nombre completo
    if user_data.nombre_completo is not None:
        user.nombre_completo = user_data.nombre_completo
    
    # Actualizar contraseña si se proporciona
    if user_data.password is not None and user_data.password.strip() != "":
        if len(user_data.password) < 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La contraseña debe tener al menos 4 caracteres"
            )
        user.password_hash = get_password_hash(user_data.password)
    
    # Actualizar rol
    if user_data.rol is not None:
        valid_roles = ["SUPERADMIN", "ADMIN", "CAJERO"]
        if user_data.rol.upper() not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Rol inválido. Debe ser uno de: {', '.join(valid_roles)}"
            )
        user.rol = user_data.rol.upper()
    
    # Actualizar estado activo
    if user_data.activo is not None:
        user.activo = user_data.activo
    
    db.commit()
    db.refresh(user)
    
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(verify_superadmin)
):
    """
    Eliminar un usuario (desactivarlo)
    Solo accesible para SUPERADMIN
    """
    # Buscar usuario
    user = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # No permitir que el superadmin se elimine a sí mismo
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivar tu propia cuenta"
        )
    
    # Desactivar en lugar de eliminar
    user.activo = False
    db.commit()
    
    return None