import os
import io
import sqlite3
from datetime import datetime
from flask import Flask, jsonify, request as REQ, Response, render_template_string
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

App = Flask(__name__)
App.config['JSON_AS_ASCII'] = False

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'datalogger.db')


def init_db():
    """Crea la base de datos SQLite y la tabla de mediciones con DateTime si no existen."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mediciones (
                id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
                uma_id INTEGER NOT NULL,
                mp01 INTEGER NOT NULL,
                mp02 INTEGER NOT NULL,
                mp03 INTEGER NOT NULL,
                hi01 INTEGER NOT NULL,
                hi02 INTEGER NOT NULL,
                hi03 INTEGER NOT NULL,
                hi04 INTEGER NOT NULL,
                hi05 INTEGER NOT NULL,
                hi06 INTEGER NOT NULL,
                te INTEGER NOT NULL,
                hr INTEGER NOT NULL,
                fecha_hora TEXT NOT NULL
            )
        """)
        conn.commit()


def row_to_dict(row):
    return {
        'id_registro': row[0],
        'id': row[1],
        'uma': f'UMA {row[1]}',
        'mp01': row[2],
        'mp02': row[3],
        'mp03': row[4],
        'hi01': row[5],
        'hi02': row[6],
        'hi03': row[7],
        'hi04': row[8],
        'hi05': row[9],
        'hi06': row[10],
        'te': row[11],
        'hr': row[12],
        'datetime': row[13]
    }


@App.route('/data', methods=['POST', 'GET'])
def get_data():
    """
    POST: Recibe los datos JSON enviados desde Lazarus Pascal (TFPHttpClient),
          los imprime en consola y los almacena en SQLite con DateTime.
    GET:  Permite consultar todos los registros en formato JSON desde el navegador.
    """
    if REQ.method == 'GET':
        return api_obtener_registros()

    dD = REQ.get_json(force=True, silent=True)
    if not dD:
        return jsonify({'status': 'error', 'mensaje': 'JSON inválido o vacío'}), 400

    fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print(
        f"[{fecha_actual}] UMA:", dD['id'],
        "| MP:", dD['mp01'], dD['mp02'], dD['mp03'],
        "| Histo:", dD['hi01'], dD['hi02'], dD['hi03'], dD['hi04'], dD['hi05'], dD['hi06'],
        "| Temp/HR:", dD['te'], dD['hr']
    )

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO mediciones (
                uma_id, mp01, mp02, mp03,
                hi01, hi02, hi03, hi04, hi05, hi06,
                te, hr, fecha_hora
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            int(dD.get('id', 1)),
            int(dD.get('mp01', 0)),
            int(dD.get('mp02', 0)),
            int(dD.get('mp03', 0)),
            int(dD.get('hi01', 0)),
            int(dD.get('hi02', 0)),
            int(dD.get('hi03', 0)),
            int(dD.get('hi04', 0)),
            int(dD.get('hi05', 0)),
            int(dD.get('hi06', 0)),
            int(dD.get('te', 0)),
            int(dD.get('hr', 0)),
            fecha_actual
        ))
        conn.commit()

    return 'Todo OK'


# ==============================================================================
# ENDPOINTS API REST (CONSULTAS EN FORMATO JSON EN EL NAVEGADOR)
# ==============================================================================

@App.route('/api/registros', methods=['GET'])
@App.route('/registros', methods=['GET'])
def api_obtener_registros():
    """
    Endpoint API REST para consultar en el navegador los registros en formato JSON.
    Soporta parámetros opcionales: ?uma=1..5 y ?limit=100
    """
    uma_id = REQ.args.get('uma', type=int)
    limit = REQ.args.get('limit', default=100, type=int)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        if uma_id:
            cursor.execute("""
                SELECT * FROM mediciones
                WHERE uma_id = ?
                ORDER BY id_registro DESC
                LIMIT ?
            """, (uma_id, limit))
        else:
            cursor.execute("""
                SELECT * FROM mediciones
                ORDER BY id_registro DESC
                LIMIT ?
            """, (limit,))
        rows = cursor.fetchall()

    registros = [row_to_dict(r) for r in rows]
    return jsonify({
        'total_registros': len(registros),
        'filtro_uma': uma_id if uma_id else 'Todas (UMA 1-5)',
        'fecha_consulta': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'registros': registros
    })


