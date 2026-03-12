import webview
import threading
from app import app
import time
import sys
import socket
import random
import requests
from threading import Event

# ==================== FUNGSI UTILITY ====================

def find_free_port():
    """Mencari port yang tersedia secara otomatis"""
    while True:
        port = random.randint(49152, 65535)  # Rentang port dinamis
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue  # Port dipakai, coba port lain

def wait_for_server(url, timeout=10):
    """Menunggu server Flask benar-benar siap"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            requests.get(url, timeout=1)
            print(f"✅ Server siap di {url}")
            return True
        except requests.ConnectionError:
            print(".", end="", flush=True)
            time.sleep(0.5)
    print("\n❌ Server tidak merespon dalam {} detik".format(timeout))
    return False

# ==================== KELAS MANAJEMEN SERVER ====================

class FlaskServer:
    def __init__(self):
        self.port = find_free_port()
        self.host = '127.0.0.1'
        self.url = f"http://{self.host}:{self.port}"
        self.is_running = False
        self.thread = None
        
    def start(self):
        """Menjalankan Flask server di thread terpisah"""
        def run_flask():
            try:
                # Nonaktifkan debug mode untuk production
                app.config['DEBUG'] = False
                app.config['TESTING'] = False
                
                # Jalankan Flask
                print(f"🚀 Memulai Flask server di {self.url}")
                app.run(
                    host=self.host, 
                    port=self.port, 
                    debug=False, 
                    threaded=True,
                    use_reloader=False  # Matikan reloader karena di thread
                )
            except Exception as e:
                print(f"\n❌ Server Error: {e}")
                self.is_running = False
        
        # Start thread
        self.thread = threading.Thread(target=run_flask)
        self.thread.daemon = True
        self.thread.start()
        
        # Tunggu server siap
        print("⏳ Menunggu server siap", end="", flush=True)
        if wait_for_server(self.url, timeout=15):
            self.is_running = True
            return True
        else:
            return False
    
    def stop(self):
        """Menghentikan server (sebenarnya tidak perlu karena daemon thread)"""
        self.is_running = False
        print("🛑 Server dihentikan")

# ==================== FUNGSI UTAMA ====================

def main():
    """Fungsi utama untuk menjalankan aplikasi"""
    print("=" * 60)
    print("🚀 TELEGRAM BLASTER PRO - DESKTOP APP")
    print("=" * 60)
    
    # Inisialisasi dan start server
    server = FlaskServer()
    if not server.start():
        print("❌ Gagal memulai server. Aplikasi akan ditutup.")
        input("Tekan Enter untuk keluar...")
        sys.exit(1)
    
    try:
        # Buat window webview
        print(f"🪟 Membuka window aplikasi...")
        window = webview.create_window(
            title='Telegram Blaster Pro - Desktop App',
            url=server.url,
            width=1280,  # Sedikit lebih lebar
            height=768,
            resizable=True,
            fullscreen=False,
            min_size=(800, 600),
            confirm_close=True,  # Konfirmasi sebelum tutup
            text_select=True,     # Izinkan select text
        )
        
        # Start webview
        webview.start(debug=False, http_server=True)
        
    except KeyboardInterrupt:
        print("\n⚠️  Aplikasi dihentikan oleh user")
    except Exception as e:
        print(f"❌ GUI Error: {e}")
        import traceback
        traceback.print_exc()
        input("Tekan Enter untuk keluar...")
        sys.exit(1)
    finally:
        server.stop()
        print("👋 Aplikasi ditutup. Sampai jumpa!")

# ==================== ENTRY POINT ====================

if __name__ == '__main__':
    main()