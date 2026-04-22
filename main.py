import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import gspread
from datetime import datetime, timedelta

# --- CONFIGURACION ---
BOT_TOKEN = "8632469715:AAGLQG3mDgL0tBpV61jnG6n2Ds89YIEx0zY"
DAVID_ADMIN_ID = 1391102818  # Tu ID de Telegram
SHEET_ID = "1muS4qETcWdyh0zvbhl3-sJ7uQIxwBNhUMHP109rF3dQ"

bot = telebot.TeleBot(BOT_TOKEN)
worksheet = None

def get_worksheet():
    global worksheet
    if worksheet is None:
        gc = gspread.service_account(filename="credentials.json")
        worksheet = gc.open_by_key(SHEET_ID).sheet1
    return worksheet

EMPLEADOS = {
    "543489674990": {"legajo": "5210", "nombre": "Alcaraz Ronald"},
    "543484590105": {"legajo": "5218", "nombre": "Kalbermatter Claudio"},
    "541125759590": {"legajo": "5242", "nombre": "Leiva Luis"},
    "541165255117": {"legajo": "5274", "nombre": "Siri Lucas"},
    "541168568818": {"legajo": "5291", "nombre": "Amadeo Ricardo"},
    "541132133913": {"legajo": "5296", "nombre": "Hess Erick"},
    "541138605331": {"legajo": "5329", "nombre": "Filgueira Darwin"},
    "543329302671": {"legajo": "5398", "nombre": "Reinick Alejo"},
    "543743601005": {"legajo": "5404", "nombre": "Britez Joel"},
    "543489552250": {"legajo": "5407", "nombre": "Sanabria Braian"},
    "543487235615": {"legajo": "5418", "nombre": "Genta Francisco"},
}

user_sessions = {}
verified_users = {} 
pending_approvals = {} 

def normalize_phone(phone_number):
    return phone_number.replace("+", "")

@bot.message_handler(commands=['start'])
def start_message(message):
    chat_id = message.chat.id
    if chat_id == DAVID_ADMIN_ID:
        bot.send_message(chat_id, "👋 Hola David. Modo Admin Activo. Aquí recibirás las alertas para aprobar horas. (Pero también te mostraré el menú para que puedas probar la carga de horas).")

    if chat_id not in verified_users:
        markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        btn = KeyboardButton("📱 Compartir mi Contacto", request_contact=True)
        markup.add(btn)
        bot.send_message(chat_id, "Hola! Bienvenido al sistema de novedades de Almacén Granix.\n\nPor favor, presiona el botón de abajo para verificar tu identidad.", reply_markup=markup)
    else:
        show_main_menu(chat_id)

@bot.message_handler(content_types=['contact'])
def contact_handler(message):
    chat_id = message.chat.id
    if message.contact is not None:
        phone = normalize_phone(message.contact.phone_number)
        
        if phone in EMPLEADOS:
            empleado = EMPLEADOS[phone]
            verified_users[chat_id] = empleado
            bot.send_message(chat_id, f"✅ Identidad verificada.\nBienvenido, **{empleado['nombre']}** (Legajo: {empleado['legajo']}).", parse_mode="Markdown")
            show_main_menu(chat_id)
        else:
            verified_users[chat_id] = {"legajo": "9999", "nombre": "David Modo Prueba"}
            bot.send_message(chat_id, "⚠️ Tu número no está en la BD, pero te dejo pasar modo prueba.\nBienvenido David Modo Prueba.")
            show_main_menu(chat_id)

def show_main_menu(chat_id):
    user_sessions[chat_id] = {} 
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Horas Extras", "Cambio de Turno")
    markup.row("Reemplazo", "Cancelar")
    bot.send_message(chat_id, "¿Qué novedad necesitas reportar?", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ["Horas Extras", "Cambio de Turno", "Reemplazo"])
def handle_novedad_type(message):
    chat_id = message.chat.id
    if chat_id not in verified_users:
        bot.send_message(chat_id, "Por favor envía /start primero.")
        return
        
    tipo = message.text
    user_sessions[chat_id] = {"tipo": tipo}
    
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Hoy", "Ayer", "Cancelar")
    
    if tipo == "Cambio de Turno":
        bot.send_message(chat_id, "Seleccionaste **Cambio de Turno**.\n\nPara empezar, dime **la FECHA EXACTA** en la que te vas a ausentar / faltar. (Ej: 2026-04-12)", parse_mode="Markdown", reply_markup=markup)
        bot.register_next_step_handler(message, process_ct_date)
    else:
        bot.send_message(chat_id, f"Seleccionaste **{tipo}**.\n¿A qué día corresponde? (Si no es hoy o ayer, escríbelo. Ej: 2026-04-12)", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_date_he)

def process_ct_date(message):
    chat_id = message.chat.id
    if message.text == "Cancelar":
        show_main_menu(chat_id)
        return
        
    fecha_texto = message.text
    if fecha_texto == "Hoy":
        fecha_texto = datetime.now().strftime("%Y-%m-%d")
    elif fecha_texto == "Ayer":
        fecha_texto = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
    user_sessions[chat_id]["fecha_falta"] = fecha_texto
    bot.send_message(chat_id, "¿En qué **horario exacto** te vas a ausentar o cambiar turno ese día?\n(Ej: De 22:00 a 06:00)", reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, process_ct_horario)

def process_ct_horario(message):
    chat_id = message.chat.id
    if message.text == "Cancelar":
        show_main_menu(chat_id)
        return
        
    user_sessions[chat_id]["horario_falta"] = message.text
    # Mensaje de compensación múltiple libre
    bot.send_message(chat_id, "Excelente. Finalmente dime:\n\n¿Qué día (o días) y en qué horarios vas a **compensarlo/devolverlo**?\n(Escríbelo todo en un mensaje detallado. Ej: Mitad el sábado de 06 a 10 y mitad el lunes de 10 a 14)")
    bot.register_next_step_handler(message, process_ct_compensacion)

