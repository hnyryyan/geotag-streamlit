# geotag-app.py
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import zipfile
from datetime import datetime
import folium
from streamlit_folium import folium_static
import requests
from io import BytesIO
import math

# Set page config
st.set_page_config(page_title="Geotag Photo Editor", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: bold;
        border-radius: 10px;
        padding: 0.75rem;
        border: none;
    }
    .main-header {
        text-align: center;
        padding: 1.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"><h1>📱 Geotag Photo Editor</h1><p>Template border 75% lebar foto | Teks lengkap</p></div>', unsafe_allow_html=True)

def get_static_map_image(latitude, longitude, width=140, height=140, zoom=16):
    """Menggunakan tile server OSM French"""
    import math
    
    lat_rad = math.radians(latitude)
    n = 2.0 ** zoom
    x_tile = int((longitude + 180.0) / 360.0 * n)
    y_tile = int((1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    
    url = f"https://c.tile.openstreetmap.fr/osmfr/{zoom}/{x_tile}/{y_tile}.png"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            map_img = Image.open(BytesIO(response.content))
            map_img = map_img.resize((width, height))
            
            # Tambah pin marker
            from PIL import ImageDraw
            draw = ImageDraw.Draw(map_img)
            cx, cy = width // 2, height // 2
            draw.polygon([(cx, cy - 10), (cx - 5, cy + 3), (cx, cy), (cx + 5, cy + 3)], 
                         fill=(255, 0, 0))
            draw.ellipse([cx - 4, cy - 14, cx + 4, cy - 6], fill=(255, 0, 0))
            
            return map_img
    except:
        pass
    
    return None

def create_fallback_map(latitude, longitude, width, height):
    """Custom fallback map if tile server fails"""
    try:
        map_img = Image.new('RGB', (width, height), color=(245, 245, 235))
        draw = ImageDraw.Draw(map_img)
        
        for i in range(4):
            y = 5 + i * (height // 4)
            draw.line([(5, y), (width - 5, y)], fill=(180, 180, 170), width=1)
            x = 5 + i * (width // 4)
            draw.line([(x, 5), (x, height - 5)], fill=(180, 180, 170), width=1)
        
        cx, cy = width // 2, height // 2
        draw.ellipse([cx - 4, cy + 2, cx + 4, cy + 8], fill=(100, 100, 100))
        draw.polygon([(cx, cy - 10), (cx - 5, cy + 3), (cx, cy), (cx + 5, cy + 3)], fill=(200, 60, 60))
        draw.ellipse([cx - 4, cy - 14, cx + 4, cy - 6], fill=(200, 60, 60))
        
        coord_text = f"{abs(latitude):.4f}°, {abs(longitude):.4f}°"
        try:
            font = ImageFont.truetype("arial.ttf", 10)
        except:
            font = ImageFont.load_default()
        draw.text((5, height - 14), coord_text, fill=(100, 100, 100), font=font)
        
        return map_img
    except:
        return None


def wrap_text(text, font, max_width, draw):
    """Wrap text automatically based on width"""
    if not text:
        return []
    
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_width = bbox[2] - bbox[0]
        
        if line_width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines if lines else [text]

def create_geotag_overlay(photo_width, photo_height, data):
    """Create geotag overlay - PERCENTAGE BASED (bukan fixed pixel)"""
    
    # ============ SEMUA UKURAN PAKAI PERSEN ============
    template_width = int(photo_width * 0.75)
    template_width = max(template_width, 280)
    
    border_margin = max(5, int(template_width * 0.015))
    
    header_font_size = max(18, int(template_width * 0.055))
    address_font_size = max(12, int(template_width * 0.028))
    label_font_size = max(14, int(template_width * 0.032))
    value_font_size = max(16, int(template_width * 0.038))
    
    map_size = max(80, int(template_width * 0.28))
    line_height = header_font_size + 8
    margin_x = max(8, int(template_width * 0.025))
    margin_y = max(8, int(template_width * 0.02))
    spacing = max(5, int(template_width * 0.015))
    
    # Load fonts
    font_paths = {
        'bold': ["arialbd.ttf", "arial.ttf", "C:\\Windows\\Fonts\\arialbd.ttf", 
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
        'regular': ["arial.ttf", "C:\\Windows\\Fonts\\arial.ttf", 
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    }
    
    font_header = None
    font_address = None
    font_label = None
    font_value = None
    
    for font_path in font_paths['bold']:
        try:
            font_header = ImageFont.truetype(font_path, header_font_size)
            font_value = ImageFont.truetype(font_path, value_font_size)
            break
        except:
            continue
    
    for font_path in font_paths['regular']:
        try:
            font_address = ImageFont.truetype(font_path, address_font_size)
            font_label = ImageFont.truetype(font_path, label_font_size)
            break
        except:
            continue
    
    if font_header is None:
        font_header = ImageFont.load_default()
        font_value = ImageFont.load_default()
    if font_address is None:
        font_address = ImageFont.load_default()
        font_label = ImageFont.load_default()
    
    temp_img = Image.new('RGBA', (template_width, 100), (0, 0, 0, 0))
    temp_draw = ImageDraw.Draw(temp_img)
    
    header_max_width = template_width - (margin_x * 2)
    location_name = data.get('location_name', 'Surabaya, Jawa Timur, Indonesia')
    header_lines = wrap_text(location_name, font_header, header_max_width, temp_draw)
    
    address_max_width = template_width - map_size - (margin_x * 2) - spacing
    address = data.get('address', 'Jl. Pantai Kenjeran, Sukolilo Baru, Kec. Bulak, Surabaya, Jawa Timur')
    address_lines = wrap_text(address, font_address, address_max_width, temp_draw)
    
    lat_text = data.get('latitude_text', '-7.213549.0° S')
    lon_text = data.get('longitude_text', '112.769214° E')
    date_text = data.get('date_text', 'Selasa, 07 Apr 2026')
    time_text = data.get('time_text', '14:30:25')
    
    header_height = margin_y + (len(header_lines) * line_height)
    map_height = map_size
    address_height = len(address_lines) * (address_font_size + spacing) if address_lines else 0
    coord_height = value_font_size * 2 + spacing * 2
    datetime_height = value_font_size + spacing
    
    content_height = max(map_height, address_height + coord_height + datetime_height)
    template_height = header_height + content_height + (margin_y * 2)
    
    overlay = Image.new('RGBA', (template_width, template_height), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    text_color = (255, 255, 255, 255)
    gray_color = (200, 200, 200, 255)
    
    border_width = max(2, int(template_width * 0.008))
    draw.rectangle([border_margin, border_margin, 
                    template_width - border_margin, template_height - border_margin], 
                   outline="white", width=border_width)
    
    # Header (wrapped)
    header_y = margin_y
    header_x = margin_x
    for line in header_lines:
        draw.text((header_x, header_y), line, font=font_header, fill=text_color)
        header_y += line_height
    
    header_bottom = header_y + spacing
    sep_y = header_bottom
    draw.line([(margin_x, sep_y), (template_width - margin_x, sep_y)], fill=text_color, width=1)
    header_bottom = sep_y + spacing
    
    # Map box
    map_box_x = margin_x
    map_box_y = header_bottom
    map_box_width = map_size
    map_box_height = map_size
    
    draw.rectangle([map_box_x, map_box_y, map_box_x + map_box_width, map_box_y + map_box_height], 
                   outline="white", width=1)
    
    map_img = data.get('map_image')
    if map_img:
        try:
            map_img_resized = map_img.resize((map_box_width - 2, map_box_height - 2))
            overlay.paste(map_img_resized, (map_box_x + 1, map_box_y + 1))
        except:
            draw.text((map_box_x + map_box_width//2 - 20, map_box_y + map_box_height//2 - 10), 
                     "🗺️", font=font_label, fill=gray_color)
    else:
        draw.rectangle([map_box_x + 2, map_box_y + 2, 
                        map_box_x + map_box_width - 2, map_box_y + map_box_height - 2], 
                       fill=(50, 50, 80, 150))
        draw.text((map_box_x + map_box_width//2 - 20, map_box_y + map_box_height//2 - 10), 
                 "📍", font=font_label, fill=gray_color)
    
    # Address (wrapped)
    address_x = map_box_x + map_box_width + spacing
    address_y = map_box_y
    for line in address_lines:
        draw.text((address_x, address_y), line, font=font_address, fill=text_color)
        address_y += address_font_size + spacing
    
    # Coordinates
    if address_lines:
        coord_y = address_y + spacing
    else:
        coord_y = map_box_y + map_box_height + spacing
    
    # Latitude
    label_width = value_font_size * 5
    draw.text((address_x, coord_y), "Latitude", font=font_value, fill=text_color)
    draw.text((address_x + label_width + spacing, coord_y), lat_text, font=font_label, fill=text_color)
    
    # Longitude
    coord_y_lon = coord_y + value_font_size + spacing
    draw.text((address_x, coord_y_lon), "Longitude", font=font_value, fill=text_color)
    draw.text((address_x + label_width + spacing, coord_y_lon), lon_text, font=font_label, fill=text_color)
    
    # Date & Time (sebaris dalam 1 baris)
    datetime_y = coord_y_lon + value_font_size + spacing
    datetime_text = f"📅 {date_text}  |  🕐 {time_text}"
    draw.text((address_x, datetime_y), datetime_text, font=font_value, fill=text_color)
    
    return overlay


def format_coordinate_dms(coord, is_latitude):
    """Format koordinat ke DMS (Degrees Minutes Seconds)"""
    if coord is None:
        return "0° 0' 0\""
    
    abs_coord = abs(coord)
    degrees = int(abs_coord)
    minutes = int((abs_coord - degrees) * 60)
    seconds = int(((abs_coord - degrees) * 60 - minutes) * 60)
    
    direction = ""
    if is_latitude:
        direction = "S" if coord < 0 else "N"
    else:
        direction = "E" if coord > 0 else "W"
    
    return f"{degrees}° {minutes}' {seconds}\" {direction}"

def add_geotag_to_image(image_bytes, data):
    """Add geotag overlay to image"""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        img_width, img_height = img.size
        
        overlay = create_geotag_overlay(img_width, img_height, data)
        overlay_width, overlay_height = overlay.size
        
        margin_bottom = 20
        x = (img_width - overlay_width) // 2
        y = img_height - overlay_height - margin_bottom
        x = max(5, x)
        
        img_rgba = img.convert('RGBA')
        result = Image.new('RGBA', img_rgba.size, (0, 0, 0, 0))
        result.paste(img_rgba, (0, 0))
        result.paste(overlay, (x, y), overlay)
        
        rgb_result = Image.new('RGB', result.size, (255, 255, 255))
        rgb_result.paste(result, mask=result.split()[3] if len(result.split()) > 3 else None)
        
        output = io.BytesIO()
        rgb_result.save(output, format='JPEG', quality=95)
        output.seek(0)
        
        return output
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

# Sidebar settings
with st.sidebar:
    st.header("⚙️ Pengaturan")
    
    st.subheader("📍 Lokasi")
    location_name = st.text_area("Nama Tempat", 
                                  value="Surabaya, Jawa Timur, Indonesia",
                                  height=68,
                                  help="Bisa panjang, akan auto wrap")
    
    address = st.text_area("Alamat Lengkap", 
                           value="Jl. Dukuh Bulak Banteng Suropati 7A No.5A, Bulak Banteng, Kec. Kenjeran 60127",
                           height=100,
                           help="Alamat panjang akan auto wrap")
    
    st.subheader("🗺️ Koordinat")
    col1, col2 = st.columns(2)
    with col1:
        latitude = st.number_input("Latitude", value=-7.213549, format="%.6f")
    with col2:
        longitude = st.number_input("Longitude", value=112.769214, format="%.6f")
    
    coord_format = st.radio("Format Koordinat", ["Decimal", "DMS"])
    
    if coord_format == "Decimal":
        lat_dir = "S" if latitude < 0 else "N"
        lon_dir = "E" if longitude > 0 else "W"
        latitude_text = f"{abs(latitude):.6f}° {lat_dir}"
        longitude_text = f"{abs(longitude):.6f}° {lon_dir}"
    else:
        latitude_text = format_coordinate_dms(latitude, True)
        longitude_text = format_coordinate_dms(longitude, False)
    
        st.subheader("📅 Tanggal & Waktu")
    
    with st.form(key="datetime_form"):
        col_tgl, col_wkt = st.columns(2)
        
        with col_tgl:
            selected_date = st.date_input("Tanggal", datetime.now())
        
        with col_wkt:
            selected_time = st.time_input("Waktu", datetime.now().time())
        
        submitted = st.form_submit_button("✅ Terapkan Tanggal & Waktu")
        
        if submitted or 'datetime_applied' not in st.session_state:
            day_name = selected_date.strftime("%A")
            day_ind = {"Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu",
                       "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu",
                       "Sunday": "Minggu"}.get(day_name, day_name)
            date_text = f"{day_ind}, {selected_date.day:02d} {selected_date.strftime('%b')} {selected_date.year}"
            time_text = selected_time.strftime("%H:%M:%S")
            st.session_state.date_text = date_text
            st.session_state.time_text = time_text
            st.session_state.datetime_applied = True
    
    # Ambil dari session state
    date_text = st.session_state.get('date_text', f"{day_ind}, {datetime.now().day:02d} {datetime.now().strftime('%b')} {datetime.now().year}")
    time_text = st.session_state.get('time_text', datetime.now().strftime("%H:%M:%S"))
    
    st.info(f"📅 {date_text} | 🕐 {time_text}")
    
    st.subheader("👁️ Preview")
    
    map_img = get_static_map_image(latitude, longitude, 140, 140, 16)
    
    preview_data = {
        'location_name': location_name,
        'address': address,
        'latitude_text': latitude_text,
        'longitude_text': longitude_text,
        'date_text': date_text,
        'time_text': time_text,
        'map_image': map_img,
        'latitude': latitude,
        'longitude': longitude
    }
    
    preview_overlay = create_geotag_overlay(800, 600, preview_data)
    st.image(preview_overlay, caption="Preview Template", use_container_width=True)
    st.caption(f"📐 Lebar border = {int(800 * 0.75)}px (75% dari lebar foto)")

# Main content
st.subheader("📸 Upload Foto")

uploaded_files = st.file_uploader(
    "Pilih foto (bisa banyak)",
    type=['jpg', 'jpeg', 'png'],
    accept_multiple_files=True
)

if uploaded_files:
    for f in uploaded_files[:2]:
        img = Image.open(io.BytesIO(f.getvalue()))
        border_width = int(img.size[0] * 0.75)
        st.caption(f"📷 {f.name}: {img.size[0]}x{img.size[1]}px → lebar border: {border_width}px (75% dari lebar foto)")
    
    if st.button("🎨 TAMBAHKAN GEOTAG", type="primary", use_container_width=True):
        processed_images = []
        
        map_img = get_static_map_image(latitude, longitude, 140, 140, 16)
        
        geotag_data = {
            'location_name': location_name,
            'address': address,
            'latitude_text': latitude_text,
            'longitude_text': longitude_text,
            'date_text': date_text,
            'time_text': time_text,
            'map_image': map_img,
            'latitude': latitude,
            'longitude': longitude
        }
        
        with st.spinner("Memproses..."):
            progress_bar = st.progress(0)
            for idx, uploaded_file in enumerate(uploaded_files):
                processed_img = add_geotag_to_image(uploaded_file.getvalue(), geotag_data)
                if processed_img:
                    processed_images.append((uploaded_file.name, processed_img))
                progress_bar.progress((idx + 1) / len(uploaded_files))
        
        if processed_images:
            st.success(f"✅ {len(processed_images)} foto selesai!")
            
            # ============ OPSI DOWNLOAD ============
            st.subheader("📥 Download Hasil")
            
            tab1, tab2 = st.tabs(["📦 Download ZIP", "📸 Download Semua JPG"])
            
            with tab1:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for original_name, img_bytes in processed_images:
                        name, ext = os.path.splitext(original_name)
                        zip_file.writestr(f"{name}_geotagged{ext}", img_bytes.getvalue())
                
                zip_buffer.seek(0)
                st.download_button(
                    label="📦 Download SEMUA dalam 1 file ZIP",
                    data=zip_buffer,
                    file_name=f"geotag_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip",
                    use_container_width=True
                )
                st.caption("✅ Cocok untuk download banyak foto sekaligus")
            
            with tab2:
                st.write("Klik tombol di bawah untuk download satu per satu:")
                
                col_left, col_right = st.columns(2)
                for idx, (original_name, img_bytes) in enumerate(processed_images):
                    with col_left if idx % 2 == 0 else col_right:
                        name, ext = os.path.splitext(original_name)
                        st.download_button(
                            label=f"⬇️ {name}_geotagged{ext}",
                            data=img_bytes,
                            file_name=f"{name}_geotagged{ext}",
                            mime="image/jpeg",
                            key=f"download_jpg_{idx}",
                            use_container_width=True
                        )
                st.caption("✅ Download file JPG satu per satu")
            
            # Tampilkan preview hasil
            st.subheader("📷 Preview Hasil")
            preview_cols = st.columns(2)
            for idx, (name, img_bytes) in enumerate(processed_images[:4]):
                with preview_cols[idx % 2]:
                    st.image(img_bytes, caption=name, use_container_width=True)

# Map reference
with st.expander("🗺️ Lihat Lokasi", expanded=False):
    m = folium.Map(location=[latitude, longitude], zoom_start=20)
    folium.Marker([latitude, longitude], popup=location_name,
                  icon=folium.Icon(color='red')).add_to(m)
    folium_static(m, width=700, height=400)

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray;">
    <p>✅ Lebar border = 75% lebar foto (proporsional) | ✅ Teks panjang auto wrap | ✅ Tanggal & waktu dalam 1 baris</p>
    <p>✅ Edit tanggal dan waktu langsung (tanpa checkbox)</p>
</div>
""", unsafe_allow_html=True)