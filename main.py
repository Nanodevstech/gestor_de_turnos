# ==============================================================================
# 🏥 GESTOR DE TURNOS - MEDIDOC 2.0 (VERSION FINAL INNOVADORA)
# ==============================================================================

# 1. IMPORTACIONES Y LIBRERÍAS
# ------------------------------------------------------------------------------
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import tkinter.font as tkfont
import os
import re
import csv
from datetime import datetime, timedelta
import calendar
from collections import Counter
import webbrowser 
from urllib.parse import quote 

# MÓDULOS PROPIOS
import database  
import reportes  

# 2. CONFIGURACIÓN Y CONSTANTES DE TEMA
# ------------------------------------------------------------------------------
HORARIOS = [f"{h:02d}:00" for h in range(8, 21)]

THEMES = {
    "LIGHT": {
        "primary": "#0288D1",       
        "primary_light": "#5EB8FF", 
        "primary_dark": "#01579B",  
        "accent": "#009688",        
        "success": "#4CAF50",
        "warning": "#FF9800",
        "danger": "#F44336",
        "background": "#F5F7FA",    
        "card": "#FFFFFF",          
        "text": "#263238",          
        "text_light": "#78909C",    
        "border": "#CFD8DC"         
    },
    "DARK": {
        "primary": "#0288D1",       
        "primary_light": "#0288D1", 
        "primary_dark": "#01579B",  
        "accent": "#00BFA5",        
        "success": "#388E3C",
        "warning": "#F57C00",
        "danger": "#D32F2F",
        "background": "#121212",    
        "card": "#1E1E1E",          
        "text": "#E0E0E0",          
        "text_light": "#9E9E9E",    
        "border": "#333333"         
    }
}

MODO_OSCURO = False
COLORS = THEMES["LIGHT"]

# Variables Globales de Estado
rol_usuario_actual = None 
turno_en_edicion = None

# Componentes de ayuda para UI
def crear_boton(parent, text, command, bg_color, fg_color="white", width=16, pady=8, font_size=9, bold=True):
    """Crea un botón estilizado reutilizable."""
    font_style = ("Segoe UI", font_size, "bold" if bold else "normal")
    return tk.Button(parent, text=text, command=command, bg=bg_color, fg=fg_color,
                     font=font_style, relief="flat", cursor="hand2", width=width, pady=pady, bd=0)

# ==============================================================================
# 🧠 BLOQUE BACKEND: FUNCIONES DE DATOS Y ESTADÍSTICAS
# ==============================================================================

def cargar_turnos(): 
    return database.obtener_turnos_db()

def cargar_pacientes(): 
    return database.obtener_pacientes_db()

def cargar_medicos(): 
    return database.obtener_medicos_db()

def obtener_nombres_medicos(): 
    lista = cargar_medicos()
    if not lista: 
        return []
    return [m["nombre"] for m in lista]

def obtener_estadisticas(): 
    turnos = cargar_turnos()
    total = len(turnos)
    if total == 0:
        return {"total": 0, "por_medico": {}, "proximos_7_dias": 0}
    
    por_medico = Counter(t.get("medico", "N/A") for t in turnos)
    
    hoy = datetime.today().date()
    proximos_7 = 0
    for t in turnos:
        try:
            fecha_dt = datetime.strptime(t["fecha"], "%d/%m/%Y").date()
            if hoy <= fecha_dt <= hoy + timedelta(days=7):
                proximos_7 += 1
        except ValueError:
            pass 
    
    return {
        "total": total,
        "por_medico": dict(por_medico),
        "proximos_7_dias": proximos_7
    }

def cargar_historial_de_paciente(dni): 
    return database.obtener_historial_db(dni)

def guardar_observacion_visita(dni_paciente, observacion): 
    if not observacion.strip():
        messagebox.showwarning("Advertencia", "El campo de observación no puede estar vacío.")
        return False
        
    if database.guardar_observacion_db(dni_paciente, observacion.strip()):
        return True
    else:
        messagebox.showerror("Error", "No se pudo guardar la observación en la Base de Datos.")
        return False

def dictar_observacion(widget_texto):
    """Herramienta de dictado por voz para notas clínicas."""
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.Microphone() as source:
            messagebox.showinfo("Dictado por Voz", "Escuchando... Hable ahora claramente hacia el micrófono.")
            audio = r.listen(source, timeout=6)
            texto = r.recognize_google(audio, language="es-ES")
            widget_texto.insert(tk.END, " " + texto)
            messagebox.showinfo("Éxito", f"Texto transcrito:\n{texto}")
    except ImportError:
        messagebox.showinfo("Dictado por Voz", "Para utilizar el dictado por voz automático, instale la librería speech_recognition:\n\npip install SpeechRecognition pyaudio")
    except Exception as e:
        messagebox.showwarning("Dictado por Voz", f"No se pudo procesar el audio:\n{e}")

# ==============================================================================
# 🎨 BLOQUE UI: CLASES VISUALES
# ==============================================================================

class TarjetaEstadistica(tk.Frame): 
    def __init__(self, master, titulo, valor, icono, color):
        super().__init__(master, bg=COLORS["card"], relief="flat", bd=0)
        self.config(highlightbackground=COLORS["border"], highlightthickness=1)
        
        container = tk.Frame(self, bg=COLORS["card"])
        container.pack(padx=20, pady=15)
        
        icon_frame = tk.Frame(container, bg=color, width=50, height=50)
        icon_frame.pack(side="left", padx=(0, 15))
        icon_frame.pack_propagate(False)
        
        tk.Label(icon_frame, text=icono, font=("Segoe UI", 20), 
                 bg=color, fg="white").place(relx=0.5, rely=0.5, anchor="center")
        
        text_frame = tk.Frame(container, bg=COLORS["card"])
        text_frame.pack(side="left")
        
        tk.Label(text_frame, text=titulo, font=("Segoe UI", 10), 
                 bg=COLORS["card"], fg=COLORS["text_light"]).pack(anchor="w")
        tk.Label(text_frame, text=str(valor), font=("Segoe UI", 24, "bold"), 
                 bg=COLORS["card"], fg=COLORS["text"]).pack(anchor="w")

# ------------------------------------------------------------------------------

class CalendarioPersonalizado: 
    def __init__(self, master):
        self.master = master
        self.hoy = datetime.today()
        self.mes_actual = self.hoy.month
        self.anio_actual = self.hoy.year
        self.fecha_seleccionada = None

        self.frame = tk.Frame(master, bg=COLORS["card"], relief="flat")
        self.frame.config(highlightbackground=COLORS["border"], highlightthickness=1)
        self.frame.pack(padx=10, pady=10)

        self.crear_encabezado()
        self.crear_dias()

    def crear_encabezado(self):
        self.header = tk.Frame(self.frame, bg=COLORS["primary"], height=50)
        self.header.pack(fill="x")

        self.btn_prev = tk.Button(self.header, text="◀", command=self.mes_anterior,
                                     bg=COLORS["primary_light"], fg="white", relief="flat",
                                     font=("Segoe UI", 11, "bold"), width=3, cursor="hand2",
                                     activebackground=COLORS["primary_dark"], activeforeground="white",
                                     bd=0)
        self.btn_prev.pack(side="left", padx=10, pady=10)

        self.lbl_mes = tk.Label(self.header, text="", font=("Segoe UI", 13, "bold"),
                                     bg=COLORS["primary"], fg="white")
        self.lbl_mes.pack(side="left", expand=True)

        self.btn_next = tk.Button(self.header, text="▶", command=self.mes_siguiente,
                                     bg=COLORS["primary_light"], fg="white", relief="flat",
                                     font=("Segoe UI", 11, "bold"), width=3, cursor="hand2",
                                     activebackground=COLORS["primary_dark"], activeforeground="white",
                                     bd=0)
        self.btn_next.pack(side="right", padx=10, pady=10)

    def crear_dias(self):
        self.dias_frame = tk.Frame(self.frame, bg=COLORS["card"])
        self.dias_frame.pack(padx=10, pady=10)
        self.actualizar_calendario()

    def actualizar_calendario(self):
        for widget in self.dias_frame.winfo_children():
            widget.destroy()

        meses_es = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                      "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        self.lbl_mes.config(text=f"{meses_es[self.mes_actual]} {self.anio_actual}")

        dias_semana = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        for i, dia in enumerate(dias_semana):
            tk.Label(self.dias_frame, text=dia, bg=COLORS["card"], fg=COLORS["text_light"],
                     font=("Segoe UI", 9, "bold"), width=6).grid(row=0, column=i, pady=(0, 5))

        cal = calendar.Calendar(firstweekday=0)
        semanas = cal.monthdayscalendar(self.anio_actual, self.mes_actual)
        
        for fila, semana in enumerate(semanas, start=1):
            for col, dia in enumerate(semana):
                if dia == 0:
                    tk.Label(self.dias_frame, text="", bg=COLORS["card"], width=6, height=2).grid(
                        row=fila, column=col, padx=2, pady=2)
                else:
                    fecha = datetime(self.anio_actual, self.mes_actual, dia)
                    bg_color = COLORS["card"]
                    fg_color = COLORS["text"]
                    font_weight = "normal"

                    turnos = cargar_turnos()
                    hay_turnos = any(t["fecha"] == fecha.strftime("%d/%m/%Y") for t in turnos)
                    
                    if self.fecha_seleccionada and fecha.date() == self.fecha_seleccionada.date():
                        bg_color = COLORS["accent"]
                        fg_color = "white"
                        font_weight = "bold"
                    elif fecha.date() == datetime.today().date():
                        bg_color = COLORS["primary"]
                        fg_color = "white"
                        font_weight = "bold"
                    elif fecha.date() < datetime.today().date():
                        fg_color = COLORS["text_light"]
                    
                    texto = str(dia)
                    if hay_turnos:
                        texto = f"{dia}\n●"

                    btn = tk.Button(self.dias_frame, text=texto, bg=bg_color, fg=fg_color,
                                     font=("Segoe UI", 9, font_weight), width=6, height=2,
                                     relief="flat", cursor="hand2",
                                     activebackground=COLORS["accent"], activeforeground="white",
                                     command=lambda f=fecha: self.seleccionar_fecha(f))
                    btn.grid(row=fila, column=col, padx=2, pady=2)

    def seleccionar_fecha(self, fecha):
        self.fecha_seleccionada = fecha
        filtrar_horarios(fecha.strftime("%d/%m/%Y"))
        self.actualizar_calendario()
        actualizar_estadisticas()

    def mes_siguiente(self):
        if self.mes_actual == 12:
            self.mes_actual = 1
            self.anio_actual += 1
        else:
            self.mes_actual += 1
        self.actualizar_calendario()

    def mes_anterior(self):
        if self.mes_actual == 1:
            self.mes_actual = 12
            self.anio_actual -= 1
        else:
            self.mes_actual -= 1
        self.actualizar_calendario()

