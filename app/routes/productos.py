from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional
from app import models, schemas
from app.database import get_db
from app.auth import require_role, get_current_user

router = APIRouter(prefix="/productos", tags=["productos"])

@router.get("/", response_model=schemas.ProductosPaginados)
def listar_productos(
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(50, ge=1, le=500, description="Número de registros a retornar"),
    busqueda: Optional[str] = Query(None, description="Búsqueda por nombre, categoría o código"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoría"),
    estado_stock: Optional[str] = Query(None, description="Filtrar por estado: todos, normal, bajo, critico"),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Listar productos con paginación y filtros.
    Retorna total de registros para implementar scroll infinito.
    """
    # Query base
    query = db.query(models.Producto).filter(models.Producto.activo == True)
    
    # Aplicar filtro de búsqueda
    if busqueda:
        busqueda_lower = f"%{busqueda.lower()}%"
        query = query.filter(
            or_(
                func.lower(models.Producto.nombre).like(busqueda_lower),
                func.lower(models.Producto.categoria).like(busqueda_lower),
                models.Producto.codigo_barras.like(busqueda_lower)
            )
        )
    
    # Aplicar filtro de categoría
    if categoria and categoria != 'todas':
        if categoria == 'Sin categoría':
            query = query.filter(
                or_(
                    models.Producto.categoria == None,
                    models.Producto.categoria == ''
                )
            )
        else:
            query = query.filter(models.Producto.categoria == categoria)
    
    # Aplicar filtro de estado de stock
    if estado_stock and estado_stock != 'todos':
        if estado_stock == 'critico':
            query = query.filter(models.Producto.stock < 10)
        elif estado_stock == 'bajo':
            query = query.filter(
                models.Producto.stock >= 10,
                models.Producto.stock < models.Producto.stock_minimo
            )
        elif estado_stock == 'normal':
            query = query.filter(models.Producto.stock >= models.Producto.stock_minimo)
    
    # Obtener total de registros (para el scroll infinito)
    total = query.count()
    
    # Ordenar alfabéticamente y aplicar paginación
    productos = query.order_by(models.Producto.nombre.asc()).offset(skip).limit(limit).all()
    
    return {
        "productos": productos,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": (skip + limit) < total
    }

@router.get("/categorias", response_model=List[str])
def listar_categorias(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Obtener lista de todas las categorías únicas.
    """
    categorias = db.query(models.Producto.categoria).filter(
        models.Producto.activo == True,
        models.Producto.categoria != None,
        models.Producto.categoria != ''
    ).distinct().order_by(models.Producto.categoria).all()
    
    return [cat[0] for cat in categorias if cat[0]]

@router.get("/buscar-codigo", response_model=schemas.ProductoBusqueda)
def buscar_por_codigo_barras(
    codigo: str = Query(..., description="Código de barras del producto"),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    producto = db.query(models.Producto).filter(
        models.Producto.codigo_barras == codigo,
        models.Producto.activo == True
    ).first()
    
    if not producto:
        raise HTTPException(
            status_code=404, 
            detail=f"Producto con código de barras '{codigo}' no encontrado"
        )
    
    if producto.stock <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"El producto '{producto.nombre}' no tiene stock disponible"
        )
    
    return producto

@router.get("/{producto_id}", response_model=schemas.Producto)
def obtener_producto(
    producto_id: int, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    producto = db.query(models.Producto).filter(
        models.Producto.id == producto_id
    ).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto

@router.post("/", response_model=schemas.Producto)
def crear_producto(
    producto: schemas.ProductoCreate, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role(["admin"]))
):
    # Verificar si el código de barras ya existe
    if producto.codigo_barras:
        existing = db.query(models.Producto).filter(
            models.Producto.codigo_barras == producto.codigo_barras
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Ya existe un producto con ese código de barras"
            )
    
    db_producto = models.Producto(**producto.dict())
    db.add(db_producto)
    db.commit()
    db.refresh(db_producto)
    return db_producto

@router.put("/{producto_id}", response_model=schemas.Producto)
def actualizar_producto(
    producto_id: int, 
    producto: schemas.ProductoUpdate, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role(["admin"]))
):
    db_producto = db.query(models.Producto).filter(
        models.Producto.id == producto_id
    ).first()
    if not db_producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    # Verificar código de barras único si se está actualizando
    if producto.codigo_barras:
        existing = db.query(models.Producto).filter(
            models.Producto.codigo_barras == producto.codigo_barras,
            models.Producto.id != producto_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Ya existe otro producto con ese código de barras"
            )
    
    update_data = producto.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_producto, key, value)
    
    db.commit()
    db.refresh(db_producto)
    return db_producto

@router.delete("/{producto_id}")
def eliminar_producto(
    producto_id: int, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role(["admin"]))
):
    db_producto = db.query(models.Producto).filter(
        models.Producto.id == producto_id
    ).first()
    if not db_producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    db_producto.activo = False
    db.commit()
    return {"message": "Producto eliminado correctamente"}

@router.get("/stock/bajo")
def productos_stock_bajo(
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(20, ge=1, le=50, description="Número de registros a retornar"),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    query = db.query(models.Producto).filter(
        models.Producto.stock < models.Producto.stock_minimo,
        models.Producto.stock >= 10,  # Bajo pero no crítico
        models.Producto.activo == True
    ).order_by(models.Producto.stock.asc())
    total = query.count()
    productos = query.offset(skip).limit(limit).all()
    resultado = {
        "productos": productos,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": (skip + limit) < total
    }
    return resultado

@router.get("/stock/critico")
def productos_stock_critico(
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(20, ge=1, le=50, description="Número de registros a retornar"),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    query = db.query(models.Producto).filter(
        models.Producto.stock < 10,
        models.Producto.activo == True
    ).order_by(models.Producto.stock.asc())
    total = query.count()
    productos = query.offset(skip).limit(limit).all()
   
    resultado = {
        "productos": productos,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": (skip + limit) < total
    }
    
    return resultado