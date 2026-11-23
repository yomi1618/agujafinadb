import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from marshmallow import ValidationError, validate, fields
from sqlalchemy import text, ForeignKeyConstraint, or_, func
from sqlalchemy.engine import URL
from sqlalchemy.exc import IntegrityError, OperationalError

load_dotenv()

app = Flask(__name__, static_folder='gui', static_url_path='/gui')

app.config['SQLALCHEMY_DATABASE_URI'] = URL.create(
    drivername='mysql+pymysql',
    username=os.environ['DB_USER'],
    password=os.environ['DB_PASSWORD'],
    host=os.environ['DB_HOST'],
    port=int(os.environ.get('DB_PORT', 3306)),
    database=os.environ['DB_NAME'],
)

db = SQLAlchemy(app)
ma = Marshmallow(app)

# =====================================================================
# MODELOS (una clase por tabla)
# =====================================================================

# ---------- Catalogo ----------

class Prenda(db.Model):
    __tablename__ = 'prenda'
    id_prenda = db.Column(db.Integer, primary_key=True)
    tipo_prenda = db.Column(db.String(60), nullable=False, unique=True)

class Servicio(db.Model):
    __tablename__ = 'servicio'
    id_servicio = db.Column(db.Integer, primary_key=True)
    nombre_servicio = db.Column(db.String(80), nullable=False, unique=True)

class PrecioServicio(db.Model):
    __tablename__ = 'precio_servicio'
    id_precio = db.Column(db.Integer, primary_key=True)
    id_servicio = db.Column(db.Integer, db.ForeignKey('servicio.id_servicio'), nullable=False)
    id_prenda = db.Column(db.Integer, db.ForeignKey('prenda.id_prenda'), nullable=False)
    descripcion_arreglo = db.Column(db.String(120), nullable=False)
    precio_minimo = db.Column(db.Numeric(8, 2), nullable=False)
    precio_maximo = db.Column(db.Numeric(8, 2), nullable=False)

# ---------- Operacion ----------

class Cliente(db.Model):
    __tablename__ = 'cliente'
    id_cliente = db.Column(db.Integer, primary_key=True)
    tipo_cliente = db.Column(db.String(7), nullable=False)          # persona | empresa
    nombre = db.Column(db.String(150), nullable=False)
    apellido = db.Column(db.String(100))                            # solo personas
    tipo_identificacion = db.Column(db.String(20))                  # cedula | ruc
    numero_identificacion = db.Column(db.String(20))
    telefono = db.Column(db.String(20), nullable=False)
    direccion = db.Column(db.String(200))
    ciudad = db.Column(db.String(60))
    email = db.Column(db.String(120))
    fecha_registro = db.Column(db.Date, nullable=False, server_default=text('(CURRENT_DATE)'))

class Pedido(db.Model):
    __tablename__ = 'pedido'
    id_pedido = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('cliente.id_cliente'), nullable=False)
    fecha_hora_recepcion = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    descuento_porcentaje = db.Column(db.Numeric(4, 2), nullable=False, server_default='0')
    observaciones_pedido = db.Column(db.String(255))

class DetallePedido(db.Model):
    __tablename__ = 'detalle_pedido'
    id_detalle = db.Column(db.Integer, primary_key=True)
    id_precio = db.Column(db.Integer, db.ForeignKey('precio_servicio.id_precio'), nullable=False)
    id_pedido = db.Column(db.Integer, db.ForeignKey('pedido.id_pedido'), nullable=False)
    precio_acordado = db.Column(db.Numeric(8, 2), nullable=False)
    fecha_entrega_estimada = db.Column(db.Date, nullable=False)
    usa_repuesto = db.Column(db.Boolean, nullable=False, server_default=db.false())
    notas = db.Column(db.String(255))

# ---------- Salida ----------

class Entrega(db.Model):
    __tablename__ = 'entrega'
    id_entrega = db.Column(db.Integer, primary_key=True)
    id_pedido = db.Column(db.Integer, db.ForeignKey('pedido.id_pedido'), nullable=False)
    fecha_hora_entrega = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    observaciones_entrega = db.Column(db.String(255))
    motivo_deuda = db.Column(db.String(255))   # si no es NULL, se entrego con deuda