# ==============================================================================
# ⚙️ BLOQUE LÓGICA FRONTEND: FUNCIONES DE INTERACCIÓN
# ==============================================================================

# --- SECCIÓN TURNOS Y SCORE DE AUSENTISMO ---

def eliminar_turno(): 
    global turno_en_edicion
    selected = tabla_turnos.focus()
    if not selected:
        messagebox.showwarning("Atención", "Debe seleccionar un turno de la tabla")
        return

    valores = tabla_turnos.item(selected)["values"]
    fecha = valores[0]
    hora = valores[1]
    medico = valores[5] 

    if messagebox.askyesno("Confirmar", "¿Está seguro de eliminar este turno?"):
        if database.eliminar_turno_db(fecha, hora, medico):
            turno_en_edicion = None
            actualizar_tabla_turnos()
            calendario_moderno.actualizar_calendario()
            actualizar_estadisticas()
            
            # Notificar Lista de Espera Inteligente
            notificar_lista_espera_vacante(medico, fecha, hora)
            messagebox.showinfo("Éxito", "Turno eliminado correctamente")
        else:
            messagebox.showerror("Error", "No se pudo eliminar el turno.")

def editar_turno(): 
    global turno_en_edicion
    selected = tabla_turnos.focus()
    if not selected:
        messagebox.showwarning("Atención", "Debe seleccionar un turno de la tabla")
        return
    
    try:
        index = int(selected)
        turnos = cargar_turnos()
        turnos_ordenados = sorted(turnos, key=lambda x: (
            datetime.strptime(x["fecha"], "%d/%m/%Y"), x["hora"]))
        turno = turnos_ordenados[index]
    except (ValueError, IndexError):
        messagebox.showerror("Error", "No se pudo identificar el turno para editar.")
        return
    
    dato_paciente = turno.get("paciente","")
    if not str(dato_paciente).isdigit():
        p = database.obtener_paciente_por_nombre(dato_paciente)
        if p:
            dato_paciente = p["dni"] 

    entry_paciente.delete(0, tk.END)
    entry_paciente.insert(0, dato_paciente) 
    
    entry_motivo.delete(0, tk.END)
    entry_motivo.insert(0, turno.get("motivo",""))
    
    combo_hora.set(turno.get("hora",""))
    combo_medico.set(turno.get("medico",""))
    
    try:
        fecha_dt = datetime.strptime(turno.get("fecha","01/01/2000"), "%d/%m/%Y")
        calendario_moderno.fecha_seleccionada = fecha_dt
    except ValueError:
        pass
    
    turno_en_edicion = {
        "fecha": turno["fecha"],
        "hora": turno["hora"],
        "medico": turno["medico"]
    }
    
    messagebox.showinfo("Modo Edición", "Datos cargados en el formulario.\n\nModifique los campos deseados y presione 'Agendar Turno' para guardar las modificaciones.")
        
def filtrar_horarios(fecha): 
    turnos = cargar_turnos()
    medico_actual = combo_medico.get()
    ocupados = [t["hora"] for t in turnos if t["fecha"] == fecha and t.get("medico") == medico_actual]
    disponibles = [h for h in HORARIOS if h not in ocupados]
    combo_hora["values"] = disponibles
    if disponibles:
        combo_hora.set(disponibles[0])
    else:
        combo_hora.set("")
    
    lbl_disponibles.config(text=f"Horarios disponibles: {len(disponibles)}")

def agendar_turno(): 
    global turno_en_edicion
    fecha = calendario_moderno.fecha_seleccionada
    if not fecha:
        messagebox.showwarning("Atención", "Seleccione una fecha en el calendario")
        return

    if fecha.date() < datetime.today().date():
        messagebox.showwarning("Atención", "No se pueden agendar turnos en fechas pasadas")
        return

    turno = {
        "fecha": fecha.strftime("%d/%m/%Y"),
        "hora": combo_hora.get(),
        "paciente": entry_paciente.get().strip(), 
        "motivo": entry_motivo.get().strip(),
        "medico": combo_medico.get()
    }

    if not all([turno["hora"], turno["paciente"], turno["motivo"], turno["medico"]]):
        messagebox.showwarning("Atención", "Complete todos los campos. En Paciente ingrese el DNI.")
        return

    if turno_en_edicion:
        exito = database.actualizar_turno_db(
            turno_en_edicion["fecha"],
            turno_en_edicion["hora"],
            turno_en_edicion["medico"],
            turno
        )
        msg_exito = "Turno modificado correctamente."
    else:
        exito = database.guardar_turno_db(turno)
        msg_exito = "Turno agendado correctamente."

    if exito:
        turno_en_edicion = None
        actualizar_tabla_turnos()
        calendario_moderno.actualizar_calendario()
        actualizar_estadisticas()

        entry_paciente.delete(0, tk.END)
        entry_motivo.delete(0, tk.END)
        messagebox.showinfo("Éxito", msg_exito)
    else:
        messagebox.showerror("Error", "No se pudo guardar el turno. \nVerifique:\n1. Que el DNI del paciente exista en el sistema.\n2. Que sea un número válido.")

def enviar_whatsapp():
    selected = tabla_turnos.focus()
    if not selected:
        messagebox.showwarning("Atención", "Seleccione un turno para enviar el recordatorio.")
        return
    
    valores = tabla_turnos.item(selected)["values"]
    fecha = valores[0]
    hora = valores[1]
    nombre_paciente = valores[2]
    medico = valores[5]
    
    paciente_obj = database.obtener_paciente_por_nombre(nombre_paciente)
    if not paciente_obj:
        paciente_obj = database.obtener_paciente_por_dni(nombre_paciente)

    telefono_raw = paciente_obj["telefono"] if paciente_obj else ""
    telefono = re.sub(r'\D', '', str(telefono_raw))
            
    if not telefono or len(telefono) < 6:
        messagebox.showerror("Error", f"El paciente {nombre_paciente} no tiene un teléfono válido registrado.")
        return

    mensaje = f"""Hola {nombre_paciente}, le recordamos su turno del {fecha} a las {hora} hs con el Dr/a {medico}.

1 - Confirmar
2 - Cancelar
3 - Modificar

Saludos, MEDIDOC 2.0 Soft"""

    mensaje_codificado = quote(mensaje)
    
    if not telefono.startswith("54"): 
        telefono = "549" + telefono 
        
    url = f"https://web.whatsapp.com/send?phone={telefono}&text={mensaje_codificado}"
    webbrowser.open(url, new=0, autoraise=True)

def registrar_llegada_desde_turnos():
    """Envía al paciente seleccionado a la Sala de Espera 'En Vivo'."""
    selected = tabla_turnos.focus()
    if not selected:
        messagebox.showwarning("Atención", "Seleccione un turno de la tabla.")
        return

    valores = tabla_turnos.item(selected)["values"]
    nombre_paciente = valores[2]
    medico = valores[5]

    paciente_obj = database.obtener_paciente_por_nombre(nombre_paciente)
    if not paciente_obj:
        messagebox.showerror("Error", "No se encontró el registro del paciente.")
        return

    if database.registrar_llegada_sala_db(paciente_obj["dni"], medico):
        actualizar_tabla_sala_espera()
        messagebox.showinfo("Sala de Espera", f"{nombre_paciente} ingresó a la Sala de Espera 'En Vivo'.")
    else:
        messagebox.showerror("Error", "No se pudo registrar la llegada.")

def actualizar_tabla_turnos(): 
    for item in tabla_turnos.get_children():
        tabla_turnos.delete(item)
    
    turnos = cargar_turnos()
    turnos_ordenados = sorted(turnos, key=lambda x: (
        datetime.strptime(x["fecha"], "%d/%m/%Y"),
        x["hora"]
    ))
    
    for i, turno in enumerate(turnos_ordenados):
        dni_pac = turno.get("dni", "")
        score_badge, score_desc = database.calcular_score_paciente_db(dni_pac)
        
        tabla_turnos.insert("", "end", iid=i, values=(
            turno.get("fecha",""),
            turno.get("hora",""),
            turno.get("paciente",""),
            score_badge,
            turno.get("motivo",""),
            turno.get("medico",""),
            turno.get("estado", "Pendiente")
        ))

def actualizar_estadisticas(): 
    stats = obtener_estadisticas()
    
    for widget in frame_stats.winfo_children():
        widget.destroy()
    
    TarjetaEstadistica(frame_stats, "Total Turnos", stats["total"], "📊", COLORS["primary"]).pack(
        side="left", padx=5)
    TarjetaEstadistica(frame_stats, "Próximos 7 días", stats["proximos_7_dias"], "📅", COLORS["success"]).pack(
        side="left", padx=5)
    
    crear_grafico_medicos(stats["por_medico"])

def crear_grafico_medicos(por_medico): 
    for widget in frame_grafico.winfo_children():
        widget.destroy()
    
    if not por_medico:
        tk.Label(frame_grafico, text="No hay datos para mostrar", 
                 font=("Segoe UI", 10), bg=COLORS["card"], fg=COLORS["text_light"]).pack(pady=20)
        return
    
    max_val = max(por_medico.values()) if por_medico else 1
    
    tk.Label(frame_grafico, text="Turnos por Médico", font=("Segoe UI", 11, "bold"),
             bg=COLORS["card"], fg=COLORS["text"]).pack(pady=(10, 5))
    
    colores_medicos = [COLORS["primary"], COLORS["accent"], COLORS["success"], COLORS["warning"]]
    
    for i, (medico, cantidad) in enumerate(sorted(por_medico.items(), key=lambda x: x[1], reverse=True)):
        fila = tk.Frame(frame_grafico, bg=COLORS["card"])
        fila.pack(fill="x", padx=20, pady=5)
        
        tk.Label(fila, text=medico, font=("Segoe UI", 9), bg=COLORS["card"], 
                 fg=COLORS["text"], width=15, anchor="w").pack(side="left")
        
        barra_bg = tk.Frame(fila, bg=COLORS["background"], height=20, width=200)
        barra_bg.pack(side="left", padx=(5, 10))
        barra_bg.pack_propagate(False)
        
        ancho_barra = int((cantidad / max_val) * 190) if max_val > 0 else 0
        barra = tk.Frame(barra_bg, bg=colores_medicos[i % len(colores_medicos)], height=20, width=ancho_barra)
        barra.place(x=0, y=0)
        
        tk.Label(fila, text=str(cantidad), font=("Segoe UI", 9, "bold"), 
                 bg=COLORS["card"], fg=COLORS["text"]).pack(side="left")

