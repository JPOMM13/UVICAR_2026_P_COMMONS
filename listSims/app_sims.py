import os
from flask import Flask, jsonify
import requests
import re
import json
import time
import threading
from datetime import datetime, timedelta

app = Flask(__name__)

# Configuración mediante variables de entorno
LOGIN_URL = os.getenv('SMARTM2M_LOGIN_URL', 'https://smartm2m.com.pe/proca.php')
BASE_SIMS_URL = os.getenv('SMARTM2M_SIMS_URL', 'https://smartm2m.com.pe/Sims')
USER = os.getenv('SMARTM2M_USER', 'uvicarop@uvicar.com.pe')
PASS = os.getenv('SMARTM2M_PASS', 'uvicar2024')
CACHE_FILE = os.getenv('CACHE_PATH', os.path.join(os.path.dirname(__file__), 'sims_cache.json'))

# Variable global para mantener los datos en memoria
sims_data_cache = {
    "last_updated": None,
    "last_status": "Desconocido",
    "data": [],
    "count": 0
}

def get_sims_from_web():
    """Realiza la extracción completa paginada desde la web de SmartM2M."""
    global sims_data_cache
    if not USER or not PASS:
        error_msg = "ERROR: Credenciales SMARTM2M_USER o SMARTM2M_PASS no configuradas."
        print(f"[{datetime.now()}] {error_msg}")
        sims_data_cache["last_status"] = error_msg
        return None

    session = requests.Session()
    login_data = {'user': USER, 'pass': PASS, 'pro': 'login'}
    
    try:
        print(f"[{datetime.now()}] Iniciando actualización de SIMs desde SmartM2M...")
        response = session.post(LOGIN_URL, data=login_data, timeout=15)
        response.raise_for_status()
        
        all_full_data = []
        page = 1
        
        while True:
            url = f"{BASE_SIMS_URL}?limite=100&pagina={page}"
            sims_response = session.get(url, timeout=20)
            sims_response.raise_for_status()
            
            # Intentar capturar el JSON inyectado en el script (const initialData)
            match = re.search(r'const initialData\s*=\s*(\[.*?\]);', sims_response.text, re.DOTALL)
            if not match:
                # Reintento con formato 'var datos =' por si cambia la plataforma
                match = re.search(r'var datos\s*=\s*(\[.*?\]);', sims_response.text, re.DOTALL)
            
            if not match:
                print(f"[{datetime.now()}] Advertencia: No se encontró JSON en la página {page}.")
                break
            
            try:
                page_data = json.loads(match.group(1))
            except json.JSONDecodeError:
                print(f"[{datetime.now()}] Error decodificando JSON en la página {page}.")
                break
                
            if not page_data: 
                break
            
            all_full_data.extend(page_data)
            
            # Si recibimos menos del límite, es probable que sea la última página
            if len(page_data) < 50: 
                break
            
            page += 1
            time.sleep(0.3) # Respetar el servidor
            if page > 50: # Límite de seguridad
                break
        
        if not all_full_data:
            sims_data_cache["last_status"] = "Error: No se obtuvieron datos de la web."
            return None

        # Campos que queremos conservar para la API
        fields = [
            "id", "icc", "msisdn", "imei", "apn", "ip", 
            "simModel", "plan_comercial", "nombre_cliente", 
            "Estado_gprs", "lifeCycleStatus", "activationDate", 
            "Ultima_conexion", "Ultima_desconexion", 
            "ConsumptionMonthly_data_str", "traduccion_operator"
        ]
        
        filtered_data = []
        for s in all_full_data:
            item = {f: s.get(f) for f in fields}
            item["platform"] = "SmartM2M" # Identificador de origen
            filtered_data.append(item)
        
        result = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_status": "Exitoso",
            "data": filtered_data,
            "count": len(filtered_data)
        }
        
        # Guardar en caché local
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(result, f, indent=2)
        except Exception as e:
            print(f"Advertencia: No se pudo escribir en el archivo de caché: {e}")
            
        sims_data_cache = result
        print(f"[{datetime.now()}] Actualización completada: {len(filtered_data)} SIMs procesados.")
        return result

    except Exception as e:
        error_msg = f"Error en la actualización: {str(e)}"
        print(f"[{datetime.now()}] {error_msg}")
        sims_data_cache["last_status"] = error_msg
        return None

def load_cache():
    """Carga los datos desde el archivo local si existe."""
    global sims_data_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                saved_data = json.load(f)
                # Validar estructura básica
                if "data" in saved_data:
                    sims_data_cache = saved_data
                    print(f"Caché cargada: {len(sims_data_cache.get('data', []))} SIMs (de {sims_data_cache.get('last_updated', 'ayer')}).")
        except Exception as e:
            print(f"Error cargando caché: {e}")

def background_scheduler():
    """Hilo que actualiza los datos periódicamente (cada 24 horas)."""
    while True:
        needs_update = False
        # Si no hay datos previos o el último intento falló, se necesita actualizar/insistir
        if not sims_data_cache.get("last_updated") or sims_data_cache.get("last_status") != "Exitoso":
            needs_update = True
        else:
            try:
                last_time = datetime.strptime(sims_data_cache["last_updated"], "%Y-%m-%d %H:%M:%S")
                # Si han pasado más de 24 horas desde la última actualización exitosa
                if datetime.now() - last_time > timedelta(hours=24):
                    needs_update = True
            except:
                needs_update = True
        
        if needs_update:
            print(f"[{datetime.now()}] Iniciando intento de actualización automática...")
            result = get_sims_from_web()
            if result:
                print(f"[{datetime.now()}] Actualización automática exitosa. Próxima revisión en 1 hora.")
                time.sleep(3600)
            else:
                # Si falla, insistir más rápido (cada 10 minutos) hasta tener éxito
                print(f"[{datetime.now()}] Actualización automática fallida. Reintentando en 10 minutos...")
                time.sleep(600) 
        else:
            # Si todo está al día, esperar una hora antes de volver a verificar el reloj
            time.sleep(3600) 

@app.route('/api/sims', methods=['GET'])
def list_sims():
    if not sims_data_cache.get("data"):
        load_cache()
        if not sims_data_cache.get("data"):
            return jsonify({
                "error": "Datos no disponibles.",
                "status": sims_data_cache.get("last_status", "Caché vacía")
            }), 503
            
    return jsonify({
        "count": len(sims_data_cache["data"]),
        "last_updated": sims_data_cache["last_updated"],
        "status": sims_data_cache["last_status"],
        "sims": sims_data_cache["data"]
    })

@app.route('/api/sims/refresh', methods=['POST', 'GET'])
def refresh_sims():
    # Ejecutar en segundo plano para no bloquear la respuesta HTTP
    thread = threading.Thread(target=get_sims_from_web)
    thread.start()
    return jsonify({
        "message": "Actualización forzada iniciada.",
        "status": "Iniciando..."
    })

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "last_updated": sims_data_cache.get("last_updated"),
        "last_status": sims_data_cache.get("last_status"),
        "count": sims_data_cache.get("count", 0),
        "cache_file_exists": os.path.exists(CACHE_FILE)
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "uptime": "running"})

if __name__ == '__main__':
    load_cache()
    
    # Iniciar el scheduler
    updater_thread = threading.Thread(target=background_scheduler, daemon=True)
    updater_thread.start()
    
    # Si no hay datos, intentar primera carga inmediata en hilo aparte
    if not sims_data_cache.get("data"):
        threading.Thread(target=get_sims_from_web).start()
        
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port)
