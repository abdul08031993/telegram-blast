; installer.iss
[Setup]
AppName=Telegram Blaster Pro
AppVersion=1.0
AppPublisher=Your Company
AppPublisherURL=https://media21.com
DefaultDirName={pf}\TelegramBlasterPro
DefaultGroupName=Telegram Blaster Pro
UninstallDisplayIcon={app}\TelegramBlasterPro.exe
Compression=lzma2
SolidCompression=yes
OutputDir=installer_output
OutputBaseFilename=TelegramBlasterPro_Setup
SetupIconFile=icon.png
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\TelegramBlasterPro.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon.png"; DestDir: "{app}"; Flags: ignoreversion
; Tambahkan file lain jika perlu

[Icons]
Name: "{group}\Telegram Blaster Pro"; Filename: "{app}\TelegramBlasterPro.exe"; IconFilename: "{app}\icon.png"
Name: "{group}\Uninstall Telegram Blaster Pro"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Telegram Blaster Pro"; Filename: "{app}\TelegramBlasterPro.exe"; IconFilename: "{app}\icon.png"

[Run]
Filename: "{app}\TelegramBlasterPro.exe"; Description: "Jalankan Telegram Blaster Pro"; Flags: postinstall nowait skipifsilent

[UninstallRun]
; Hapus folder data pengguna saat uninstall
[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\.telegramblaster"