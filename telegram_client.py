# telegram_client.py
from telethon import TelegramClient
from telethon.errors import (
    PhoneCodeInvalidError, 
    PhoneCodeExpiredError,
    SessionPasswordNeededError,
    FloodWaitError,
    PhoneNumberInvalidError,
    ApiIdInvalidError
)
from telethon.tl.functions.messages import AddChatUserRequest
import asyncio
import os
import logging
import time
import threading
from datetime import datetime

logger = logging.getLogger(__name__)

class TelegramClientManager:
    def __init__(self):
        self.clients = {}  # {account_id: client}
        self.loops = {}     # {account_id: loop}
        self.sessions = {}  # {account_id: session_string}
        
        # ============ TAMBAHAN UNTUK STOP BROADCAST ============
        self.broadcast_stop_events = {}  # {account_id: threading.Event}
        self.broadcast_threads = {}      # {account_id: threading.Thread}
        self.broadcast_results = {}      # {account_id: dict} untuk menyimpan hasil sementara
        # ======================================================
    
    def _get_or_create_loop(self, account_id):
        """Dapatkan atau buat event loop untuk account"""
        if account_id not in self.loops:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.loops[account_id] = loop
        return self.loops[account_id]
    
    def create_client(self, account_id, api_id, api_hash, session_string=None):
        """Buat client baru atau reconnect"""
        try:
            logger.info(f"Creating/reconnecting client for account {account_id}")
            
            # Dapatkan loop
            loop = self._get_or_create_loop(account_id)
            
            # Buat client baru
            session_name = f"sessions/session_{account_id}"
            client = TelegramClient(session_name, int(api_id), api_hash)
            
            # Connect
            loop.run_until_complete(client.connect())
            
            # Jika ada session string, coba start
            if session_string:
                try:
                    logger.info(f"Attempting to start with session for account {account_id}")
                    client.session = client.session.load(session_string)
                    loop.run_until_complete(client.start())
                    
                    # Cek apakah authorized
                    if loop.run_until_complete(client.is_user_authorized()):
                        logger.info(f"Successfully authorized account {account_id}")
                        self.clients[account_id] = client
                        self.sessions[account_id] = session_string
                        return {"success": True, "client": client, "authorized": True}
                except Exception as e:
                    logger.error(f"Failed to start with session: {e}")
            
            self.clients[account_id] = client
            return {"success": True, "client": client, "authorized": False}
            
        except Exception as e:
            logger.error(f"Error creating client: {e}")
            return {"success": False, "error": str(e)}
    
    def ensure_client(self, account_id):
        """Pastikan client ada dan terhubung"""
        try:
            if account_id not in self.clients:
                logger.error(f"Client {account_id} not found")
                return False
            
            client = self.clients[account_id]
            loop = self.loops[account_id]
            
            # Cek koneksi
            if not client.is_connected():
                logger.info(f"Client {account_id} not connected, reconnecting...")
                loop.run_until_complete(client.connect())
            
            # Cek authorized
            if not loop.run_until_complete(client.is_user_authorized()):
                logger.error(f"Client {account_id} not authorized")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error ensuring client: {e}")
            return False
    
    def get_client_status(self, account_id):
        """Dapatkan status client"""
        try:
            if account_id not in self.clients:
                return {"exists": False}
            
            client = self.clients[account_id]
            loop = self.loops[account_id]
            
            connected = client.is_connected()
            authorized = False
            
            if connected:
                try:
                    authorized = loop.run_until_complete(client.is_user_authorized())
                except:
                    pass
            
            return {
                "exists": True,
                "connected": connected,
                "authorized": authorized
            }
        except Exception as e:
            return {"exists": False, "error": str(e)}
    
    def send_code(self, account_id, phone_number):
        """Kirim kode verifikasi"""
        try:
            if account_id not in self.clients:
                return {"success": False, "error": "Client tidak ditemukan"}
            
            client = self.clients[account_id]
            loop = self.loops[account_id]
            
            result = loop.run_until_complete(client.send_code_request(phone_number))
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def sign_in(self, account_id, phone_number, code, password=None):
        """Login dengan kode"""
        try:
            if account_id not in self.clients:
                return {"success": False, "error": "Client tidak ditemukan"}
            
            client = self.clients[account_id]
            loop = self.loops[account_id]
            
            try:
                user = loop.run_until_complete(client.sign_in(phone_number, code))
            except SessionPasswordNeededError:
                if password:
                    user = loop.run_until_complete(client.sign_in(password=password))
                else:
                    return {"success": False, "error": "password_required"}
            
            session_string = client.session.save()
            self.sessions[account_id] = session_string
            
            return {"success": True, "session_string": session_string}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_dialogs(self, account_id):
        """Dapatkan daftar chat"""
        try:
            # Pastikan client OK
            if not self.ensure_client(account_id):
                return {"success": False, "error": "Client tidak tersedia"}
            
            client = self.clients[account_id]
            loop = self.loops[account_id]
            
            dialogs = loop.run_until_complete(client.get_dialogs())
            
            chats = []
            for dialog in dialogs:
                chat_type = 'user'
                if dialog.is_group:
                    chat_type = 'group'
                elif dialog.is_channel:
                    chat_type = 'channel'
                
                chats.append({
                    'id': dialog.id,
                    'name': dialog.name or 'Unknown',
                    'type': chat_type,
                    'unread_count': dialog.unread_count
                })
            
            return {"success": True, "chats": chats}
            
        except Exception as e:
            logger.error(f"Error getting dialogs: {e}")
            return {"success": False, "error": str(e)}
    
    def get_chat_history(self, account_id, chat_id, limit=50):
        """Dapatkan histori chat"""
        try:
            logger.info(f"Getting chat history for account {account_id}, chat {chat_id}, limit {limit}")
            
            # Pastikan client OK
            if not self.ensure_client(account_id):
                return {"success": False, "error": "Client tidak tersedia"}
            
            client = self.clients[account_id]
            loop = self.loops[account_id]
            
            # Dapatkan entity
            try:
                entity = loop.run_until_complete(client.get_entity(int(chat_id)))
                logger.info(f"Entity found: {entity.id}")
            except Exception as e:
                logger.error(f"Error getting entity: {e}")
                return {"success": False, "error": f"Gagal mendapatkan chat: {str(e)}"}
            
            # Ambil messages
            messages = []
            try:
                # Gunakan get_messages untuk mendapatkan pesan
                for message in loop.run_until_complete(
                    client.get_messages(entity, limit=limit)
                ):
                    sender_name = 'Unknown'
                    if message.sender:
                        sender_name = (
                            message.sender.first_name or 
                            message.sender.username or 
                            'Unknown'
                        )
                    
                    # Format pesan
                    msg_data = {
                        'id': message.id,
                        'date': message.date.strftime('%Y-%m-%d %H:%M:%S'),
                        'sender_id': message.sender_id,
                        'sender_name': sender_name,
                        'text': message.text or '',
                        'media': bool(message.media),
                        'out': message.out
                    }
                    
                    # Tambahkan info media jika ada
                    if message.media:
                        msg_data['media_type'] = type(message.media).__name__
                    
                    messages.append(msg_data)
                    
            except Exception as e:
                logger.error(f"Error getting messages: {e}")
                return {"success": False, "error": f"Gagal mengambil pesan: {str(e)}"}
            
            logger.info(f"Found {len(messages)} messages")
            return {"success": True, "messages": messages}
            
        except Exception as e:
            logger.error(f"Error in get_chat_history: {e}")
            return {"success": False, "error": str(e)}
    
    # ==================== BROADCAST DENGAN FITUR STOP ====================
    
    def stop_broadcast(self, account_id):
        """
        Menghentikan proses broadcast yang sedang berjalan
        """
        try:
            if account_id in self.broadcast_stop_events:
                # Set stop event
                self.broadcast_stop_events[account_id].set()
                logger.info(f"Stop signal sent for broadcast account {account_id}")
                
                # Tunggu thread selesai (maks 3 detik)
                if account_id in self.broadcast_threads:
                    self.broadcast_threads[account_id].join(timeout=3)
                
                return {'success': True, 'message': 'Broadcast dihentikan'}
            else:
                return {'success': False, 'error': 'Tidak ada broadcast yang berjalan'}
        except Exception as e:
            logger.error(f"Error stopping broadcast: {e}")
            return {'success': False, 'error': str(e)}
    
    def send_broadcast(self, account_id, recipients, message, media_path=None):
        """
        Kirim broadcast (versi asli) - LANGSUNG DI THREAD
        """
        try:
            logger.info(f"Starting broadcast from account {account_id} to {len(recipients)} recipients")
            
            # Buat stop event
            stop_event = threading.Event()
            self.broadcast_stop_events[account_id] = stop_event
            
            # Buat thread untuk broadcast
            thread = threading.Thread(
                target=self._broadcast_worker,
                args=(account_id, recipients, message, media_path, stop_event)
            )
            thread.daemon = True
            self.broadcast_threads[account_id] = thread
            thread.start()
            
            return {
                'success': True, 
                'message': 'Broadcast dimulai',
                'account_id': account_id,
                'total': len(recipients)
            }
            
        except Exception as e:
            logger.error(f"Error starting broadcast: {e}")
            return {"success": False, "error": str(e)}
    
    def _broadcast_worker(self, account_id, recipients, message, media_path, stop_event):
        """
        Worker untuk broadcast yang berjalan di thread terpisah
        """
        results = {
            'success_count': 0,
            'failed_count': 0,
            'failed_recipients': [],
            'total': len(recipients),
            'stopped': False
        }
        
        try:
            logger.info(f"Broadcast worker started for account {account_id}")
            
            # Pastikan client OK
            if not self.ensure_client(account_id):
                logger.error(f"Client not available for account {account_id}")
                results['error'] = "Client tidak tersedia"
                self.broadcast_results[account_id] = results
                return
            
            client = self.clients[account_id]
            loop = self.loops[account_id]
            
            for i, recipient in enumerate(recipients):
                # Cek apakah harus berhenti
                if stop_event.is_set():
                    logger.info(f"Broadcast stopped by user for account {account_id}")
                    results['stopped'] = True
                    break
                
                try:
                    logger.info(f"[{i+1}/{len(recipients)}] Sending to {recipient}...")
                    
                    # Dapatkan entity
                    entity = loop.run_until_complete(client.get_entity(recipient))
                    
                    # Kirim pesan
                    if media_path and os.path.exists(media_path):
                        loop.run_until_complete(
                            client.send_file(
                                entity, 
                                media_path, 
                                caption=message,
                                force_document=False,
                                parse_mode='html'
                            )
                        )
                    else:
                        loop.run_until_complete(
                            client.send_message(entity, message)
                        )
                    
                    results['success_count'] += 1
                    logger.info(f"Successfully sent to {recipient}")
                    
                except FloodWaitError as e:
                    # Flood wait error
                    wait_time = e.seconds
                    results['failed_count'] += 1
                    results['failed_recipients'].append({
                        'recipient': recipient,
                        'error': f'Flood wait {wait_time} detik'
                    })
                    logger.warning(f"Flood wait for {wait_time} seconds")
                    time.sleep(wait_time)
                    
                except Exception as e:
                    results['failed_count'] += 1
                    results['failed_recipients'].append({
                        'recipient': recipient,
                        'error': str(e)
                    })
                    logger.error(f"Failed to send to {recipient}: {e}")
                
                # Delay antar pengiriman (500ms)
                time.sleep(0.5)
            
            logger.info(f"Broadcast finished for account {account_id}: {results['success_count']} success, {results['failed_count']} failed")
            
        except Exception as e:
            logger.error(f"Error in broadcast worker: {e}")
            results['error'] = str(e)
            
        finally:
            # Simpan hasil
            self.broadcast_results[account_id] = results
            
            # Cleanup
            if account_id in self.broadcast_stop_events:
                del self.broadcast_stop_events[account_id]
            if account_id in self.broadcast_threads:
                del self.broadcast_threads[account_id]
    
    # ==================== METHOD REPLY TO MESSAGE ====================
    
    def reply_to_message(self, account_id, chat_id, message_id, reply_text, media_path=None):
        """
        Membalas pesan tertentu
        """
        try:
            logger.info(f"Replying to message {message_id} in chat {chat_id} using account {account_id}")
            
            # Pastikan client OK
            if not self.ensure_client(account_id):
                return {"success": False, "error": "Client tidak tersedia"}
            
            client = self.clients[account_id]
            loop = self.loops[account_id]
            
            # Dapatkan entity chat
            try:
                entity = loop.run_until_complete(client.get_entity(int(chat_id)))
                logger.info(f"Entity found: {entity.id}")
            except Exception as e:
                logger.error(f"Error getting entity: {e}")
                return {"success": False, "error": f"Gagal mendapatkan chat: {str(e)}"}
            
            # Kirim balasan
            try:
                if media_path and os.path.exists(media_path):
                    logger.info(f"Sending reply with media from {media_path}")
                    result = loop.run_until_complete(
                        client.send_file(
                            entity, 
                            media_path, 
                            caption=reply_text,
                            reply_to=message_id
                        )
                    )
                else:
                    logger.info(f"Sending text reply")
                    result = loop.run_until_complete(
                        client.send_message(
                            entity, 
                            reply_text,
                            reply_to=message_id
                        )
                    )
                
                logger.info(f"Reply sent successfully, message ID: {result.id}")
                return {"success": True, "message_id": result.id}
                
            except Exception as e:
                logger.error(f"Error sending reply: {e}")
                return {"success": False, "error": str(e)}
            
        except Exception as e:
            logger.error(f"Error in reply_to_message: {e}")
            return {"success": False, "error": str(e)}
    
    # ==================== SCRAP MEMBERS ====================
    
    def scrap_group_members(self, account_id, group_id):
        """Scrap anggota grup"""
        try:
            if not self.ensure_client(account_id):
                return {"success": False, "error": "Client tidak tersedia"}
            
            client = self.clients[account_id]
            loop = self.loops[account_id]
            
            # Bersihkan group_id
            clean_id = group_id.strip()
            if clean_id.startswith('https://t.me/'):
                clean_id = clean_id.replace('https://t.me/', '')
            if clean_id.startswith('@'):
                clean_id = clean_id[1:]
            
            # Dapatkan entity
            entity = loop.run_until_complete(client.get_entity(clean_id))
            
            # Ambil participants
            members = []
            participants = loop.run_until_complete(client.get_participants(entity))
            
            for user in participants:
                members.append({
                    'id': user.id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'phone': user.phone
                })
            
            return {"success": True, "members": members}
            
        except Exception as e:
            logger.error(f"Error scrapping members: {e}")
            return {"success": False, "error": str(e)}
    
    # ==================== ADD MEMBERS ====================
    
    def add_members_to_group(self, account_id, group_id, members_ids):
        """Tambah anggota ke grup"""
        try:
            if not self.ensure_client(account_id):
                return {"success": False, "error": "Client tidak tersedia"}
            
            client = self.clients[account_id]
            loop = self.loops[account_id]
            
            entity = loop.run_until_complete(client.get_entity(group_id))
            
            results = {'success': 0, 'failed': 0, 'failed_members': []}
            
            for member_id in members_ids:
                try:
                    user = loop.run_until_complete(client.get_entity(int(member_id)))
                    loop.run_until_complete(
                        client(AddChatUserRequest(
                            chat_id=entity.id,
                            user_id=user.id,
                            fwd_limit=100
                        ))
                    )
                    results['success'] += 1
                except Exception as e:
                    results['failed'] += 1
                    results['failed_members'].append({
                        'member_id': member_id,
                        'error': str(e)
                    })
                
                time.sleep(2)
            
            return {"success": True, "results": results}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==================== DISCONNECT ====================
    
    def disconnect_client(self, account_id):
        """Putuskan koneksi client"""
        try:
            # Hentikan broadcast jika sedang berjalan
            if account_id in self.broadcast_threads:
                self.stop_broadcast(account_id)
            
            if account_id in self.clients:
                client = self.clients[account_id]
                loop = self.loops[account_id]
                
                if client.is_connected():
                    loop.run_until_complete(client.disconnect())
                
                del self.clients[account_id]
                if account_id in self.loops:
                    self.loops[account_id].close()
                    del self.loops[account_id]
                
                logger.info(f"Client {account_id} disconnected")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
            return False

# Instance global
client_manager = TelegramClientManager()