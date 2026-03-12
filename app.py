# app.py
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import asyncio
import os
import json
import pickle
import logging
import uuid
import hashlib
import hmac
import base64
import platform
import socket
import sys
import tempfile
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from functools import wraps
import time
from pathlib import Path

# Import client manager
from telegram_client import TelegramClientManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== KONFIGURASI PATH UNTUK EXECUTABLE ====================

def get_base_path():
    """Mendapatkan base path yang benar untuk executable"""
    if getattr(sys, 'frozen', False):
        # Jika running sebagai executable (PyInstaller)
        return sys._MEIPASS
    else:
        # Jika running sebagai script python biasa
        return os.path.abspath(".")

def get_writable_path():
    """Mendapatkan path yang writable untuk menyimpan file (sessions, uploads, license)"""
    if getattr(sys, 'frozen', False):
        # Untuk executable, gunakan folder user agar bisa write
        system = platform.system()
        if system == "Windows":
            # Windows: C:\Users\Username\AppData\Local\TelegramBlasterPro
            base = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
            return os.path.join(base, 'TelegramBlasterPro')
        elif system == "Darwin":  # macOS
            # macOS: ~/Library/Application Support/TelegramBlasterPro
            base = os.path.expanduser('~')
            return os.path.join(base, 'Library', 'Application Support', 'TelegramBlasterPro')
        else:  # Linux
            # Linux: ~/.config/telegramblasterpro
            base = os.path.expanduser('~')
            return os.path.join(base, '.config', 'telegramblasterpro')
    else:
        # Untuk development, gunakan folder lokal
        return os.path.abspath(".")

# Setup paths
BASE_PATH = get_base_path()
WRITABLE_PATH = get_writable_path()

# Buat folder yang diperlukan di writable path
os.makedirs(WRITABLE_PATH, exist_ok=True)
os.makedirs(os.path.join(WRITABLE_PATH, 'sessions'), exist_ok=True)
os.makedirs(os.path.join(WRITABLE_PATH, 'uploads'), exist_ok=True)

logger.info(f"BASE_PATH: {BASE_PATH}")
logger.info(f"WRITABLE_PATH: {WRITABLE_PATH}")

# Inisialisasi Flask dengan template_folder yang benar
app = Flask(__name__,
            template_folder=os.path.join(BASE_PATH, 'templates'),
            static_folder=os.path.join(BASE_PATH, 'static'))

app.secret_key = 'telegram-blas-secret-key-2026-ganti-ini'
app.config['UPLOAD_FOLDER'] = os.path.join(WRITABLE_PATH, 'uploads')
app.config['SESSION_FOLDER'] = os.path.join(WRITABLE_PATH, 'sessions')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload

# ==================== SISTEM LISENSI LIFETIME SEDERHANA ====================