# --- SECCIÓN SALA DE ESPERA "EN VIVO" (MEDIDOC 2.0) ---

def actualizar_tabla_sala_espera():
    for item in tabla_sala.get_children():
        tabla_sala.delete(item)

    pacientes_sala = database.obtener_sala_espera_db()
    for p in pacientes_sala:
        mins = p["minutos_espera"]
        tiempo_str = f"⏱️ {mins} min" if mins > 0 else "Recién ingresado"
        tabla_sala.insert("", "end", iid=p["id"], values=(
            p["paciente"],
            p["dni"],
            p["medico"],
            p["llegada"],
            tiempo_str,
            p["estado"]
        ))

def pasar_a_consulta_sala():
    selected = tabla_sala.focus()
    if not selected:
        messagebox.showwarning("Atención", "Seleccione un paciente de la lista de espera.")
        return
    id_sala = int(selected)
    database.cambiar_estado_sala_db(id_sala, "En Atencion")
    actualizar_tabla_sala_espera()
    messagebox.showinfo("Estado", "Paciente pasó a consulta médica.")

def marcar_atendido_sala():
    selected = tabla_sala.focus()
    if not selected:
        messagebox.showwarning("Atención", "Seleccione un paciente.")
        return
    id_sala = int(selected)
    database.cambiar_estado_sala_db(id_sala, "Atendido")
    actualizar_tabla_sala_espera()
    messagebox.showinfo("Éxito", "Consulta finalizada correctamente.")

def marcar_ausente_sala():
    selected = tabla_sala.focus()
    if not selected:
        messagebox.showwarning("Atención", "Seleccione un paciente.")
        return
    id_sala = int(selected)
    database.cambiar_estado_sala_db(id_sala, "Ausente")
    actualizar_tabla_sala_espera()

# --- SECCIÓN LISTA DE ESPERA INTELIGENTE (MEDIDOC 2.0) ---

def agregar_a_lista_espera():
    dni = entry_le_dni.get().strip()
    medico = combo_le_medico.get().strip()
    pref = entry_le_pref.get().strip()

    if not dni or not medico:
        messagebox.showwarning("Atención", "DNI y Médico son obligatorios.")
        return

    pac = database.obtener_paciente_por_dni(dni)
    if not pac:
        messagebox.showerror("Error", "El DNI ingresado no corresponde a un paciente registrado.")
        return

    if database.agregar_lista_espera_db(dni, medico, pref if pref else "Indiferente"):
        entry_le_dni.delete(0, tk.END)
        entry_le_pref.delete(0, tk.END)
        actualizar_tabla_lista_espera()
        messagebox.showinfo("Éxito", f"{pac['nombre']} registrado en la Lista de Espera.")
    else:
        messagebox.showerror("Error", "No se pudo registrar en la Lista de Espera.")

def actualizar_tabla_lista_espera():
    for item in tabla_lista_espera.get_children():
        tabla_lista_espera.delete(item)

    items = database.obtener_lista_espera_db()
    for it in items:
        tabla_lista_espera.insert("", "end", iid=it["id"], values=(
            it["paciente"],
            it["dni"],
            it["medico"],
            it["fecha"],
            it["preferencia"],
            it["telefono"]
        ))

def notificar_lista_espera_vacante(medico_nombre, fecha, hora):
    """Detecta pacientes en lista de espera y ofrece vacante por WhatsApp."""
    espera = database.obtener_lista_espera_db(medico_nombre)
    if not espera:
        return

    prox = espera[0]
    if messagebox.askyesno("Lista de Espera Inteligente", 
                            f"Se liberó un turno con {medico_nombre} para el {fecha} a las {hora}.\n\n"
                            f"¿Desea enviar una invitación por WhatsApp a {prox['paciente']} (Lista de Espera)?"):
        tel = re.sub(r'\D', '', str(prox['telefono']))
        if not tel.startswith("54"): tel = "549" + tel
        msg = f"Hola {prox['paciente']}, se liberó un turno con {medico_nombre} para el {fecha} a las {hora} hs. ¿Desea confirmarlo? Saludos, MEDIDOC 2.0"
        url = f"https://web.whatsapp.com/send?phone={tel}&text={quote(msg)}"
        webbrowser.open(url)
        database.cambiar_estado_lista_espera_db(prox["id"], "Notificado")
        actualizar_tabla_lista_espera()

# --- SECCIÓN RECETAS Y ÓRDENES PDF (MEDIDOC 2.0) ---

def generar_receta_medica():
    dni = entry_rec_dni.get().strip()
    medico_nom = combo_rec_medico.get()
    indicacion = text_rec_indicacion.get("1.0", "end-1c").strip()
    diag = entry_rec_diag.get().strip()

    if not dni or not medico_nom or not indicacion:
        messagebox.showwarning("Atención", "Complete el DNI del Paciente, Médico e Indicaciones.")
        return

    pac = database.obtener_paciente_por_dni(dni)
    if not pac:
        messagebox.showerror("Error", "No se encontró ningún paciente registrado con ese DNI.")
        return

    medicos = cargar_medicos()
    medico_obj = next((m for m in medicos if m["nombre"] == medico_nom), {"nombre": medico_nom, "especialidad": "General", "matricula": "N/A"})

    ruta = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("Archivos PDF", "*.pdf")],
        initialfile=f"Receta_{pac['nombre'].replace(' ', '_')}.pdf",
        title="Guardar Receta Médica Digital"
    )

    if ruta:
        if reportes.generar_pdf_receta(pac, medico_obj, indicacion, diag, ruta):
            messagebox.showinfo("Éxito", "Receta Médica PDF generada correctamente.")
            try:
                os.startfile(ruta)
            except Exception:
                pass

# --- SECCIÓN GESTIÓN DE MÉDICOS (ABM) ---

def abrir_gestion_medicos(): 
    if rol_usuario_actual == "Medico":
        messagebox.showerror("Acceso Denegado", "No tiene permisos para administrar personal médico.")
        return

    ventana_abm = tk.Toplevel(ventana)
    ventana_abm.title("Administrar Médicos (SQL)") 
    ventana_abm.minsize(950, 600) 
    ventana_abm.config(bg=COLORS["background"])
    
    header_abm = tk.Frame(ventana_abm, bg=COLORS["primary"], height=60)
    header_abm.pack(fill="x")
    tk.Label(header_abm, text="👨‍⚕️ Gestión de Staff Médico (Base de Datos)", font=("Segoe UI", 16, "bold"),
             bg=COLORS["primary"], fg="white").pack(pady=10)

    main_abm = tk.Frame(ventana_abm, bg=COLORS["background"])
    main_abm.pack(fill="both", expand=True, padx=20, pady=20)

    # PANEL IZQUIERDO
    panel_form = tk.Frame(main_abm, bg=COLORS["card"], padx=20, pady=20)
    panel_form.pack(side="left", fill="both", expand=True, padx=(0, 10))
    panel_form.config(highlightbackground=COLORS["border"], highlightthickness=1)

    tk.Label(panel_form, text="Nuevo / Editar Médico", font=("Segoe UI", 12, "bold"),
             bg=COLORS["card"], fg=COLORS["text"]).pack(anchor="w", pady=(0, 15))

    def crear_input(parent, label):
        tk.Label(parent, text=label, bg=COLORS["card"], font=("Segoe UI", 9)).pack(anchor="w")
        entry = ttk.Entry(parent, width=30, font=("Segoe UI", 9))
        entry.pack(fill="x", pady=(2, 10))
        return entry

    ent_nombre = crear_input(panel_form, "Nombre Completo (ej: Dr. Pérez):")
    ent_especialidad = crear_input(panel_form, "Especialidad:")
    ent_matricula = crear_input(panel_form, "Matrícula:")
    ent_telefono = crear_input(panel_form, "Teléfono:")
    ent_email = crear_input(panel_form, "Email:")

    # PANEL DERECHO
    panel_lista = tk.Frame(main_abm, bg=COLORS["card"], padx=10, pady=10)
    panel_lista.pack(side="right", fill="both", expand=True)
    panel_lista.config(highlightbackground=COLORS["border"], highlightthickness=1)

    cols = ("nombre", "especialidad", "matricula")
    tree_medicos = ttk.Treeview(panel_lista, columns=cols, show="headings", height=15)
    tree_medicos.heading("nombre", text="Nombre")
    tree_medicos.heading("especialidad", text="Especialidad")
    tree_medicos.heading("matricula", text="Matrícula")
    tree_medicos.column("nombre", width=120)
    tree_medicos.column("especialidad", width=120)
    tree_medicos.column("matricula", width=80)
    tree_medicos.pack(fill="both", expand=True)
    
    def limpiar_form_medicos():
        ent_nombre.delete(0, tk.END)
        ent_especialidad.delete(0, tk.END)
        ent_matricula.delete(0, tk.END)
        ent_telefono.delete(0, tk.END)
        ent_email.delete(0, tk.END)

    def refrescar_lista_medicos():
        for item in tree_medicos.get_children():
            tree_medicos.delete(item)
        medicos = cargar_medicos() 
        for m in medicos:
            tree_medicos.insert("", "end", values=(m["nombre"], m["especialidad"], m["matricula"]))

    def guardar_medico_abm():
        email_ingresado = ent_email.get().strip()
        if not email_ingresado:
            email_ingresado = "-"

        nuevo_medico = {
            "nombre": ent_nombre.get().strip(),
            "especialidad": ent_especialidad.get().strip(),
            "matricula": ent_matricula.get().strip(),
            "telefono": ent_telefono.get().strip(), 
            "email": email_ingresado              
        }

        if not nuevo_medico["nombre"] or not nuevo_medico["matricula"]:
            messagebox.showwarning("Faltan datos", "Nombre y Matrícula son obligatorios.")
            return

        exito = database.guardar_medico_db(nuevo_medico)
        
        if exito:
            limpiar_form_medicos()
            refrescar_lista_medicos()
            actualizar_combo_medicos_main()
            messagebox.showinfo("Éxito", "Médico guardado en Base de Datos SQL.")
        else:
            messagebox.showerror("Error", "No se pudo guardar el médico en la base de datos.")

    def eliminar_medico_abm():
        selected = tree_medicos.focus()
        if not selected:
            return
        values = tree_medicos.item(selected)["values"]
        nombre_sel = values[0]

        if messagebox.askyesno("Confirmar", f"¿Eliminar a {nombre_sel} de la Base de Datos?"):
            if database.eliminar_medico_db(nombre_sel):
                refrescar_lista_medicos()
                actualizar_combo_medicos_main()
                messagebox.showinfo("Éxito", "Médico eliminado.")
            else:
                messagebox.showerror("Error", "No se pudo eliminar.")

    frame_btns = tk.Frame(panel_form, bg=COLORS["card"])
    frame_btns.pack(fill="x", pady=20) 

    container_btns_abm = tk.Frame(frame_btns, bg=COLORS["card"])
    container_btns_abm.pack()

    crear_boton(container_btns_abm, "💾 Guardar", guardar_medico_abm, COLORS["success"]).pack(side="left", padx=5)
    crear_boton(container_btns_abm, "🗑️ Eliminar", eliminar_medico_abm, COLORS["danger"]).pack(side="left", padx=5)

    refrescar_lista_medicos()