def process_ct_compensacion(message):
    chat_id = message.chat.id
    if message.text == "Cancelar":
        show_main_menu(chat_id)
        return
        
    user_sessions[chat_id]["detalles_compensacion"] = message.text
    finalize_request(chat_id)

def process_date_he(message):
    chat_id = message.chat.id
    if message.text == "Cancelar":
        show_main_menu(chat_id)
        return
        
    fecha_texto = message.text
    if fecha_texto == "Hoy":
        fecha_texto = datetime.now().strftime("%Y-%m-%d")
    elif fecha_texto == "Ayer":
        fecha_texto = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
    user_sessions[chat_id]["fecha_falta"] = fecha_texto
    bot.send_message(chat_id, "¿Cuántas horas fueron? (Escribe el número, ej: 4, 3.5)", reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, process_hours_he)

def process_hours_he(message):
    chat_id = message.chat.id
    if message.text == "Cancelar":
        show_main_menu(chat_id)
        return
        
    user_sessions[chat_id]["horas"] = message.text
    user_sessions[chat_id]["detalles_compensacion"] = "" # Vacío para horas extras
    finalize_request(chat_id)

def finalize_request(chat_id):
    session = user_sessions[chat_id]
    empleado = verified_users[chat_id]
    
    req_id = f"req_{int(datetime.now().timestamp())}_{chat_id}"
    
    # Manejar variables dependiendo si es HE o CT
    fecha_info = session.get("fecha_falta", "")
    # Para HE las horas estan en 'horas'. Para CT el texto del rango está en 'fecha_falta'. 
    # Mejor separemos en la vista
    if session['tipo'] == 'Cambio de Turno':
        desc_falta = session.get("fecha_falta", "")
        desc_comp = session.get("detalles_compensacion", "")
    else:
        desc_falta = f"{session.get('fecha_falta')} - {session.get('horas')}hs"
        desc_comp = ""
        
    # Standard data to save
    # "Timestamp", "Legajo", "Nombre", "Tipo Novedad", "Fecha Solicitud", "Horas/Horario Falta", "Detalles de Compensacion"
    
    data = {
        "legajo": empleado['legajo'],
        "nombre": empleado['nombre'],
        "tipo": session['tipo'],
        "fecha": session.get('fecha_falta'), 
        "horas_o_rango": session.get('horas') if session['tipo'] != 'Cambio de Turno' else session.get('horario_falta'),
        "detalles": desc_comp,
        "chat_id": chat_id
    }
    pending_approvals[req_id] = data
    
    bot.send_message(chat_id, "⏳ Tu solicitud fue enviada a David para su aprobación.")
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("✅ APROBAR", callback_data=f"approve_{req_id}"),
        InlineKeyboardButton("❌ RECHAZAR", callback_data=f"reject_{req_id}")
    )
    
    msg_to_david = f"🔔 **NUEVA SOLICITUD**\n\n"
    msg_to_david += f"👤 Empleado: {data['nombre']} ({data['legajo']})\n"
    msg_to_david += f"📋 Novedad: {data['tipo']}\n"
    if data['tipo'] == 'Cambio de Turno':
        msg_to_david += f"❌ Día/Hs Ausente: {data['horas_o_rango']}\n"
        msg_to_david += f"♻️ Detalle Compensación:\n{data['detalles']}\n"
    else:
        msg_to_david += f"📅 Día: {data['fecha']}\n"
        msg_to_david += f"⏱ Horas: {data['horas_o_rango']}\n"
        
    if DAVID_ADMIN_ID:
        try:
            bot.send_message(DAVID_ADMIN_ID, msg_to_david, reply_markup=keyboard, parse_mode="Markdown")
        except Exception as e:
            print("No se pudo enviar a admin:", e)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_') or call.data.startswith('reject_'))
def handle_approval(call):
    action, req_id = call.data.split('_', 1)
    if req_id not in pending_approvals:
        bot.answer_callback_query(call.id, "Esta solicitud ya fue procesada o expiró.")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        return
        
    data = pending_approvals.pop(req_id)
    if action == "approve":
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fila = [
            timestamp, 
            data['legajo'], 
            data['nombre'], 
            data['tipo'], 
            data['fecha'], 
            data['horas_o_rango'],
            data['detalles']
        ]
        
        try:
            ws = get_worksheet()
            ws.append_row(fila)
            bot.edit_message_text(f"{call.message.text}\n\n✅ **¡APROBADO Y GUARDADO EN EXCEL!**", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            
            notif = f"✅ David acaba de **APROBAR** tu solicitud de {data['tipo']}."
            bot.send_message(data['chat_id'], notif, parse_mode="Markdown")
        except Exception as e:
            bot.answer_callback_query(call.id, f"Error: {e}")
            pending_approvals[req_id] = data # rollback
    else:
        bot.edit_message_text(f"{call.message.text}\n\n❌ **RECHAZADO.**", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        bot.send_message(data['chat_id'], f"❌ Hola {data['nombre']}, tu solicitud ha sido **RECHAZADA** en esta ocasión.", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    chat_id = message.chat.id
    if chat_id not in verified_users:
        bot.send_message(chat_id, "Hola, envía /start para comenzar y verificar tu identidad.")
    else:
        # Si ya está verificado, le mostramos el menú principal de nuevo
        show_main_menu(chat_id)

print("-----------------------------------------")
print("Bot Almacen Granix Inciado Exitosamente con Compensación Múltiple!")
print("-----------------------------------------")
bot.infinity_polling()
