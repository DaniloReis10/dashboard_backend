from flask import Blueprint, jsonify, request, Response
import mysql.connector
import os
import csv
import io

bp = Blueprint("conclusoes_ano", __name__)

@bp.route("/", methods=["GET"], strict_slashes=False)
def root():
    return jsonify({"ok": True, "service": "conclusoes_ano"})

DB_CONFIG = {
    "host": "200.129.17.231",
    "user": "danilo",
    "password": "5yZ2UjcLA9SU6Rh1",
    "database": "moodle"
}

def get_modality_filter():
    modality = request.args.get("modality", "ALL").upper()
    if modality == "EAD":
        return "UPPER(`Nature of Participation`) = %s", [modality]
    return "", []

def build_dashboard_filters():
    ano_inicial = request.args.get("anoInicial", "2010")
    ano_final = request.args.get("anoFinal", "2024")
    curso = request.args.get("curso", "Todos")
    campus = request.args.get("campus", "Todos")
    modalidade = request.args.get("modalidade", "Todos")
    periodo = request.args.get("periodo", "Todos")
    search = request.args.get("search", "").strip()

    modality_sql, modality_params = get_modality_filter()

    where = ["`year` IS NOT NULL", "CAST(`year` AS UNSIGNED) BETWEEN %s AND %s"]
    params = [ano_inicial, ano_final]

    if curso != "Todos":
        where.append("`curso` = %s")
        params.append(curso)

    if modalidade != "Todos":
        where.append("`modalidade` = %s")
        params.append(modalidade)

    if periodo != "Todos":
        where.append("`periodo` = %s")
        params.append(periodo)

    if search:
        where.append("(LOWER(`curso`) LIKE %s OR LOWER(`campus`) LIKE %s)")
        like = f"%{search.lower()}%"
        params.extend([like, like])

    if modality_sql:
        where.append(modality_sql)
        params.extend(modality_params)

    return " WHERE " + " AND ".join(where), params, campus


TABLE_NAME = "conclusions_view"

CAMPUS_JOIN = f"""
LEFT JOIN mdl_course mc              ON mc.id = v.course_id
LEFT JOIN mdl_course_categories c0   ON c0.id = mc.category
LEFT JOIN mdl_course_categories c1   ON c1.id = c0.parent
LEFT JOIN mdl_course_categories c2   ON c2.id = c1.parent
"""

CAMPUS_EXPR = """
UPPER(TRIM(REPLACE(
  COALESCE(
    CASE WHEN UPPER(c0.name) LIKE '%CAMPUS %' THEN c0.name END,
    CASE WHEN UPPER(c1.name) LIKE '%CAMPUS %' THEN c1.name END,
    CASE WHEN UPPER(c2.name) LIKE '%CAMPUS %' THEN c2.name END,
    'TODOS'
  ),
  'CAMPUS ', ''
)))
"""

def campus_filter_sql(selected):
    selected = (selected or "Todos").strip()
    if selected == "Todos":
        return "", []
    return f"{CAMPUS_EXPR} = %s", [selected.upper()]