def actualizar_combo_medicos_main(): 
    nombres = obtener_nombres_medicos()
    combo_medico["values"] = nombres
    combo_le_medico["values"] = nombres
    combo_rec_medico["values"] = nombres
    if combo_medico.get() not in nombres:
        combo_medico.set("")
    elif not combo_medico.get() and nombres:
        combo_medico.set(nombres[0])

# --- SECCIÓN PACIENTES ---

def guardar_paciente(): 
    dni_texto = entry_pac_dni.get().strip()
    nombre = entry_pac_nombre.get().strip()

    if not nombre or not dni_texto:
        messagebox.showwarning("Atención", "El nombre y DNI son obligatorios")
        return

    try:
        dni_numero = int(dni_texto) 
    except ValueError:
        messagebox.showerror("Error", "El DNI debe ser un número sin puntos ni letras.")
        return

    def validar(texto):
        return texto if texto else "-"

    paciente = {
        "nombre": nombre,
        "dni": dni_numero,
        "fecha_nac": validar(entry_pac_fnac.get().strip()),
        "telefono": validar(entry_pac_tel.get().strip()),
        "email": validar(entry_pac_email.get().strip()),
        "direccion": validar(entry_pac_dir.get().strip()),
        "obra_social": validar(entry_pac_os.get().strip()),
        "num_afiliado": entry_pac_afiliado.get().strip(),
        "grupo_sanguineo": combo_grupo_sang.get(),
        "alergias": text_alergias.get("1.0", "end-1c").strip(),
        "enfermedades": text_enfermedades.get("1.0", "end-1c").strip(),
        "medicacion": text_medicacion.get("1.0", "end-1c").strip(),
        "observaciones": text_observaciones.get("1.0", "end-1c").strip()
    }
    
    if database.guardar_paciente_db(paciente):
        messagebox.showinfo("Éxito", "Paciente guardado correctamente en SQL")
        limpiar_formulario_paciente()
        actualizar_tabla_pacientes()
        actualizar_stats_pacientes()
    else:
        messagebox.showerror("Error", "No se pudo guardar el paciente.")

def limpiar_formulario_paciente(): 
    entry_pac_nombre.delete(0, tk.END)
    entry_pac_dni.delete(0, tk.END)
    entry_pac_fnac.delete(0, tk.END)
    entry_pac_tel.delete(0, tk.END)
    entry_pac_email.delete(0, tk.END)
    entry_pac_dir.delete(0, tk.END)
    entry_pac_os.delete(0, tk.END)
    entry_pac_afiliado.delete(0, tk.END)
    combo_grupo_sang.set("")
    text_alergias.delete("1.0", "end")
    text_enfermedades.delete("1.0", "end")
    text_medicacion.delete("1.0", "end")
    text_observaciones.delete("1.0", "end")

def poblar_tabla_pacientes(pacientes): 
    for item in tabla_pacientes.get_children():
        tabla_pacientes.delete(item)
    
    for i, pac in enumerate(pacientes):
        tabla_pacientes.insert("", "end", iid=i, values=(
            pac.get("dni",""),
            pac.get("nombre",""),
            pac.get("fecha_nac",""),
            pac.get("telefono",""),
            pac.get("obra_social",""),
            pac.get("grupo_sanguineo","")
        ))

def actualizar_tabla_pacientes(): 
    poblar_tabla_pacientes(cargar_pacientes())

