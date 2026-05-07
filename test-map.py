import requests
import math
from PIL import Image, ImageDraw
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

# --- KONFIGURASI TEST ---
latitude = -7.213549
longitude = 112.769247
zoom = 18             # Gunakan 18 agar data peta PASTI ADA (HD)
target_size = (800, 800)
output_name = "map_surabaya_hd.png"

def download_tile(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Referer': 'https://leafletjs.com'
    }
    try:
        # Timeout ditambah agar tidak mudah gagal
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return Image.open(BytesIO(res.content))
    except:
        return None
    return None

def get_hd_map_fast(lat, lon, zoom, size):
    print(f"🛰️ Memproses koordinat: {lat}, {lon}...")
    
    # 1. Konversi ke Pixel Presisi
    n = 2.0 ** zoom
    center_x = (lon + 180.0) / 360.0 * n * 256
    lat_rad = math.radians(lat)
    center_y = (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n * 256

    # 2. Ukuran render 2x (Supersampling agar HD)
    render_w, render_h = size[0] * 2, size[1] * 2
    
    # Hitung batas tile yang dibutuhkan
    start_x = int(math.floor((center_x - render_w/2) / 256))
    end_x = int(math.floor((center_x + render_w/2) / 256))
    start_y = int(math.floor((center_y - render_h/2) / 256))
    end_y = int(math.floor((center_y + render_h/2) / 256))

    # 3. Perbaikan URL: Gunakan subdomain 'a' dan path 'light_all'
    urls = []
    positions = []
    for x in range(start_x, end_x + 1):
        for y in range(start_y, end_y + 1):
            # URL INI ADALAH KUNCI (CartoDB Positron)
            urls.append(f"https://cartocdn.com{zoom}/{x}/{y}.png")
            positions.append(((x - start_x) * 256, (y - start_y) * 256))

    print(f"📥 Mendownload {len(urls)} tiles secara paralel...")

    # 4. Multithreading
    with ThreadPoolExecutor(max_workers=10) as executor:
        tiles = list(executor.map(download_tile, urls))

    # 5. Susun ubin ke Kanvas
    canvas_w = (end_x - start_x + 1) * 256
    canvas_h = (end_y - start_y + 1) * 256
    canvas = Image.new('RGB', (canvas_w, canvas_h), (245, 245, 245))
    
    for tile, pos in zip(tiles, positions):
        if tile:
            canvas.paste(tile, pos)

    # 6. Potong agar titik berada TEPAT di TENGAH (PENTING)
    # offset_x/y adalah posisi titik lat/long di dalam kanvas besar
    offset_x = center_x - (start_x * 256)
    offset_y = center_y - (start_y * 256)
    
    left = offset_x - render_w/2
    top = offset_y - render_h/2
    map_hd = canvas.crop((left, top, left + render_w, top + render_h))

    # 7. Tambah Marker Pin Merah (HD)
    draw = ImageDraw.Draw(map_hd)
    cx, cy = render_w // 2, render_h // 2
    # Gambar pin merah yang lebih besar agar tajam setelah resize
    draw.ellipse([cx - 12, cy - 36, cx + 12, cy - 12], fill=(255, 0, 0)) 
    draw.polygon([(cx - 12, cy - 24), (cx + 12, cy - 24), (cx, cy)], fill=(255, 0, 0))
    draw.ellipse([cx - 4, cy - 28, cx + 4, cy - 20], fill=(255, 255, 255))

    # 8. Resize balik ke target_size dengan LANCZOS
    print(f"🎨 Menghaluskan gambar (Resampling)...")
    return map_hd.resize(size, Image.Resampling.LANCZOS)

# --- JALANKAN TEST ---
if __name__ == "__main__":
    try:
        result = get_hd_map_fast(latitude, longitude, zoom, target_size)
        result.save(output_name)
        print("=" * 50)
        print(f"✅ BERHASIL! Gambar HD '{output_name}' siap.")
        print(f"📍 Posisi: {latitude}, {longitude} tepat di TENGAH.")
        print("=" * 50)
    except Exception as e:
        print(f"❌ Terjadi kesalahan: {e}")
