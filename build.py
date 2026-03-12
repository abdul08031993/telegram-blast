# build.py
import PyInstaller.__main__
import os
import shutil
import site
import sys
from datetime import datetime

print("=" * 60)
print("🚀 Membangun Telegram Blaster Pro untuk Linux...")
print(f"📅 Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# Bersihkan folder lama
for folder in ['dist', 'build', '__pycache__']:
    if os.path.exists(folder):
        print(f"🗑️  Menghapus folder {folder}...")
        shutil.rmtree(folder)

# Hapus file .spec lama
if os.path.exists('TelegramBlasterPro.spec'):
    os.remove('TelegramBlasterPro.spec')

# Pastikan folder sessions dan uploads ada (meski kosong)
os.makedirs('sessions', exist_ok=True)
os.makedirs('uploads', exist_ok=True)
print("📁 Folder sessions & uploads siap")

# Cek file icon
if os.path.exists('icon.png'):
    print(f"✅ icon.png ditemukan: {os.path.getsize('icon.png')} bytes")
else:
    print("⚠️  PERINGATAN: icon.png tidak ditemukan!")

# Dapatkan path site-packages
site_packages = site.getsitepackages()[0]
print(f"📦 Site packages: {site_packages}")

# Hidden imports lengkap
hidden_imports = [
    'flask',
    'webview',
    'telethon',
    'cryptography',
    'requests',
    'bottle',
    'proxy_tools',
    'asyncio',
    'pickle',
    'uuid',
    'hashlib',
    'hmac',
    'base64',
    'datetime',
    'json',
    'logging',
    'platform',
    'socket',
    'threading',
    'pathlib',
    'tempfile',
    'functools',
    'jinja2',
    'werkzeug',
    'markupsafe',
    'itsdangerous',
    'click',
    'pkg_resources.py2_warn',  # Tambahan untuk menghindari warning
]

print("📦 Menjalankan PyInstaller...")
print("-" * 60)

# Jalankan PyInstaller
PyInstaller.__main__.run([
    'run_app.py',
    '--name=TelegramBlasterPro',
    '--onefile',
    '--windowed',
    '--icon=icon.png',
    '--add-data=templates:templates',
    '--add-data=static:static',
    '--add-data=sessions:sessions',
    '--add-data=uploads:uploads',
    '--add-data=icon.png:.',
] + [f'--hidden-import={imp}' for imp in hidden_imports] + [
    '--collect-all=telethon',
    '--collect-all=cryptography',
    '--collect-all=flask',
    '--collect-all=webview',
    '--clean',
    '--noconfirm',
    '--log-level=INFO',
])

print("\n" + "=" * 60)
print("✅ Build selesai!")
print("=" * 60)

# Cek hasil
if os.path.exists('dist/TelegramBlasterPro'):
    size = os.path.getsize('dist/TelegramBlasterPro') / (1024*1024)
    print(f"📁 File executable: dist/TelegramBlasterPro")
    print(f"📊 Ukuran file: {size:.2f} MB")
    print(f"🔧 Permission: chmod +x dist/TelegramBlasterPro")
    
    # Buat file info
    with open('dist/version.txt', 'w') as f:
        f.write(f"Telegram Blaster Pro\n")
        f.write(f"Build: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Ukuran: {size:.2f} MB\n")
    
    # Buat .desktop file (untuk integrasi menu Linux)
    desktop_content = f"""[Desktop Entry]
Name=Telegram Blaster Pro
Comment=Aplikasi Broadcast Telegram
Exec={os.path.abspath('dist/TelegramBlasterPro')}
Icon={os.path.abspath('icon.png')}
Terminal=false
Type=Application
Categories=Network;Chat;
StartupNotify=true
"""
    with open('dist/TelegramBlasterPro.desktop', 'w') as f:
        f.write(desktop_content)
    
    print("📁 File desktop entry: dist/TelegramBlasterPro.desktop")
    
    # Buat archive untuk distribusi
    import tarfile
    with tarfile.open('dist/TelegramBlasterPro-Linux.tar.gz', 'w:gz') as tar:
        tar.add('dist/TelegramBlasterPro', arcname='TelegramBlasterPro')
        tar.add('dist/TelegramBlasterPro.desktop', arcname='TelegramBlasterPro.desktop')
        if os.path.exists('dist/version.txt'):
            tar.add('dist/version.txt', arcname='version.txt')
    
    print(f"📦 Archive: dist/TelegramBlasterPro-Linux.tar.gz")
    
else:
    print("❌ Build gagal! File tidak ditemukan.")
    sys.exit(1)

print("=" * 60)
print("🎉 Aplikasi siap didistribusikan!")
print("=" * 60)