def ver_historia_clinica(): 
    selected = tabla_pacientes.focus()
    if not selected:
        messagebox.showwarning("Atención", "Debe seleccionar un paciente de la tabla")
        return
    
    index = int(selected)
    pacientes_list = cargar_pacientes()
    pac = pacientes_list[index]
    
    historial_observaciones = cargar_historial_de_paciente(pac["dni"])
    
    ventana_hc = tk.Toplevel(ventana)
    ventana_hc.title(f"Historia Clínica - {pac['nombre']}")
    ventana_hc.geometry("800x900") 
    ventana_hc.config(bg=COLORS["background"])

    def descargar_pdf():
        ruta = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Archivos PDF", "*.pdf")],
            initialfile=f"Historia_{str(pac['nombre']).replace(' ', '_')}.pdf",
            title="Guardar Historia Clínica"
        )
        
        if ruta:
            if reportes.generar_pdf_historia(pac, historial_observaciones, ruta):
                messagebox.showinfo("Éxito", "PDF guardado correctamente.")
                try:
                    os.startfile(ruta) 
                except Exception:
                    pass
            
    btn_pdf = tk.Button(ventana_hc, text="📄 Descargar PDF", command=descargar_pdf,
                        bg="#E74C3C", fg="white", font=("Segoe UI", 9, "bold"), 
                        bd=0, padx=10, pady=5, cursor="hand2")
    
    btn_pdf.place(relx=0.95, rely=0.06, anchor="ne") 
    btn_pdf.lift()
    
    header_hc = tk.Frame(ventana_hc, bg=COLORS["primary"], height=60)
    header_hc.pack(fill="x")
    header_hc.pack_propagate(False)
    
    tk.Label(header_hc, text="📋 Historia Clínica Digital", font=("Segoe UI", 16, "bold"),
             bg=COLORS["primary"], fg="white").pack(pady=15)
    
    scroll_frame = tk.Frame(ventana_hc, bg=COLORS["background"])
    scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    canvas = tk.Canvas(scroll_frame, bg=COLORS["background"], highlightthickness=0)
    scrollbar = ttk.Scrollbar(scroll_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg=COLORS["background"])
    
    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Tarjeta Datos Personales
    card1 = tk.Frame(scrollable_frame, bg=COLORS["card"], relief="flat")
    card1.config(highlightbackground=COLORS["border"], highlightthickness=1)
    card1.pack(fill="x", pady=(0, 10))
    
    tk.Label(card1, text="👤 Datos Personales", font=("Segoe UI", 12, "bold"),
             bg=COLORS["card"], fg=COLORS["text"]).pack(anchor="w", padx=15, pady=(10, 5))
    
    datos = [
        ("Nombre completo:", pac.get("nombre", "N/A")),
        ("DNI:", pac.get("dni", "N/A")),
        ("Fecha de nacimiento:", pac.get("fecha_nac", "N/A")),
        ("Teléfono:", pac.get("telefono", "N/A")),
        ("Email:", pac.get("email", "N/A")),
        ("Dirección:", pac.get("direccion", "N/A")),
    ]
    
    for label, valor in datos:
        frame_dato = tk.Frame(card1, bg=COLORS["card"])
        frame_dato.pack(fill="x", padx=15, pady=2)
        tk.Label(frame_dato, text=label, font=("Segoe UI", 9, "bold"),
                 bg=COLORS["card"], fg=COLORS["text_light"], width=20, anchor="w").pack(side="left")
        tk.Label(frame_dato, text=valor, font=("Segoe UI", 9),
                 bg=COLORS["card"], fg=COLORS["text"], anchor="w").pack(side="left", fill="x", expand=True)
    
    # Tarjeta Adjuntos Médicos (MEDIDOC 2.0)
    card_adj = tk.Frame(scrollable_frame, bg=COLORS["card"], relief="flat")
    card_adj.config(highlightbackground=COLORS["border"], highlightthickness=1)
    card_adj.pack(fill="x", pady=(0, 10))

    tk.Label(card_adj, text="📂 Estudios y Archivos Adjuntos (PDF/Imágenes)", font=("Segoe UI", 12, "bold"),
             bg=COLORS["card"], fg=COLORS["text"]).pack(anchor="w", padx=15, pady=(10, 5))

    frame_adj_lista = tk.Frame(card_adj, bg=COLORS["card"])
    frame_adj_lista.pack(fill="x", padx=15, pady=5)

    def refrescar_adjuntos():
        for w in frame_adj_lista.winfo_children(): w.destroy()
        adjuntos = database.obtener_adjuntos_db(pac["dni"])
        if not adjuntos:
            tk.Label(frame_adj_lista, text="No hay archivos adjuntos guardados.", bg=COLORS["card"], fg=COLORS["text_light"]).pack()
        else:
            for adj in adjuntos:
                f_item = tk.Frame(frame_adj_lista, bg=COLORS["card"])
                f_item.pack(fill="x", pady=2)
                tk.Label(f_item, text=f"📎 {adj['nombre']} ({adj['fecha']})", bg=COLORS["card"], fg=COLORS["text"]).pack(side="left")
                tk.Button(f_item, text="Abrir", command=lambda r=adj['ruta']: os.startfile(r) if os.path.exists(r) else messagebox.showerror("Error", "Archivo no encontrado"),
                          bg=COLORS["primary"], fg="white", font=("Segoe UI", 8), relief="flat").pack(side="right", padx=5)

    def subir_adjunto():
        ruta = filedialog.askopenfilename(title="Seleccionar Estudio o Análisis", filetypes=[("Archivos", "*.pdf *.png *.jpg *.jpeg *.doc *.docx")])
        if ruta:
            if database.guardar_adjunto_db(pac["dni"], ruta):
                refrescar_adjuntos()
                messagebox.showinfo("Éxito", "Estudio adjuntado correctamente.")
            else:
                messagebox.showerror("Error", "No se pudo adjuntar el archivo.")

    tk.Button(card_adj, text="➕ Subir Archivo Adjunto", command=subir_adjunto, bg=COLORS["accent"], fg="white", font=("Segoe UI", 9, "bold"), relief="flat").pack(padx=15, pady=(0, 10), anchor="w")
    refrescar_adjuntos()
    
    # Tarjeta Observaciones Historial
    card_historial_obs = tk.Frame(scrollable_frame, bg=COLORS["card"], relief="flat")
    card_historial_obs.config(highlightbackground=COLORS["border"], highlightthickness=1)
    card_historial_obs.pack(fill="x", pady=(0, 10))

    tk.Label(card_historial_obs, text="⏰ Historial de Observaciones Médicas", font=("Segoe UI", 12, "bold"),
             bg=COLORS["card"], fg=COLORS["text"]).pack(anchor="w", padx=15, pady=(10, 5))
    
    frame_tabla_obs = tk.Frame(card_historial_obs, bg=COLORS["card"])
    frame_tabla_obs.pack(fill="x", expand=True, padx=15, pady=(0, 10))

    columnas_obs = ("fecha", "hora", "observacion")
    tabla_obs = ttk.Treeview(frame_tabla_obs, columns=columnas_obs, show="headings", height=5)
    
    encabezados_obs = ["Fecha", "Hora", "Observación"]
    for col, enc in zip(columnas_obs, encabezados_obs):
        tabla_obs.heading(col, text=enc)
        tabla_obs.column(col, anchor="center", width=80 if col in ["fecha", "hora"] else 400)
    
    if historial_observaciones:
        for i, obs in enumerate(historial_observaciones):
            tabla_obs.insert("", "end", iid=i, values=(
                obs.get("fecha",""),
                obs.get("hora",""),
                obs.get("observacion","")
            ))
    else:
        tk.Label(card_historial_obs, text="No hay observaciones guardadas.", 
                 bg=COLORS["card"], fg=COLORS["text_light"]).pack(pady=10)
        
    tabla_obs.pack(fill="x", expand=True)

    # Tarjeta Visita Actual con Dictado por Voz (MEDIDOC 2.0)
    card_visita = tk.Frame(scrollable_frame, bg=COLORS["card"], relief="flat")
    card_visita.config(highlightbackground=COLORS["primary_light"], highlightthickness=2)
    card_visita.pack(fill="x", pady=(0, 10))
    
    frame_visita_head = tk.Frame(card_visita, bg=COLORS["card"])
    frame_visita_head.pack(fill="x", padx=15, pady=(10, 5))

    tk.Label(frame_visita_head, text="✍️ Observaciones de la Visita ACTUAL", font=("Segoe UI", 12, "bold"),
             bg=COLORS["card"], fg=COLORS["primary"]).pack(side="left")
    
    text_observaciones_visita = scrolledtext.ScrolledText(card_visita, height=6, font=("Segoe UI", 9), wrap="word")
    text_observaciones_visita.pack(fill="x", padx=15, pady=(0, 10))

    tk.Button(frame_visita_head, text="🎙️ Dictar por Voz", command=lambda: dictar_observacion(text_observaciones_visita),
              bg=COLORS["warning"], fg="white", font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2").pack(side="right")
    
    def cmd_guardar_observacion():
        dni = pac.get("dni")
        observacion = text_observaciones_visita.get("1.0", "end-1c")
        if guardar_observacion_visita(dni, observacion):
            messagebox.showinfo("Éxito", "Observación guardada y añadida al historial.")
            ventana_hc.destroy()
            ver_historia_clinica_recarga(pacientes_list.index(pac)) 

    def ver_historia_clinica_recarga(index_paciente):
        tabla_pacientes.focus(index_paciente)
        ver_historia_clinica()

    btn_guardar_obs = tk.Button(card_visita, text="💾 Guardar Observación", command=cmd_guardar_observacion,
                                     bg=COLORS["primary"], fg="white", font=("Segoe UI", 10, "bold"),
                                     relief="flat", cursor="hand2", pady=8, width=25,
                                     activebackground=COLORS["primary_dark"], activeforeground="white", bd=0)
    btn_guardar_obs.pack(pady=(0, 15))
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    tk.Button(ventana_hc, text="Cerrar", command=ventana_hc.destroy,
             bg=COLORS["danger"], fg="white", font=("Segoe UI", 10, "bold"),
             relief="flat", cursor="hand2", pady=8, width=25).pack(pady=10)

def editar_paciente():
    selected = tabla_pacientes.focus()
    if not selected:
        messagebox.showwarning("Atención", "Debe seleccionar un paciente de la tabla")
        return
    
    index = int(selected)
    pacientes = cargar_pacientes()
    pac = pacientes[index]
    
    entry_pac_nombre.delete(0, tk.END)
    entry_pac_nombre.insert(0, pac.get("nombre", ""))
    entry_pac_dni.delete(0, tk.END)
    entry_pac_dni.insert(0, pac.get("dni", ""))
    entry_pac_fnac.delete(0, tk.END)
    entry_pac_fnac.insert(0, pac.get("fecha_nac", ""))
    entry_pac_tel.delete(0, tk.END)
    entry_pac_tel.insert(0, pac.get("telefono", ""))
    entry_pac_email.delete(0, tk.END)
    entry_pac_email.insert(0, pac.get("email", ""))
    entry_pac_dir.delete(0, tk.END)
    entry_pac_dir.insert(0, pac.get("direccion", ""))
    entry_pac_os.delete(0, tk.END)
    entry_pac_os.insert(0, pac.get("obra_social", ""))
    entry_pac_afiliado.delete(0, tk.END)
    entry_pac_afiliado.insert(0, pac.get("num_afiliado", ""))
    combo_grupo_sang.set(pac.get("grupo_sanguineo", ""))
    text_alergias.delete("1.0", "end")
    text_alergias.insert("1.0", pac.get("alergias", ""))
    text_enfermedades.delete("1.0", "end")
    text_enfermedades.insert("1.0", pac.get("enfermedades", ""))
    text_medicacion.delete("1.0", "end")
    text_medicacion.insert("1.0", pac.get("medicacion", ""))
    text_observaciones.delete("1.0", "end")
    text_observaciones.insert("1.0", pac.get("observaciones", ""))

def eliminar_paciente():
    selected = tabla_pacientes.focus()
    if not selected:
        messagebox.showwarning("Atención", "Debe seleccionar un paciente de la tabla")
        return
    
    values = tabla_pacientes.item(selected)["values"]
    dni_seleccionado = str(values[0]) 
    
    if messagebox.askyesno("Confirmar", "¿Está seguro de eliminar este paciente de la Base de Datos?"):
        if database.eliminar_paciente_db(dni_seleccionado):
            actualizar_tabla_pacientes()
            actualizar_stats_pacientes()
            messagebox.showinfo("Éxito", "Paciente eliminado correctamente")
        else:
            messagebox.showerror("Error", "No se pudo eliminar el paciente.")

def buscar_paciente():
    termino = entry_buscar_pac.get().strip().lower()
    if not termino:
        actualizar_tabla_pacientes()
        return
    
    pacientes = cargar_pacientes()
    resultados = [p for p in pacientes if 
                  termino in str(p.get("nombre", "")).lower() or 
                  termino in str(p.get("dni", "")).lower()]
    
    poblar_tabla_pacientes(resultados)

def es_particular(os_texto):
    val = str(os_texto).strip().lower()
    return not val or val in ["-", "particular", "ninguna", "none", "no", "no tiene", "n/a", "sin obra social"]

def actualizar_stats_pacientes():
    pacientes = cargar_pacientes()
    total_pac = len(pacientes)
    
    for widget in frame_stats_pac.winfo_children():
        widget.destroy()
    
    TarjetaEstadistica(frame_stats_pac, "Total Pacientes", total_pac, "👥", COLORS["primary"]).pack(
        side="left", padx=5)
    
    con_os = sum(1 for p in pacientes if not es_particular(p.get("obra_social", "")))
    TarjetaEstadistica(frame_stats_pac, "Con Obra Social", con_os, "🏥", COLORS["success"]).pack(
        side="left", padx=5)
    
    sin_os = total_pac - con_os
    TarjetaEstadistica(frame_stats_pac, "Particular", sin_os, "💳", COLORS["warning"]).pack(
        side="left", padx=5)

# --- EXPORTACIÓN DE DATOS (CSV) ---

def exportar_turnos_csv():
    ruta = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("Archivos CSV", "*.csv")], initialfile="Reporte_Turnos.csv")
    if ruta:
        turnos = cargar_turnos()
        try:
            with open(ruta, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Fecha", "Hora", "Paciente", "DNI", "Médico", "Motivo", "Estado"])
                for t in turnos:
                    writer.writerow([t.get("fecha"), t.get("hora"), t.get("paciente"), t.get("dni"), t.get("medico"), t.get("motivo"), t.get("estado")])
            messagebox.showinfo("Éxito", "Reporte de turnos exportado a CSV correctamente.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar:\n{e}")

def realizar_backup_manual():
    path = database.crear_backup_db()
    if path:
        messagebox.showinfo("Backup Completado", f"Copia de seguridad guardada en:\n{path}")
    else:
        messagebox.showerror("Error", "No se pudo realizar el backup.")

# --- MODO OSCURO / MODO CLARO (MEDIDOC 2.0) ---

def alternar_modo_oscuro():
    global MODO_OSCURO, COLORS
    MODO_OSCURO = not MODO_OSCURO
    COLORS = THEMES["DARK"] if MODO_OSCURO else THEMES["LIGHT"]
    ventana.config(bg=COLORS["background"])
    messagebox.showinfo("Tema Actualizado", f"Modo {'Oscuro' if MODO_OSCURO else 'Claro'} activado. Reinicie la aplicación si desea un refresco completo de la paleta.")

# ==============================================================================
# 🔐 BLOQUE LOGIN Y SEGURIDAD
# ==============================================================================

def mostrar_login(): 
    login_window = tk.Toplevel()
    login_window.title("Login MEDIDOC 2.0")
    login_window.geometry("320x270")
    login_window.config(bg=COLORS["background"])
    login_window.resizable(False, False)

    login_window.grab_set()

    tk.Label(login_window, text="MEDIDOC 2.0", font=("Segoe UI", 18, "bold"), 
             bg=COLORS["background"], fg=COLORS["primary"]).pack(pady=(15, 2))
    tk.Label(login_window, text="Acceso al Sistema", font=("Segoe UI", 10), 
             bg=COLORS["background"], fg=COLORS["text_light"]).pack(pady=(0, 15))

    tk.Label(login_window, text="Usuario:", bg=COLORS["background"], fg=COLORS["text"]).pack()
    entry_user = tk.Entry(login_window)
    entry_user.pack(pady=3)
    entry_user.focus()

    tk.Label(login_window, text="Contraseña:", bg=COLORS["background"], fg=COLORS["text"]).pack()
    entry_pass = tk.Entry(login_window, show="*")
    entry_pass.pack(pady=3)

    def intentar_ingreso(event=None):
        usu = entry_user.get().strip()
        pas = entry_pass.get().strip()
        
        rol = database.validar_login_db(usu, pas)
        
        if rol:
            global rol_usuario_actual
            rol_usuario_actual = rol
            messagebox.showinfo("Bienvenido", f"Hola {usu}, ingresaste como {rol}")
            login_window.destroy() 
            ventana.deiconify()    
            ventana.state('zoomed')

            aplicar_permisos_rol()
        else:
            messagebox.showerror("Error", "Datos incorrectos")

    btn = tk.Button(login_window, text="INGRESAR", bg=COLORS["primary"], fg="white", font=("Segoe UI", 10, "bold"), command=intentar_ingreso, relief="flat")
    btn.pack(pady=15, ipadx=15, ipady=3)
    login_window.bind('<Return>', intentar_ingreso)

    def cerrar_todo():
        try:
            ventana.destroy()
        except Exception:
            pass
    login_window.protocol("WM_DELETE_WINDOW", cerrar_todo)
    
def mostrar_login_protegido():
    mostrar_login() 
    for widget in ventana.winfo_children():
        if isinstance(widget, tk.Toplevel):
            widget.protocol("WM_DELETE_WINDOW", cerrar_todo_seguro)

def aplicar_permisos_rol():
    global rol_usuario_actual
    
    if rol_usuario_actual == "Medico":
        try:
            notebook.hide(tab_turnos) 
        except Exception:
            pass

        try:
            menu_bar.entryconfig("Administrar Médicos", state="disabled")
        except Exception:
            pass

    elif rol_usuario_actual == "Admin":
        try:
            notebook.add(tab_turnos, text="Gestión de Turnos") 
            menu_bar.entryconfig("Administrar Médicos", state="normal")
        except Exception:
            pass

# ==============================================================================
# 🏗️ CONFIGURACIÓN FINAL Y ARRANQUE (MAIN UI)
# ==============================================================================

ventana = tk.Tk()
ventana.withdraw() 
ventana.title("Medidoc 2.0 - Gestión Médica Inteligente") 
ventana.config(bg=COLORS["background"])

# Backup automático preventivo al iniciar
database.crear_backup_db()

fuentes_preferidas = ["Segoe UI", "Arial"]
fuente_elegida = "Segoe UI" 

default_font = tkfont.nametofont("TkDefaultFont")
default_font.configure(family=fuente_elegida, size=10)

# --- MENU SUPERIOR ---
menu_bar = tk.Menu(ventana)
ventana.config(menu=menu_bar)

menu_config = tk.Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="Archivo", menu=menu_config)
menu_config.add_command(label="Administrar Médicos", command=abrir_gestion_medicos)
menu_config.add_command(label="💾 Realizar Copia de Seguridad (Backup)", command=realizar_backup_manual)
menu_config.add_command(label="📊 Exportar Turnos a CSV", command=exportar_turnos_csv)

