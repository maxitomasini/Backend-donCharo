from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

# Schemas para Usuarios
class UsuarioBase(BaseModel):
    username: str
    email: EmailStr
    nombre_completo: Optional[str] = None
    rol: str = "cajero"

class UsuarioCreate(UsuarioBase):
    password: str

class UsuarioLogin(BaseModel):
    username: str
    password: str

class Usuario(UsuarioBase):
    id: int
    activo: bool
    fecha_creacion: datetime
    ultimo_acceso: Optional[datetime]
    
    class Config:
        from_attributes = True

class UsuarioResponse(BaseModel):
    id: int
    username: str
    email: str
    nombre_completo: Optional[str]
    rol: str
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UsuarioResponse

# Schemas para Productos
class ProductoBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    precio_costo: float  
    precio_venta: float  
    stock: int
    stock_minimo: int = 10
    categoria: Optional[str] = None
    codigo_barras: Optional[str] = None

class ProductoCreate(ProductoBase):
    pass

class ProductoUpdate(BaseModel):
    nombre: Optional[str] = None
    precio_costo: Optional[float] = None  
    precio_venta: Optional[float] = None 
    stock: Optional[int] = None
    categoria: Optional[str] = None
    codigo_barras: Optional[str] = None

class Producto(ProductoBase):
    id: int
    activo: bool
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True

# Schema para búsqueda por código de barras
class ProductoBusqueda(BaseModel):
    id: int
    nombre: str
    precio_venta: float
    stock: int
    categoria: Optional[str]
    codigo_barras: Optional[str]
    
    class Config:
        from_attributes = True

# Schemas para Ventas
class ItemVentaCreate(BaseModel):
    producto_id: int
    cantidad: int
    precio_unitario: float

class ItemVenta(BaseModel):
    id: int
    producto_id: int
    cantidad: int
    precio_unitario: float
    subtotal: float
    
    class Config:
        from_attributes = True

class VentaCreate(BaseModel):
    items: List[ItemVentaCreate]
    metodo_pago: str = "efectivo"
    observaciones: Optional[str] = None

class Venta(BaseModel):
    id: int
    fecha: datetime
    total: float
    metodo_pago: str
    items: List[ItemVenta]
    
    class Config:
        from_attributes = True

# Schemas para Movimientos Financieros
class MovimientoFinancieroCreate(BaseModel):
    tipo: str
    monto: float
    concepto: str
    categoria: Optional[str] = None
    observaciones: Optional[str] = None

class MovimientoFinanciero(BaseModel):
    id: int
    fecha: datetime
    tipo: str
    monto: float
    concepto: str
    categoria: Optional[str]
    
    class Config:
        from_attributes = True

class ProductosPaginados(BaseModel):
    productos: List[Producto]
    total: int
    skip: int
    limit: int
    has_more: bool
    
    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    nombre_completo: Optional[str] = None
    rol: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    nombre_completo: Optional[str] = None
    rol: Optional[str] = None
    activo: Optional[bool] = None

class UserListResponse(BaseModel):
    id: int
    username: str
    email: str
    nombre_completo: Optional[str]
    rol: str
    activo: bool
    fecha_creacion: datetime
    ultimo_acceso: Optional[datetime]
    
    class Config:
        from_attributes = True

class UsersListResponse(BaseModel):
    usuarios: List[UserListResponse]
    total: int

class UserProfileUpdate(BaseModel):
    username: Optional[str] = None
    nombre_completo: Optional[str] = None
    password: Optional[str] = None
