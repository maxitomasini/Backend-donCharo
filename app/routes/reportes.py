from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from app import models
from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/reportes", tags=["reportes"])

@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    total_ventas = db.query(func.sum(models.Venta.total)).scalar() or 0
    cantidad_ventas = db.query(func.count(models.Venta.id)).scalar()
    productos_vendidos = db.query(func.sum(models.ItemVenta.cantidad)).scalar() or 0
    
    hoy = datetime.now().date()
    ventas_hoy = db.query(func.sum(models.Venta.total)).filter(
        func.date(models.Venta.fecha) == hoy
    ).scalar() or 0
    
    stock_bajo = db.query(func.count(models.Producto.id)).filter(
        models.Producto.stock < models.Producto.stock_minimo,
        models.Producto.activo == True
    ).scalar()
    
    ganancia_query = db.query(
        func.sum(
            (models.Producto.precio_venta - models.Producto.precio_costo) * 
            models.ItemVenta.cantidad
        )
    ).join(
        models.ItemVenta.producto
    ).scalar() or 0
    
    return {
        "total_ventas": float(total_ventas),
        "cantidad_ventas": cantidad_ventas,
        "productos_vendidos": productos_vendidos,
        "ventas_hoy": float(ventas_hoy),
        "productos_stock_bajo": stock_bajo,
        "ganancia_total": float(ganancia_query)
    }

