import os
from datetime import date
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify
from flask_cors import CORS


app = Flask(__name__)
CORS(app)


def get_conn():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise Exception("Falta configurar DATABASE_URL en Render")
    return psycopg2.connect(database_url)


def convertir_valores(row):
    resultado = {}
    for k, v in row.items():
        if isinstance(v, Decimal):
            resultado[k] = float(v)
        elif isinstance(v, date):
            resultado[k] = v.isoformat()
        else:
            resultado[k] = v
    return resultado


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS movimientos_financieros (
            id SERIAL PRIMARY KEY,
            fecha DATE NOT NULL DEFAULT CURRENT_DATE,
            tipo TEXT NOT NULL,
            categoria TEXT NOT NULL,
            descripcion TEXT,
            monto NUMERIC(12,2) NOT NULL,
            origen TEXT DEFAULT 'manual',
            nota_id TEXT,
            comprobante TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mov_fin_nota_pagada
        ON movimientos_financieros(nota_id)
        WHERE origen = 'nota_pagada'
    """)

    conn.commit()
    cur.close()
    conn.close()


@app.route("/")
def home():
    return jsonify({
        "ok": True,
        "mensaje": "API de contabilidad funcionando"
    })


@app.route("/api/movimientos", methods=["GET"])
def listar_movimientos():
    init_db()

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT
            id,
            fecha,
            tipo,
            categoria,
            descripcion,
            monto,
            origen,
            nota_id,
            comprobante,
            created_at
        FROM movimientos_financieros
        ORDER BY fecha DESC, id DESC
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([convertir_valores(r) for r in rows])


@app.route("/api/movimientos", methods=["POST"])
def crear_movimiento():
    init_db()

    data = request.get_json() or {}

    fecha = data.get("fecha")
    tipo = data.get("tipo")
    categoria = data.get("categoria")
    descripcion = data.get("descripcion", "")
    monto = data.get("monto")
    origen = data.get("origen", "manual")
    nota_id = data.get("nota_id")
    comprobante = data.get("comprobante")

    if tipo not in ["ingreso", "gasto"]:
        return jsonify({"ok": False, "error": "Tipo inválido"}), 400

    if not categoria:
        return jsonify({"ok": False, "error": "Falta categoría"}), 400

    try:
        monto = float(monto)
    except Exception:
        return jsonify({"ok": False, "error": "Monto inválido"}), 400

    if monto <= 0:
        return jsonify({"ok": False, "error": "El monto debe ser mayor a 0"}), 400

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        INSERT INTO movimientos_financieros
        (fecha, tipo, categoria, descripcion, monto, origen, nota_id, comprobante)
        VALUES (
            COALESCE(%s::date, CURRENT_DATE),
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
        RETURNING *
    """, (
        fecha,
        tipo,
        categoria,
        descripcion,
        monto,
        origen,
        nota_id,
        comprobante
    ))

    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "ok": True,
        "movimiento": convertir_valores(row)
    })


@app.route("/api/movimientos/<int:movimiento_id>", methods=["DELETE"])
def eliminar_movimiento(movimiento_id):
    init_db()

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM movimientos_financieros
        WHERE id = %s
    """, (movimiento_id,))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"ok": True})


@app.route("/api/ingreso-nota", methods=["POST"])
def ingreso_desde_nota():
    init_db()

    data = request.get_json() or {}

    nota_id = str(data.get("nota_id") or "").strip()
    cliente = data.get("cliente", "")
    monto = data.get("monto")
    comprobante = data.get("comprobante", "")

    if not nota_id:
        return jsonify({"ok": False, "error": "Falta nota_id"}), 400

    try:
        monto = float(monto)
    except Exception:
        return jsonify({"ok": False, "error": "Monto inválido"}), 400

    if monto <= 0:
        return jsonify({"ok": False, "error": "El monto debe ser mayor a 0"}), 400

    descripcion = f"Pago nota #{nota_id}"
    if cliente:
        descripcion += f" - {cliente}"

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            INSERT INTO movimientos_financieros
            (fecha, tipo, categoria, descripcion, monto, origen, nota_id, comprobante)
            VALUES (
                CURRENT_DATE,
                'ingreso',
                'Ventas',
                %s,
                %s,
                'nota_pagada',
                %s,
                %s
            )
            RETURNING *
        """, (
            descripcion,
            monto,
            nota_id,
            comprobante
        ))

        row = cur.fetchone()
        conn.commit()

        respuesta = {
            "ok": True,
            "duplicado": False,
            "movimiento": convertir_valores(row)
        }

    except psycopg2.errors.UniqueViolation:
        conn.rollback()

        cur.execute("""
            SELECT *
            FROM movimientos_financieros
            WHERE origen = 'nota_pagada'
            AND nota_id = %s
            LIMIT 1
        """, (nota_id,))

        row = cur.fetchone()

        respuesta = {
            "ok": True,
            "duplicado": True,
            "mensaje": "Esta nota ya tenía ingreso registrado",
            "movimiento": convertir_valores(row) if row else None
        }

    cur.close()
    conn.close()

    return jsonify(respuesta)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
