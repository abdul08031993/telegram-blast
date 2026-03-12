# generate_license.py
from app import license_manager
from datetime import datetime

def main():
    print("=" * 60)
    print("🎫 GENERATOR LICENSE KEY TELEGRAM BLASTER PRO")
    print("=" * 60)
    
    print("\n📋 Pilih tipe lisensi:")
    print("1. Basic (5 akun) - Rp 500.000")
    print("2. Pro (20 akun) - Rp 1.500.000")
    print("3. Enterprise (100 akun) - Rp 3.000.000")
    print("4. Trial (2 akun, 7 hari) - Gratis")
    
    pilihan = input("\nMasukkan pilihan (1/2/3/4): ").strip()
    
    email = input("Email customer: ").strip()
    
    # Tentukan tipe lisensi
    if pilihan == '1':
        license_type = 'basic'
        days = 365  # 1 tahun
        price = "Rp 500.000"
    elif pilihan == '2':
        license_type = 'pro'
        days = 365  # 1 tahun
        price = "Rp 1.500.000"
    elif pilihan == '3':
        license_type = 'enterprise'
        days = 365  # 1 tahun
        price = "Rp 3.000.000"
    elif pilihan == '4':
        license_type = 'basic'  # Trial pake tipe basic tapi durasi pendek
        days = 7  # 7 hari
        price = "GRATIS"
    else:
        print("❌ Pilihan tidak valid!")
        return
    
    # Generate license key
    license_key = license_manager.generate_license(email, license_type, days)
    
    # Hitung tanggal kadaluarsa
    expiry_date = (datetime.now() + timedelta(days=days)).strftime("%d/%m/%Y")
    
    print("\n" + "=" * 60)
    print("✅ LICENSE KEY BERHASIL DIBUAT!")
    print("=" * 60)
    print(f"📧 Email        : {email}")
    print(f"📦 Tipe Lisensi : {license_type.upper()}")
    print(f"⏰ Masa Berlaku : {days} hari (sampai {expiry_date})")
    print(f"💰 Harga        : {price}")
    print(f"🎫 License Key  : {license_key}")
    print("=" * 60)
    
    # Simpan ke file
    filename = f"license_{email.replace('@', '_at_')}.txt"
    with open(filename, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("TELEGRAM BLASTER PRO - LICENSE KEY\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Email        : {email}\n")
        f.write(f"Tipe Lisensi : {license_type.upper()}\n")
        f.write(f"Masa Berlaku : {days} hari (sampai {expiry_date})\n")
        f.write(f"Harga        : {price}\n\n")
        f.write(f"License Key  : {license_key}\n\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated on : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    
    print(f"\n📁 File license disimpan di: {filename}")
    print("\n📝 Instruksi untuk customer:")
    print("1. Buka aplikasi Telegram Blaster Pro")
    print("2. Masukkan license key di atas")
    print("3. Klik 'Aktivasi Sekarang'")
    print("4. Setelah aktif, restart aplikasi")

if __name__ == "__main__":
    from datetime import timedelta
    main()