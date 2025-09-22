from flask import Blueprint, jsonify
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv() # This loads variables from a .env file

bp = Blueprint("polos", __name__, url_prefix="/polos")

# --- My Database Configuration ---
DB_CONFIG = {
    'user': os.getenv('DB_USER'),
    'password':  os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME')
}

#DB_CONFIG = {
#    "host": os.environ.get("DB_HOST", "200.129.17.231"),
#    "user": os.environ.get("DB_USER", "danilo"),
#    "password": os.environ.get("DB_PASS", "5yZ2UjcLA9SU6Rh1"),
#    "database": os.environ.get("DB_NAME", "moodle"),
#}

@bp.route("/", methods=["GET"], strict_slashes=False)
@bp.route("", methods=["GET"])
def list_polos():
    """
    Retorna lista distinta de polos em formato de array de strings.
    Usa a coluna `Pole` da tabela `suap_students`.
    """
    conn = mysql.connector.connect(**DB_CONFIG, connection_timeout=8)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT TRIM(`Pole`) AS polo
        FROM suap_students
        WHERE `Pole` IS NOT NULL AND TRIM(`Pole`) <> ''
        ORDER BY polo
        """
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return jsonify([r[0] for r in rows])