@bp.route("", methods=["GET"], strict_slashes=False)
def get_conclusions_aggregated():
    where_sql, params, campus_selected = build_dashboard_filters()
    campus_where, campus_params = campus_filter_sql(campus_selected)
    if campus_where:
        where_sql = where_sql + (" AND " + campus_where)
        params += campus_params
    query = f"""
        SELECT `year`, SUM(`value`) AS total
        FROM {TABLE_NAME} v
        {CAMPUS_JOIN}
        {where_sql}
        GROUP BY `year`
        ORDER BY CAST(`year` AS UNSIGNED)
    """

    try:
        conn = mysql.connector.connect(**DB_CONFIG, connection_timeout=15)
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        cursor.close(); conn.close()
        data = [{"year": str(r[0]), "value": int(r[1] or 0)} for r in rows]
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/stats", methods=["GET"], strict_slashes=False)
def get_conclusions_stats():
    where_sql, params, campus_selected = build_dashboard_filters()
    campus_where, campus_params = campus_filter_sql(campus_selected)
    if campus_where:
        where_sql = where_sql + (" AND " + campus_where)
        params += campus_params
    query = f"""
        SELECT `year`, SUM(`value`) AS total
        FROM {TABLE_NAME} v
        {CAMPUS_JOIN}
        {where_sql}
        GROUP BY `year`
        ORDER BY CAST(`year` AS UNSIGNED)
    """

    try:
        conn = mysql.connector.connect(**DB_CONFIG, connection_timeout=15)
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        cursor.close(); conn.close()

        agg = [(str(y), int(v or 0)) for y, v in rows]
        total = sum(v for _, v in agg)
        years_span = len(agg)
        avg_growth = None
        if years_span > 1 and agg[0][1] != 0:
            first = agg[0][1]
            last = agg[-1][1]
            avg_growth = round(((last - first) / first) * 100, 1)
        peak_year, peak_value = ("N/A", 0)
        if agg:
            peak_year, peak_value = max(agg, key=lambda x: x[1])

        return jsonify({
            "periodo": f"{request.args.get('anoInicial','2010')}-{request.args.get('anoFinal','2024')}",
            "totalStudents": total,
            "avgGrowthPercent": avg_growth,
            "peakYear": peak_year,
            "peakValue": peak_value,
            "yearsSpan": years_span
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/export/csv", methods=["GET"], strict_slashes=False)
def export_conclusions_csv():
    where_sql, params, campus_selected = build_dashboard_filters()
    campus_where, campus_params = campus_filter_sql(campus_selected)
    if campus_where:
        where_sql = where_sql + (" AND " + campus_where)
        params += campus_params
    query = f"""
        SELECT `year`, SUM(`value`) AS total
        FROM {TABLE_NAME} v
        {CAMPUS_JOIN}
        {where_sql}
        GROUP BY `year`
        ORDER BY CAST(`year` AS UNSIGNED)
    """

    try:
        conn = mysql.connector.connect(**DB_CONFIG, connection_timeout=15)
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        cursor.close(); conn.close()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["year", "value"])
        for y, v in rows:
            writer.writerow([str(y), int(v or 0)])
        csv_data = output.getvalue()

        return Response(
            u"\ufeff" + csv_data,
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=conclusions.csv"}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/export/json", methods=["GET"], strict_slashes=False)
def export_conclusions_json():
    where_sql, params, campus_selected = build_dashboard_filters()
    campus_where, campus_params = campus_filter_sql(campus_selected)
    if campus_where:
        where_sql = where_sql + (" AND " + campus_where)
        params += campus_params
    query = f"""
        SELECT `year`, SUM(`value`) AS total
        FROM {TABLE_NAME} v
        {CAMPUS_JOIN}
        {where_sql}
        GROUP BY `year`
        ORDER BY CAST(`year` AS UNSIGNED)
    """

    try:
        conn = mysql.connector.connect(**DB_CONFIG, connection_timeout=15)
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        cursor.close(); conn.close()
        data = [{"year": str(y), "value": int(v or 0)} for y, v in rows]
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/meta/options", methods=["GET"], strict_slashes=False)
def get_meta_options():
    try:
        conn = mysql.connector.connect(**DB_CONFIG, connection_timeout=15)
        cursor = conn.cursor()

        cursor.execute(f"SELECT DISTINCT `year` FROM {TABLE_NAME} ORDER BY CAST(`year` AS UNSIGNED)")
        anos = [str(r[0]) for r in cursor.fetchall()]

        def uniq(col_sql_name):
            cursor.execute(f"""
                SELECT DISTINCT {col_sql_name}
                FROM {TABLE_NAME}
                WHERE {col_sql_name} IS NOT NULL AND {col_sql_name} != ''
                ORDER BY {col_sql_name}
            """)
            return [r[0] for r in cursor.fetchall()]

        cursos = ["Todos", *uniq("`curso`")]

        cursor.execute("""
            SELECT DISTINCT
                TRIM(REPLACE(
                    UPPER(
                        COALESCE(
                            CASE WHEN UPPER(c0.name) LIKE '%CAMPUS %' THEN c0.name END,
                            CASE WHEN UPPER(c1.name) LIKE '%CAMPUS %' THEN c1.name END,
                            CASE WHEN UPPER(c2.name) LIKE '%CAMPUS %' THEN c2.name END
                        )
                    ),
                'CAMPUS ', '')) AS campus_norm
            FROM mdl_course c
            LEFT JOIN mdl_course_categories c0 ON c0.id = c.category
            LEFT JOIN mdl_course_categories c1 ON c1.id = c0.parent
            LEFT JOIN mdl_course_categories c2 ON c2.id = c1.parent
            WHERE COALESCE(c0.name, c1.name, c2.name) IS NOT NULL
            AND (UPPER(c0.name) LIKE '%CAMPUS %'
                OR UPPER(c1.name) LIKE '%CAMPUS %'
                OR UPPER(c2.name) LIKE '%CAMPUS %')
            ORDER BY campus_norm;
        """)

        campi = ["Todos", *[r[0].title() for r in cursor.fetchall() if r[0]]]

        modalidades = ["Todos", *uniq("`modalidade`")]
        periodos = ["Todos", *uniq("`periodo`")]

        cursor.close(); conn.close()
        return jsonify({
            "anos": anos,
            "cursos": cursos,
            "campi": campi,
            "modalidades": modalidades,
            "periodos": periodos
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