class LicenseManager:
    def __init__(self):
        # Gunakan WRITABLE_PATH untuk license file
        self.app_data = Path(WRITABLE_PATH)
        self.license_file = self.app_data / 'license.key'
        
        # 🔐 PENTING: GANTI DENGAN KODE RAHASIA ANDA SENDIRI!
        # HARUS SAMA DENGAN YANG DI FILE generate_license.py
        self.secret_key = b"RAHASIA_KUAT_12345!@#$%"
        
        # Buat folder AppData
        self.app_data.mkdir(parents=True, exist_ok=True)
        logger.info(f"License manager initialized: {self.app_data}")
    
    def get_hwid(self):
        """
        Mendapatkan Hardware ID unik komputer
        (untuk mengikat license dengan 1 komputer)
        """
        components = []
        
        # MAC Address (cukup unik untuk setiap komputer)
        try:
            mac = hex(uuid.getnode())[2:].upper()
            components.append(mac)
        except:
            pass
        
        # Hostname
        try:
            components.append(socket.gethostname())
        except:
            pass
        
        # Gabungkan semua komponen
        combined = '|'.join(components)
        hwid = hashlib.sha256(combined.encode()).hexdigest()[:16].upper()
        
        logger.debug(f"Generated HWID: {hwid}")
        return hwid
    
    def verify_license(self, license_key):
        """
        Verifikasi license key
        Format: email|timestamp|signature (dalam base64)
        """
        try:
            # Decode base64
            decoded = base64.b64decode(license_key.encode()).decode()
            parts = decoded.split('|')
            
            # Format harus memiliki 3 bagian
            if len(parts) != 3:
                logger.warning(f"Invalid license format: {len(parts)} parts")
                return {'valid': False, 'reason': 'invalid_format'}
            
            email, timestamp, signature = parts
            
            # Verifikasi signature
            data = f"{email}|{timestamp}"
            expected = hmac.new(self.secret_key, data.encode(), hashlib.sha256).hexdigest()[:8]
            
            if signature != expected:
                logger.warning(f"Invalid signature for {email}")
                return {'valid': False, 'reason': 'invalid_signature'}
            
            logger.info(f"License verified for email: {email}")
            return {
                'valid': True,
                'email': email,
                'max_accounts': 20  # Default untuk lifetime
            }
            
        except Exception as e:
            logger.error(f"License verification error: {e}")
            return {'valid': False, 'reason': 'verification_error'}
    
    def save_license(self, license_key, email):
        """
        Simpan license yang valid
        Menyimpan license key + HWID komputer ini
        """
        try:
            data = {
                'key': license_key,
                'email': email,
                'hwid': self.get_hwid(),
                'activated_at': datetime.now().isoformat()
            }
            with open(self.license_file, 'w') as f:
                json.dump(data, f)
            logger.info(f"License saved to {self.license_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving license: {e}")
            return False
    
    def load_license(self):
        """
        Load license yang tersimpan
        Sekaligus cek apakah HWID masih sama
        """
        if self.license_file.exists():
            try:
                with open(self.license_file, 'r') as f:
                    data = json.load(f)
                
                # Verifikasi license key
                result = self.verify_license(data['key'])
                
                if result.get('valid'):
                    # Cek HWID (apakah ini komputer yang sama?)
                    current_hwid = self.get_hwid()
                    if data.get('hwid') == current_hwid:
                        return data
                    else:
                        logger.warning(f"HWID mismatch! License for different computer")
                        return None
                else:
                    logger.warning("Stored license is invalid")
                    return None
                    
            except Exception as e:
                logger.error(f"Error loading license: {e}")
                return None
        
        return None
    
    def is_licensed(self):
        """Cek apakah aplikasi sudah terlisensi"""
        license_data = self.load_license()
        return license_data is not None
    
    def get_license_info(self):
        """Dapatkan informasi lisensi (untuk ditampilkan)"""
        license_data = self.load_license()
        if license_data:
            return {
                'email': license_data.get('email'),
                'activated_at': license_data.get('activated_at'),
                'max_accounts': 20
            }
        return None
    
    def activate(self, license_key):
        """
        Aktivasi dengan license key
        Returns: {'success': bool, 'email': str, 'error': str}
        """
        result = self.verify_license(license_key)
        
        if result.get('valid'):
            # Simpan license di komputer ini
            if self.save_license(license_key, result['email']):
                return {
                    'success': True, 
                    'email': result['email'],
                    'max_accounts': result['max_accounts']
                }
            else:
                return {'success': False, 'error': 'Gagal menyimpan license'}
        else:
            error_messages = {
                'invalid_format': 'Format license key tidak valid',
                'invalid_signature': 'License key tidak valid',
                'verification_error': 'Gagal memverifikasi license key'
            }
            return {
                'success': False, 
                'error': error_messages.get(result.get('reason'), 'License key tidak valid')
            }

# Inisialisasi license manager
license_manager = LicenseManager()

# ==================== DECORATOR UNTUK PROTEKSI ====================

