import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageCms
import cv2
import io
import time
import shutil
from zipfile import ZipFile
from werkzeug.utils import secure_filename

# Motor facial estático en memoria
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def abrir_plantilla(ruta):
    img = Image.open(ruta)
    if img.mode == 'CMYK' and 'icc_profile' in img.info:
        try:
            f = io.BytesIO(img.info.get('icc_profile'))
            src_profile = ImageCms.ImageCmsProfile(f)
            dst_profile = ImageCms.createProfile('sRGB')
            return ImageCms.profileToProfile(img, src_profile, dst_profile, outputMode='RGB')
        except: pass
    if img.mode == 'RGBA':
        bg = Image.new('RGB', img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        return bg
    return img.convert('RGB')

def preparar_imagen(ruta, tamano, es_foto=True):
    try:
        if not os.path.exists(ruta): return None
        img_pil = Image.open(ruta).convert("RGBA")
        
        if es_foto:
            img_cv = cv2.imread(ruta)
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            if len(faces) > 0:
                x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                mx, my = int(w * 0.6), int(h * 0.8)
                img_pil = img_pil.crop((max(0, x-mx), max(0, y-my), min(img_pil.width, x+w+mx), min(img_pil.height, y+h+my)))
            
            img_res = ImageOps.fit(ImageOps.autocontrast(img_pil.convert("RGB")), tamano, Image.Resampling.LANCZOS).convert("RGBA")
            mask = Image.new('L', img_res.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, img_res.width, img_res.height), radius=50, fill=255)
            img_res.putalpha(mask)
            return img_res
        else:
            return ImageOps.fit(img_pil, tamano, Image.Resampling.LANCZOS)
    except:
        return None

def escribir_centrado(draw, texto, y_pos, fuente, color=(0,0,0), espaciado=15, ancho_p=3060):
    txt_str = str(texto).upper()
    if not txt_str or txt_str == 'NAN': return
    
    try:
        char_widths = [draw.textlength(c, font=fuente) for c in txt_str]
    except AttributeError:
        char_widths = [draw.textbbox((0, 0), c, font=fuente)[2] - draw.textbbox((0, 0), c, font=fuente)[0] for c in txt_str]
        
    w_txt = sum(char_widths) + (espaciado * (len(txt_str) - 1))
    x_actual = (ancho_p - w_txt) / 2
    
    for c, w in zip(txt_str, char_widths):
        draw.text((x_actual, y_pos), c, font=fuente, fill=color)
        x_actual += w + espaciado

