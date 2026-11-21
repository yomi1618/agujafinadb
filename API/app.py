import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from marshmallow import ValidationError, validate, fields
from sqlalchemy import text, ForeignKeyConstraint
from sqlalchemy.engine import URL
from sqlalchemy.exc import IntegrityError

load_dotenv()   # lee el archivo .env (debe ir ANTES de usar os.environ)

app = Flask(__name__)

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

# La base de datos se crea con logical_model.sql (incluye CHECK, vistas e índices),
# por eso aquí NO se usa db.create_all(): los modelos solo "mapean" tablas existentes.


# =====================================================================
# MODELOS (una clase por tabla)
# =====================================================================

# ---------- Catálogo ----------
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


# ---------- Operación ----------
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
    motivo_deuda = db.Column(db.String(255))   # si no es NULL, se entregó con deuda


class DetalleEntrega(db.Model):
    __tablename__ = 'detalle_entrega'
    # Una línea de pedido solo se puede entregar una vez -> PK = id_detalle
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
        include_fk = True        # incluye las llaves foráneas (id_cliente, id_pedido...)
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
    return jsonify({'error': e.messages}), 400


@app.errorhandler(IntegrityError)
def handle_integrity(e):
    db.session.rollback()
    # Duplicados, FK (p. ej. borrar algo que tiene registros hijos) o CHECK incumplido
    return jsonify({'error': 'Operación no permitida por las reglas de la base de datos',
                    'detalle': str(e.orig)}), 409


# =====================================================================
# RUTAS CRUD (mismo patrón para cada tabla)
# =====================================================================
def register_crud(path, model, schema_cls):
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
        db.session.add(obj)
        db.session.commit()
        db.session.refresh(obj)                         # trae los valores por defecto del servidor
        return jsonify(schema.dump(obj)), 201

    def actualizar(item_id):
        obj = db.session.get(model, item_id)
        if not obj:
            return jsonify({'error': 'No encontrado'}), 404
        schema.load(request.get_json(), instance=obj, partial=True, session=db.session)
        db.session.commit()
        return jsonify(schema.dump(obj))

    def eliminar(item_id):
        obj = db.session.get(model, item_id)
        if not obj:
            return jsonify({'error': 'No encontrado'}), 404
        db.session.delete(obj)
        db.session.commit()
        return jsonify({'message': 'Eliminado correctamente'})

    app.add_url_rule(f'/{path}', f'{name}_listar', listar, methods=['GET'])
    app.add_url_rule(f'/{path}', f'{name}_crear', crear, methods=['POST'])
    app.add_url_rule(f'/{path}/<int:item_id>', f'{name}_obtener', obtener, methods=['GET'])
    app.add_url_rule(f'/{path}/<int:item_id>', f'{name}_actualizar', actualizar, methods=['PUT'])
    app.add_url_rule(f'/{path}/<int:item_id>', f'{name}_eliminar', eliminar, methods=['DELETE'])


register_crud('prendas', Prenda, PrendaSchema)
register_crud('servicios', Servicio, ServicioSchema)
register_crud('precios-servicio', PrecioServicio, PrecioServicioSchema)
register_crud('clientes', Cliente, ClienteSchema)
register_crud('pedidos', Pedido, PedidoSchema)
register_crud('detalles-pedido', DetallePedido, DetallePedidoSchema)
register_crud('entregas', Entrega, EntregaSchema)
register_crud('detalles-entrega', DetalleEntrega, DetalleEntregaSchema)
register_crud('pagos', Pago, PagoSchema)


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


if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get('PORT', 5000)))
