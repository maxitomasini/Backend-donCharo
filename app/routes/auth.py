from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from app import models, schemas
from app.database import get_db
from app.auth import get_current_user, verify_password, get_password_hash, create_access_token

router = APIRouter(prefix="/auth", tags=["autenticacion"])

@router.post("/register", response_model=schemas.UsuarioResponse)
def registrar_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    # Verificar si el usuario ya existe
    db_user = db.query(models.Usuario).filter(
        (models.Usuario.username == usuario.username) | 
        (models.Usuario.email == usuario.email)
    ).first()
    
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="El usuario o email ya está registrado"
        )
    
    # Crear nuevo usuario
    hashed_password = get_password_hash(usuario.password)
    db_usuario = models.Usuario(
        username=usuario.username,
        email=usuario.email,
        password_hash=hashed_password,
        nombre_completo=usuario.nombre_completo,
        rol=usuario.rol
    )
    
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

@router.post("/login", response_model=schemas.Token)
def login(usuario: schemas.UsuarioLogin, db: Session = Depends(get_db)):
    # Buscar usuario
    db_user = db.query(models.Usuario).filter(
        models.Usuario.username == usuario.username
    ).first()
    
    if not db_user or not verify_password(usuario.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not db_user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    
    # Actualizar último acceso
    db_user.ultimo_acceso = datetime.now()
    db.commit()
    
    # Crear token
    access_token = create_access_token(data={"sub": db_user.username})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": db_user.id,
            "username": db_user.username,
            "email": db_user.email,
            "nombre_completo": db_user.nombre_completo,
            "rol": db_user.rol,
            "dark_mode": db_user.dark_mode
        }
    }

@router.get("/me", response_model=schemas.UsuarioResponse)
def obtener_usuario_actual(current_user: models.Usuario = Depends(get_current_user)):
    return current_user