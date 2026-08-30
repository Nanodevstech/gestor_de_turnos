# ==============================================================================
# 🧠 CEREBRO DE DATOS - GESTOR DE BASE DE DATOS (SQLITE) - MEDIDOC 2.0
# ==============================================================================

import sqlite3
import os
import sys
import hashlib
import shutil
from datetime import datetime
from contextlib import contextmanager

# ------------------------------------------------------------------------------
# ⚙️ CONFIGURACIÓN DE CONEXIÓN Y DIRECTORIOS
# ------------------------------------------------------------------------------

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "Turnos.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
ADJUNTOS_DIR = os.path.join(BASE_DIR, "adjuntos")

for d in [BACKUP_DIR, ADJUNTOS_DIR]:
    os.makedirs(d, exist_ok=True)

def conectar():
    """Crea y retorna la conexión a la base de datos."""
    try:
        conn = sqlite3.connect(DB_PATH)
        return conn
    except Exception as e:
        print(f"⚠️ Error Crítico: No se pudo conectar a la BD: {e}")
        return None

@contextmanager
def obtener_cursor():
    """Context Manager para gestionar de forma segura conexiones y transacciones."""
    conn = conectar()
    if not conn:
        yield None
        return
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error en operación de BD: {e}")
        yield None
    finally:
        conn.close()