@App.route('/api/registros/<int:uma_id>', methods=['GET'])
def api_obtener_por_uma(uma_id):
    """Consulta en formato JSON filtrada por ID de Unidad Medio Ambiental (UMA 1..5)."""
    limit = REQ.args.get('limit', default=100, type=int)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM mediciones
            WHERE uma_id = ?
            ORDER BY id_registro DESC
            LIMIT ?
        """, (uma_id, limit))
        rows = cursor.fetchall()

    registros = [row_to_dict(r) for r in rows]
    return jsonify({
        'uma_id': uma_id,
        'total_registros': len(registros),
        'fecha_consulta': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'registros': registros
    })


@App.route('/api/ultimo', methods=['GET'])
def api_ultimo_registro():
    """Devuelve en formato JSON la última medición registrada en la base de datos."""
    uma_id = REQ.args.get('uma', type=int)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        if uma_id:
            cursor.execute("SELECT * FROM mediciones WHERE uma_id = ? ORDER BY id_registro DESC LIMIT 1", (uma_id,))
        else:
            cursor.execute("SELECT * FROM mediciones ORDER BY id_registro DESC LIMIT 1")
        row = cursor.fetchone()

    if not row:
        return jsonify({'mensaje': 'No hay registros almacenados aún.'}), 404
    return jsonify(row_to_dict(row))


@App.route('/api/estadisticas', methods=['GET'])
def api_estadisticas():
    """Devuelve estadísticas resumidas por UMA en formato JSON."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT uma_id,
                   COUNT(*) as total,
                   ROUND(AVG(mp01), 2),
                   ROUND(AVG(mp02), 2),
                   ROUND(AVG(mp03), 2),
                   ROUND(AVG(te), 2),
                   ROUND(AVG(hr), 2),
                   MIN(fecha_hora),
                   MAX(fecha_hora)
            FROM mediciones
            GROUP BY uma_id
            ORDER BY uma_id ASC
        """)
        rows = cursor.fetchall()

    resumen = []
    for r in rows:
        resumen.append({
            'uma_id': r[0],
            'total_muestras': r[1],
            'promedio_mp01_ug_m3': r[2],
            'promedio_mp25_ug_m3': r[3],
            'promedio_mp10_ug_m3': r[4],
            'promedio_temperatura_c': r[5],
            'promedio_humedad_relativa_pct': r[6],
            'primera_medicion': r[7],
            'ultima_medicion': r[8]
        })
    return jsonify({
        'fecha_consulta': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'estadisticas_por_uma': resumen
    })


# ==============================================================================
# GENERACIÓN DE GRÁFICA CON MATPLOTLIB EN EL NAVEGADOR
# ==============================================================================

@App.route('/grafica.png', methods=['GET'])
def generar_grafica_png():
    """Genera una imagen PNG con Matplotlib a partir de los registros en SQLite."""
    uma_id = REQ.args.get('uma', type=int)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        if uma_id:
            cursor.execute("""
                SELECT * FROM (
                    SELECT * FROM mediciones WHERE uma_id = ? ORDER BY id_registro DESC LIMIT 12
                ) ORDER BY id_registro ASC
            """, (uma_id,))
        else:
            cursor.execute("""
                SELECT * FROM (
                    SELECT * FROM mediciones ORDER BY id_registro DESC LIMIT 12
                ) ORDER BY id_registro ASC
            """)
        rows = cursor.fetchall()

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), dpi=110)
    fig.patch.set_facecolor('#f8fafc')

    titulo_uma = f"UMA {uma_id}" if uma_id else "Todas las Unidades (UMA 1-5)"
    fig.suptitle(f"Data Logger Ambiental INFO1128 - Reporte Matplotlib ({titulo_uma})",
                 fontsize=13, fontweight='bold', color='#0f172a', y=0.98)

    if not rows:
        for ax in axes:
            ax.text(0.5, 0.5, 'Sin datos en SQLite aún', ha='center', va='center', fontsize=12)
            ax.set_axis_off()
    else:
        indices = list(range(len(rows)))
        etiquetas_x = [r[13].split(' ')[-1] if ' ' in r[13] else str(i) for i, r in enumerate(rows)]
        mp01_vals = [r[2] for r in rows]
        mp25_vals = [r[3] for r in rows]
        mp10_vals = [r[4] for r in rows]
        te_vals = [r[11] for r in rows]
        hr_vals = [r[12] for r in rows]

        # Panel 1: Series de Tiempo Material Particulado (MP01, MP25, MP10)
        ax1 = axes[0]
        ax1.set_facecolor('#eef6ff')
        ax1.plot(indices, mp01_vals, marker='s', color='#dc2626', linewidth=2, label='MP 1.0 (ug/m3)')
        ax1.plot(indices, mp25_vals, marker='o', color='#16a34a', linewidth=2, label='MP 2.5 (ug/m3)')
        ax1.plot(indices, mp10_vals, marker='^', color='#2563eb', linewidth=2, label='MP 10 (ug/m3)')
        for idx, val in zip(indices, mp01_vals):
            ax1.annotate(str(val), (idx, val), textcoords="offset points", xytext=(0, 6),
                         ha='center', fontsize=8, fontweight='bold', color='white',
                         bbox=dict(boxstyle='square,pad=0.2', fc='#dc2626', ec='black', lw=0.6))
        ax1.set_title('Datos Ambientales (Series MP)', fontweight='bold', fontsize=11)
        ax1.set_xlabel('Hora de Medición (DateTime)')
        ax1.set_ylabel('Concentración (ug/m3)')
        ax1.set_xticks(indices)
        ax1.set_xticklabels(etiquetas_x, rotation=35, fontsize=8)
        ax1.grid(True, linestyle='--', alpha=0.5)
        ax1.legend(loc='upper right', fontsize=8)

        # Panel 2: Histograma MP de la última muestra recibida
        ax2 = axes[1]
        ax2.set_facecolor('#ecfdf5')
        ultima = rows[-1]
        diametros = ['0.3um', '0.5um', '1.0um', '2.5um', '5.0um', '10um']
        conteos = [ultima[5], ultima[6], ultima[7], ultima[8], ultima[9], ultima[10]]
        colores = ['#ef4444', '#15803d', '#1d4ed8', '#eab308', '#22c55e', '#93c5fd']
        barras = ax2.bar(diametros, conteos, color=colores, edgecolor='#1e293b', linewidth=1.1)
        for bar, c in zip(barras, conteos):
            ax2.annotate(f'{c}',
                         xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                         xytext=(0, 4), textcoords="offset points",
                         ha='center', va='bottom', fontsize=8, fontweight='bold',
                         bbox=dict(boxstyle='square,pad=0.2', fc='#fef08a', ec='#1e293b', lw=0.6))
        ax2.set_title(f'Histograma MP (Última Muestra UMA {ultima[1]})', fontweight='bold', fontsize=11)
        ax2.set_xlabel('Diámetro de Partículas (um)')
        ax2.set_ylabel('Conteo de Partículas')
        ax2.set_ylim(0, max(conteos + [1000]) * 1.18)
        ax2.grid(axis='y', linestyle='--', alpha=0.5)

        # Panel 3: Temperatura y Humedad Relativa
        ax3 = axes[2]
        ax3.set_facecolor('#fff7ed')
        ax3.plot(indices, te_vals, marker='o', color='#dc2626', linewidth=2, label='Temperatura (°C)')
        ax3.plot(indices, hr_vals, marker='d', color='#2563eb', linewidth=2, label='Humedad Relativa (%)')
        ax3.set_title('Temperatura y Humedad Relativa', fontweight='bold', fontsize=11)
        ax3.set_xlabel('Hora de Medición (DateTime)')
        ax3.set_ylabel('Valor (°C / %)')
        ax3.set_xticks(indices)
        ax3.set_xticklabels(etiquetas_x, rotation=35, fontsize=8)
        ax3.grid(True, linestyle='--', alpha=0.5)
        ax3.legend(loc='upper right', fontsize=8)

    plt.tight_layout(rect=[0, 0, 1, 0.93])
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    return Response(buf.getvalue(), mimetype='image/png')


# ==============================================================================
# DASHBOARD WEB PRINCIPAL Y VISUALIZACIÓN EN NAVEGADOR
# ==============================================================================

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Data Logger Ambiental - INFO1128</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f1f5f9;
            color: #1e293b;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1250px;
            margin: 0 auto;
            background: #ffffff;
            padding: 24px;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }
        h1 {
            margin-top: 0;
            color: #0f172a;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 10px;
        }
        .toolbar {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 18px;
            background: #f8fafc;
            padding: 12px 16px;
            border-radius: 8px;
            border: 1px solid #cbd5e1;
        }
        .btn {
            display: inline-block;
            padding: 8px 14px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 600;
            font-size: 14px;
            background: #2563eb;
            color: white;
        }
        .btn:hover { background: #1d4ed8; }
        .btn-json { background: #059669; }
        .btn-json:hover { background: #047857; }
        .btn-active { background: #dc2626; }
        .chart-box {
            text-align: center;
            margin: 15px 0 25px 0;
            padding: 12px;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            background: #f8fafc;
        }
        .chart-box img {
            max-width: 100%;
            height: auto;
            border-radius: 6px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13.5px;
        }
        th, td {
            border: 1px solid #cbd5e1;
            padding: 8px 10px;
            text-align: center;
        }
        th {
            background-color: #1e293b;
            color: #ffffff;
        }
        tr:nth-child(even) { background-color: #f8fafc; }
        .badge-temp { color: #dc2626; font-weight: bold; }
        .badge-hr { color: #2563eb; font-weight: bold; }
    </style>
</head>
<body>
<div class="container">
    <h1>Data Logger Ambiental INFO1128 - Servidor Flask + SQLite + Matplotlib</h1>

    <div class="toolbar">
        <div>
            <strong>Filtrar Gráfica y Tabla por UMA:</strong>
            <a href="/?uma=" class="btn {% if not uma_id %}btn-active{% endif %}">Todas</a>
            {% for i in range(1, 6) %}
                <a href="/?uma={{ i }}" class="btn {% if uma_id == i %}btn-active{% endif %}">UMA {{ i }}</a>
            {% endfor %}
        </div>
        <div>
            <strong>Consultas API REST (Formato JSON):</strong>
            <a href="/api/registros" target="_blank" class="btn btn-json">JSON Todos (/api/registros)</a>
            {% if uma_id %}
                <a href="/api/registros/{{ uma_id }}" target="_blank" class="btn btn-json">JSON UMA {{ uma_id }}</a>
            {% endif %}
            <a href="/api/ultimo" target="_blank" class="btn btn-json">JSON Último (/api/ultimo)</a>
            <a href="/api/estadisticas" target="_blank" class="btn btn-json">JSON Estadísticas</a>
        </div>
    </div>

    <div class="chart-box">
        <img src="/grafica.png{% if uma_id %}?uma={{ uma_id }}{% endif %}" alt="Gráfica Matplotlib en Tiempo Real">
    </div>

    <h3>Últimos Registros Almacenados en SQLite (con DateTime)</h3>
    <table>
        <thead>
            <tr>
                <th>ID Reg</th>
                <th>DateTime</th>
                <th>UMA</th>
                <th>MP 1.0</th>
                <th>MP 2.5</th>
                <th>MP 10</th>
                <th>0.3um</th>
                <th>0.5um</th>
                <th>1.0um</th>
                <th>2.5um</th>
                <th>5.0um</th>
                <th>10um</th>
                <th>Temp (°C)</th>
                <th>Hu Re (%)</th>
            </tr>
        </thead>
        <tbody>
            {% for r in registros %}
            <tr>
                <td>{{ r.id_registro }}</td>
                <td><strong>{{ r.datetime }}</strong></td>
                <td>UMA {{ r.id }}</td>
                <td>{{ r.mp01 }}</td>
                <td>{{ r.mp02 }}</td>
                <td>{{ r.mp03 }}</td>
                <td>{{ r.hi01 }}</td>
                <td>{{ r.hi02 }}</td>
                <td>{{ r.hi03 }}</td>
                <td>{{ r.hi04 }}</td>
                <td>{{ r.hi05 }}</td>
                <td>{{ r.hi06 }}</td>
                <td class="badge-temp">{{ r.te }} °C</td>
                <td class="badge-hr">{{ r.hr }} %</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
</body>
</html>
"""


@App.route('/', methods=['GET'])
@App.route('/grafica', methods=['GET'])
def vista_navegador():
    """Muestra en el navegador el panel con la gráfica de Matplotlib y accesos directos al JSON."""
    uma_id = REQ.args.get('uma', type=int)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        if uma_id:
            cursor.execute("SELECT * FROM mediciones WHERE uma_id = ? ORDER BY id_registro DESC LIMIT 25", (uma_id,))
        else:
            cursor.execute("SELECT * FROM mediciones ORDER BY id_registro DESC LIMIT 25")
        rows = cursor.fetchall()

    registros = [row_to_dict(r) for r in rows]
    return render_template_string(HTML_DASHBOARD, registros=registros, uma_id=uma_id)


if __name__ == '__main__':
    init_db()
    App.run(debug=True, host='0.0.0.0', port=7070)