def procesar_lote(folders_dict, tipo_personal='militar'):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fuente_bold = os.path.join(base_dir, "bold.ttf")
    fuente_reg = os.path.join(base_dir, "regular.ttf")
    
    excel_key = f'excel_{tipo_personal}'
    archivos_excel = [f for f in os.listdir(folders_dict[excel_key]) if f.endswith(('.xls', '.xlsx'))]
    if not archivos_excel: raise Exception(f"Base de datos {tipo_personal.upper()} no encontrada. Por favor sube el archivo Excel correspondiente al área designada.")
    df = pd.read_excel(os.path.join(folders_dict[excel_key], archivos_excel[0]))
    
    ruta_plantilla = os.path.join(folders_dict['plantillas'], "template_final.tif")
    if not os.path.exists(ruta_plantilla): raise Exception("Falta subir template_final.tif en la sección de plantillas.")
    
    is_militar = (tipo_personal == 'militar')
    
    if is_militar and 'Rango' not in df.columns:
        raise Exception("Has seleccionado personal MILITAR, pero el Excel subido NO contiene la columna 'Rango'. Por favor verifica la base de datos.")
    
    # Coordenadas Generales
    X_FOTO, Y_FOTO = (1075, 1689)
    W_FOTO, H_FOTO = (930, 1083)
    POS_CODIGO = (2280, 4080)
    
    try:
        f_nombre = ImageFont.truetype(fuente_bold, 210)
        f_dpto   = ImageFont.truetype(fuente_bold, 280) 
        f_cargo  = ImageFont.truetype(fuente_bold, 145)
        f_mini   = ImageFont.truetype(fuente_bold, 110)
        
        if is_militar:
            f_rango   = ImageFont.truetype(fuente_bold, 120)
            f_cedula  = ImageFont.truetype(fuente_bold, 130)
        else:
            f_cedula = ImageFont.truetype(fuente_reg, 130)
            f_datos  = ImageFont.truetype(fuente_bold, 150)
    except Exception as e:
        raise Exception(f"Faltan las tipografías bold.ttf y regular.ttf en la base del servidor. {e}")

    out_dir = os.path.join(folders_dict['temp'], "generados")
    os.makedirs(out_dir, exist_ok=True)
    
    for _, fila in df.iterrows():
        carnet = abrir_plantilla(ruta_plantilla)
        draw = ImageDraw.Draw(carnet)
        ancho_p = carnet.size[0]
        
        foto_filename = secure_filename(str(fila['Foto']))
        foto_path = os.path.join(folders_dict['fotos'], foto_filename)
        foto_img = preparar_imagen(foto_path, (W_FOTO, H_FOTO), es_foto=True)
        if foto_img:
            carnet.paste(foto_img, (X_FOTO, Y_FOTO), foto_img)
            
        if is_militar:
            rango_val = str(fila['Rango']).strip().upper()
            insig_filename = secure_filename(f"{rango_val}.png")
            ruta_insig = os.path.join(folders_dict['insignias'], insig_filename)
            insig_img = preparar_imagen(ruta_insig, (1200, 600), es_foto=False)
            if insig_img: 
                carnet.paste(insig_img, (int((ancho_p - 1200)/2), 2725), insig_img)
                
            escribir_centrado(draw, fila['Rango'], 3280, f_rango, espaciado=20)
            escribir_centrado(draw, fila['Nombre'], 3450, f_nombre, espaciado=5)
            
            ced_str = f"CI: {int(fila['Cedula']):,}".replace(',', '.')
            escribir_centrado(draw, ced_str, 3740, f_cedula, (50,50,50), espaciado=20)
            escribir_centrado(draw, fila['Cargo'], 3940, f_cargo, (50,50,50), espaciado=15)
            escribir_centrado(draw, fila['Departamento'], 4325, f_dpto, (30,30,30), espaciado=25)
            
            cod_str = "CODIGO: " + str(fila['Codigo']).zfill(5)
            xc, yc = POS_CODIGO
            for c in cod_str:
                draw.text((xc, yc), c, font=f_mini, fill=(0,0,0))
                xc += draw.textlength(c, font=f_mini) + 12
                
            out_name = f"{fila['Nombre']}.png".replace(" ", "_")
            carnet.save(os.path.join(out_dir, out_name))
            
        else: # Admin logic
            escribir_centrado(draw, fila['Nombre'], 3100, f_nombre, espaciado=5)
            try: ced_str = f"CI: {int(fila['Cedula']):,}".replace(',', '.')
            except: ced_str = "CI: " + str(fila['Cedula'])
                
            escribir_centrado(draw, ced_str, 3475, f_cedula, (50,50,50), espaciado=15)
            escribir_centrado(draw, fila['Cargo'], 3750, f_cargo, (50,50,50), espaciado=15)
            escribir_centrado(draw, fila['Departamento'], 4325, f_dpto, (30,30,30), espaciado=25)
            
            try: cod_form = f"CODIGO: {int(fila['Codigo']):05d}"
            except: cod_form = "CODIGO: "+ str(fila['Codigo']).zfill(5)
            
            xc, yc = POS_CODIGO
            char_w = [draw.textlength(c, font=f_mini) for c in cod_form]
            for c, w in zip(cod_form, char_w):
                draw.text((xc, yc), c, font=f_mini, fill=(0,0,0))
                xc += w + 10
                
            out_name = f"{str(fila['Nombre']).strip()}.png".replace("/", "-")
            carnet.save(os.path.join(out_dir, out_name))

            ruta_rev = os.path.join(folders_dict['plantillas'], "template_reverso.tif")
            if os.path.exists(ruta_rev):
                rev = abrir_plantilla(ruta_rev)
                draw_rev = ImageDraw.Draw(rev)
                
                v_raw = fila.get('Vence', '')
                v_str = v_raw.strftime('%Y-%m-%d') if pd.notna(v_raw) and isinstance(v_raw, pd.Timestamp) else str(v_raw).split()[0].strip()
                c_str = str(fila.get('Condicion', '')).strip()
                s_str = str(fila.get('Tipo de sangre', '')).strip()
                
                v_str = "" if v_str.lower() in ('nan', 'none', 'nat') else v_str
                c_str = "" if c_str.lower() in ('nan', 'none') else c_str
                s_str = "" if s_str.lower() in ('nan', 'none') else s_str
                
                draw_rev.text((1000, 2500), v_str, font=f_datos, fill=(0,0,0))
                draw_rev.text((1000, 2750), c_str, font=f_datos, fill=(0,0,0))
                draw_rev.text((1000, 3000), s_str, font=f_datos, fill=(0,0,0))
                
                out_rev = f"{str(fila['Nombre']).strip()}_REVERSO.png".replace("/", "-")
                rev.save(os.path.join(out_dir, out_rev))

    # Compress
    zip_filename = f"Lote_Carnets_{int(time.time())}.zip"
    zip_path = os.path.join(folders_dict['temp'], zip_filename)
    
    with ZipFile(zip_path, 'w') as zipf:
        for f in os.listdir(out_dir):
            zipf.write(os.path.join(out_dir, f), arcname=f)
            
    shutil.rmtree(out_dir)
    return zip_path