def hash_password(password: str) -> str:
    """Genera un hash SHA-256 seguro para contraseñas."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def inicializar_tablas():
    """Crea automáticamente todas las tablas de MEDIDOC 2.0 si no existen."""
    with obtener_cursor() as cursor:
        if cursor is None: return
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Medicos (
                id_medico INTEGER PRIMARY KEY AUTOINCREMENT,
                Nombre_completo TEXT, Especialidad TEXT, Matricula TEXT, Telefono TEXT, Email TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Registro_de_paciente (
                DNI INTEGER PRIMARY KEY, Nombre_completo TEXT, Fecha_nacimiento TEXT,
                Telefono TEXT, Email TEXT, Dirección TEXT, Obra_social TEXT, Nro_afiliado TEXT,
                Grupo_sanguineo TEXT, Alergias TEXT, Enfermedades_crónicas TEXT,
                Medicación_actual TEXT, Observaciones_generales TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Turnos (
                id_turno INTEGER PRIMARY KEY AUTOINCREMENT,
                dni_paciente INTEGER, id_medico INTEGER, Fecha TEXT, Hora TEXT,
                Motivo_consulta TEXT, Estado TEXT DEFAULT 'Pendiente'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Historial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dni_paciente TEXT, fecha TEXT, hora TEXT, observacion TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Usuarios (
                usuario TEXT PRIMARY KEY, password TEXT, rol TEXT
            )
        """)
        # TABLAS MEDIDOC 2.0
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Sala_Espera (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dni_paciente TEXT, id_medico INTEGER, llegada TEXT, estado TEXT, observaciones TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Lista_Espera (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dni_paciente TEXT, id_medico INTEGER, fecha_registro TEXT, preferencia TEXT, estado TEXT DEFAULT 'Pendiente'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Adjuntos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dni_paciente TEXT, nombre_archivo TEXT, ruta_archivo TEXT, fecha_subida TEXT, categoria TEXT
            )
        """)

# Inicialización automática de esquema
inicializar_tablas()

# ==============================================================================
# 👨‍⚕️ SECCIÓN: MÉDICOS (CRUD)
# ==============================================================================

def obtener_medicos_db():
    """Recupera la lista completa de médicos."""
    with obtener_cursor() as cursor:
        if cursor is None: return []
        cursor.execute("SELECT Nombre_completo, Especialidad, Matricula, Telefono FROM Medicos")
        filas = cursor.fetchall()
        return [{"nombre": f[0], "especialidad": f[1], "matricula": f[2], "telefono": f[3]} for f in filas]

def guardar_medico_db(nuevo_medico):
    """Inserta un nuevo profesional en la tabla."""
    with obtener_cursor() as cursor:
        if cursor is None: return False
        sql = """
            INSERT INTO Medicos (Nombre_completo, Especialidad, Matricula, Telefono, Email)
            VALUES (?, ?, ?, ?, ?)
        """
        valores = (nuevo_medico["nombre"], nuevo_medico["especialidad"], 
                   nuevo_medico["matricula"], nuevo_medico["telefono"], nuevo_medico["email"])
        cursor.execute(sql, valores)
        return True

def eliminar_medico_db(nombre_medico):
    """Borra un médico buscando por su nombre exacto."""
    with obtener_cursor() as cursor:
        if cursor is None: return False
        cursor.execute("DELETE FROM Medicos WHERE Nombre_completo = ?", (nombre_medico,))
        return True

# ==============================================================================
# 👥 SECCIÓN: PACIENTES (CRUD)
# ==============================================================================

def obtener_pacientes_db():
    """Trae la lista de pacientes con todos sus datos personales."""
    with obtener_cursor() as cursor:
        if cursor is None: return []
        sql = """
            SELECT DNI, Nombre_completo, Fecha_nacimiento, Telefono, Email, Dirección, 
                   Obra_social, Nro_afiliado, Grupo_sanguineo, Alergias, 
                   Enfermedades_crónicas, Medicación_actual, Observaciones_generales
            FROM Registro_de_paciente
        """
        cursor.execute(sql)
        filas = cursor.fetchall()
        
        lista_pacientes = []
        for fila in filas:
            pac = {
                "dni": str(fila[0]), "nombre": fila[1], "fecha_nac": fila[2],
                "telefono": fila[3], "email": fila[4], "direccion": fila[5],
                "obra_social": fila[6], "num_afiliado": fila[7], "grupo_sanguineo": fila[8],
                "alergias": fila[9], "enfermedades": fila[10], "medicacion": fila[11],
                "observaciones": fila[12]
            }
            lista_pacientes.append(pac)
        return lista_pacientes

def obtener_paciente_por_nombre(nombre):
    """Busca un paciente específico por su nombre exacto o aproximado."""
    pacientes = obtener_pacientes_db()
    nombre_clean = str(nombre).strip().lower()
    for p in pacientes:
        if p["nombre"].strip().lower() == nombre_clean:
            return p
    return None

def obtener_paciente_por_dni(dni):
    """Busca un paciente específico por su DNI."""
    pacientes = obtener_pacientes_db()
    dni_str = str(dni).strip()
    for p in pacientes:
        if str(p["dni"]).strip() == dni_str:
            return p
    return None

def guardar_paciente_db(pac):
    """Guarda (INSERT) o Actualiza (UPDATE) un paciente según si el DNI ya existe."""
    with obtener_cursor() as cursor:
        if cursor is None: return False
        cursor.execute("SELECT DNI FROM Registro_de_paciente WHERE DNI = ?", (pac["dni"],))
        existe = cursor.fetchone()
        
        if existe:
            sql = """
                UPDATE Registro_de_paciente SET
                    Nombre_completo = ?, Fecha_nacimiento = ?, Telefono = ?, Email = ?, 
                    Dirección = ?, Obra_social = ?, Nro_afiliado = ?, Grupo_sanguineo = ?, 
                    Alergias = ?, Enfermedades_crónicas = ?, Medicación_actual = ?, 
                    Observaciones_generales = ?
                WHERE DNI = ?
            """
        else:
            sql = """
                INSERT INTO Registro_de_paciente (
                    Nombre_completo, Fecha_nacimiento, Telefono, Email, Dirección, 
                    Obra_social, Nro_afiliado, Grupo_sanguineo, Alergias, 
                    Enfermedades_crónicas, Medicación_actual, Observaciones_generales, DNI
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
        valores = (
            pac["nombre"], pac["fecha_nac"], pac["telefono"], pac["email"],
            pac["direccion"], pac["obra_social"], pac["num_afiliado"], pac["grupo_sanguineo"],
            pac["alergias"], pac["enfermedades"], pac["medicacion"], pac["observaciones"],
            pac["dni"]
        )
        cursor.execute(sql, valores)
        return True

def eliminar_paciente_db(dni):
    """Borra un paciente y su historial."""
    with obtener_cursor() as cursor:
        if cursor is None: return False
        cursor.execute("DELETE FROM Registro_de_paciente WHERE DNI = ?", (dni,))
        return True

# ==============================================================================
# 📅 SECCIÓN: TURNOS Y SCORE DE AUSENTISMO
# ==============================================================================

def obtener_turnos_db():
    """Obtiene turnos uniendo tablas (JOIN) para traer nombres en vez de IDs."""
    with obtener_cursor() as cursor:
        if cursor is None: return []
        sql = """
            SELECT t.Fecha, t.Hora, p.Nombre_completo, t.Motivo_consulta, m.Nombre_completo, t.rowid, t.dni_paciente, t.Estado
            FROM Turnos t
            JOIN Registro_de_paciente p ON t.dni_paciente = p.DNI
            JOIN Medicos m ON t.id_medico = m.id_medico
        """
        cursor.execute(sql)
        filas = cursor.fetchall()
        return [{
            "fecha": f[0], "hora": f[1], "paciente": f[2], 
            "motivo": f[3], "medico": f[4], "id": f[5],
            "dni": f[6], "estado": f[7] if len(f) > 7 and f[7] else "Pendiente"
        } for f in filas]

def guardar_turno_db(turno_dict):
    """Busca IDs relacionales y guarda el turno."""
    with obtener_cursor() as cursor:
        if cursor is None: return False
        cursor.execute("SELECT id_medico FROM Medicos WHERE Nombre_completo = ?", (turno_dict["medico"],))
        res_med = cursor.fetchone()
        if not res_med: return False
        id_medico = res_med[0]

        try:
            dni_paciente = int(turno_dict["paciente"])
        except ValueError:
            return False

        sql = """
            INSERT INTO Turnos (dni_paciente, id_medico, Fecha, Hora, Motivo_consulta, Estado)
            VALUES (?, ?, ?, ?, ?, 'Pendiente')
        """
        cursor.execute(sql, (dni_paciente, id_medico, turno_dict["fecha"], turno_dict["hora"], turno_dict["motivo"]))
        return True

def actualizar_turno_db(fecha_orig, hora_orig, medico_orig, turno_dict):
    """Actualiza un turno existente sin tener que eliminarlo primero."""
    with obtener_cursor() as cursor:
        if cursor is None: return False
        cursor.execute("SELECT id_medico FROM Medicos WHERE Nombre_completo = ?", (turno_dict["medico"],))
        res_med = cursor.fetchone()
        if not res_med: return False
        id_medico_nuevo = res_med[0]

        cursor.execute("SELECT id_medico FROM Medicos WHERE Nombre_completo = ?", (medico_orig,))
        res_med_orig = cursor.fetchone()
        if not res_med_orig: return False
        id_medico_orig = res_med_orig[0]

        try:
            dni_paciente = int(turno_dict["paciente"])
        except ValueError:
            return False

        sql = """
            UPDATE Turnos 
            SET dni_paciente = ?, id_medico = ?, Fecha = ?, Hora = ?, Motivo_consulta = ?
            WHERE Fecha = ? AND Hora = ? AND id_medico = ?
        """
        cursor.execute(sql, (dni_paciente, id_medico_nuevo, turno_dict["fecha"], turno_dict["hora"], 
                            turno_dict["motivo"], fecha_orig, hora_orig, id_medico_orig))
        return cursor.rowcount > 0

def cambiar_estado_turno_db(fecha, hora, medico_nombre, nuevo_estado):
    """Cambia el estado de un turno (Atendido, Ausente, Cancelado, Pendiente)."""
    with obtener_cursor() as cursor:
        if cursor is None: return False
        cursor.execute("SELECT id_medico FROM Medicos WHERE Nombre_completo = ?", (medico_nombre,))
        res = cursor.fetchone()
        if not res: return False
        sql = "UPDATE Turnos SET Estado = ? WHERE Fecha = ? AND Hora = ? AND id_medico = ?"
        cursor.execute(sql, (nuevo_estado, fecha, hora, res[0]))
        return True

def eliminar_turno_db(fecha, hora, medico):
    """Elimina un turno específico."""
    with obtener_cursor() as cursor:
        if cursor is None: return False
        cursor.execute("SELECT id_medico FROM Medicos WHERE Nombre_completo = ?", (medico,))
        res = cursor.fetchone()
        if not res: return False
        
        sql = "DELETE FROM Turnos WHERE Fecha = ? AND Hora = ? AND id_medico = ?"
        cursor.execute(sql, (fecha, hora, res[0]))
        return True

def calcular_score_paciente_db(dni):
    """
    Calcula el Score de Asistencia / Predictor de Ausentismo de un paciente.
    Retorna (icono_badge, texto_descriptivo)
    """
    with obtener_cursor() as cursor:
        if cursor is None: return ("🟢 Alto", "Asistencia Puntual")
        cursor.execute("SELECT Estado FROM Turnos WHERE dni_paciente = ?", (dni,))
        filas = cursor.fetchall()
        if not filas:
            return ("🟢 Alto", "Sin historial negativo")
        
        total = len(filas)
        ausencias = sum(1 for f in filas if f[0] in ['Ausente', 'Cancelado'])
        
        if ausencias == 0:
            return ("🟢 Alto", "100% de asistencia")
        elif ausencias / total <= 0.3:
            return ("🟡 Medio", "Asistencia regular")
        else:
            return ("🔴 Bajo", "Alto riesgo de ausentismo")

# ==============================================================================
# 🚦 SECCIÓN: SALA DE ESPERA "EN VIVO" (MEDIDOC 2.0)
# ==============================================================================

def registrar_llegada_sala_db(dni, medico_nombre):
    """Registra la llegada de un paciente a la sala de espera."""
    with obtener_cursor() as cursor:
        if cursor is None: return False
        cursor.execute("SELECT id_medico FROM Medicos WHERE Nombre_completo = ?", (medico_nombre,))
        res = cursor.fetchone()
        id_medico = res[0] if res else 0

        llegada_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sql = "INSERT INTO Sala_Espera (dni_paciente, id_medico, llegada, estado, observaciones) VALUES (?, ?, ?, 'En Espera', '')"
        cursor.execute(sql, (dni, id_medico, llegada_actual))
        return True

def obtener_sala_espera_db():
    """Retorna la lista de pacientes actualmente en sala de espera o atención."""
    with obtener_cursor() as cursor:
        if cursor is None: return []
        sql = """
            SELECT s.id, p.Nombre_completo, m.Nombre_completo, s.llegada, s.estado, s.dni_paciente
            FROM Sala_Espera s
            JOIN Registro_de_paciente p ON s.dni_paciente = p.DNI
            LEFT JOIN Medicos m ON s.id_medico = m.id_medico
            WHERE s.estado IN ('En Espera', 'En Atencion')
            ORDER BY s.llegada ASC
        """
        cursor.execute(sql)
        filas = cursor.fetchall()
        
        resultado = []
        ahora = datetime.now()
        for f in filas:
            try:
                llegada_dt = datetime.strptime(f[3], "%Y-%m-%d %H:%M:%S")
                minutos_espera = int((ahora - llegada_dt).total_seconds() // 60)
            except Exception:
                minutos_espera = 0
                
            resultado.append({
                "id": f[0], "paciente": f[1], "medico": f[2] if f[2] else "Sin asignar",
                "llegada": f[3], "estado": f[4], "dni": f[5], "minutos_espera": minutos_espera
            })
        return resultado

def cambiar_estado_sala_db(id_sala, nuevo_estado):
    """Cambia el estado de un registro de sala de espera."""
    with obtener_cursor() as cursor:
        if cursor is None: return False
        cursor.execute("UPDATE Sala_Espera SET estado = ? WHERE id = ?", (nuevo_estado, id_sala))
        return True

# ==============================================================================
# ⚡ SECCIÓN: LISTA DE ESPERA INTELIGENTE (MEDIDOC 2.0)
# ==============================================================================

def agregar_lista_espera_db(dni, medico_nombre, preferencia):
    """Registra a un paciente en la lista de espera de un médico."""
    with obtener_cursor() as cursor:
        if cursor is None: return False
        cursor.execute("SELECT id_medico FROM Medicos WHERE Nombre_completo = ?", (medico_nombre,))
        res = cursor.fetchone()
        id_medico = res[0] if res else 0

        fecha_reg = datetime.now().strftime("%d/%m/%Y %H:%M")
        sql = "INSERT INTO Lista_Espera (dni_paciente, id_medico, fecha_registro, preferencia, estado) VALUES (?, ?, ?, ?, 'Pendiente')"
        cursor.execute(sql, (dni, id_medico, fecha_reg, preferencia))
        return True

def obtener_lista_espera_db(medico_nombre=None):
    """Obtiene pacientes en lista de espera."""
    with obtener_cursor() as cursor:
        if cursor is None: return []
        if medico_nombre:
            cursor.execute("SELECT id_medico FROM Medicos WHERE Nombre_completo = ?", (medico_nombre,))
            res = cursor.fetchone()
            id_med = res[0] if res else 0
            sql = """
                SELECT l.id, p.Nombre_completo, m.Nombre_completo, l.fecha_registro, l.preferencia, l.estado, p.Telefono, p.DNI
                FROM Lista_Espera l
                JOIN Registro_de_paciente p ON l.dni_paciente = p.DNI
                JOIN Medicos m ON l.id_medico = m.id_medico
                WHERE l.id_medico = ? AND l.estado = 'Pendiente'
                ORDER BY l.id ASC
            """
            cursor.execute(sql, (id_med,))
        else:
            sql = """
                SELECT l.id, p.Nombre_completo, m.Nombre_completo, l.fecha_registro, l.preferencia, l.estado, p.Telefono, p.DNI
                FROM Lista_Espera l
                JOIN Registro_de_paciente p ON l.dni_paciente = p.DNI
                JOIN Medicos m ON l.id_medico = m.id_medico
                WHERE l.estado = 'Pendiente'
                ORDER BY l.id ASC
            """
            cursor.execute(sql)
        filas = cursor.fetchall()
        return [{
            "id": f[0], "paciente": f[1], "medico": f[2],
            "fecha": f[3], "preferencia": f[4], "estado": f[5],
            "telefono": f[6], "dni": f[7]
        } for f in filas]

def cambiar_estado_lista_espera_db(id_item, nuevo_estado):
    """Actualiza el estado de un registro de lista de espera."""
    with obtener_cursor() as cursor:
        if cursor is None: return False
        cursor.execute("UPDATE Lista_Espera SET estado = ? WHERE id = ?", (nuevo_estado, id_item))
        return True

# ==============================================================================
# 📂 SECCIÓN: ADJUNTOS Y DOCUMENTOS MÉDICOS (MEDIDOC 2.0)
# ==============================================================================

def guardar_adjunto_db(dni, ruta_origen, categoria="General"):
    """Copia un archivo al directorio de adjuntos y registra en BD."""
    if not os.path.exists(ruta_origen): return False
    nombre_base = os.path.basename(ruta_origen)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
    nombre_destino = f"{dni}_{timestamp}{nombre_base}"
    ruta_destino = os.path.join(ADJUNTOS_DIR, nombre_destino)

    try:
        shutil.copy2(ruta_origen, ruta_destino)
        with obtener_cursor() as cursor:
            if cursor is None: return False
            fecha_subida = datetime.now().strftime("%d/%m/%Y %H:%M")
            sql = "INSERT INTO Adjuntos (dni_paciente, nombre_archivo, ruta_archivo, fecha_subida, categoria) VALUES (?, ?, ?, ?, ?)"
            cursor.execute(sql, (dni, nombre_base, ruta_destino, fecha_subida, categoria))
            return True
    except Exception as e:
        print(f"Error guardando adjunto: {e}")
        return False

def obtener_adjuntos_db(dni):
    """Obtiene todos los archivos adjuntos de un paciente."""
    with obtener_cursor() as cursor:
        if cursor is None: return []
        sql = "SELECT id, nombre_archivo, ruta_archivo, fecha_subida, categoria FROM Adjuntos WHERE dni_paciente = ? ORDER BY id DESC"
        cursor.execute(sql, (dni,))
        return [{
            "id": f[0], "nombre": f[1], "ruta": f[2], "fecha": f[3], "categoria": f[4]
        } for f in cursor.fetchall()]

# ==============================================================================
# 🔐 SECCIÓN: SEGURIDAD, USUARIOS Y BACKUP
# ==============================================================================

def validar_login_db(usuario, password):
    """Verifica credenciales (con hash SHA-256) y migra contraseñas legacy de texto plano."""
    conn = conectar()
    if not conn: return None
    
    cursor = conn.cursor()
    try:
        pass_hash = hash_password(password)
        sql = "SELECT rol, password FROM Usuarios WHERE usuario = ?"
        cursor.execute(sql, (usuario,))
        resultado = cursor.fetchone()
        
        if resultado:
            rol_db, pass_db = resultado[0], resultado[1]
            if pass_db == pass_hash:
                return rol_db
            elif pass_db == password:
                cursor.execute("UPDATE Usuarios SET password = ? WHERE usuario = ?", (pass_hash, usuario))
                conn.commit()
                return rol_db
        return None
    except Exception as e:
        print(f"Error login: {e}")
        return None
    finally:
        conn.close()

def crear_backup_db():
    """Genera una copia de seguridad timestamped de Turnos.db."""
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"Turnos_backup_{ts}.db")
        shutil.copy2(DB_PATH, backup_path)
        return backup_path
    except Exception as e:
        print(f"Error creando backup: {e}")
        return None

# ==============================================================================
# 📋 SECCIÓN: HISTORIA CLÍNICA (OBSERVACIONES)
# ==============================================================================

def guardar_observacion_db(dni, observacion):
    """Agrega una nota al historial con fecha/hora automáticas."""
    with obtener_cursor() as cursor:
        if cursor is None: return False
        fecha = datetime.now().strftime("%d/%m/%Y")
        hora = datetime.now().strftime("%H:%M")
        sql = "INSERT INTO Historial (dni_paciente, fecha, hora, observacion) VALUES (?, ?, ?, ?)"
        cursor.execute(sql, (dni, fecha, hora, observacion))
        return True

def obtener_historial_db(dni):
    """Retorna historial ordenado por fecha descendente."""
    with obtener_cursor() as cursor:
        if cursor is None: return []
        sql = "SELECT fecha, hora, observacion FROM Historial WHERE dni_paciente = ? ORDER BY id DESC"
        cursor.execute(sql, (dni,))
        return [{"fecha": d[0], "hora": d[1], "observacion": d[2]} for d in cursor.fetchall()]