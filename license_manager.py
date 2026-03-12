# license_manager.py
import os
import json
import hashlib
import platform
import socket
from pathlib import Path

class LicenseManager:
    def __init__(self):
        # Pindahkan license.key ke folder yang lebih tersembunyi
        self.app_data = Path.home() / '.telegramblaster'
        self.license_file = self.app_data / 'license.dat'
        self.key_file = Path('license.key')  # File asli (akan dihapus setelah aktivasi)
        
    def get_hardware_id(self):
        """Mendapatkan ID unik komputer"""
        system = platform.system()
        
        if system == "Windows":
            try:
                import subprocess
                result = subprocess.run(['wmic', 'cpu', 'get', 'ProcessorId'], 
                                      capture_output=True, text=True)
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    cpu_id = lines[1].strip()
                    return hashlib.sha256(cpu_id.encode()).hexdigest()[:16]
            except:
                pass
                
        elif system == "Darwin":  # macOS
            try:
                import subprocess
                result = subprocess.run(['system_profiler', 'SPHardwareDataType', '|', 'grep', 'Serial'],
                                      capture_output=True, text=True, shell=True)
                return hashlib.sha256(result.stdout.encode()).hexdigest()[:16]
            except:
                pass
        else:  # Linux
            try:
                with open('/etc/machine-id', 'r') as f:
                    return hashlib.sha256(f.read().encode()).hexdigest()[:16]
            except:
                pass
        
        # Fallback: kombinasi hostname + MAC address
        hostname = socket.gethostname()
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                       for elements in range(0,48,8)][::-1])
        return hashlib.sha256(f"{hostname}{mac}".encode()).hexdigest()[:16]
    
    def generate_license(self, user_email, days_valid=3650):  # 10 tahun (lifetime)
        """Generate license key (untuk Anda sebagai developer)"""
        import hmac
        import datetime
        
        secret = b"RAHASIA_SUPER_RAHASIA_12345"  # GANTI INI!
        
        expiry = (datetime.datetime.now() + datetime.timedelta(days=days_valid)).strftime("%Y%m%d")
        data = f"{user_email}|{expiry}|{self.get_hardware_id()}"
        
        signature = hmac.new(secret, data.encode(), hashlib.sha256).hexdigest()[:8]
        license_key = f"{data}|{signature}"
        
        # Encode base64 biar pendek
        import base64
        return base64.b64encode(license_key.encode()).decode()
    
    def verify_license(self, license_key):
        """Verifikasi license key (offline)"""
        try:
            import base64
            import hmac
            import datetime
            
            secret = b"RAHASIA_SUPER_RAHASIA_12345"  # SAMA dengan di atas
            
            # Decode base64
            decoded = base64.b64decode(license_key.encode()).decode()
            parts = decoded.split('|')
            
            if len(parts) != 4:
                return False
            
            email, expiry_str, hardware_id, signature = parts
            
            # Verifikasi signature
            data = f"{email}|{expiry_str}|{hardware_id}"
            expected = hmac.new(secret, data.encode(), hashlib.sha256).hexdigest()[:8]
            
            if signature != expected:
                return False
            
            # Verifikasi hardware ID (optional: bisa dimatikan jika ingin fleksibel)
            if hardware_id != self.get_hardware_id():
                return False  # Lisensi dipasang di komputer lain!
            
            # Verifikasi expiry
            expiry = datetime.datetime.strptime(expiry_str, "%Y%m%d")
            if expiry < datetime.datetime.now():
                return False  # Lisensi expired
            
            return True
            
        except Exception as e:
            print(f"Error verifikasi: {e}")
            return False
    
    def save_license(self, license_key):
        """Simpan license key yang valid"""
        self.app_data.mkdir(exist_ok=True)
        
        # Simpan license
        with open(self.license_file, 'w') as f:
            f.write(license_key)
        
        # Hapus license.key lama kalau ada
        if self.key_file.exists():
            self.key_file.unlink()
        
        return True
    
    def load_license(self):
        """Load license yang tersimpan"""
        if self.license_file.exists():
            with open(self.license_file, 'r') as f:
                return f.read().strip()
        
        # Cek legacy license.key
        if self.key_file.exists():
            with open(self.key_file, 'r') as f:
                return f.read().strip()
        
        return None
    
    def is_licensed(self):
        """Cek apakah aplikasi sudah terlisensi"""
        license_key = self.load_license()
        if license_key:
            return self.verify_license(license_key)
        return False
    
    def activate(self, license_key):
        """Aktivasi dengan license key"""
        if self.verify_license(license_key):
            self.save_license(license_key)
            return True
        return False