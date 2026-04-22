import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import gspread
from datetime import datetime

# --- CONFIGURACION ---
BOT_TOKEN = "8632469715:AAGLQG3mDgL0tBpV61jnG6n2Ds89YIEx0zY"
DAVID_ADMIN_ID = 1391102818  # Tu ID de Telegram
SHEET_ID = "1muS4qETcWdyh0zvbhl3-sJ7uQIxwBNhUMHP109rF3dQ"

# Inicializar Bot y Google Sheets
bot = telebot.TeleBot(BOT_TOKEN)
try:
    gc = gspread.service_account(filename="credentials.json")
    worksheet = gc.open_by_key(SHEET_ID).sheet1
except Exception as e:
    print(f"Error conectando a Sheets: {e}")

# Base de datos de empleados
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
    # Opcional: Agregamos tu número aquí también por si quieres testear como empleado.
    # Asume que si nos pasaste el ID, la prueba está bien si lo forzamos.
}

# Memoria temporal del bot
user_sessions = {}
verified_users = {} # chat_id -> empleado_data
pending_approvals = {} # req_id -> data

def normalize_phone(phone_number):
    # Eliminar el + de los teléfonos de Telegram para que crucen con la BD
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
            # Si David prueba con su número personal y no está en la base de datos... vamos a dejarlo pasar para poder probar
            # ESTO ES SOLO PARA PRUEBAS:
            verified_users[chat_id] = {"legajo": "9999", "nombre": "David Modo Prueba"}
            bot.send_message(chat_id, "⚠️ Tu número no está en la BD, pero te dejo pasar modo prueba.\nBienvenido David Modo Prueba.")
            show_main_menu(chat_id)

def show_main_menu(chat_id):
    user_sessions[chat_id] = {} # reset state
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
        
    user_sessions[chat_id] = {"tipo": message.text}
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Hoy", "Ayer", "Cancelar")
    bot.send_message(chat_id, f"Seleccionaste **{message.text}**.\n¿A qué día corresponde?", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, process_date)

def process_date(message):
    chat_id = message.chat.id
    if message.text == "Cancelar":
        show_main_menu(chat_id)
        return
        
    user_sessions[chat_id]["fecha"] = message.text
    bot.send_message(chat_id, "¿Cuántas horas fueron? (Escribe el número, ej: 4, 3.5)", reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, process_hours)

def process_hours(message):
    chat_id = message.chat.id
    if message.text == "Cancelar":
        show_main_menu(chat_id)
        return
        
    horas = message.text
    session = user_sessions[chat_id]
    empleado = verified_users[chat_id]
    
    # Generar un ID unico de solicitud
    req_id = f"req_{int(datetime.now().timestamp())}_{chat_id}"
    
    data = {
        "legajo": empleado['legajo'],
        "nombre": empleado['nombre'],
        "tipo": session['tipo'],
        "fecha": session['fecha'],
        "horas": horas,
        "chat_id": chat_id
    }
    pending_approvals[req_id] = data
    
    # Avisar al usuario
    bot.send_message(chat_id, "⏳ Tu solicitud fue enviada a David para su aprobación. Te avisaremos cuando sea procesada.")
    
    # Enviar peticion a David
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("✅ APROBAR", callback_data=f"approve_{req_id}"),
        InlineKeyboardButton("❌ RECHAZAR", callback_data=f"reject_{req_id}")
    )
    
    msg_to_david = f"🔔 **NUEVA SOLICITUD**\n\n"
    msg_to_david += f"👤 Empleado: {data['nombre']} ({data['legajo']})\n"
    msg_to_david += f"📋 Novedad: {data['tipo']}\n"
    msg_to_david += f"📅 Día: {data['fecha']}\n"
    msg_to_david += f"⏱ Horas: {data['horas']}hs\n"
    
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
            data['horas']
        ]
        
        try:
            worksheet.append_row(fila)
            bot.edit_message_text(f"{call.message.text}\n\n✅ **¡APROBADO Y GUARDADO EN EXCEL!**", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            bot.send_message(data['chat_id'], f"✅ Buenas noticias {data['nombre']}, David acaba de **APROBAR** tu solicitud de {data['horas']} hs ({data['tipo']}).", parse_mode="Markdown")
        except Exception as e:
            bot.answer_callback_query(call.id, f"Error de Google Sheets: {e}")
            pending_approvals[req_id] = data # rollback
    else:
        bot.edit_message_text(f"{call.message.text}\n\n❌ **RECHAZADO.**", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        bot.send_message(data['chat_id'], f"❌ Hola {data['nombre']}, tu solicitud de {data['horas']} hs ({data['tipo']}) ha sido **RECHAZADA** en esta ocasión.", parse_mode="Markdown")

print("-----------------------------------------")
print("Bot Almacen Granix Inciado Exitosamente!")
print("Esperando mensajes de Telegram...")
print("-----------------------------------------")

bot.infinity_polling()
