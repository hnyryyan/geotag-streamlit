# geotag-app.py
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import tempfile
import zipfile
from datetime import datetime
import folium
from streamlit_folium import folium_static
import pandas as pd
import numpy as np
import cv2
import base64
import piexif
import requests
import pip

# Set page config
st.set_page_config(page_title="Geotag Photo Editor", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    .main-header {
        text-align: center;
        padding: 1.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .info-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header"><h1>🗺️ Geotag Photo Editor Pro</h1><p>Tambahkan geotag kustom ke foto dengan berbagai template</p></div>', unsafe_allow_html=True)

# Template definitions
def get_templates():
    return {
        "Modern Dark": {
            "bg_color": (0, 0, 0, 180),
            "text_color": (255, 255, 255),
            "border_radius": 10,
            "padding": 15,
            "font_size": 24,
            "icon": "📍"
        },
        "Vintage Paper": {
            "bg_color": (210, 180, 140, 200),
            "text_color": (139, 69, 19),
            "border_radius": 5,
            "padding": 12,
            "font_size": 22,
            "icon": "📜"
        },
        "Neon Green": {
            "bg_color": (0, 0, 0, 200),
            "text_color": (0, 255, 0),
            "border_radius": 8,
            "padding": 10,
            "font_size": 26,
            "icon": "⚡"
        },
        "Elegant Gold": {
            "bg_color": (255, 255, 255, 230),
            "text_color": (184, 134, 11),
            "border_radius": 15,
            "padding": 12,
            "font_size": 23,
            "icon": "✨"
        },
        "Beach Style": {
            "bg_color": (135, 206, 235, 200),
            "text_color": (25, 25, 112),
            "border_radius": 20,
            "padding": 12,
            "font_size": 22,
            "icon": "🏖️"
        },
        "Cyberpunk": {
            "bg_color": (25, 25, 112, 220),
            "text_color": (255, 0, 255),
            "border_radius": 3,
            "padding": 10,
            "font_size": 25,
            "icon": "🦾"
        }
    }

def add_geotag_to_image(image_bytes, latitude, longitude, datetime_str, template_name, custom_text=""):
    """Add geotag text to image without piexif"""
    # Convert bytes to PIL Image
    img = Image.open(io.BytesIO(image_bytes))
    
    # Convert to RGB if needed
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    draw = ImageDraw.Draw(img)
    
    templates = get_templates()
    template = templates.get(template_name, templates["Modern Dark"])
    
    # Try to load font with multiple fallbacks
    font = None
    font_paths = [
        "arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
        "C:\\Windows\\Fonts\\Arial.ttf",  # Windows
        "/System/Library/Fonts/Helvetica.ttc"  # Mac
    ]
    
    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, template["font_size"])
            break
        except:
            continue
    
    if font is None:
        font = ImageFont.load_default()
    
    # Format geotag text
    location_text = f"{latitude:.6f}, {longitude:.6f}"
    
    if custom_text:
        geotag_text = f"{template['icon']} {custom_text}\n📍 {location_text}\n📅 {datetime_str}"
    else:
        geotag_text = f"{template['icon']} Location: {location_text}\n📅 {datetime_str}"
    
    # Calculate text size
    try:
        bbox = draw.multiline_textbbox((0, 0), geotag_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except:
        text_width = len(geotag_text) * template["font_size"] // 2
        text_height = template["font_size"] * 3
    
    # Position (bottom right)
    padding = template["padding"]
    x = img.width - text_width - padding * 2
    y = img.height - text_height - padding * 2
    
    # Draw rounded rectangle background
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    # Draw rectangle with rounded corners
    overlay_draw.rectangle(
        [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
        fill=template["bg_color"],
        outline=None
    )
    
    # Composite the overlay
    img = img.convert('RGBA')
    img = Image.alpha_composite(img, overlay)
    
    # Draw text on the image
    draw = ImageDraw.Draw(img)
    draw.multiline_text((x, y), geotag_text, fill=template["text_color"], font=font)
    
    # Convert back to RGB for JPEG
    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
    rgb_img.paste(img, mask=img.split()[3] if len(img.split()) > 3 else None)
    
    # Save to bytes
    output = io.BytesIO()
    rgb_img.save(output, format='JPEG', quality=95)
    output.seek(0)
    
    return output

# Sidebar
with st.sidebar:
    st.header("⚙️ Pengaturan")
    
    # Coordinate input
    st.subheader("📍 Koordinat")
    col1, col2 = st.columns(2)
    with col1:
        latitude = st.number_input("Latitude", value=-6.200000, format="%.6f", 
                                  help="Contoh: -6.200000 untuk Jakarta")
    with col2:
        longitude = st.number_input("Longitude", value=106.816666, format="%.6f",
                                   help="Contoh: 106.816666 untuk Jakarta")
    
    # Show map
    if st.checkbox("Tampilkan Peta", value=True):
        m = folium.Map(location=[latitude, longitude], zoom_start=12)
        folium.Marker(
            [latitude, longitude],
            popup=f"📍 {latitude}, {longitude}",
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(m)
        folium_static(m, width=300, height=250)
    
    # Time settings
    st.subheader("⏰ Waktu")
    use_custom_time = st.checkbox("Gunakan waktu kustom")
    if use_custom_time:
        custom_datetime = st.datetime_input("Pilih waktu", datetime.now())
        datetime_str = custom_datetime.strftime("%d/%m/%Y %H:%M:%S")
    else:
        datetime_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        st.info(f"Waktu sekarang: {datetime_str}")
    
    # Template
    st.subheader("🎨 Template")
    template_name = st.selectbox("Pilih style", list(get_templates().keys()))
    
    # Custom text
    st.subheader("✏️ Teks Kustom")
    custom_text = st.text_area("Teks tambahan", placeholder="Misal: Pantai Kuta, Bali", height=80)
    
    # Preview
    if st.checkbox("Preview template"):
        st.info(f"""
        **Template:** {template_name}
        **Contoh:**
        {get_templates()[template_name]['icon']} {custom_text if custom_text else 'Contoh Lokasi'}
        📍 {latitude:.6f}, {longitude:.6f}
        📅 {datetime_str}
        """)

# Main content
st.subheader("📸 Upload & Edit Foto")

# Multiple file upload
uploaded_files = st.file_uploader(
    "Pilih foto (bisa banyak sekaligus)",
    type=['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG'],
    accept_multiple_files=True,
    help="Support JPG, JPEG, PNG"
)

if uploaded_files:
    st.success(f"✓ {len(uploaded_files)} foto siap diproses")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        process_button = st.button("🎨 PROSES SEMUA FOTO", type="primary", use_container_width=True)
    
    if process_button:
        processed_images = []
        
        with st.spinner(f"Memproses {len(uploaded_files)} foto..."):
            progress_bar = st.progress(0)
            
            for idx, uploaded_file in enumerate(uploaded_files):
                # Process image
                processed_img = add_geotag_to_image(
                    uploaded_file.getvalue(), 
                    latitude, longitude, 
                    datetime_str, 
                    template_name, 
                    custom_text
                )
                
                processed_images.append((uploaded_file.name, processed_img))
                progress_bar.progress((idx + 1) / len(uploaded_files))
        
        st.success(f"✅ Berhasil! {len(processed_images)} foto telah diproses")
        
        # Create ZIP download
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for original_name, img_bytes in processed_images:
                name, ext = os.path.splitext(original_name)
                new_name = f"{name}_geotagged{ext}"
                zip_file.writestr(new_name, img_bytes.getvalue())
        
        zip_buffer.seek(0)
        
        # Download button
        st.download_button(
            label="📥 DOWNLOAD SEMUA (ZIP)",
            data=zip_buffer,
            file_name=f"geotagged_photos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip",
            use_container_width=True
        )
        
        # Preview results
        st.subheader("📷 Preview Hasil")
        cols = st.columns(3)
        for idx, (name, img_bytes) in enumerate(processed_images[:6]):
            with cols[idx % 3]:
                st.image(img_bytes, caption=name[:30], use_container_width=True)

# Instructions
with st.expander("ℹ️ Panduan Penggunaan", expanded=False):
    st.markdown("""
    ### Cara Menggunakan:
    1. **Masukkan koordinat** - Bisa manual atau lihat peta
    2. **Pilih template** - Ada 6 style berbeda
    3. **Upload foto** - Bisa banyak sekaligus
    4. **Klik proses** - Tunggu sebentar
    5. **Download** - Semua foto akan di-zip
    
    ### Tips:
    - Gunakan teks kustom untuk menambah keterangan lokasi
    - Koordinat bisa dicari di Google Maps
    - Format koordinat: desimal (contoh: -6.200000)
    - Foto akan disimpan dengan kualitas original
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray; padding: 1rem;">
    <p>© 2024 Geotag Photo Editor | Dengan 6 Template Kustom | Support Multiple Files</p>
</div>
""", unsafe_allow_html=True)