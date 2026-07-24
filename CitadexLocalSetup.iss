#define AppName "Citadex Local"
#define AppVersion "0.2.0"

#ifndef SourceBundle
  #error SourceBundle must point to the prepared Citadex Local portable folder
#endif

#ifndef SetupOutput
  #define SetupOutput ".\dist-installer"
#endif

[Setup]
AppId={{D81A26E5-3EA5-49E8-AB62-32CC7872218A}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Citadex
DefaultDirName={localappdata}\Citadex Local
DefaultGroupName=Citadex Local
UninstallDisplayIcon={app}\Citadex-Local.exe
OutputDir={#SetupOutput}
OutputBaseFilename=Citadex-Local-Web-Setup-{#AppVersion}
SetupIconFile=assets\citadex.ico
WizardStyle=modern dark polar includetitlebar hidebevels
WizardSizePercent=125
WizardImageFile=assets\citadex-icon.png
WizardSmallImageFile=assets\citadex-icon.png
WizardImageOpacity=210
WizardImageBackColor=#100C1D
WizardBackColor=#090812
DisableWelcomePage=no
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
Compression=none
SolidCompression=no
ArchitecturesAllowed=x64compatible
MinVersion=10.0.17763
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes
AllowNoIcons=yes
DiskSpanning=no
Uninstallable=yes
VersionInfoVersion={#AppVersion}.0
VersionInfoProductName={#AppName}
VersionInfoDescription=Offline AI coding agent powered by Qwen2.5-Coder 3B

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Ярлыки"; Flags: checkedonce
Name: "startmenuicon"; Description: "Добавить в меню «Пуск»"; GroupDescription: "Ярлыки"; Flags: checkedonce

[Files]
Source: "{#SourceBundle}\*"; DestDir: "{app}"; Excludes: "models\*"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF/resolve/main/qwen2.5-coder-3b-instruct-q4_k_m.gguf?download=true"; DestDir: "{app}\models"; DestName: "qwen2.5-coder-3b-instruct-q4_k_m.gguf"; ExternalSize: 2104932800; Hash: "724fb256bec1ff062b2f65e4569e871ad2e95ab2a3989723d1769c54294730b7"; Flags: external download ignoreversion

[Icons]
Name: "{autodesktop}\Citadex Local"; Filename: "{app}\Citadex-Local.exe"; WorkingDir: "{userdocs}"; Tasks: desktopicon
Name: "{autoprograms}\Citadex Local"; Filename: "{app}\Citadex-Local.exe"; WorkingDir: "{userdocs}"; Tasks: startmenuicon

[Run]
Filename: "{app}\Citadex-Local.exe"; Description: "Запустить Citadex Local"; WorkingDir: "{userdocs}"; Flags: nowait postinstall skipifsilent

[Code]
var
  BrandLabel: TNewStaticText;
  SubtitleLabel: TNewStaticText;
  StepLabel: TNewStaticText;
  StorageLabel: TNewStaticText;

procedure UpdateStep;
var
  StepText: String;
begin
  case WizardForm.CurPageID of
    wpWelcome: StepText := '01  ПРИВЕТСТВИЕ   ─   02  ХРАНИЛИЩЕ   ─   03  УСТАНОВКА';
    wpSelectDir: StepText := '01  ГОТОВО        ─   02  ХРАНИЛИЩЕ   ─   03  УСТАНОВКА';
    wpSelectTasks: StepText := '01  ГОТОВО        ─   02  ЯРЛЫКИ      ─   03  УСТАНОВКА';
    wpReady: StepText := '01  ГОТОВО        ─   02  ГОТОВО       ─   03  ПРОВЕРКА';
    wpInstalling: StepText := '01  ГОТОВО        ─   02  ГОТОВО       ─   03  УСТАНОВКА';
    wpFinished: StepText := '01  ГОТОВО        ─   02  ГОТОВО       ─   03  ЗАВЕРШЕНО';
  else
    StepText := 'CITADEX  /  OFFLINE AI';
  end;
  StepLabel.Caption := StepText;
end;

procedure InitializeWizard;
begin
  WizardForm.Color := $120809;
  WizardForm.InnerPage.Color := $1D1826;
  WizardForm.MainPanel.Color := $1D1826;
  WizardForm.WelcomePage.Color := $1D1826;
  WizardForm.FinishedPage.Color := $1D1826;

  BrandLabel := TNewStaticText.Create(WizardForm);
  BrandLabel.Parent := WizardForm;
  BrandLabel.Left := ScaleX(24);
  BrandLabel.Top := ScaleY(16);
  BrandLabel.Width := ScaleX(250);
  BrandLabel.Height := ScaleY(32);
  BrandLabel.Caption := '✦  CITADEX LOCAL';
  BrandLabel.Font.Name := 'Segoe UI';
  BrandLabel.Font.Size := 18;
  BrandLabel.Font.Style := [fsBold];
  BrandLabel.Font.Color := $FA8BA7;

  SubtitleLabel := TNewStaticText.Create(WizardForm);
  SubtitleLabel.Parent := WizardForm;
  SubtitleLabel.Left := ScaleX(28);
  SubtitleLabel.Top := ScaleY(49);
  SubtitleLabel.Width := ScaleX(260);
  SubtitleLabel.Caption := 'QWEN2.5-CODER 3B  •  PRIVATE  •  OFFLINE';
  SubtitleLabel.Font.Name := 'Segoe UI';
  SubtitleLabel.Font.Size := 8;
  SubtitleLabel.Font.Color := $EED322;

  StepLabel := TNewStaticText.Create(WizardForm);
  StepLabel.Parent := WizardForm;
  StepLabel.Left := ScaleX(320);
  StepLabel.Top := ScaleY(29);
  StepLabel.Width := ScaleX(520);
  StepLabel.Height := ScaleY(25);
  StepLabel.Alignment := taRightJustify;
  StepLabel.Font.Name := 'Segoe UI Semibold';
  StepLabel.Font.Size := 8;
  StepLabel.Font.Color := $C9C4D4;

  WizardForm.OuterNotebook.Top := ScaleY(82);
  WizardForm.OuterNotebook.Height := WizardForm.ClientHeight - ScaleY(145);
  WizardForm.NextButton.Caption := 'ПРОДОЛЖИТЬ  ›';
  WizardForm.BackButton.Caption := '‹  НАЗАД';
  WizardForm.CancelButton.Caption := 'ОТМЕНА';

  StorageLabel := TNewStaticText.Create(WizardForm.SelectDirPage);
  StorageLabel.Parent := WizardForm.SelectDirPage;
  StorageLabel.Left := ScaleX(0);
  StorageLabel.Top := ScaleY(92);
  StorageLabel.Width := WizardForm.SelectDirPage.Width;
  StorageLabel.Height := ScaleY(48);
  StorageLabel.Caption :=
    'Модель Qwen будет скачана с официального Hugging Face в выбранную папку.' + #13#10 +
    'Нужно около 2.4 ГБ. После установки интернет и API-ключи не требуются.';
  StorageLabel.Font.Name := 'Segoe UI';
  StorageLabel.Font.Size := 9;
  StorageLabel.Font.Color := $D9D5E3;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  UpdateStep;
end;
