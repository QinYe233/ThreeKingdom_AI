; 千秋弈·群雄逐鹿 - Inno Setup 安装脚本
; 版本: 1.0.0
; 需要安装 Inno Setup 6.x 来编译此脚本

#define MyAppName "千秋弈·群雄逐鹿"
#define MyAppNameEn "SanGuo"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "QinYe233"
#define MyAppURL "https://github.com/QinYe233/ThreeKingdom_AI"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppNameEn}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=installer
OutputBaseFilename=SanGuo-Setup-{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#MyAppName}

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
; 启动脚本
Source: "启动游戏.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "停止服务.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "安装依赖.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "SanGuo.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "Stop-SanGuo.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "install-deps.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "check_dependencies.py"; DestDir: "{app}"; Flags: ignoreversion

; 后端文件
Source: "backend\*"; DestDir: "{app}\backend"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__,*.pyc,venv,*.pyo,.env,*.pyc"

; 前端文件
Source: "frontend\*"; DestDir: "{app}\frontend"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "node_modules,dist,.git"

; 配置文件
Source: "backend\data\game_config.json"; DestDir: "{app}\backend\data"; Flags: ignoreversion

; 文档
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\启动游戏.bat"
Name: "{group}\停止服务"; Filename: "{app}\停止服务.bat"
Name: "{group}\安装依赖"; Filename: "{app}\安装依赖.bat"
Name: "{group}\{cm:ProgramOnTheWeb,{#MyAppName}}"; Filename: "{#MyAppURL}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\启动游戏.bat"; Tasks: desktopicon

[Run]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\install-deps.ps1"""; Description: "安装依赖 (Python/Node.js)"; Flags: nowait postinstall skipifsilent unchecked
Filename: "{app}\启动游戏.bat"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  PythonInstalled: Boolean;
  NodeInstalled: Boolean;

function CheckPythonVersion: Boolean;
var
  VersionStr: String;
  Major, Minor: Integer;
  ResultCode: Integer;
begin
  Result := False;
  ShellExec('', 'python', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  // 检查版本是否 >= 3.11
  VersionStr := GetFileVersion('python.exe');
  if VersionStr <> '' then
  begin
    // 简化版本检查 - 实际上我们需要运行 python --version 并解析输出
    // 这里我们简化为：只要注册表中有 Python 就认为已安装
    Result := RegKeyExists(HKLM, 'SOFTWARE\Python\PythonCore') or RegKeyExists(HKCU, 'SOFTWARE\Python\PythonCore');
  end;
end;

function InitializeSetup: Boolean;
begin
  Result := True;

  PythonInstalled := RegKeyExists(HKLM, 'SOFTWARE\Python\PythonCore') or RegKeyExists(HKCU, 'SOFTWARE\Python\PythonCore');
  NodeInstalled := RegKeyExists(HKLM, 'SOFTWARE\Node.js') or RegKeyExists(HKCU, 'SOFTWARE\Node.js');

  if not PythonInstalled or not NodeInstalled then
  begin
    if MsgBox('检测到缺少必要依赖：'#13#10#13#10 +
      IfThen(not PythonInstalled, '  - Python 3.11+'#13#10, '') +
      IfThen(not NodeInstalled, '  - Node.js 18+'#13#10, '') +
      #13#10'安装程序可以在安装完成后自动帮您安装这些依赖。'#13#10#13#10'是否继续安装？',
      mbConfirmation, MB_YESNO) = IDNO then
      Result := False;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    if not PythonInstalled or not NodeInstalled then
    begin
      if MsgBox('是否现在安装缺失的依赖？'#13#10#13#10 +
        '点击"是"将自动下载并安装 Python 和 Node.js（需要联网）'#13#10#13#10 +
        '安装过程可能需要几分钟，请耐心等待。',
        mbConfirmation, MB_YESNO) = IDYES then
      begin
        // 首先运行 Python 依赖检查脚本
        if FileExists(ExpandConstant('{app}\check_dependencies.py')) then
        begin
          ShellExec('', 'python', '"' + ExpandConstant('{app}\check_dependencies.py') + '"',
            '', SW_SHOW, ewWaitUntilTerminated, ResultCode);
        end
        else
        begin
          // 回退到 PowerShell 脚本
          ShellExec('', 'powershell.exe',
            '-ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\install-deps.ps1') + '"',
            '', SW_SHOW, ewWaitUntilTerminated, ResultCode);
        end;

        if ResultCode = 0 then
        begin
          MsgBox('依赖安装完成！'#13#10#13#10'重要提示：'#13#10 +
            '1. 请关闭当前安装程序'#13#10 +
            '2. 重新打开命令行窗口'#13#10 +
            '3. 再次运行游戏启动器'#13#10#13#10 +
            '这是为了让新安装的程序在新的环境中生效。',
            mbInformation, MB_OK);
        end
        else
        begin
          MsgBox('依赖安装可能失败。'#13#10#13#10 +
            '您可以稍后手动运行"安装依赖"快捷方式来完成安装。',
            mbWarning, MB_OK);
        end;
      end;
    end
    else
    begin
      // 所有依赖都已安装
      MsgBox('安装完成！'#13#10#13#10'使用说明：'#13#10 +
        '1. 双击桌面快捷方式启动游戏'#13#10 +
        '2. 浏览器将自动打开 http://localhost:5173'#13#10 +
        '3. 如需手动安装依赖，请运行"安装依赖"快捷方式',
        mbInformation, MB_OK);
    end;
  end;
end;