def require_license(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip untuk halaman aktivasi dan static
        if request.endpoint in ['activate_page', 'api_activate', 'api_check_license', 'static']:
            return f(*args, **kwargs)
        
        # Cek lisensi
        if not license_manager.is_licensed():
            # Redirect ke aktivasi
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'License required'}), 403
            return redirect(url_for('activate_page'))
        
        return f(*args, **kwargs)
    return decorated_function

def check_account_limit():
    """Decorator untuk cek batasan jumlah akun (lifetime: 20 akun)"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Batasan untuk lifetime: 20 akun
            max_accounts = 20
            
            # Hitung akun yang sudah ada
            current_accounts = len(accounts)
            
            # Jika ini request tambah akun, cek limit
            if request.endpoint == 'add_account' and current_accounts >= max_accounts:
                return jsonify({
                    'success': False, 
                    'error': f'Batas maksimal akun ({max_accounts}) telah tercapai.'
                }), 403
            
            return f(*args, **kwargs)
        return wrapped
    return decorator

# ==================== INISIALISASI CLIENT MANAGER ====================

# Inisialisasi client manager
client_manager = TelegramClientManager()

# Set session folder (jika diperlukan oleh telegram_client.py)
try:
    client_manager.session_folder = app.config['SESSION_FOLDER']
    logger.info(f"Session folder set to: {app.config['SESSION_FOLDER']}")
except AttributeError:
    logger.warning("TelegramClientManager doesn't have session_folder attribute")
    pass

# Data storage in memory
accounts = {}
next_account_id = 1

# Save/Load accounts
def save_account(account):
    """Simpan akun ke file pickle di folder sessions"""
    try:
        account_file = os.path.join(app.config['SESSION_FOLDER'], f"account_{account['id']}.pkl")
        with open(account_file, 'wb') as f:
            pickle.dump(account, f)
        logger.info(f"Account {account['id']} saved to {account_file}")
    except Exception as e:
        logger.error(f"Error saving account {account['id']}: {e}")

def load_accounts():
    """Load semua akun dari file pickle"""
    global accounts, next_account_id
    accounts = {}
    max_id = 0
    
    session_folder = app.config['SESSION_FOLDER']
    logger.info(f"Loading accounts from {session_folder}")
    
    if os.path.exists(session_folder):
        for filename in os.listdir(session_folder):
            if filename.startswith('account_') and filename.endswith('.pkl'):
                try:
                    filepath = os.path.join(session_folder, filename)
                    with open(filepath, 'rb') as f:
                        account = pickle.load(f)
                        accounts[account['id']] = account
                        max_id = max(max_id, account['id'])
                        logger.info(f"Loaded account {account['id']}: {account['phone']}")
                except Exception as e:
                    logger.error(f"Error loading {filename}: {e}")
    
    next_account_id = max_id + 1
    logger.info(f"Loaded {len(accounts)} accounts, next ID: {next_account_id}")

def delete_account_file(account_id):
    """Hapus file akun"""
    try:
        filename = os.path.join(app.config['SESSION_FOLDER'], f"account_{account_id}.pkl")
        if os.path.exists(filename):
            os.remove(filename)
            logger.info(f"Deleted account file for {account_id}")
    except Exception as e:
        logger.error(f"Error deleting account file {account_id}: {e}")

# Load accounts on startup
load_accounts()

# ==================== ROUTES LISENSI ====================

@app.route('/activate')
def activate_page():
    """Halaman untuk memasukkan lisensi"""
    if license_manager.is_licensed():
        return redirect(url_for('dashboard'))
    
    return render_template('activate.html', 
                         hwid=license_manager.get_hwid())

@app.route('/api/activate', methods=['POST'])
def api_activate():
    """API untuk memproses kunci lisensi"""
    try:
        key = request.form.get('license_key', '').strip()
        
        if not key:
            return jsonify({'success': False, 'error': 'License key tidak boleh kosong'})
        
        result = license_manager.activate(key)
        
        if result['success']:
            flash('✅ Lisensi berhasil diaktifkan! Selamat menggunakan Telegram Blaster Pro.', 'success')
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': result['error']})
            
    except Exception as e:
        logger.error(f"Activation error: {e}")
        return jsonify({'success': False, 'error': 'Terjadi kesalahan server'})

@app.route('/api/check-license')
def api_check_license():
    """Cek status lisensi via AJAX"""
    try:
        if license_manager.is_licensed():
            info = license_manager.get_license_info()
            return jsonify({
                'licensed': True,
                'email': info.get('email', ''),
                'activated_at': info.get('activated_at', ''),
                'max_accounts': 20,
                'current_accounts': len(accounts)
            })
        
        return jsonify({'licensed': False})
        
    except Exception as e:
        logger.error(f"Check license error: {e}")
        return jsonify({'licensed': False, 'error': str(e)})

# ==================== ROUTES AKUN ====================

@app.route('/')
@require_license
def index():
    """Halaman utama"""
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@require_license
def dashboard():
    """Dashboard utama"""
    license_info = license_manager.get_license_info()
    
    return render_template('dashboard.html', 
                         accounts=accounts.values(),
                         license_info=license_info)

@app.route('/accounts')
@require_license
def accounts_page():
    """Halaman manajemen akun"""
    license_info = license_manager.get_license_info()
    
    return render_template('accounts.html', 
                         accounts=accounts.values(),
                         max_accounts=20,
                         current_accounts=len(accounts))

@app.route('/add_account', methods=['POST'])
@require_license
@check_account_limit()
def add_account():
    """Tambah akun baru (dengan cek limit)"""
    global next_account_id
    
    try:
        phone = request.form.get('phone')
        api_id = request.form.get('api_id')
        api_hash = request.form.get('api_hash')
        
        logger.info(f"Adding account with phone: {phone}")
        
        if not all([phone, api_id, api_hash]):
            return jsonify({'success': False, 'error': 'Semua field harus diisi'})
        
        # Format nomor telepon
        phone = phone.strip()
        if not phone.startswith('+'):
            phone = '+' + phone.replace(' ', '')
        
        # Cek duplikat
        for acc in accounts.values():
            if acc['phone'] == phone:
                return jsonify({'success': False, 'error': 'Nomor telepon sudah terdaftar'})
        
        account_id = next_account_id
        next_account_id += 1
        
        account = {
            'id': account_id,
            'phone': phone,
            'api_id': api_id,
            'api_hash': api_hash,
            'session_string': None,
            'is_active': False,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_used': None
        }
        
        accounts[account_id] = account
        save_account(account)
        
        return jsonify({
            'success': True, 
            'account_id': account_id,
            'message': 'Akun berhasil ditambahkan'
        })
    except Exception as e:
        logger.error(f"Error adding account: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/login_account/<int:account_id>', methods=['POST'])
@require_license
def login_account(account_id):
    """Login ke akun Telegram"""
    try:
        if account_id not in accounts:
            return jsonify({'success': False, 'error': 'Akun tidak ditemukan'})
        
        account = accounts[account_id]
        if account.get('session_string'):
            return jsonify({'success': False, 'error': 'Akun sudah login'})
        
        session['login_account_id'] = account_id
        result = client_manager.create_client(account_id, account['api_id'], account['api_hash'])
        
        if not result['success']:
            return jsonify({'success': False, 'error': result.get('error', 'Gagal membuat client')})
        
        code_result = client_manager.send_code(account_id, account['phone'])
        if code_result['success']:
            return jsonify({'success': True, 'requires_code': True})
        else:
            client_manager.disconnect_client(account_id)
            return jsonify({'success': False, 'error': code_result.get('error', 'Gagal mengirim kode')})
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/verify_code', methods=['POST'])
@require_license
def verify_code():
    """Verifikasi kode login"""
    try:
        code = request.form.get('code')
        password = request.form.get('password', '')
        account_id = session.get('login_account_id')
        
        if not account_id or account_id not in accounts:
            return jsonify({'success': False, 'error': 'Sesi login tidak ditemukan'})
        
        account = accounts[account_id]
        result = client_manager.sign_in(account_id, account['phone'], code, password if password else None)
        
        if result['success']:
            account['session_string'] = result['session_string']
            account['is_active'] = True
            account['last_used'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_account(account)
            session.pop('login_account_id', None)
            return jsonify({'success': True})
        else:
            if result.get('error') == 'password_required':
                return jsonify({'success': False, 'error': 'password_required'})
            return jsonify({'success': False, 'error': result.get('error', 'Gagal verifikasi')})
    except Exception as e:
        logger.error(f"Verify code error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/check_login_status/<int:account_id>')
@require_license
def check_login_status(account_id):
    """Cek status login akun (untuk auto-refresh)"""
    try:
        if account_id not in accounts:
            return jsonify({'success': False, 'error': 'Akun tidak ditemukan'}), 404
        
        account = accounts[account_id]
        return jsonify({
            'success': True,
            'is_active': account.get('is_active', False),
            'has_session': account.get('session_string') is not None
        })
    except Exception as e:
        logger.error(f"Check login status error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/account_status/<int:account_id>')
@require_license
def account_status(account_id):
    """Get detail lengkap akun (untuk modal detail)"""
    try:
        if account_id not in accounts:
            return jsonify({'success': False, 'error': 'Akun tidak ditemukan'}), 404
        
        account = accounts[account_id]
        return jsonify({
            'success': True,
            'id': account['id'],
            'phone': account['phone'],
            'api_id': account['api_id'],
            'api_hash': account['api_hash'],
            'is_active': account.get('is_active', False),
            'has_session': account.get('session_string') is not None,
            'created_at': account['created_at'],
            'last_used': account.get('last_used')
        })
    except Exception as e:
        logger.error(f"Account status error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/logout_account/<int:account_id>', methods=['POST'])
@require_license
def logout_account(account_id):
    """Logout dari akun"""
    try:
        if account_id not in accounts:
            return jsonify({'success': False, 'error': 'Akun tidak ditemukan'})
        
        account = accounts[account_id]
        client_manager.disconnect_client(account_id)
        account['session_string'] = None
        account['is_active'] = False
        save_account(account)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete_account/<int:account_id>', methods=['POST'])
@require_license
def delete_account(account_id):
    """Hapus akun"""
    try:
        if account_id not in accounts:
            return jsonify({'success': False, 'error': 'Akun tidak ditemukan'})
        
        client_manager.disconnect_client(account_id)
        del accounts[account_id]
        delete_account_file(account_id)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Delete account error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ==================== ROUTES BROADCAST ====================

@app.route('/broadcast')
@require_license
def broadcast():
    """Halaman broadcast"""
    active_accounts = [acc for acc in accounts.values() if acc['is_active']]
    return render_template('broadcast.html', accounts=active_accounts)

@app.route('/send_broadcast', methods=['POST'])
@require_license
def send_broadcast():
    """Kirim broadcast"""
    try:
        account_id = int(request.form.get('account_id'))
        recipients = json.loads(request.form.get('recipients', '[]'))
        message = request.form.get('message')
        media_file = request.files.get('media')
        
        if account_id not in accounts:
            return jsonify({'success': False, 'error': 'Akun tidak ditemukan'})
        
        account = accounts[account_id]
        status = client_manager.get_client_status(account_id)
        
        if not status.get('exists'):
            client_manager.create_client(account_id, account['api_id'], account['api_hash'], account.get('session_string'))
        
        media_path = None
        if media_file and media_file.filename:
            filename = secure_filename(media_file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            media_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{timestamp}_{filename}")
            media_file.save(media_path)
            logger.info(f"Media saved to {media_path}")
        
        result = client_manager.send_broadcast(account_id, recipients, message, media_path)
        
        # Hapus file temporary
        if media_path and os.path.exists(media_path):
            try:
                os.remove(media_path)
            except:
                pass
        
        if result['success']:
            account['last_used'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_account(account)
            
            # ============ SIMPAN HISTORY BROADCAST ============
            try:
                history_file = os.path.join(WRITABLE_PATH, 'broadcast_history.json')
                
                # Load history yang ada
                if os.path.exists(history_file):
                    with open(history_file, 'r') as f:
                        history = json.load(f)
                else:
                    history = []
                
                # Buat entri history baru
                history_entry = {
                    'id': len(history) + 1,
                    'account_id': account_id,
                    'account_phone': account['phone'],
                    'message_content': message[:50] + '...' if message and len(message) > 50 else message,
                    'recipients_count': len(recipients),
                    'success_count': result.get('success_count', 0),
                    'failed_count': result.get('failed_count', 0),
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Tambahkan ke awal array
                history.insert(0, history_entry)
                
                # Simpan hanya 100 history terakhir
                history = history[:100]
                
                with open(history_file, 'w') as f:
                    json.dump(history, f, indent=2)
                    
                logger.info(f"History saved: {history_entry}")
                    
            except Exception as e:
                logger.error(f"Error saving history: {e}")
            # ============ AKHIR SIMPAN HISTORY ============
            
        return jsonify(result)
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ==================== ROUTES STOP BROADCAST (DIPISAH) ====================

@app.route('/stop_broadcast/<int:account_id>', methods=['POST'])
@require_license
def stop_broadcast(account_id):
    """Menghentikan proses broadcast yang sedang berjalan"""
    try:
        if account_id not in accounts:
            return jsonify({'success': False, 'error': 'Akun tidak ditemukan'})
        
        result = client_manager.stop_broadcast(account_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Stop broadcast error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/broadcast_status/<int:account_id>')
@require_license
def broadcast_status(account_id):
    """Cek status broadcast yang sedang berjalan"""
    try:
        is_running = account_id in client_manager.broadcast_threads
        return jsonify({
            'success': True,
            'is_running': is_running
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== ROUTES HISTORY ====================

@app.route('/get_history')
@require_license
def get_history():
    """Mendapatkan riwayat broadcast"""
    try:
        # Cek apakah ada file history
        history_file = os.path.join(WRITABLE_PATH, 'broadcast_history.json')
        
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                history = json.load(f)
        else:
            history = []
        
        # Batasi jumlah history yang ditampilkan (misal 50 terakhir)
        history = history[:50]
        
        return jsonify({
            'success': True,
            'history': history
        })
        
    except Exception as e:
        logger.error(f"Error loading history: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'history': []
        })

# ==================== ROUTES MONITOR ====================

@app.route('/monitor')
@require_license
def monitor():
    """Halaman monitor chat"""
    active_accounts = [acc for acc in accounts.values() if acc['is_active']]
    return render_template('monitor.html', accounts=active_accounts)

@app.route('/get_chats/<int:account_id>')
@require_license
def get_chats(account_id):
    """Ambil daftar chat"""
    try:
        if account_id not in accounts or not accounts[account_id]['is_active']:
            return jsonify({'success': False, 'error': 'Akun tidak aktif'})
        result = client_manager.get_dialogs(account_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Get chats error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_chat_history/<int:account_id>/<int:chat_id>')
@require_license
def get_chat_history(account_id, chat_id):
    """Ambil histori chat"""
    try:
        limit = request.args.get('limit', 50, type=int)
        if account_id not in accounts or not accounts[account_id]['is_active']:
            return jsonify({'success': False, 'error': 'Akun tidak aktif'})
        result = client_manager.get_chat_history(account_id, chat_id, limit)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Get chat history error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/reply_message', methods=['POST'])
@require_license
def reply_message():
    """Endpoint untuk membalas pesan"""
    try:
        account_id = int(request.form.get('account_id'))
        chat_id = request.form.get('chat_id')
        message_id = int(request.form.get('message_id'))
        reply_text = request.form.get('reply_text')
        media_file = request.files.get('media')
        
        if account_id not in accounts or not accounts[account_id]['is_active']:
            return jsonify({'success': False, 'error': 'Akun tidak aktif'})
        
        media_path = None
        if media_file and media_file.filename:
            filename = secure_filename(media_file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            media_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{timestamp}_{filename}")
            media_file.save(media_path)
        
        result = client_manager.reply_to_message(account_id, chat_id, message_id, reply_text, media_path)
        
        if media_path and os.path.exists(media_path):
            try:
                os.remove(media_path)
            except:
                pass
        
        if result['success']:
            accounts[account_id]['last_used'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_account(accounts[account_id])
        return jsonify(result)
    except Exception as e:
        logger.error(f"Reply message error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ==================== ROUTES SCRAP ====================

@app.route('/scrap')
@require_license
def scrap():
    """Halaman scrap member"""
    active_accounts = [acc for acc in accounts.values() if acc['is_active']]
    return render_template('scrap.html', accounts=active_accounts)

@app.route('/scrap_group_members', methods=['POST'])
@require_license
def scrap_group_members():
    """Scrap anggota grup"""
    try:
        account_id = int(request.form.get('account_id'))
        group_id = request.form.get('group_id')
        if account_id not in accounts or not accounts[account_id]['is_active']:
            return jsonify({'success': False, 'error': 'Akun tidak aktif'})
        result = client_manager.scrap_group_members(account_id, group_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Scrap members error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ==================== ROUTES ADD MEMBERS ====================

@app.route('/add_members')
@require_license
def add_members():
    """Halaman tambah anggota"""
    active_accounts = [acc for acc in accounts.values() if acc['is_active']]
    return render_template('add_members.html', accounts=active_accounts)

@app.route('/add_members_to_group', methods=['POST'])
@require_license
def add_members_to_group():
    """Tambah anggota ke grup"""
    try:
        account_id = int(request.form.get('account_id'))
        group_id = request.form.get('group_id')
        members_ids = json.loads(request.form.get('members_ids', '[]'))
        if account_id not in accounts or not accounts[account_id]['is_active']:
            return jsonify({'success': False, 'error': 'Akun tidak aktif'})
        result = client_manager.add_members_to_group(account_id, group_id, members_ids)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Add members error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ==================== DEBUG ROUTES ====================

@app.route('/debug_clients')
@require_license
def debug_clients():
    """Endpoint untuk debug client"""
    try:
        client_info = {
            'clients': list(client_manager.clients.keys()),
            'loops': list(client_manager.loops.keys()),
            'accounts_loaded': list(accounts.keys()),
            'session_folder': app.config['SESSION_FOLDER'],
            'writable_path': WRITABLE_PATH,
            'base_path': BASE_PATH
        }
        return jsonify({'success': True, 'client_manager': client_info})
    except Exception as e:
        logger.error(f"Debug clients error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/health')
def health():
    """Endpoint untuk cek kesehatan aplikasi"""
    return jsonify({
        'status': 'OK',
        'time': datetime.now().isoformat(),
        'licensed': license_manager.is_licensed(),
        'accounts': len(accounts),
        'writable_path': WRITABLE_PATH,
        'base_path': BASE_PATH
    })

@app.route('/favicon.ico')
def favicon():
    """Handle favicon request"""
    return '', 204  # Return no content

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'success': False, 'error': 'Endpoint tidak ditemukan'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

# ==================== MAIN ====================

if __name__ == '__main__':
    # Untuk development, jalankan langsung
    print("=" * 60)
    print("🚀 Telegram Blaster Pro - Development Mode")
    print("=" * 60)
    print(f"Base path: {BASE_PATH}")
    print(f"Writable path: {WRITABLE_PATH}")
    print(f"License file: {license_manager.license_file}")
    print(f"Templates: {app.template_folder}")
    print(f"Static: {app.static_folder}")
    print(f"Sessions: {app.config['SESSION_FOLDER']}")
    print(f"Uploads: {app.config['UPLOAD_FOLDER']}")
    print("=" * 60)
    
    # Untuk production, set debug=False
    app.run(debug=True, host='127.0.0.1', port=5005)