@router.get("/ventas-por-periodo")
def ventas_por_periodo(
    periodo: str = Query("dia"),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    hoy = datetime.now()
    
    if periodo == "dia":
        fecha_inicio = hoy - timedelta(days=30)
        ventas = db.query(
            func.date(models.Venta.fecha).label('fecha'),
            func.sum(models.Venta.total).label('total'),
            func.count(models.Venta.id).label('cantidad')
        ).filter(
            models.Venta.fecha >= fecha_inicio
        ).group_by(func.date(models.Venta.fecha)).order_by('fecha').all()
        
        return [{
            "periodo": v.fecha.strftime("%d/%m"),
            "total": float(v.total),
            "cantidad": v.cantidad
        } for v in ventas]
    
    elif periodo == "semana":
        fecha_inicio = hoy - timedelta(weeks=12)
        ventas = db.query(
            extract('year', models.Venta.fecha).label('año'),
            extract('week', models.Venta.fecha).label('semana'),
            func.sum(models.Venta.total).label('total'),
            func.count(models.Venta.id).label('cantidad')
        ).filter(
            models.Venta.fecha >= fecha_inicio
        ).group_by('año', 'semana').order_by('año', 'semana').all()
        
        return [{
            "periodo": f"S{int(v.semana)}",
            "total": float(v.total),
            "cantidad": v.cantidad
        } for v in ventas]
    
    elif periodo == "mes":
        fecha_inicio = hoy - timedelta(days=365)
        ventas = db.query(
            extract('year', models.Venta.fecha).label('año'),
            extract('month', models.Venta.fecha).label('mes'),
            func.sum(models.Venta.total).label('total'),
            func.count(models.Venta.id).label('cantidad')
        ).filter(
            models.Venta.fecha >= fecha_inicio
        ).group_by('año', 'mes').order_by('año', 'mes').all()
        
        meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        return [{
            "periodo": f"{meses[int(v.mes)-1]}",
            "total": float(v.total),
            "cantidad": v.cantidad
        } for v in ventas]
    
    else:
        ventas = db.query(
            extract('year', models.Venta.fecha).label('año'),
            func.sum(models.Venta.total).label('total'),
            func.count(models.Venta.id).label('cantidad')
        ).group_by('año').order_by('año').all()
        
        return [{
            "periodo": str(int(v.año)),
            "total": float(v.total),
            "cantidad": v.cantidad
        } for v in ventas]

@router.get("/categorias-mas-vendidas")
def categorias_mas_vendidas(
    limite: int = Query(10),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    categorias = db.query(
        func.coalesce(models.Producto.categoria, 'Sin categoría').label('categoria'),
        func.sum(models.ItemVenta.cantidad).label('cantidad'),
        func.sum(models.ItemVenta.subtotal).label('total')
    ).join(
        models.ItemVenta.producto
    ).group_by('categoria').order_by(func.sum(models.ItemVenta.cantidad).desc()).limit(limite).all()
    
    return [{
        "categoria": c.categoria,
        "cantidad": int(c.cantidad),
        "total": float(c.total)
    } for c in categorias]

@router.get("/productos-mas-vendidos")
def productos_mas_vendidos(
    limite: int = Query(10),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    productos = db.query(
        models.Producto.nombre,
        func.sum(models.ItemVenta.cantidad).label('cantidad'),
        func.sum(models.ItemVenta.subtotal).label('total')
    ).join(
        models.ItemVenta.producto
    ).group_by(models.Producto.nombre).order_by(func.sum(models.ItemVenta.cantidad).desc()).limit(limite).all()
    
    return [{
        "nombre": p.nombre,
        "cantidad": int(p.cantidad),
        "total": float(p.total)
    } for p in productos]

@router.get("/ganancias")
def ganancias(
    periodo: str = Query("mes"),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    hoy = datetime.now()
    
    if periodo == "dia":
        fecha_inicio = hoy - timedelta(days=30)
        ganancias = db.query(
            func.date(models.Venta.fecha).label('fecha'),
            func.sum(models.ItemVenta.subtotal).label('ventas'),
            func.sum(
                (models.Producto.precio_venta - models.Producto.precio_costo) * 
                models.ItemVenta.cantidad
            ).label('ganancia')
        ).join(
            models.Venta
        ).join(
            models.ItemVenta.producto
        ).filter(
            models.Venta.fecha >= fecha_inicio
        ).group_by('fecha').order_by('fecha').all()
        
        return [{
            "periodo": g.fecha.strftime("%d/%m"),
            "ventas": float(g.ventas),
            "ganancia": float(g.ganancia),
            "margen": (float(g.ganancia) / float(g.ventas) * 100) if g.ventas > 0 else 0
        } for g in ganancias]
    
    elif periodo == "semana":
        fecha_inicio = hoy - timedelta(weeks=12)
        ganancias = db.query(
            extract('week', models.Venta.fecha).label('semana'),
            func.sum(models.ItemVenta.subtotal).label('ventas'),
            func.sum(
                (models.Producto.precio_venta - models.Producto.precio_costo) * 
                models.ItemVenta.cantidad
            ).label('ganancia')
        ).join(
            models.Venta
        ).join(
            models.ItemVenta.producto
        ).filter(
            models.Venta.fecha >= fecha_inicio
        ).group_by('semana').order_by('semana').all()
        
        return [{
            "periodo": f"S{int(g.semana)}",
            "ventas": float(g.ventas),
            "ganancia": float(g.ganancia),
            "margen": (float(g.ganancia) / float(g.ventas) * 100) if g.ventas > 0 else 0
        } for g in ganancias]
    
    else:
        fecha_inicio = hoy - timedelta(days=365)
        ganancias = db.query(
            extract('month', models.Venta.fecha).label('mes'),
            func.sum(models.ItemVenta.subtotal).label('ventas'),
            func.sum(
                (models.Producto.precio_venta - models.Producto.precio_costo) * 
                models.ItemVenta.cantidad
            ).label('ganancia')
        ).join(
            models.Venta
        ).join(
            models.ItemVenta.producto
        ).filter(
            models.Venta.fecha >= fecha_inicio
        ).group_by('mes').order_by('mes').all()
        
        meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        return [{
            "periodo": meses[int(g.mes)-1],
            "ventas": float(g.ventas),
            "ganancia": float(g.ganancia),
            "margen": (float(g.ganancia) / float(g.ventas) * 100) if g.ventas > 0 else 0
        } for g in ganancias]

@router.get("/metodos-pago")
def metodos_pago(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    metodos = db.query(
        models.Venta.metodo_pago,
        func.count(models.Venta.id).label('cantidad'),
        func.sum(models.Venta.total).label('total')
    ).group_by(models.Venta.metodo_pago).all()
    
    return [{
        "metodo": m.metodo_pago.capitalize(),
        "cantidad": m.cantidad,
        "total": float(m.total)
    } for m in metodos]

@router.get("/dashboard-hoy")
def dashboard_hoy(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Dashboard con datos SOLO del día de hoy
    """
    hoy = datetime.now().date()
    
    # Ventas de hoy
    ventas_hoy = db.query(func.sum(models.Venta.total)).filter(
        func.date(models.Venta.fecha) == hoy
    ).scalar() or 0
    
    # Cantidad de transacciones hoy
    cantidad_ventas_hoy = db.query(func.count(models.Venta.id)).filter(
        func.date(models.Venta.fecha) == hoy
    ).scalar()
    
    # Productos vendidos hoy (unidades)
    productos_vendidos_hoy = db.query(func.sum(models.ItemVenta.cantidad)).join(
        models.Venta
    ).filter(
        func.date(models.Venta.fecha) == hoy
    ).scalar() or 0
    
    # Ganancias de hoy
    ganancia_hoy = db.query(
        func.sum(
            (models.Producto.precio_venta - models.Producto.precio_costo) * 
            models.ItemVenta.cantidad
        )
    ).join(
        models.ItemVenta.producto
    ).join(
        models.Venta
    ).filter(
        func.date(models.Venta.fecha) == hoy
    ).scalar() or 0
    
    # Stock bajo (menos del mínimo pero más de 10)
    stock_bajo = db.query(func.count(models.Producto.id)).filter(
        models.Producto.stock < models.Producto.stock_minimo,
        models.Producto.stock >= 10,
        models.Producto.activo == True
    ).scalar()
    
    # Stock crítico (menos de 10)
    stock_critico = db.query(func.count(models.Producto.id)).filter(
        models.Producto.stock < 10,
        models.Producto.activo == True
    ).scalar()
    
    return {
        "ventas_hoy": float(ventas_hoy),
        "cantidad_ventas_hoy": cantidad_ventas_hoy,
        "productos_vendidos_hoy": productos_vendidos_hoy,
        "ganancia_hoy": float(ganancia_hoy),
        "productos_stock_bajo": stock_bajo,
        "productos_stock_critico": stock_critico
    }

@router.get("/ventas-por-horario-fecha")
def ventas_por_horario_fecha(
    fecha: str = Query(None),  # Formato: "2024-12-10"
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Obtener ventas por horario de una fecha específica.
    Si no se proporciona fecha, muestra el día de hoy.
    """
    if fecha:
        try:
            fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
        except ValueError:
            # Si el formato es incorrecto, usar hoy
            fecha_obj = datetime.now().date()
    else:
        # Si no hay fecha, mostrar hoy
        fecha_obj = datetime.now().date()
    
    horarios = db.query(
        extract('hour', models.Venta.fecha).label('hora'),
        func.count(models.Venta.id).label('cantidad')
    ).filter(
        func.date(models.Venta.fecha) == fecha_obj
    ).group_by('hora').order_by('hora').all()
    
    # Crear array con todas las horas (0-23) para mostrar horas sin ventas
    resultado = []
    horas_con_datos = {int(h.hora): h.cantidad for h in horarios}
    
    for hora in range(24):
        resultado.append({
            "hora": f"{hora:02d}:00",
            "cantidad": horas_con_datos.get(hora, 0)
        })
    
    return resultado