menu_ver = tk.Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="Ver / Apariencia", menu=menu_ver)
menu_ver.add_command(label="🌙 / ☀️ Alternar Modo Oscuro", command=alternar_modo_oscuro)

# --- HEADER ---
header = tk.Frame(ventana, bg=COLORS["primary"], height=70)
header.pack(fill="x")
header.pack_propagate(False)

tk.Label(header, text="🏥 MEDIDOC 2.0", font=("Segoe UI", 20, "bold"),
         bg=COLORS["primary"], fg="white").pack(side="left", padx=20)

tk.Label(header, text="Sistema de Gestión Médica Inteligente", font=("Segoe UI", 10),
         bg=COLORS["primary"], fg=COLORS["primary_light"]).pack(side="left")

btn_tema = tk.Button(header, text="🌙 / ☀️ Tema", command=alternar_modo_oscuro,
                     bg=COLORS["primary_dark"], fg="white", font=("Segoe UI", 9, "bold"), relief="flat", bd=0, padx=10, pady=5)
btn_tema.pack(side="right", padx=20)

notebook = ttk.Notebook(ventana)
notebook.pack(fill="both", expand=True, padx=10, pady=10)

style = ttk.Style()
style.theme_use("clam")
style.configure("TNotebook", background=COLORS["background"], borderwidth=0)
style.configure("TNotebook.Tab", padding=[15, 4], font=("Segoe UI", 10, "bold"))

AZUL_MEDICO = "#2d2d85" 

style.map('TNotebook.Tab',
          padding=[('selected', [17, 6])], 
          background=[('selected', AZUL_MEDICO)], 
          foreground=[('selected', 'white')]
)

# ==================== PESTAÑA 1: TURNOS ====================
tab_turnos = tk.Frame(notebook, bg=COLORS["background"])
notebook.add(tab_turnos, text="📅 Gestión de Turnos")

main_container = tk.Frame(tab_turnos, bg=COLORS["background"])
main_container.pack(fill="both", expand=True, padx=5, pady=5)

panel_izq = tk.Frame(main_container, bg=COLORS["background"])
panel_izq.pack(side="left", fill="both", padx=(0, 5))

calendario_moderno = CalendarioPersonalizado(panel_izq)

form_card = tk.Frame(panel_izq, bg=COLORS["card"], relief="flat")
form_card.config(highlightbackground=COLORS["border"], highlightthickness=1)
form_card.pack(fill="x", pady=10, padx=10)

tk.Label(form_card, text="Agendar Nuevo Turno", font=("Segoe UI", 12, "bold"),
         bg=COLORS["card"], fg=COLORS["text"]).pack(pady=(15, 10))