class DetalleEntrega(db.Model):
    __tablename__ = 'detalle_entrega'
    # Una linea de pedido solo se puede entregar una vez -> PK = id_detalle
    id_detalle = db.Column(db.Integer, primary_key=True)
    id_entrega = db.Column(db.Integer, nullable=False)
    id_pedido = db.Column(db.Integer, nullable=False)
    # FK compuestas: garantizan que entrega y detalle pertenezcan al MISMO pedido
    __table_args__ = (
        ForeignKeyConstraint(['id_entrega', 'id_pedido'],
                             ['entrega.id_entrega', 'entrega.id_pedido']),
        ForeignKeyConstraint(['id_detalle', 'id_pedido'],
                             ['detalle_pedido.id_detalle', 'detalle_pedido.id_pedido']),
    )

class Pago(db.Model):
    __tablename__ = 'pago'
    id_pago = db.Column(db.Integer, primary_key=True)
    id_pedido = db.Column(db.Integer, db.ForeignKey('pedido.id_pedido'), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    fecha_hora_pago = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    tipo_pago = db.Column(db.String(12), nullable=False)       # adelanto | saldo_final
    metodo_pago = db.Column(db.String(15), nullable=False)     # efectivo | transferencia | cheque

# =====================================================================
# ESQUEMAS (Marshmallow): validan lo que entra y dan formato a lo que sale
# =====================================================================

class BaseSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        include_fk = True        # incluye las llaves foraneas (id_cliente, id_pedido...)
        load_instance = True     # load() devuelve objetos del modelo

class PrendaSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = Prenda
        dump_only = ('id_prenda',)

class ServicioSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = Servicio
        dump_only = ('id_servicio',)

class PrecioServicioSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = PrecioServicio
        dump_only = ('id_precio',)

class ClienteSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = Cliente
        dump_only = ('id_cliente',)

    tipo_cliente = fields.String(required=True, validate=validate.OneOf(['persona', 'empresa']))
    tipo_identificacion = fields.String(allow_none=True, validate=validate.OneOf(['cedula', 'ruc']))
    nombre = fields.String(required=True,
                           validate=[validate.Length(max=150),
                                     validate.Regexp(r'^\s*\S', error='No puede estar vacio')])
    telefono = fields.String(required=True,
                             validate=[validate.Length(max=20),
                                       validate.Regexp(r'^\s*\S', error='No puede estar vacio')])

class PedidoSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = Pedido
        dump_only = ('id_pedido',)

class DetallePedidoSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = DetallePedido
        dump_only = ('id_detalle',)

class EntregaSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = Entrega
        dump_only = ('id_entrega',)

class DetalleEntregaSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = DetalleEntrega
        dump_only = ('id_detalle', 'id_entrega', 'id_pedido')

class PagoSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = Pago
        dump_only = ('id_pago',)

    tipo_pago = fields.String(required=True, validate=validate.OneOf(['adelanto', 'saldo_final']))
    metodo_pago = fields.String(required=True,
                                validate=validate.OneOf(['efectivo', 'transferencia', 'cheque']))

# =====================================================================
# MANEJO DE ERRORES (las reglas CHECK/FK de MySQL se traducen a HTTP)
# =====================================================================
@app.errorhandler(ValidationError)
def handle_validation(e):
    db.session.rollback()
    return jsonify({'error': e.normalized_messages()}), 400

@app.errorhandler(OperationalError)
def handle_operational(e):
    db.session.rollback()
    codigo = e.orig.args[0] if e.orig is not None and e.orig.args else None
    if codigo == 3819:   # CHECK de MySQL incumplido
        return jsonify({'error': 'Operacion no permitida por las reglas de la base de datos',
                        'detalle': str(e.orig)}), 409
    return jsonify({'error': 'Error de base de datos', 'detalle': str(e.orig)}), 500

@app.errorhandler(IntegrityError)
def handle_integrity(e):
    db.session.rollback()
    # Duplicados, FK (p. ej. borrar algo que tiene registros hijos) o CHECK incumplido
    return jsonify({'error': 'Operacion no permitida por las reglas de la base de datos',
                    'detalle': str(e.orig)}), 409

# =====================================================================
# RUTAS CRUD (mismo patron para cada tabla)
# =====================================================================
def validar_linea(det):
    """Reglas de una linea de pedido (FR-07, FR-08). Recibe un DetallePedido."""
    ps = db.session.get(PrecioServicio, det.id_precio)
    if ps is None:
        raise ValidationError('El precio de servicio no existe', 'id_precio')
    if not (ps.precio_minimo <= det.precio_acordado <= ps.precio_maximo):
        raise ValidationError(
            f'precio_acordado debe estar entre {ps.precio_minimo} y {ps.precio_maximo}',
            'precio_acordado')
    ped = db.session.get(Pedido, det.id_pedido)
    if ped is None:
        raise ValidationError('El pedido no existe', 'id_pedido')
    if ped.fecha_hora_recepcion and det.fecha_entrega_estimada < ped.fecha_hora_recepcion.date():
        raise ValidationError('La fecha estimada es anterior a la recepcion',
                              'fecha_entrega_estimada')

def validar_pago(p):
    r = consultar_vista('SELECT total_neto FROM v_pedido_resumen WHERE id_pedido = :id',
                        id=p.id_pedido)
    if not r:
        raise ValidationError('El pedido no existe', 'id_pedido')
    otros = db.session.query(db.func.coalesce(db.func.sum(Pago.monto), 0)).filter(
        Pago.id_pedido == p.id_pedido, Pago.id_pago != p.id_pago).scalar()
    if otros + p.monto > r[0]['total_neto']:
        raise ValidationError('La suma de pagos supera el total del pedido', 'monto')

def no_borrar_ultima_linea(det):
    n = DetallePedido.query.filter_by(id_pedido=det.id_pedido).count()
    if n <= 1:
        raise ValidationError('El pedido debe conservar al menos una linea', 'detalles')

def no_borrar_ultima_linea_entrega(de):
    n = DetalleEntrega.query.filter_by(id_entrega=de.id_entrega).count()
    if n <= 1:
        raise ValidationError('La entrega debe conservar al menos una linea', 'lineas')

def register_crud(path, model, schema_cls, validar=None, permitir_crear=True, validar_eliminar=None):
    schema = schema_cls()
    schemas = schema_cls(many=True)
    name = model.__tablename__

    def listar():
        q = model.query
        for campo, valor in request.args.items():       # filtros: /pedidos?id_cliente=3
            if hasattr(model, campo):
                q = q.filter(getattr(model, campo) == valor)
        return jsonify(schemas.dump(q.all()))

    def obtener(item_id):
        obj = db.session.get(model, item_id)
        if not obj:
            return jsonify({'error': 'No encontrado'}), 404
        return jsonify(schema.dump(obj))

    def crear():
        obj = schema.load(request.get_json(), session=db.session)
        if validar:
            validar(obj)
        db.session.add(obj)
        db.session.commit()
        db.session.refresh(obj)                         # trae los valores por defecto del servidor
        return jsonify(schema.dump(obj)), 201

    def actualizar(item_id):
        obj = db.session.get(model, item_id)
        if not obj:
            return jsonify({'error': 'No encontrado'}), 404
        schema.load(request.get_json(), instance=obj, partial=True, session=db.session)
        if validar:
            validar(obj)
        db.session.commit()
        return jsonify(schema.dump(obj))

    def eliminar(item_id):
        obj = db.session.get(model, item_id)
        if not obj:
            return jsonify({'error': 'No encontrado'}), 404
        if validar_eliminar:
            validar_eliminar(obj)
        db.session.delete(obj)
        db.session.commit()
        return jsonify({'message': 'Eliminado correctamente'})

    app.add_url_rule(f'/{path}', f'{name}_listar', listar, methods=['GET'])
    if permitir_crear:
        app.add_url_rule(f'/{path}', f'{name}_crear', crear, methods=['POST'])
    app.add_url_rule(f'/{path}/<int:item_id>', f'{name}_obtener', obtener, methods=['GET'])
    app.add_url_rule(f'/{path}/<int:item_id>', f'{name}_actualizar', actualizar, methods=['PUT'])
    app.add_url_rule(f'/{path}/<int:item_id>', f'{name}_eliminar', eliminar, methods=['DELETE'])

register_crud('prendas', Prenda, PrendaSchema)
register_crud('servicios', Servicio, ServicioSchema)
register_crud('precios-servicio', PrecioServicio, PrecioServicioSchema)
register_crud('clientes', Cliente, ClienteSchema)
register_crud('pedidos', Pedido, PedidoSchema, permitir_crear=False)
register_crud('detalles-pedido', DetallePedido, DetallePedidoSchema, validar=validar_linea, validar_eliminar=no_borrar_ultima_linea)
register_crud('entregas', Entrega, EntregaSchema, permitir_crear=False)
register_crud('detalles-entrega', DetalleEntrega, DetalleEntregaSchema, permitir_crear=False, validar_eliminar=no_borrar_ultima_linea_entrega)
register_crud('pagos', Pago, PagoSchema, validar=validar_pago)

@app.route('/pedidos', methods=['POST'])
def crear_pedido_completo():
    data = request.get_json() or {}
    lineas = data.pop('detalles', None)
    if not isinstance(lineas, list) or len(lineas) == 0:
        raise ValidationError('El pedido debe tener al menos una linea', 'detalles')
    pedido = PedidoSchema().load(data, session=db.session)
    db.session.add(pedido)
    db.session.flush()
    db.session.refresh(pedido)          # trae fecha_hora_recepcion del servidor

    detalles = []
    for l in lineas:
        l['id_pedido'] = pedido.id_pedido
        det = DetallePedidoSchema().load(l, session=db.session)
        validar_linea(det)
        db.session.add(det)
        detalles.append(det)

    db.session.commit()
    return jsonify({
        'pedido': PedidoSchema().dump(pedido),
        'detalles': DetallePedidoSchema(many=True).dump(detalles),
    }), 201

@app.route('/pedidos/<int:id_pedido>/entregas', methods=['POST'])
def registrar_entrega(id_pedido):
    data = request.get_json() or {}
    lineas = data.get('lineas')
    if not isinstance(lineas, list) or len(lineas) == 0:
        return jsonify({'error': 'La entrega debe incluir al menos una línea'}), 400
    if not all(isinstance(x, int) and not isinstance(x, bool) for x in lineas):
        return jsonify({'error': 'lineas debe contener ids enteros'}), 400
    if len(set(lineas)) != len(lineas):
        return jsonify({'error': 'Hay líneas repetidas en la entrega'}), 400
    pago = data.get('pago')
    if pago is not None and not isinstance(pago, dict):
        return jsonify({'error': 'pago debe ser un objeto'}), 400

    pedido = db.session.get(Pedido, id_pedido, with_for_update=True)
    if not pedido:
        return jsonify({'error': 'Pedido no encontrado'}), 404

    entrega = Entrega(id_pedido=id_pedido,
                      observaciones_entrega=data.get('observaciones_entrega'))
    db.session.add(entrega)
    db.session.flush()

    for id_det in lineas:   # PK y FK compuestas rechazan repetidas o de otro pedido (409)
        db.session.add(DetalleEntrega(id_entrega=entrega.id_entrega,
                                      id_detalle=id_det, id_pedido=id_pedido))

    if pago:
        pago['id_pedido'] = id_pedido
        pago['tipo_pago'] = 'saldo_final'
        db.session.add(PagoSchema().load(pago, session=db.session))
    db.session.flush()

    r = consultar_vista('SELECT saldo_total_pendiente, deuda_exigible '
                        'FROM v_pedido_resumen WHERE id_pedido = :id', id=id_pedido)[0]
    if r['saldo_total_pendiente'] < 0:
        db.session.rollback()
        return jsonify({'error': 'Los pagos superan el total del pedido'}), 400
    if r['deuda_exigible'] > 0:
        motivo = (data.get('motivo_deuda') or '').strip()
        if not motivo:
            db.session.rollback()
            return jsonify({'error': 'Se requiere motivo_deuda'}), 400
        entrega.motivo_deuda = motivo

    db.session.commit()
    return jsonify(EntregaSchema().dump(entrega)), 201

# =====================================================================
# RUTAS DE SOLO LECTURA sobre las VISTAS
# =====================================================================
def consultar_vista(sql, **params):
    filas = db.session.execute(text(sql), params).mappings().all()
    return [dict(f) for f in filas]

@app.route('/pedidos/<int:id_pedido>/resumen', methods=['GET'])
def resumen_pedido(id_pedido):
    datos = consultar_vista('SELECT * FROM v_pedido_resumen WHERE id_pedido = :id', id=id_pedido)
    if not datos:
        return jsonify({'error': 'Pedido no encontrado'}), 404
    return jsonify(datos[0])

@app.route('/clientes/<int:id_cliente>/deuda', methods=['GET'])
def deuda_cliente(id_cliente):
    datos = consultar_vista('SELECT * FROM v_cliente_deuda WHERE id_cliente = :id', id=id_cliente)
    if not datos:
        return jsonify({'error': 'Cliente no encontrado'}), 404
    return jsonify(datos[0])

@app.route('/clientes/con-deuda', methods=['GET'])
def clientes_con_deuda():
    return jsonify(consultar_vista(
        'SELECT * FROM v_cliente_deuda WHERE saldo_pendiente > 0 ORDER BY saldo_pendiente DESC'))

@app.route('/clientes/buscar', methods=['GET'])
def buscar_clientes():
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify([])
    filas = consultar_vista("""
        SELECT c.id_cliente, c.tipo_cliente, c.nombre, c.apellido,
               c.tipo_identificacion, c.numero_identificacion, c.telefono,
               c.direccion, c.ciudad, c.email, c.fecha_registro,
               COALESCE(d.saldo_pendiente, 0) AS saldo_pendiente
        FROM cliente c
        LEFT JOIN v_cliente_deuda d ON d.id_cliente = c.id_cliente
        WHERE c.nombre LIKE :patron
           OR c.apellido LIKE :patron
           OR c.telefono LIKE :patron
           OR CONCAT_WS(' ', c.nombre, c.apellido) LIKE :patron
        ORDER BY c.nombre, c.apellido
    """, patron=f'%{q}%')
    for f in filas:
        f['fecha_registro'] = f['fecha_registro'].isoformat()
        f['alerta_deuda'] = f['saldo_pendiente'] > 0     # la GUI muestra la alerta con esto
    return jsonify(filas)

@app.route('/clientes/<int:id_cliente>/pedidos', methods=['GET'])
def pedidos_cliente(id_cliente):
    sql = 'SELECT * FROM v_pedido_resumen WHERE id_cliente = :id'
    params = {'id': id_cliente}
    if request.args.get('estado') in ('activo', 'entregado'):
        sql += ' AND estado = :estado'
        params['estado'] = request.args['estado']
    return jsonify(consultar_vista(sql + ' ORDER BY id_pedido DESC', **params))

@app.route('/prendas/<int:id_prenda>/servicios', methods=['GET'])
def servicios_por_prenda(id_prenda):
    """Nivel 2: servicios disponibles para la prenda elegida."""
    return jsonify(consultar_vista("""
        SELECT DISTINCT s.id_servicio, s.nombre_servicio
        FROM precio_servicio ps
        JOIN servicio s ON s.id_servicio = ps.id_servicio
        WHERE ps.id_prenda = :p
        ORDER BY s.nombre_servicio
    """, p=id_prenda))

@app.route('/prendas/<int:id_prenda>/servicios/<int:id_servicio>/descripciones', methods=['GET'])
def descripciones_por_prenda_servicio(id_prenda, id_servicio):
    """Nivel 3: descripciones con su id_precio y rango minimo/maximo."""
    return jsonify(consultar_vista("""
        SELECT id_precio, descripcion_arreglo, precio_minimo, precio_maximo
        FROM precio_servicio
        WHERE id_prenda = :p AND id_servicio = :s
        ORDER BY descripcion_arreglo
    """, p=id_prenda, s=id_servicio))

@app.route('/pedidos/<int:id_pedido>/lineas', methods=['GET'])
def lineas_pedido(id_pedido):
    if db.session.get(Pedido, id_pedido) is None:
        return jsonify({'error': 'Pedido no encontrado'}), 404
    filas = consultar_vista("""
        SELECT dp.id_detalle, pr.tipo_prenda, s.nombre_servicio, ps.descripcion_arreglo,
               ps.precio_minimo, ps.precio_maximo, dp.precio_acordado,
               dp.fecha_entrega_estimada, dp.usa_repuesto, dp.notas,
               ed.id_entrega, (ed.id_detalle IS NOT NULL) AS entregada
        FROM detalle_pedido dp
        JOIN precio_servicio ps ON ps.id_precio = dp.id_precio
        JOIN prenda pr ON pr.id_prenda = ps.id_prenda
        JOIN servicio s ON s.id_servicio = ps.id_servicio
        LEFT JOIN detalle_entrega ed ON ed.id_detalle = dp.id_detalle
        WHERE dp.id_pedido = :id
        ORDER BY dp.id_detalle
    """, id=id_pedido)
    for f in filas:
        f['entregada'] = bool(f['entregada'])
        f['usa_repuesto'] = bool(f['usa_repuesto'])
        f['fecha_entrega_estimada'] = f['fecha_entrega_estimada'].isoformat()
    return jsonify(filas)

@app.route('/')
def inicio():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get('PORT', 5000)))
