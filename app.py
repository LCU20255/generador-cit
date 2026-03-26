import os
import shutil
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from zipfile import ZipFile
import time

# Inicializar app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'c1t_corp_2026_secur3'

# Configuración de carpetas absolutas
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024 # Max 500MB (para subidas masivas)

# Subcarpetas
FOLDERS = {
    'fotos': os.path.join(UPLOAD_FOLDER, 'fotos'),
    'insignias': os.path.join(UPLOAD_FOLDER, 'insignias'),
    'excel_militar': os.path.join(UPLOAD_FOLDER, 'archivos_excel_militar'),
    'excel_administrativo': os.path.join(UPLOAD_FOLDER, 'archivos_excel_admin'),
    'plantillas': os.path.join(UPLOAD_FOLDER, 'plantillas'),
    'temp': os.path.join(BASE_DIR, 'temp')
}

# Crear carpetas si no existen desde el inicio
for folder in FOLDERS.values():
    os.makedirs(folder, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload/<tipo>', methods=['POST'])
def upload_file(tipo):
    if tipo not in FOLDERS:
        return jsonify({'error': 'Tipo de archivo inválido'}), 400
        
    if 'file' not in request.files:
        return jsonify({'error': 'No se envió ningún archivo'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nombre de archivo vacío'}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(FOLDERS[tipo], filename)
    file.save(save_path)
    
    return jsonify({'success': True, 'filename': filename, 'tipo': tipo})

@app.route('/insignias', methods=['GET'])
def list_insignias():
    if not os.path.exists(FOLDERS['insignias']):
        return jsonify({'insignias': []})
    insignias = os.listdir(FOLDERS['insignias'])
    return jsonify({'insignias': insignias})

@app.route('/delete_insignia/<filename>', methods=['DELETE'])
def delete_insignia(filename):
    safe_name = secure_filename(filename)
    path = os.path.join(FOLDERS['insignias'], safe_name)
    if os.path.exists(path):
        try:
            os.remove(path)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Archivo no encontrado'}), 404

@app.route('/generate', methods=['POST'])
def generate_carnets():
    from core.motor_grafico import procesar_lote
    
    # Obtener el tipo de personal del front-end
    data = request.get_json() or {}
    tipo_personal = data.get('tipo_personal', 'militar')
    
    # 1. Limpiar carpeta temp antigua para evitar consumo de disco
    for file in os.listdir(FOLDERS['temp']):
        os.remove(os.path.join(FOLDERS['temp'], file))
        
    try:
        # 2. Compilar
        zip_path = procesar_lote(FOLDERS, tipo_personal)
        nombre_zip = os.path.basename(zip_path)
        
        # 3. Devolver
        return jsonify({
            'status': 'success',
            'filename': nombre_zip,
            'url': f'/download/{nombre_zip}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 200 # Devuelve 200 para que se atrape en el JSON client-side

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(FOLDERS['temp'], filename), as_attachment=True)

if __name__ == '__main__':
    # Usando waitress por defecto para Windows en entorno corporativo
    from waitress import serve
    print("Iniciando servidor Generador de Carnets en http://localhost:8080")
    serve(app, host='0.0.0.0', port=8080)
