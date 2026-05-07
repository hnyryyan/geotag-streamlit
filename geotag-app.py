# app.py
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import piexif
from datetime import datetime
import folium
from streamlit_folium import folium_static
import os
import tempfile
from pathlib import Path
import zipfile
import io
import pandas as pd
import numpy as np

# Set page config
st.set_page_config(page_title="Geotag Photo Editor", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
    }
    .main-header {
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header"><h1>📸 Geotag Photo Editor</h1><p>Tambahkan geotag dengan template kustom ke foto Anda</p></div>', unsafe_allow_html=True)

# Template definitions
def get_templates():
    return {
        "Modern": {
            "bg_color": "rgba(0,0,0,0.7)",
            "text_color": "white",
            "border_radius": 10,
            "padding": 10,
            "font_size": 24,
            "icon": "📍"
        },
        "Vintage": {
            "bg_color": "rgba(139,69,19,0.8)",
            "text_color": "#FFD700",
            "border_radius": 0,
            "padding": 15,
            "font_size": 22,
            "icon": "📜"
        },
        "Minimal": {
            "bg_color": "rgba(255,255,255,0.9)",
            "text_color": "black",
            "border_radius": 5,
            "padding": 8,
            "font_size": 20,
            "icon": "●"
        },
        "Neon": {
            "bg_color": "rgba(0,0,0,0.8)",
            "text_color": "#00ff00",
            "border_radius": 15,
            "padding": 12,
            "font_size": 26,
            "icon": "⚡"
        },
        "Elegant": {
            "bg_color": "rgba(255,255,255,0.95)",
            "text_color": "#8B4513",
            "border_radius": 20,
            "padding": 12,
            "font_size": 23,
            "icon": "✨"
        }
    }

def add_geotag_to_image(image_path, latitude, longitude, datetime_str, template_name, custom_text=""):
    """Add geotag text to image"""
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    
    templates = get_templates()
    template = templates.get(template_name, templates["Modern"])
    
    # Try to load font
    try:
        font = ImageFont.truetype("arial.ttf", template["font_size"])
    except:
        font = ImageFont.load_default()
    
    # Format geotag text
    if custom_text:
        geotag_text = f"{template['icon']} {custom_text}\n📍 {latitude}, {longitude}\n📅 {datetime_str}"
    else:
        geotag_text = f"{template['icon']} Location: {latitude}, {longitude}\n📅 {datetime_str}"
    
    # Calculate text size and position
    bbox = draw.multiline_textbbox((0, 0), geotag_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Position (bottom right corner with padding)
    padding = template["padding"]
    x = img.width - text_width - padding
    y = img.height - text_height - padding
    
    # Draw background
    if template["bg_color"] != "transparent":
        draw.rectangle(
            [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
            fill=template["bg_color"],
            radius=template["border_radius"]
        )
    
    # Draw text
    draw.multiline_text((x, y), geotag_text, fill=template["text_color"], font=font)
    
    # Add EXIF geotag data
    exif_dict = piexif.load(img.info.get('exif', b''))
    
    # Add GPS info
    gps_ifd = {}
    gps_ifd[piexif.GPSIFD.GPSLatitudeRef] = 'N' if latitude >= 0 else 'S'
    gps_ifd[piexif.GPSIFD.GPSLatitude] = convert_to_gps_coords(abs(latitude))
    gps_ifd[piexif.GPSIFD.GPSLongitudeRef] = 'E' if longitude >= 0 else 'W'
    gps_ifd[piexif.GPSIFD.GPSLongitude] = convert_to_gps_coords(abs(longitude))
    
    exif_dict['GPS'] = gps_ifd
    
    # Save image with EXIF
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG', exif=piexif.dump(exif_dict))
    img_bytes.seek(0)
    
    return img_bytes

def convert_to_gps_coords(coord):
    """Convert decimal coordinates to GPS format"""
    degrees = int(coord)
    minutes = int((coord - degrees) * 60)
    seconds = (coord - degrees - minutes/60) * 3600
    return ((degrees, 1), (minutes, 1), (int(seconds * 100), 100))

def create_map(latitude, longitude):
    """Create folium map centered on coordinates"""
    m = folium.Map(location=[latitude, longitude], zoom_start=13)
    folium.Marker(
        [latitude, longitude],
        popup='Selected Location',
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)
    return m

# Sidebar for inputs
with st.sidebar:
    st.header("⚙️ Pengaturan Geotag")
    
    # Coordinate input methods
    coord_method = st.radio(
        "Metode Input Koordinat",
        ["Manual Input", "Pilih pada Peta", "Upload File CSV"]
    )
    
    if coord_method == "Manual Input":
        latitude = st.number_input("Latitude", value=-6.200000, format="%.6f")
        longitude = st.number_input("Longitude", value=106.816666, format="%.6f")
        
    elif coord_method == "Pilih pada Peta":
        st.write("Klik pada peta untuk memilih lokasi")
        map_center = [-6.2, 106.8]
        m = folium.Map(location=map_center, zoom_start=12)
        m.add_child(folium.LatLngPopup())
        folium_static(m)
        
        # Manual override
        latitude = st.number_input("Atau masukkan latitude", value=-6.200000, format="%.6f")
        longitude = st.number_input("Atau masukkan longitude", value=106.816666, format="%.6f")
        
    else:  # Upload CSV
        csv_file = st.file_uploader("Upload CSV (columns: filename, latitude, longitude)", type=['csv'])
        if csv_file:
            df = pd.read_csv(csv_file)
            st.dataframe(df)
    
    # Time settings
    st.subheader("📅 Pengaturan Waktu")
    use_custom_time = st.checkbox("Gunakan waktu kustom")
    if use_custom_time:
        custom_datetime = st.datetime_input("Pilih waktu", datetime.now())
        datetime_str = custom_datetime.strftime("%Y-%m-%d %H:%M:%S")
    else:
        datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.info(f"Menggunakan waktu sekarang: {datetime_str}")
    
    # Template selection
    st.subheader("🎨 Template Geotag")
    template_name = st.selectbox("Pilih template", list(get_templates().keys()))
    
    # Custom text
    st.subheader("✏️ Teks Kustom")
    custom_text = st.text_area("Teks tambahan (opsional)", placeholder="Masukkan teks kustom...")
    
    # Preview template
    if st.checkbox("Preview template"):
        st.code(f"""
        Template: {template_name}
        Contoh tampilan:
        {get_templates()[template_name]['icon']} {custom_text if custom_text else 'Contoh Teks'}
        📍 {latitude}, {longitude}
        📅 {datetime_str}
        """)

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📸 Upload & Edit Foto")
    
    # Multiple file upload
    uploaded_files = st.file_uploader(
        "Pilih foto (multiple files allowed)",
        type=['jpg', 'jpeg', 'png'],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        st.write(f"📁 {len(uploaded_files)} file terupload")
        
        if st.button("🎨 Tambahkan Geotag ke Semua Foto", type="primary"):
            processed_images = []
            
            with st.spinner("Memproses foto..."):
                progress_bar = st.progress(0)
                
                for idx, uploaded_file in enumerate(uploaded_files):
                    # Save temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_path = tmp_file.name
                    
                    # Process image
                    processed_img = add_geotag_to_image(
                        tmp_path, latitude, longitude, datetime_str, 
                        template_name, custom_text
                    )
                    
                    processed_images.append((uploaded_file.name, processed_img))
                    
                    # Cleanup
                    os.unlink(tmp_path)
                    progress_bar.progress((idx + 1) / len(uploaded_files))
            
            # Display results
            st.success(f"✅ Berhasil memproses {len(processed_images)} foto!")
            
            # Create zip file for download
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for original_name, img_bytes in processed_images:
                    name, ext = os.path.splitext(original_name)
                    new_name = f"{name}_geotagged{ext}"
                    zip_file.writestr(new_name, img_bytes.getvalue())
            
            zip_buffer.seek(0)
            
            # Provide download
            st.download_button(
                label="📥 Download Semua Foto (ZIP)",
                data=zip_buffer,
                file_name="geotagged_photos.zip",
                mime="application/zip"
            )
            
            # Display individual images
            st.subheader("📷 Preview Foto yang Telah Diproses")
            cols = st.columns(3)
            for idx, (name, img_bytes) in enumerate(processed_images[:6]):  # Show max 6 previews
                with cols[idx % 3]:
                    st.image(img_bytes, caption=name, use_container_width=True)

with col2:
    st.subheader("🗺️ Preview Lokasi")
    
    if coord_method != "Pilih pada Peta" or 'latitude' in locals():
        try:
            map_display = create_map(latitude, longitude)
            folium_static(map_display, width=400, height=300)
            
            st.info(f"""
            **Informasi Lokasi:**
            - Latitude: {latitude:.6f}
            - Longitude: {longitude:.6f}
            - Waktu: {datetime_str}
            - Template: {template_name}
            """)
        except:
            st.warning("Masukkan koordinat yang valid")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray;">
    <p>Geotag Photo Editor v1.0 | Dengan template kustom dan dukungan multiple files</p>
</div>
""", unsafe_allow_html=True)