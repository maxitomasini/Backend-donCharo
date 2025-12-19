from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db, SessionLocal
from app.routes import productos, ventas, reportes, profile, users, ventasDetalle
from app.routes import auth
from app import models
from app.auth import get_password_hash
from datetime import datetime


app = FastAPI(title="Sistema Don Charo API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

@app.on_event("startup")
def on_startup():
    init_db()
    
    db = SessionLocal()
    try:
        # Crear usuario superadmin por defecto si no existe
        superadmin = db.query(models.Usuario).filter(models.Usuario.username == "pepe").first()
        if not superadmin:
            superadmin = models.Usuario(
                username="pepe",
                email="superadmin@doncharo.com",
                password_hash=get_password_hash("1234"),
                nombre_completo="Super Administrador",
                rol="superadmin"
            )
            db.add(superadmin)
            db.commit()
            print("Usuario superadmin creado: pepe / 1234")
        
        # Crear usuario admin por defecto si no existe
        admin = db.query(models.Usuario).filter(models.Usuario.username == "admin").first()
        if not admin:
            admin = models.Usuario(
                username="admin",
                email="admin@doncharo.com",
                password_hash=get_password_hash("admin123"),
                nombre_completo="Administrador",
                rol="admin"
            )
            db.add(admin)
            db.commit()
            print("Usuario admin creado: admin / admin123")
        
        # Crear usuario cajero por defecto
        cajero = db.query(models.Usuario).filter(models.Usuario.username == "cajero").first()
        if not cajero:
            cajero = models.Usuario(
                username="cajero",
                email="cajero@doncharo.com",
                password_hash=get_password_hash("cajero123"),
                nombre_completo="Cajero",
                rol="cajero"
            )
            db.add(cajero)
            db.commit()
            print("Usuario cajero creado: cajero / cajero123")
    finally:
        db.close()

app.include_router(auth.router)
app.include_router(productos.router)
app.include_router(ventas.router)
app.include_router(reportes.router)
app.include_router(profile.router)
app.include_router(users.router)
app.include_router(ventasDetalle.router)

@app.get("/")
def root():
    return {"message": "API Sistema Don Charo - Funcionando correctamente"}

@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    }