# COMBOBOX MÉDICOS
frame_med = tk.Frame(form_card, bg=COLORS["card"])
frame_med.pack(fill="x", padx=20, pady=5)
tk.Label(frame_med, text="Médico:", bg=COLORS["card"], fg=COLORS["text"], 
         font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")

nombres_medicos_inicial = obtener_nombres_medicos()

combo_medico = ttk.Combobox(frame_med, values=nombres_medicos_inicial, state="readonly", width=25, font=("Segoe UI", 9))
combo_medico.pack(side="left", fill="x", expand=True)

if nombres_medicos_inicial:
    combo_medico.set(nombres_medicos_inicial[0])

combo_medico.bind("<<ComboboxSelected>>", lambda e: filtrar_horarios(
    calendario_moderno.fecha_seleccionada.strftime("%d/%m/%Y") 
    if calendario_moderno.fecha_seleccionada else ""))

frame_hora = tk.Frame(form_card, bg=COLORS["card"])
frame_hora.pack(fill="x", padx=20, pady=5)
tk.Label(frame_hora, text="Hora:", bg=COLORS["card"], fg=COLORS["text"], 
         font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")
combo_hora = ttk.Combobox(frame_hora, values=HORARIOS, state="readonly", width=25, font=("Segoe UI", 9))
combo_hora.pack(side="left", fill="x", expand=True)

lbl_disponibles = tk.Label(form_card, text="", bg=COLORS["card"], fg=COLORS["text_light"], font=("Segoe UI", 8))
lbl_disponibles.pack()

frame_pac = tk.Frame(form_card, bg=COLORS["card"])
frame_pac.pack(fill="x", padx=20, pady=5)
tk.Label(frame_pac, text="DNI Paciente:", bg=COLORS["card"], fg=COLORS["text"], 
         font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")
entry_paciente = ttk.Entry(frame_pac, width=25, font=("Segoe UI", 9))
entry_paciente.pack(side="left", fill="x", expand=True)

frame_mot = tk.Frame(form_card, bg=COLORS["card"])
frame_mot.pack(fill="x", padx=20, pady=5)
tk.Label(frame_mot, text="Motivo:", bg=COLORS["card"], fg=COLORS["text"], 
         font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")
entry_motivo = ttk.Entry(frame_mot, width=25, font=("Segoe UI", 9))
entry_motivo.pack(side="left", fill="x", expand=True)

btn_agendar = tk.Button(form_card, text="✓ Agendar Turno", command=agendar_turno,
                          bg=COLORS["success"], fg="white", font=("Segoe UI", 10, "bold"),
                          relief="flat", cursor="hand2", bd=0, pady=10)
btn_agendar.pack(fill="x", padx=20, pady=(10, 15))

panel_der = tk.Frame(main_container, bg=COLORS["background"])
panel_der.pack(side="right", fill="both", expand=True, padx=(5, 0))

frame_stats = tk.Frame(panel_der, bg=COLORS["background"])
frame_stats.pack(fill="x", pady=(0, 10))

frame_grafico = tk.Frame(panel_der, bg=COLORS["card"], relief="flat", height=180)
frame_grafico.config(highlightbackground=COLORS["border"], highlightthickness=1)
frame_grafico.pack(fill="x", pady=(0, 10))
frame_grafico.pack_propagate(False)

tabla_card = tk.Frame(panel_der, bg=COLORS["card"], relief="flat")
tabla_card.config(highlightbackground=COLORS["border"], highlightthickness=1)
tabla_card.pack(fill="both", expand=True)

tk.Label(tabla_card, text="Turnos Agendados", font=("Segoe UI", 11, "bold"),
         bg=COLORS["card"], fg=COLORS["text"]).pack(pady=(10, 5))

# BOTONES TURNOS
frame_botones = tk.Frame(tabla_card, bg=COLORS["card"])
frame_botones.pack(side="bottom", fill="x", pady=15)

container_botones_turnos = tk.Frame(frame_botones, bg=COLORS["card"])
container_botones_turnos.pack()

crear_boton(container_botones_turnos, "✏️ Editar", editar_turno, COLORS["primary"]).pack(side="left", padx=4)
crear_boton(container_botones_turnos, "🗑️ Eliminar", eliminar_turno, COLORS["danger"]).pack(side="left", padx=4)
crear_boton(container_botones_turnos, "📲 WhatsApp", enviar_whatsapp, "#25D366").pack(side="left", padx=4)
crear_boton(container_botones_turnos, "🚦 Marcar Llegada", registrar_llegada_desde_turnos, COLORS["warning"]).pack(side="left", padx=4)

# TABLA TURNOS
frame_tabla_scroll = tk.Frame(tabla_card, bg=COLORS["card"])
frame_tabla_scroll.pack(side="top", fill="both", expand=True, padx=10, pady=(0, 10))

columnas = ("fecha", "hora", "paciente", "score", "motivo", "medico", "estado")
tabla_turnos = ttk.Treeview(frame_tabla_scroll, columns=columnas, show="headings", height=10)

scrollbar_turnos = ttk.Scrollbar(frame_tabla_scroll, orient="vertical", command=tabla_turnos.yview)
tabla_turnos.configure(yscrollcommand=scrollbar_turnos.set)

headers_turnos = ["Fecha", "Hora", "Paciente", "Score Asistencia", "Motivo", "Médico", "Estado"]
for col, h in zip(columnas, headers_turnos):
    tabla_turnos.heading(col, text=h)
    ancho = 90 if col in ["fecha", "hora", "score"] else 130
    tabla_turnos.column(col, anchor="center", width=ancho)

tabla_turnos.pack(side="left", fill="both", expand=True)
scrollbar_turnos.pack(side="right", fill="y")

# ==================== PESTAÑA 2: SALA DE ESPERA "EN VIVO" ====================
tab_sala = tk.Frame(notebook, bg=COLORS["background"])
notebook.add(tab_sala, text="🚦 Sala de Espera 'En Vivo'")

container_sala = tk.Frame(tab_sala, bg=COLORS["background"])
container_sala.pack(fill="both", expand=True, padx=15, pady=15)

card_sala = tk.Frame(container_sala, bg=COLORS["card"], relief="flat")
card_sala.config(highlightbackground=COLORS["border"], highlightthickness=1)
card_sala.pack(fill="both", expand=True)

tk.Label(card_sala, text="🚦 Monitor de Recepción y Consulta en Tiempo Real", font=("Segoe UI", 13, "bold"),
         bg=COLORS["card"], fg=COLORS["primary"]).pack(pady=15)

frame_sala_tabla = tk.Frame(card_sala, bg=COLORS["card"])
frame_sala_tabla.pack(fill="both", expand=True, padx=15, pady=10)

cols_sala = ("paciente", "dni", "medico", "llegada", "tiempo", "estado")
tabla_sala = ttk.Treeview(frame_sala_tabla, columns=cols_sala, show="headings", height=12)
head_sala = ["Paciente", "DNI", "Médico", "Hora Llegada", "Tiempo Espera", "Estado Actual"]

for c, h in zip(cols_sala, head_sala):
    tabla_sala.heading(c, text=h)
    tabla_sala.column(c, anchor="center", width=120)

tabla_sala.pack(side="left", fill="both", expand=True)

frame_sala_btns = tk.Frame(card_sala, bg=COLORS["card"])
frame_sala_btns.pack(pady=15)

crear_boton(frame_sala_btns, "👨‍⚕️ Pasar a Consulta", pasar_a_consulta_sala, COLORS["primary"], width=20).pack(side="left", padx=10)
crear_boton(frame_sala_btns, "✅ Finalizar / Atendido", marcar_atendido_sala, COLORS["success"], width=20).pack(side="left", padx=10)
crear_boton(frame_sala_btns, "❌ Marcar Ausente", marcar_ausente_sala, COLORS["danger"], width=20).pack(side="left", padx=10)
crear_boton(frame_sala_btns, "🔄 Refrescar", actualizar_tabla_sala_espera, COLORS["accent"], width=15).pack(side="left", padx=10)

# ==================== PESTAÑA 3: LISTA DE ESPERA INTELIGENTE ====================
tab_lista_espera = tk.Frame(notebook, bg=COLORS["background"])
notebook.add(tab_lista_espera, text="⚡ Lista de Espera Inteligente")

container_le = tk.Frame(tab_lista_espera, bg=COLORS["background"])
container_le.pack(fill="both", expand=True, padx=15, pady=15)

# Panel Formulario Lista de Espera
card_le_form = tk.Frame(container_le, bg=COLORS["card"], relief="flat")
card_le_form.config(highlightbackground=COLORS["border"], highlightthickness=1)
card_le_form.pack(side="left", fill="both", padx=(0, 10))

tk.Label(card_le_form, text="Anotar en Lista de Espera", font=("Segoe UI", 12, "bold"),
         bg=COLORS["card"], fg=COLORS["text"]).pack(pady=15, padx=20)

tk.Label(card_le_form, text="DNI Paciente:", bg=COLORS["card"], fg=COLORS["text"]).pack(anchor="w", padx=20)
entry_le_dni = ttk.Entry(card_le_form, width=25)
entry_le_dni.pack(padx=20, pady=(2, 10))

tk.Label(card_le_form, text="Médico Solicitado:", bg=COLORS["card"], fg=COLORS["text"]).pack(anchor="w", padx=20)
combo_le_medico = ttk.Combobox(card_le_form, values=nombres_medicos_inicial, state="readonly", width=23)
combo_le_medico.pack(padx=20, pady=(2, 10))
if nombres_medicos_inicial: combo_le_medico.set(nombres_medicos_inicial[0])

tk.Label(card_le_form, text="Preferencia Horaria:", bg=COLORS["card"], fg=COLORS["text"]).pack(anchor="w", padx=20)
entry_le_pref = ttk.Entry(card_le_form, width=25)
entry_le_pref.pack(padx=20, pady=(2, 15))

crear_boton(card_le_form, "➕ Registrar Espera", agregar_a_lista_espera, COLORS["success"], width=22).pack(padx=20, pady=10)

# Tabla Lista de Espera
card_le_tabla = tk.Frame(container_le, bg=COLORS["card"], relief="flat")
card_le_tabla.config(highlightbackground=COLORS["border"], highlightthickness=1)
card_le_tabla.pack(side="right", fill="both", expand=True)

tk.Label(card_le_tabla, text="Pacientes en Espera por Vacante", font=("Segoe UI", 12, "bold"),
         bg=COLORS["card"], fg=COLORS["primary"]).pack(pady=15)

cols_le = ("paciente", "dni", "medico", "fecha", "pref", "tel")
tabla_lista_espera = ttk.Treeview(card_le_tabla, columns=cols_le, show="headings", height=12)
head_le = ["Paciente", "DNI", "Médico Requerido", "Registrado El", "Preferencia", "Teléfono"]

for c, h in zip(cols_le, head_le):
    tabla_lista_espera.heading(c, text=h)
    tabla_lista_espera.column(c, anchor="center", width=110)

tabla_lista_espera.pack(fill="both", expand=True, padx=15, pady=10)

# ==================== PESTAÑA 4: RECETAS Y ÓRDENES ====================
tab_recetas = tk.Frame(notebook, bg=COLORS["background"])
notebook.add(tab_recetas, text="📝 Recetas y Órdenes")

container_rec = tk.Frame(tab_recetas, bg=COLORS["background"])
container_rec.pack(fill="both", expand=True, padx=20, pady=20)

card_rec = tk.Frame(container_rec, bg=COLORS["card"], relief="flat")
card_rec.config(highlightbackground=COLORS["border"], highlightthickness=1)
card_rec.pack(fill="both", expand=True, padx=40, pady=10)

tk.Label(card_rec, text="💊 Generador de Receta / Orden Médica Digital PDF", font=("Segoe UI", 14, "bold"),
         bg=COLORS["card"], fg=COLORS["primary"]).pack(pady=15)

f_rec_form = tk.Frame(card_rec, bg=COLORS["card"])
f_rec_form.pack(padx=30, pady=10, fill="both", expand=True)

tk.Label(f_rec_form, text="DNI del Paciente:*", bg=COLORS["card"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
entry_rec_dni = ttk.Entry(f_rec_form, width=30)
entry_rec_dni.pack(anchor="w", pady=(2, 10))

tk.Label(f_rec_form, text="Médico Prescriptor:*", bg=COLORS["card"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
combo_rec_medico = ttk.Combobox(f_rec_form, values=nombres_medicos_inicial, state="readonly", width=28)
combo_rec_medico.pack(anchor="w", pady=(2, 10))
if nombres_medicos_inicial: combo_rec_medico.set(nombres_medicos_inicial[0])

tk.Label(f_rec_form, text="Diagnóstico / Motivo:*", bg=COLORS["card"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
entry_rec_diag = ttk.Entry(f_rec_form, width=60)
entry_rec_diag.pack(anchor="w", pady=(2, 10))

tk.Label(f_rec_form, text="Indicaciones / Medicamentos / Estudios Solicitados:*", bg=COLORS["card"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
text_rec_indicacion = scrolledtext.ScrolledText(f_rec_form, height=8, font=("Segoe UI", 10), wrap="word")
text_rec_indicacion.pack(fill="x", pady=(2, 15))

crear_boton(card_rec, "📄 Generar Receta PDF", generar_receta_medica, COLORS["success"], width=25, pady=10).pack(pady=(0, 20))

# ==================== PESTAÑA 5: PACIENTES ====================
tab_pacientes = tk.Frame(notebook, bg=COLORS["background"])
notebook.add(tab_pacientes, text="👥 Historias Clínicas")

container_pac = tk.Frame(tab_pacientes, bg=COLORS["background"])
container_pac.pack(fill="both", expand=True, padx=5, pady=5)

panel_pac_izq = tk.Frame(container_pac, bg=COLORS["background"], width=570)
panel_pac_izq.pack(side="left", fill="both", padx=(0, 5))
panel_pac_izq.pack_propagate(False)

form_pac_card = tk.Frame(panel_pac_izq, bg=COLORS["card"], relief="flat")
form_pac_card.config(highlightbackground=COLORS["border"], highlightthickness=1)
form_pac_card.pack(fill="both", expand=True, padx=5, pady=5)

canvas_form = tk.Canvas(form_pac_card, bg=COLORS["card"], highlightthickness=0)
scrollbar_form = ttk.Scrollbar(form_pac_card, orient="vertical", command=canvas_form.yview)
scrollable_form = tk.Frame(canvas_form, bg=COLORS["card"])

scrollable_form.bind("<Configure>", lambda e: canvas_form.configure(scrollregion=canvas_form.bbox("all")))
canvas_form.create_window((0, 0), window=scrollable_form, anchor="nw")
canvas_form.configure(yscrollcommand=scrollbar_form.set)

def on_mousewheel(event):
    canvas_form.yview_scroll(int(-1*(event.delta/120)), "units")

scrollable_form.bind('<Enter>', lambda e: canvas_form.bind_all("<MouseWheel>", on_mousewheel))
scrollable_form.bind('<Leave>', lambda e: canvas_form.unbind_all("<MouseWheel>"))

tk.Label(scrollable_form, text="Registro de Paciente", font=("Segoe UI", 12, "bold"),
         bg=COLORS["card"], fg=COLORS["text"]).pack(pady=(15, 10))

tk.Label(scrollable_form, text="📋 Datos Personales", font=("Segoe UI", 10, "bold"),
         bg=COLORS["card"], fg=COLORS["primary"]).pack(anchor="w", padx=20, pady=(10, 5))

def crear_campo_paciente(parent, label_text, ancho=30):
    frame = tk.Frame(parent, bg=COLORS["card"])
    frame.pack(fill="x", padx=20, pady=3)
    
    tk.Label(frame, text=label_text, bg=COLORS["card"], fg=COLORS["text"], 
             font=("Segoe UI", 9), width=15, anchor="w").pack(side="left")
    
    entry = ttk.Entry(frame, width=ancho, font=("Segoe UI", 9))
    entry.pack(side="left", fill="x", expand=True)
    
    return entry

entry_pac_nombre = crear_campo_paciente(scrollable_form, "Nombre completo:*")
entry_pac_dni = crear_campo_paciente(scrollable_form, "DNI:*")
entry_pac_fnac = crear_campo_paciente(scrollable_form, "Fecha Nac.:")
entry_pac_tel = crear_campo_paciente(scrollable_form, "Teléfono:")
entry_pac_email = crear_campo_paciente(scrollable_form, "Email:")
entry_pac_dir = crear_campo_paciente(scrollable_form, "Dirección:")

tk.Label(scrollable_form, text="🏥 Cobertura Médica", font=("Segoe UI", 10, "bold"),
         bg=COLORS["card"], fg=COLORS["primary"]).pack(anchor="w", padx=20, pady=(15, 5))

entry_pac_os = crear_campo_paciente(scrollable_form, "Obra Social:")
entry_pac_afiliado = crear_campo_paciente(scrollable_form, "Nº Afiliado:")

frame_gs = tk.Frame(scrollable_form, bg=COLORS["card"])
frame_gs.pack(fill="x", padx=20, pady=3)
tk.Label(frame_gs, text="Grupo Sanguíneo:", bg=COLORS["card"], fg=COLORS["text"], 
         font=("Segoe UI", 9), width=15, anchor="w").pack(side="left")
combo_grupo_sang = ttk.Combobox(frame_gs, values=["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"], 
                                 state="readonly", width=28, font=("Segoe UI", 9))
combo_grupo_sang.pack(side="left", fill="x", expand=True)

def silenciar_scroll_combo(event):
    canvas_form.yview_scroll(int(-1*(event.delta/120)), "units")
    return "break"

combo_grupo_sang.bind("<MouseWheel>", silenciar_scroll_combo)

tk.Label(scrollable_form, text="⚕️ Información Clínica", font=("Segoe UI", 10, "bold"),
         bg=COLORS["card"], fg=COLORS["primary"]).pack(anchor="w", padx=20, pady=(15, 5))

def crear_campo_texto(parent, label_text):
    tk.Label(parent, text=label_text, bg=COLORS["card"], fg=COLORS["text"], 
             font=("Segoe UI", 9), anchor="w").pack(anchor="w", padx=20, pady=(5, 2))
    text = scrolledtext.ScrolledText(parent, height=3, font=("Segoe UI", 9), wrap="word")
    text.pack(fill="x", padx=20, pady=(0, 5))
    return text

text_alergias = crear_campo_texto(scrollable_form, "Alergias:")
text_enfermedades = crear_campo_texto(scrollable_form, "Enfermedades Crónicas:")
text_medicacion = crear_campo_texto(scrollable_form, "Medicación Actual:")
text_observaciones = crear_campo_texto(scrollable_form, "Observaciones Generales:")

frame_btns_form = tk.Frame(scrollable_form, bg=COLORS["card"])
frame_btns_form.pack(fill="x", padx=20, pady=15)

tk.Button(frame_btns_form, text="💾 Guardar Paciente", command=guardar_paciente,
         bg=COLORS["success"], fg="white", font=("Segoe UI", 10, "bold"),
         relief="flat", cursor="hand2", bd=0, pady=10).pack(fill="x", pady=(0, 5))

tk.Button(frame_btns_form, text="🔄 Limpiar Formulario", command=limpiar_formulario_paciente,
         bg=COLORS["text_light"], fg="white", font=("Segoe UI", 9, "bold"),
         relief="flat", cursor="hand2", bd=0, pady=8).pack(fill="x")

canvas_form.pack(side="left", fill="both", expand=True)
scrollbar_form.pack(side="right", fill="y")

panel_pac_der = tk.Frame(container_pac, bg=COLORS["background"])
panel_pac_der.pack(side="right", fill="both", expand=True, padx=(5, 0))

frame_stats_pac = tk.Frame(panel_pac_der, bg=COLORS["background"])
frame_stats_pac.pack(fill="x", pady=(0, 10))

busqueda_card = tk.Frame(panel_pac_der, bg=COLORS["card"], relief="flat")
busqueda_card.config(highlightbackground=COLORS["border"], highlightthickness=1)
busqueda_card.pack(fill="x", pady=(0, 10))

frame_busq = tk.Frame(busqueda_card, bg=COLORS["card"])
frame_busq.pack(fill="x", padx=15, pady=10)

tk.Label(frame_busq, text="🔍", font=("Segoe UI", 14), bg=COLORS["card"]).pack(side="left", padx=(0, 10))
entry_buscar_pac = ttk.Entry(frame_busq, font=("Segoe UI", 10))
entry_buscar_pac.pack(side="left", fill="x", expand=True, padx=(0, 10))
tk.Button(frame_busq, text="Buscar", command=buscar_paciente,
         bg=COLORS["accent"], fg="white", font=("Segoe UI", 9, "bold"),
         relief="flat", cursor="hand2", bd=0, padx=15, pady=5).pack(side="left")

tabla_pac_card = tk.Frame(panel_pac_der, bg=COLORS["card"], relief="flat")
tabla_pac_card.config(highlightbackground=COLORS["border"], highlightthickness=1)
tabla_pac_card.pack(fill="both", expand=True)

tk.Label(tabla_pac_card, text="Pacientes Registrados", font=("Segoe UI", 11, "bold"),
         bg=COLORS["card"], fg=COLORS["text"]).pack(pady=(10, 5))

frame_btns_pac = tk.Frame(tabla_pac_card, bg=COLORS["card"])
frame_btns_pac.pack(side="bottom", fill="x", pady=15) 

container_botones = tk.Frame(frame_btns_pac, bg=COLORS["card"])
container_botones.pack()

crear_boton(container_botones, "📋 Ver Historia", ver_historia_clinica, COLORS["primary"]).pack(side="left", padx=5)
crear_boton(container_botones, "✏️ Editar", editar_paciente, COLORS["warning"]).pack(side="left", padx=5)
crear_boton(container_botones, "🗑️ Eliminar", eliminar_paciente, COLORS["danger"]).pack(side="left", padx=5)

frame_tabla_pac = tk.Frame(tabla_pac_card, bg=COLORS["card"])
frame_tabla_pac.pack(side="top", fill="both", expand=True, padx=10, pady=(0, 10))

columnas_pac = ("dni", "nombre", "fecha_nac", "telefono", "obra_social", "grupo_sang")
tabla_pacientes = ttk.Treeview(frame_tabla_pac, columns=columnas_pac, show="headings", height=12)

scrollbar_pac = ttk.Scrollbar(frame_tabla_pac, orient="vertical", command=tabla_pacientes.yview)
tabla_pacientes.configure(yscrollcommand=scrollbar_pac.set)

encabezados_pac = ["DNI", "Nombre", "F. Nacimiento", "Teléfono", "Obra Social", "Grupo Sang."]
for col, enc in zip(columnas_pac, encabezados_pac):
    tabla_pacientes.heading(col, text=enc)
    ancho = 110 if col == "nombre" else 90
    tabla_pacientes.column(col, anchor="center", width=ancho)

tabla_pacientes.pack(side="left", fill="both", expand=True)
scrollbar_pac.pack(side="right", fill="y")

# INICIALIZACIÓN DE DATOS Y TABLAS
actualizar_tabla_turnos()
actualizar_estadisticas()
actualizar_tabla_pacientes()
actualizar_stats_pacientes()
actualizar_tabla_sala_espera()
actualizar_tabla_lista_espera()

# 4. LÓGICA DE CIERRE SEGURO
def cerrar_todo_seguro():
    try:
        database.crear_backup_db()
        ventana.destroy()
    except Exception:
        pass 

# 5. PANTALLA DE CARGA Y ARRANQUE FINAL
def iniciar_programa():
    splash = tk.Toplevel()
    splash.title("Cargando MEDIDOC 2.0...")
    
    COLOR_FONDO = "#1E293B" 
    COLOR_LETRA = "#F8FAFC" 
    
    splash.overrideredirect(True) 
    
    ancho, alto = 520, 320
    x = (splash.winfo_screenwidth() // 2) - (ancho // 2)
    y = (splash.winfo_screenheight() // 2) - (alto // 2)
    splash.geometry(f"{ancho}x{alto}+{x}+{y}")
    splash.config(bg=COLOR_FONDO)
    
    tk.Label(splash, text="MEDIDOC 2.0", font=("Segoe UI", 42, "bold"), 
             bg=COLOR_FONDO, fg=COLOR_LETRA).pack(expand=True, pady=(40, 0))
    
    tk.Label(splash, text="Gestión Médica Inteligente de Vanguardia", font=("Segoe UI", 12), 
             bg=COLOR_FONDO, fg="#94A3B8").pack()
    
    tk.Label(splash, text="By NanoDevs", font=("Segoe UI", 10, "italic"), 
             bg=COLOR_FONDO, fg="#38BDF8").pack(side="bottom", pady=20)
    
    barra_bg = tk.Frame(splash, bg="#334155", height=8)
    barra_bg.pack(side="bottom", fill="x")
    barra_fg = tk.Frame(barra_bg, bg="#38BDF8", height=8, width=0)
    barra_fg.pack(side="left")
    
    def animar(progreso=0):
        if progreso <= 520:
            barra_fg.config(width=progreso)
            splash.after(18, lambda: animar(progreso + 6)) 
        else:
            splash.destroy() 
            mostrar_login_protegido() 

    animar()

iniciar_programa() 
ventana.mainloop()