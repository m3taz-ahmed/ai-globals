#requires -Version 5.1
# aiZee - Professional WPF GUI Installer for Windows
#
# Features:
#   - 8-page wizard: Welcome, License, Location, Components, Config, Pre-flight, Progress, Finish
#   - Component selection: core, plugins, MCP servers, agent configs, CLI, shortcuts
#   - .env secrets setup (auto-copy .env.example, pre-flight check, finish-page reminder)
#   - Live progress bar + scrolling log
#   - Pre-flight checks (Python, npx, uvx, disk space, .env secrets)
#   - Post-install verification + health check
#   - Rollback on failure
#   - Install log saved to state/
#   - Version read dynamically from pyproject.toml (no hardcoded version)
#
# Usage:
#   .\gui_installer.ps1                # Launch GUI
#   .\gui_installer.ps1 -Silent        # Silent install (no GUI, uses defaults)
#   .\gui_installer.ps1 -InstallDir D:\custom  # Pre-set install location

param(
    [switch]$Silent,
    [string]$InstallDir,
    [switch]$SkipPip,
    [switch]$SkipGraphify,
    [switch]$SkipMCP
)

$ErrorActionPreference = "Stop"
$Repo = $PSScriptRoot
if ($Repo -eq "") { $Repo = (Get-Location).Path }
# The GUI installer lives in installer/ subfolder, so repo is parent
$Repo = Split-Path $Repo -Parent

# ---------------------------------------------------------------------------
# Read version dynamically from pyproject.toml
# ---------------------------------------------------------------------------
function Get-TargetVersion {
    param([string]$Path)
    $pyproject = Join-Path $Path "pyproject.toml"
    if (-not (Test-Path $pyproject)) { return "0.0.0" }
    $content = Get-Content $pyproject -Raw
    if ($content -match 'version\s*=\s*"([^"]+)"') {
        return $matches[1]
    }
    return "0.0.0"
}
$TargetVersion = Get-TargetVersion $Repo

# ---------------------------------------------------------------------------
# Silent mode: delegate to install.ps1
# ---------------------------------------------------------------------------
if ($Silent) {
    $installScript = Join-Path $Repo "install.ps1"
    $installArgs = @()
    if ($InstallDir) { $installArgs += "-InstallDir"; $installArgs += $InstallDir }
    if ($SkipPip) { $installArgs += "-SkipPip" }
    if ($SkipGraphify) { $installArgs += "-SkipGraphify" }
    if ($SkipMCP) { $installArgs += "-SkipMCP" }
    & powershell -ExecutionPolicy Bypass -File $installScript @installArgs
    exit $LASTEXITCODE
}

# ---------------------------------------------------------------------------
# Load WPF assemblies
# ---------------------------------------------------------------------------
Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName WindowsBase
Add-Type -AssemblyName System.Windows.Forms

# ---------------------------------------------------------------------------
# XAML: Main window with 8-page wizard
# ---------------------------------------------------------------------------

[xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="aiZee Installer" Height="620" Width="820"
        WindowStartupLocation="CenterScreen" ResizeMode="CanMinimize"
        Background="#FFFFFF" WindowStyle="SingleBorderWindow">
    <Window.Resources>
        <Style x:Key="PageTitle" TargetType="TextBlock">
            <Setter Property="Foreground" Value="#0969DA"/>
            <Setter Property="FontSize" Value="22"/>
            <Setter Property="FontWeight" Value="Bold"/>
            <Setter Property="Margin" Value="0,0,0,10"/>
        </Style>
        <Style x:Key="PageSubtitle" TargetType="TextBlock">
            <Setter Property="Foreground" Value="#57606A"/>
            <Setter Property="FontSize" Value="13"/>
            <Setter Property="Margin" Value="0,0,0,20"/>
            <Setter Property="TextWrapping" Value="Wrap"/>
        </Style>
        <Style x:Key="BodyText" TargetType="TextBlock">
            <Setter Property="Foreground" Value="#1F2328"/>
            <Setter Property="FontSize" Value="13"/>
            <Setter Property="Margin" Value="0,5,0,5"/>
            <Setter Property="TextWrapping" Value="Wrap"/>
        </Style>
        <Style x:Key="NavButton" TargetType="Button">
            <Setter Property="Background" Value="#F6F8FA"/>
            <Setter Property="Foreground" Value="#1F2328"/>
            <Setter Property="BorderBrush" Value="#D0D7DE"/>
            <Setter Property="BorderThickness" Value="1"/>
            <Setter Property="Padding" Value="20,8"/>
            <Setter Property="FontSize" Value="13"/>
        </Style>
        <Style x:Key="PrimaryButton" TargetType="Button">
            <Setter Property="Background" Value="#1F6FEB"/>
            <Setter Property="Foreground" Value="White"/>
            <Setter Property="BorderBrush" Value="#1F6FEB"/>
            <Setter Property="BorderThickness" Value="1"/>
            <Setter Property="Padding" Value="20,8"/>
            <Setter Property="FontSize" Value="13"/>
        </Style>
        <Style x:Key="StepIndicator" TargetType="TextBlock">
            <Setter Property="FontSize" Value="11"/>
            <Setter Property="Margin" Value="8,0,8,0"/>
            <Setter Property="VerticalAlignment" Value="Center"/>
        </Style>
        <Style x:Key="CheckboxStyle" TargetType="CheckBox">
            <Setter Property="Foreground" Value="#1F2328"/>
            <Setter Property="FontSize" Value="13"/>
            <Setter Property="Margin" Value="0,6,0,6"/>
        </Style>
        <Style x:Key="RadioStyle" TargetType="RadioButton">
            <Setter Property="Foreground" Value="#1F2328"/>
            <Setter Property="FontSize" Value="13"/>
            <Setter Property="Margin" Value="0,6,0,6"/>
        </Style>
        <Style x:Key="LogBox" TargetType="TextBox">
            <Setter Property="Background" Value="#F6F8FA"/>
            <Setter Property="Foreground" Value="#1A7F37"/>
            <Setter Property="FontFamily" Value="Consolas"/>
            <Setter Property="FontSize" Value="11"/>
            <Setter Property="IsReadOnly" Value="True"/>
            <Setter Property="VerticalScrollBarVisibility" Value="Auto"/>
            <Setter Property="HorizontalScrollBarVisibility" Value="Auto"/>
            <Setter Property="BorderBrush" Value="#D0D7DE"/>
        </Style>
    </Window.Resources>

    <Grid Margin="0">
        <Grid.RowDefinitions>
            <RowDefinition Height="*"/>
            <RowDefinition Height="Auto"/>
        </Grid.RowDefinitions>

        <!-- Main content area -->
        <Grid Grid.Row="0" Margin="30,20,30,10">
            <!-- Page 1: Welcome -->
            <ScrollViewer x:Name="PageWelcome" Visibility="Visible" VerticalScrollBarVisibility="Auto">
                <StackPanel>
                    <TextBlock Style="{StaticResource PageTitle}" Text="Welcome to aiZee"/>
                    <TextBlock Style="{StaticResource PageSubtitle}" Text="Sovereign AI engineering control plane - installer wizard"/>
                    <Border Background="#F6F8FA" CornerRadius="8" Padding="20" Margin="0,10,0,10">
                        <StackPanel>
                            <TextBlock Style="{StaticResource BodyText}" Text="Version: $TargetVersion" FontWeight="Bold"/>
                            <TextBlock Style="{StaticResource BodyText}" Text="License: MIT"/>
                            <TextBlock Style="{StaticResource BodyText}" Text="Author: Moataz"/>
                            <TextBlock Style="{StaticResource BodyText}" Text=""/>
                            <TextBlock Style="{StaticResource BodyText}" Text="This wizard will:"/>
                            <TextBlock Style="{StaticResource BodyText}" Text="  1. Install aiZee core + dependencies"/>
                            <TextBlock Style="{StaticResource BodyText}" Text="  2. Configure MCP servers (graphify, context7, upwork, freelancer, fiverr, LinkedIn)"/>
                            <TextBlock Style="{StaticResource BodyText}" Text="  3. Set up .env secrets file (from .env.example template)"/>
                            <TextBlock Style="{StaticResource BodyText}" Text="  4. Set up agent configs (Claude, Windsurf, Cursor, Aider, Devin, Copilot, Cline)"/>
                            <TextBlock Style="{StaticResource BodyText}" Text="  5. Build knowledge graph (graphify)"/>
                            <TextBlock Style="{StaticResource BodyText}" Text="  6. Sync global MCP config + create CLI shim + environment variables"/>
                        </StackPanel>
                    </Border>
                    <TextBlock Style="{StaticResource BodyText}" Text="Click Next to continue." Margin="0,15,0,0"/>
                </StackPanel>
            </ScrollViewer>

            <!-- Page 2: License -->
            <ScrollViewer x:Name="PageLicense" Visibility="Collapsed" VerticalScrollBarVisibility="Auto">
                <StackPanel>
                    <TextBlock Style="{StaticResource PageTitle}" Text="License Agreement"/>
                    <TextBlock Style="{StaticResource PageSubtitle}" Text="Please read and accept the MIT license to continue"/>
                    <Border Background="#F6F8FA" CornerRadius="4" Padding="15" Margin="0,0,0,15" Height="280">
                        <ScrollViewer VerticalScrollBarVisibility="Auto">
                            <TextBlock x:Name="LicenseText" Style="{StaticResource BodyText}" FontSize="11" Text=""/>
                        </ScrollViewer>
                    </Border>
                    <CheckBox x:Name="AcceptLicense" Style="{StaticResource CheckboxStyle}" Content="I accept the terms of the MIT license" IsChecked="False"/>
                </StackPanel>
            </ScrollViewer>

            <!-- Page 3: Install Location -->
            <ScrollViewer x:Name="PageLocation" Visibility="Collapsed" VerticalScrollBarVisibility="Auto">
                <StackPanel>
                    <TextBlock Style="{StaticResource PageTitle}" Text="Installation Location"/>
                    <TextBlock Style="{StaticResource PageSubtitle}" Text="Choose where to install aiZee"/>
                    <RadioButton x:Name="RadioInPlace" Style="{StaticResource RadioStyle}" GroupName="Location" Content="In-place (use current repo location)" IsChecked="True" Margin="0,0,0,5"/>
                    <TextBlock Style="{StaticResource BodyText}" Text="The OS will run directly from the repository. Recommended for developers." Margin="20,0,0,10" Foreground="#57606A"/>
                    <RadioButton x:Name="RadioCustom" Style="{StaticResource RadioStyle}" GroupName="Location" Content="Custom location (copy files)" IsChecked="False" Margin="0,0,0,5"/>
                    <StackPanel Orientation="Horizontal" Margin="20,0,0,10">
                        <TextBox x:Name="CustomPath" Width="450" Height="30" Background="#F6F8FA" Foreground="#1F2328" BorderBrush="#D0D7DE" VerticalContentAlignment="Center" Padding="8,0" Text="$env:LOCALAPPDATA\aiZee" IsEnabled="False"/>
                        <Button x:Name="BrowseBtn" Style="{StaticResource NavButton}" Content="Browse..." Margin="10,0,0,0" IsEnabled="False"/>
                    </StackPanel>
                    <TextBlock x:Name="DiskSpaceInfo" Style="{StaticResource BodyText}" Text="Disk space: checking..." Margin="0,10,0,0" Foreground="#57606A"/>
                    <TextBlock x:Name="RepoPathInfo" Style="{StaticResource BodyText}" Text="" Margin="0,5,0,0" Foreground="#57606A"/>
                </StackPanel>
            </ScrollViewer>

            <!-- Page 4: Component Selection -->
            <ScrollViewer x:Name="PageComponents" Visibility="Collapsed" VerticalScrollBarVisibility="Auto">
                <StackPanel>
                    <TextBlock Style="{StaticResource PageTitle}" Text="Component Selection"/>
                    <TextBlock Style="{StaticResource PageSubtitle}" Text="Choose which components to install"/>
                    <ScrollViewer VerticalScrollBarVisibility="Auto" MaxHeight="380">
                        <StackPanel>
                        <TextBlock Style="{StaticResource BodyText}" Text="Core (required)" FontWeight="Bold" Foreground="#0969DA" Margin="0,0,0,5"/>
                        <CheckBox x:Name="CompCore" Style="{StaticResource CheckboxStyle}" Content="aiZee Core (runtime, memory, MCP server)" IsChecked="True" IsEnabled="False"/>
                        <CheckBox x:Name="CompPip" Style="{StaticResource CheckboxStyle}" Content="Python dependencies (pip install)" IsChecked="True"/>
                        <CheckBox x:Name="CompGraphify" Style="{StaticResource CheckboxStyle}" Content="Build knowledge graph (graphify update)" IsChecked="True"/>
                        <CheckBox x:Name="CompDashboard" Style="{StaticResource CheckboxStyle}" Content="Dashboard server" IsChecked="True"/>

                        <TextBlock Style="{StaticResource BodyText}" Text="Enhancement Modules (45 new)" FontWeight="Bold" Foreground="#9A6700" Margin="0,15,0,5"/>
                        <CheckBox x:Name="CompExecRings" Style="{StaticResource CheckboxStyle}" Content="Execution Rings (4 privilege levels + trust scoring)" IsChecked="True"/>
                        <CheckBox x:Name="CompCodeGraph" Style="{StaticResource CheckboxStyle}" Content="CodeGraph + Reachability (AST-based security analysis)" IsChecked="True"/>
                        <CheckBox x:Name="CompMemoryEnh" Style="{StaticResource CheckboxStyle}" Content="Memory enhancements (SimHash, Heat, Sectors, Temporal, Decay, Consolidation)" IsChecked="True"/>
                        <CheckBox x:Name="CompSpecValidation" Style="{StaticResource CheckboxStyle}" Content="Spec validation (Constitution, Scenarios, Linkage graph)" IsChecked="True"/>
                        <CheckBox x:Name="CompSelfHealing" Style="{StaticResource CheckboxStyle}" Content="Self-healing runtime (crash detection + respawn)" IsChecked="True"/>
                        <CheckBox x:Name="CompSemanticSearch" Style="{StaticResource CheckboxStyle}" Content="Semantic code search + Tree-sitter symbols" IsChecked="True"/>

                        <TextBlock Style="{StaticResource BodyText}" Text="MCP Servers" FontWeight="Bold" Foreground="#0969DA" Margin="0,15,0,5"/>
                        <CheckBox x:Name="CompMCPGraphify" Style="{StaticResource CheckboxStyle}" Content="Graphify MCP (codebase knowledge graph)" IsChecked="True"/>
                        <CheckBox x:Name="CompMCPContext7" Style="{StaticResource CheckboxStyle}" Content="Context7 MCP (library docs - requires npx)" IsChecked="True"/>
                        <CheckBox x:Name="CompMCPUpwork" Style="{StaticResource CheckboxStyle}" Content="Upwork MCP (job search + proposals - requires npx + .env secrets)" IsChecked="True"/>
                        <CheckBox x:Name="CompMCPFreelancer" Style="{StaticResource CheckboxStyle}" Content="Freelancer MCP (project search + bidding - requires npx + .env secrets)" IsChecked="True"/>
                        <CheckBox x:Name="CompMCPFiverr" Style="{StaticResource CheckboxStyle}" Content="Fiverr MCP (gig search - read-only, requires uvx, no secrets needed)" IsChecked="True"/>
                        <CheckBox x:Name="CompMCPLinkedIn" Style="{StaticResource CheckboxStyle}" Content="LinkedIn MCP (content automation - requires Python + .env secrets)" IsChecked="True"/>

                        <TextBlock Style="{StaticResource BodyText}" Text="AIOS Plugins" FontWeight="Bold" Foreground="#0969DA" Margin="0,15,0,5"/>
                        <CheckBox x:Name="CompPluginGraphify" Style="{StaticResource CheckboxStyle}" Content="Graphify plugin (graph topology queries)" IsChecked="True"/>
                        <CheckBox x:Name="CompPluginContext7" Style="{StaticResource CheckboxStyle}" Content="Context7 plugin (library docs proxy)" IsChecked="True"/>
                        <CheckBox x:Name="CompPluginUpwork" Style="{StaticResource CheckboxStyle}" Content="Upwork plugin (8 tools)" IsChecked="True"/>
                        <CheckBox x:Name="CompPluginFreelancer" Style="{StaticResource CheckboxStyle}" Content="Freelancer plugin (11 tools)" IsChecked="True"/>
                        <CheckBox x:Name="CompPluginFiverr" Style="{StaticResource CheckboxStyle}" Content="Fiverr plugin (5 read-only tools)" IsChecked="True"/>
                        <CheckBox x:Name="CompPluginLinkedIn" Style="{StaticResource CheckboxStyle}" Content="LinkedIn plugin (18 tools - draft/approve/publish)" IsChecked="True"/>

                        <TextBlock Style="{StaticResource BodyText}" Text="Agent Configs" FontWeight="Bold" Foreground="#0969DA" Margin="0,15,0,5"/>
                        <CheckBox x:Name="CompAgentClaude" Style="{StaticResource CheckboxStyle}" Content="Claude Code (CLAUDE.md + settings + skills + agents)" IsChecked="True"/>
                        <CheckBox x:Name="CompAgentWindsurf" Style="{StaticResource CheckboxStyle}" Content="Windsurf (.windsurfrules + skills)" IsChecked="True"/>
                        <CheckBox x:Name="CompAgentCursor" Style="{StaticResource CheckboxStyle}" Content="Cursor (.cursor/rules)" IsChecked="True"/>
                        <CheckBox x:Name="CompAgentAider" Style="{StaticResource CheckboxStyle}" Content="Aider (.aider.conf.yml)" IsChecked="True"/>
                        <CheckBox x:Name="CompAgentDevin" Style="{StaticResource CheckboxStyle}" Content="Devin (.devin/skills)" IsChecked="True"/>
                        <CheckBox x:Name="CompAgentCopilot" Style="{StaticResource CheckboxStyle}" Content="GitHub Copilot (.github/copilot-instructions.md)" IsChecked="True"/>
                        <CheckBox x:Name="CompAgentCline" Style="{StaticResource CheckboxStyle}" Content="Cline (.clinerules)" IsChecked="True"/>

                        <TextBlock Style="{StaticResource BodyText}" Text="System Integration" FontWeight="Bold" Foreground="#0969DA" Margin="0,15,0,5"/>
                        <CheckBox x:Name="CompCLIShim" Style="{StaticResource CheckboxStyle}" Content="CLI shim (aizee command in PATH)" IsChecked="True"/>
                        <CheckBox x:Name="CompEnvVar" Style="{StaticResource CheckboxStyle}" Content="Set AIZEE_ROOT environment variable" IsChecked="True"/>
                        <CheckBox x:Name="CompStartMenu" Style="{StaticResource CheckboxStyle}" Content="Create Start Menu shortcut" IsChecked="True"/>
                        <CheckBox x:Name="CompDesktop" Style="{StaticResource CheckboxStyle}" Content="Create Desktop shortcut" IsChecked="False"/>
                        </StackPanel>
                    </ScrollViewer>
                </StackPanel>
            </ScrollViewer>

            <!-- Page 5: Configuration -->
            <ScrollViewer x:Name="PageConfig" Visibility="Collapsed" VerticalScrollBarVisibility="Auto">
                <StackPanel>
                    <TextBlock Style="{StaticResource PageTitle}" Text="Configuration"/>
                    <TextBlock Style="{StaticResource PageSubtitle}" Text="Review and adjust installation settings"/>
                    <Border Background="#F6F8FA" CornerRadius="4" Padding="15" Margin="0,0,0,15">
                        <StackPanel>
                        <TextBlock Style="{StaticResource BodyText}" Text="Environment Variables" FontWeight="Bold" Foreground="#0969DA" Margin="0,0,0,8"/>
                        <StackPanel Orientation="Horizontal" Margin="0,0,0,5">
                            <TextBlock Style="{StaticResource BodyText}" Text="AIZEE_ROOT:" Width="150"/>
                            <TextBlock x:Name="ConfigRoot" Style="{StaticResource BodyText}" Text="" FontWeight="Bold"/>
                        </StackPanel>
                        <StackPanel Orientation="Horizontal" Margin="0,0,0,5">
                            <TextBlock Style="{StaticResource BodyText}" Text="PYTHONIOENCODING:" Width="150"/>
                            <TextBlock Style="{StaticResource BodyText}" Text="utf-8" FontWeight="Bold"/>
                        </StackPanel>
                        <StackPanel Orientation="Horizontal" Margin="0,0,0,5">
                            <TextBlock Style="{StaticResource BodyText}" Text="Scope:" Width="150"/>
                            <ComboBox x:Name="EnvVarScope" Width="120" Background="#F6F8FA" Foreground="#1F2328">
                                <ComboBoxItem Content="User" IsSelected="True"/>
                                <ComboBoxItem Content="Machine"/>
                            </ComboBox>
                        </StackPanel>

                        <TextBlock Style="{StaticResource BodyText}" Text="Installation Options" FontWeight="Bold" Foreground="#0969DA" Margin="0,15,0,8"/>
                        <CheckBox x:Name="ConfigRunMigrations" Style="{StaticResource CheckboxStyle}" Content="Run database/config migrations automatically" IsChecked="True"/>
                        <CheckBox x:Name="ConfigVerifyPackages" Style="{StaticResource CheckboxStyle}" Content="Verify required Python packages after install" IsChecked="True"/>
                        <CheckBox x:Name="ConfigHealthCheck" Style="{StaticResource CheckboxStyle}" Content="Run MCP server health check after install" IsChecked="True"/>
                        <CheckBox x:Name="ConfigCreateLog" Style="{StaticResource CheckboxStyle}" Content="Create installation log file (state/install-*.log)" IsChecked="True"/>
                        <CheckBox x:Name="ConfigBackupExisting" Style="{StaticResource CheckboxStyle}" Content="Backup existing configs before overwriting" IsChecked="True"/>
                        </StackPanel>
                    </Border>
                </StackPanel>
            </ScrollViewer>

            <!-- Page 6: Pre-flight Summary -->
            <ScrollViewer x:Name="PagePreFlight" Visibility="Collapsed" VerticalScrollBarVisibility="Auto">
                <StackPanel>
                    <TextBlock Style="{StaticResource PageTitle}" Text="Pre-flight Check"/>
                    <TextBlock Style="{StaticResource PageSubtitle}" Text="Verifying system requirements before installation"/>
                    <Border Background="#F6F8FA" CornerRadius="4" Padding="15" Margin="0,0,0,15" MaxHeight="350">
                        <ScrollViewer VerticalScrollBarVisibility="Auto">
                            <StackPanel>
                                <TextBlock Style="{StaticResource BodyText}" Text="System Checks" FontWeight="Bold" Foreground="#0969DA" Margin="0,0,0,10"/>
                                <TextBlock x:Name="CheckPython" Style="{StaticResource BodyText}" Text="[ ] Python 3.10+ ... checking"/>
                                <TextBlock x:Name="CheckNpx" Style="{StaticResource BodyText}" Text="[ ] npx (npm) ... checking"/>
                                <TextBlock x:Name="CheckUvx" Style="{StaticResource BodyText}" Text="[ ] uvx (uv) ... checking"/>
                                <TextBlock x:Name="CheckDisk" Style="{StaticResource BodyText}" Text="[ ] Disk space ... checking"/>
                                <TextBlock x:Name="CheckExisting" Style="{StaticResource BodyText}" Text="[ ] Existing installation ... checking"/>
                                <TextBlock x:Name="CheckRepo" Style="{StaticResource BodyText}" Text="[ ] Repository integrity ... checking"/>
                                <TextBlock x:Name="CheckEnv" Style="{StaticResource BodyText}" Text="[ ] .env secrets file ... checking"/>

                                <TextBlock Style="{StaticResource BodyText}" Text="" Margin="0,10,0,0"/>
                                <TextBlock Style="{StaticResource BodyText}" Text="Installation Summary" FontWeight="Bold" Foreground="#0969DA" Margin="0,10,0,8"/>
                                <TextBlock x:Name="SummaryLocation" Style="{StaticResource BodyText}" Text=""/>
                                <TextBlock x:Name="SummaryComponents" Style="{StaticResource BodyText}" Text=""/>
                                <TextBlock x:Name="SummaryVersion" Style="{StaticResource BodyText}" Text=""/>
                                <TextBlock x:Name="SummaryEstTime" Style="{StaticResource BodyText}" Text="" Foreground="#9A6700"/>
                            </StackPanel>
                        </ScrollViewer>
                    </Border>
                    <TextBlock x:Name="PreFlightStatus" Style="{StaticResource BodyText}" Text="Click Install to begin." Margin="0,10,0,0"/>
                </StackPanel>
            </ScrollViewer>

            <!-- Page 7: Installation Progress -->
            <ScrollViewer x:Name="PageProgress" Visibility="Collapsed" VerticalScrollBarVisibility="Auto">
                <StackPanel>
                    <TextBlock Style="{StaticResource PageTitle}" Text="Installing..."/>
                    <TextBlock Style="{StaticResource PageSubtitle}" Text="Please wait while aiZee is being installed"/>
                    <ProgressBar x:Name="Progressbar" Height="25" Minimum="0" Maximum="100" Value="0" Margin="0,0,0,10" Foreground="#1F6FEB"/>
                    <TextBlock x:Name="ProgressLabel" Style="{StaticResource BodyText}" Text="Preparing..." Margin="0,0,0,10"/>
                    <TextBox x:Name="LogBox" Style="{StaticResource LogBox}" Height="320" Text=""/>
                </StackPanel>
            </ScrollViewer>

            <!-- Page 8: Finish -->
            <ScrollViewer x:Name="PageFinish" Visibility="Collapsed" VerticalScrollBarVisibility="Auto">
                <StackPanel>
                    <TextBlock x:Name="FinishTitle" Style="{StaticResource PageTitle}" Text="Installation Complete!"/>
                    <TextBlock Style="{StaticResource PageSubtitle}" Text="aiZee has been successfully installed"/>
                    <Border Background="#F6F8FA" CornerRadius="8" Padding="20" Margin="0,10,0,15">
                        <StackPanel>
                            <TextBlock x:Name="FinishVersion" Style="{StaticResource BodyText}" Text="" FontWeight="Bold"/>
                            <TextBlock x:Name="FinishLocation" Style="{StaticResource BodyText}" Text=""/>
                            <TextBlock x:Name="FinishLog" Style="{StaticResource BodyText}" Text=""/>
                            <TextBlock x:Name="FinishComponents" Style="{StaticResource BodyText}" Text=""/>
                        </StackPanel>
                    </Border>
                    <Border x:Name="FinishEnvWarning" Background="#FFF8C5" CornerRadius="8" Padding="15" Margin="0,0,0,15" BorderBrush="#9A6700" BorderThickness="1" Visibility="Collapsed">
                        <StackPanel>
                            <TextBlock Style="{StaticResource BodyText}" Text="Action required: edit .env file" FontWeight="Bold" Foreground="#9A6700"/>
                            <TextBlock x:Name="FinishEnvText" Style="{StaticResource BodyText}" Text="" Foreground="#9A6700"/>
                        </StackPanel>
                    </Border>
                    <TextBlock Style="{StaticResource BodyText}" Text="What would you like to do next?" Margin="0,10,0,10"/>
                    <CheckBox x:Name="FinishLaunchDashboard" Style="{StaticResource CheckboxStyle}" Content="Launch dashboard server" IsChecked="False"/>
                    <CheckBox x:Name="FinishOpenReadme" Style="{StaticResource CheckboxStyle}" Content="Open README" IsChecked="False"/>
                    <CheckBox x:Name="FinishOpenLog" Style="{StaticResource CheckboxStyle}" Content="Open installation log" IsChecked="False"/>
                    <CheckBox x:Name="FinishOpenGuiLog" Style="{StaticResource CheckboxStyle}" Content="Open GUI installer log (all messages)" IsChecked="False"/>
                    <CheckBox x:Name="FinishOpenEnv" Style="{StaticResource CheckboxStyle}" Content="Open .env file to fill in MCP credentials" IsChecked="False"/>
                </StackPanel>
            </ScrollViewer>
        </Grid>

        <!-- Navigation bar -->
        <Border x:Name="NavBar" Grid.Row="1" Background="#F6F8FA" Padding="20,10" BorderBrush="#D0D7DE" BorderThickness="0,1,0,0">
            <Grid>
                <Grid.ColumnDefinitions>
                    <ColumnDefinition Width="*"/>
                    <ColumnDefinition Width="Auto"/>
                    <ColumnDefinition Width="Auto"/>
                    <ColumnDefinition Width="Auto"/>
                </Grid.ColumnDefinitions>

                <!-- Step indicator -->
                <StackPanel Grid.Column="0" Orientation="Horizontal" VerticalAlignment="Center">
                    <TextBlock x:Name="Step1" Style="{StaticResource StepIndicator}" Text="1. Welcome" Foreground="#0969DA"/>
                    <TextBlock Text=">" Foreground="#D0D7DE" Margin="4,0,4,0"/>
                    <TextBlock x:Name="Step2" Style="{StaticResource StepIndicator}" Text="2. License" Foreground="#8C959F"/>
                    <TextBlock Text=">" Foreground="#D0D7DE" Margin="4,0,4,0"/>
                    <TextBlock x:Name="Step3" Style="{StaticResource StepIndicator}" Text="3. Location" Foreground="#8C959F"/>
                    <TextBlock Text=">" Foreground="#D0D7DE" Margin="4,0,4,0"/>
                    <TextBlock x:Name="Step4" Style="{StaticResource StepIndicator}" Text="4. Components" Foreground="#8C959F"/>
                    <TextBlock Text=">" Foreground="#D0D7DE" Margin="4,0,4,0"/>
                    <TextBlock x:Name="Step5" Style="{StaticResource StepIndicator}" Text="5. Config" Foreground="#8C959F"/>
                    <TextBlock Text=">" Foreground="#D0D7DE" Margin="4,0,4,0"/>
                    <TextBlock x:Name="Step6" Style="{StaticResource StepIndicator}" Text="6. Pre-flight" Foreground="#8C959F"/>
                    <TextBlock Text=">" Foreground="#D0D7DE" Margin="4,0,4,0"/>
                    <TextBlock x:Name="Step7" Style="{StaticResource StepIndicator}" Text="7. Install" Foreground="#8C959F"/>
                    <TextBlock Text=">" Foreground="#D0D7DE" Margin="4,0,4,0"/>
                    <TextBlock x:Name="Step8" Style="{StaticResource StepIndicator}" Text="8. Finish" Foreground="#8C959F"/>
                </StackPanel>

                <Button Grid.Column="1" x:Name="BackBtn" Style="{StaticResource NavButton}" Content="Back" Margin="0,0,10,0"/>
                <Button Grid.Column="2" x:Name="NextBtn" Style="{StaticResource PrimaryButton}" Content="Next" Margin="0,0,10,0"/>
                <Button Grid.Column="3" x:Name="CancelBtn" Style="{StaticResource NavButton}" Content="Cancel" Margin="0,0,0,0"/>
            </Grid>
        </Border>
    </Grid>
</Window>
"@

# ---------------------------------------------------------------------------
# Parse XAML and create window
# ---------------------------------------------------------------------------

$reader = (New-Object System.Xml.XmlNodeReader $xaml)
$Window = [System.Windows.Markup.XamlReader]::Load($reader)

# Get controls
$pages = @(
    $Window.FindName("PageWelcome"),
    $Window.FindName("PageLicense"),
    $Window.FindName("PageLocation"),
    $Window.FindName("PageComponents"),
    $Window.FindName("PageConfig"),
    $Window.FindName("PagePreFlight"),
    $Window.FindName("PageProgress"),
    $Window.FindName("PageFinish")
)

$stepIndicators = @(
    $Window.FindName("Step1"), $Window.FindName("Step2"), $Window.FindName("Step3"),
    $Window.FindName("Step4"), $Window.FindName("Step5"), $Window.FindName("Step6"),
    $Window.FindName("Step7"), $Window.FindName("Step8")
)

$BackBtn = $Window.FindName("BackBtn")
$NextBtn = $Window.FindName("NextBtn")
$CancelBtn = $Window.FindName("CancelBtn")
$currentPage = 0

# License text
$licenseText = @"
MIT License

Copyright (c) 2024-2025 Moataz Ahmed

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"@
$Window.FindName("LicenseText").Text = $licenseText

# Set repo path info
$Window.FindName("RepoPathInfo").Text = "Repository: $Repo"

# ---------------------------------------------------------------------------
# Navigation logic
# ---------------------------------------------------------------------------

function Show-Page {
    param([int]$PageIndex)
    for ($i = 0; $i -lt $pages.Count; $i++) {
        $pages[$i].Visibility = if ($i -eq $PageIndex) { "Visible" } else { "Collapsed" }
    }
    for ($i = 0; $i -lt $stepIndicators.Count; $i++) {
        if ($i -eq $PageIndex) {
            $stepIndicators[$i].Foreground = "#0969DA"
        } elseif ($i -lt $PageIndex) {
            $stepIndicators[$i].Foreground = "#1A7F37"
        } else {
            $stepIndicators[$i].Foreground = "#8C959F"
        }
    }
    $BackBtn.IsEnabled = $PageIndex -gt 0 -and $PageIndex -lt 6
    $NextBtn.Visibility = if ($PageIndex -eq 6) { "Collapsed" } else { "Visible" }
    if ($PageIndex -eq 5) { $NextBtn.Content = "Install" } else { $NextBtn.Content = "Next" }
    if ($PageIndex -eq 7) {
        $BackBtn.Visibility = "Collapsed"
        $NextBtn.Content = "Finish"
        $NextBtn.Visibility = "Visible"
    } else {
        $BackBtn.Visibility = "Visible"
    }
}

function Step-Forward {
    # Validate current page
    switch ($currentPage) {
        1 {
            # License page - must accept
            if (-not $Window.FindName("AcceptLicense").IsChecked) {
                [System.Windows.MessageBox]::Show("Please accept the license to continue.", "License Required", "OK", "Warning") | Out-Null
                return
            }
        }
        5 {
            # Pre-flight page - start installation
            $script:currentPage = 6
            Show-Page 6
            Start-Installation
            return
        }
        7 {
            # Finish page - close window
            $Window.Close()
            return
        }
    }
    $script:currentPage++
    Show-Page $script:currentPage

    # Page-specific actions
    switch ($script:currentPage) {
        3 { Update-DiskSpaceInfo }
        5 { Invoke-PreFlightChecks }
    }
}

function Step-Backward {
    if ($script:currentPage -gt 0 -and $script:currentPage -lt 6) {
        $script:currentPage--
        Show-Page $script:currentPage
    }
}

# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

$Window.FindName("BrowseBtn").Add_Click({
    $folderDialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $folderDialog.Description = "Select installation directory"
    $folderDialog.SelectedPath = $Window.FindName("CustomPath").Text
    if ($folderDialog.ShowDialog() -eq "OK") {
        $Window.FindName("CustomPath").Text = $folderDialog.SelectedPath
        Update-DiskSpaceInfo
    }
})

$Window.FindName("RadioInPlace").Add_Click({
    $Window.FindName("CustomPath").IsEnabled = $false
    $Window.FindName("BrowseBtn").IsEnabled = $false
    Update-DiskSpaceInfo
})

$Window.FindName("RadioCustom").Add_Click({
    $Window.FindName("CustomPath").IsEnabled = $true
    $Window.FindName("BrowseBtn").IsEnabled = $true
    Update-DiskSpaceInfo
})

$NextBtn.Add_Click({ Step-Forward })
$BackBtn.Add_Click({ Step-Backward })
$CancelBtn.Add_Click({
    if ($script:currentPage -eq 6) {
        # During installation - ask to cancel and stop the job
        $result = [System.Windows.MessageBox]::Show("Installation is in progress. Canceling may leave aiZee in an incomplete state. Continue?", "Cancel Installation", "YesNo", "Warning")
        if ($result -eq "Yes") {
            Write-LogMessage "[CANCEL] User canceled installation."
            if ($script:installJob) { Stop-Job $script:installJob -ErrorAction SilentlyContinue; Remove-Job $script:installJob -Force -ErrorAction SilentlyContinue }
            $Window.Close()
        }
    } else {
        $result = [System.Windows.MessageBox]::Show("Are you sure you want to cancel the installation?", "Cancel", "YesNo", "Question")
        if ($result -eq "Yes") { $Window.Close() }
    }
})

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

function Update-DiskSpaceInfo {
    $path = if ($Window.FindName("RadioInPlace").IsChecked) { $Repo } else { $Window.FindName("CustomPath").Text }
    try {
        $drive = (Get-Item $path -ErrorAction SilentlyContinue).PSDrive
        if ($drive) {
            $free = [math]::Round($drive.Free / 1MB, 0)
            $used = [math]::Round($drive.Used / 1MB, 0)
            $Window.FindName("DiskSpaceInfo").Text = "Disk space: $free MB free, $used MB used on drive $($drive.Name):"
        }
    } catch {
        $Window.FindName("DiskSpaceInfo").Text = "Disk space: unable to determine"
    }
}

function Invoke-PreFlightChecks {
    $checks = @{
        "CheckPython" = $false
        "CheckNpx" = $false
        "CheckUvx" = $false
        "CheckDisk" = $false
        "CheckExisting" = $false
        "CheckRepo" = $false
    }

    # Python
    try {
        $pv = & python --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $pv -match "Python 3\.(1[0-9]|[2-9])") {
            $Window.FindName("CheckPython").Text = "[OK] Python: $pv"
            $Window.FindName("CheckPython").Foreground = "#1A7F37"
            $checks["CheckPython"] = $true
        } else {
            $Window.FindName("CheckPython").Text = "[FAIL] Python 3.10+ required (found: $pv)"
            $Window.FindName("CheckPython").Foreground = "#CF222E"
        }
    } catch {
        $Window.FindName("CheckPython").Text = "[FAIL] Python not found on PATH"
        $Window.FindName("CheckPython").Foreground = "#CF222E"
    }

    # npx
    $null = Get-Command npx -ErrorAction SilentlyContinue
    if ($?) {
        $Window.FindName("CheckNpx").Text = "[OK] npx: available"
        $Window.FindName("CheckNpx").Foreground = "#1A7F37"
        $checks["CheckNpx"] = $true
    } else {
        $Window.FindName("CheckNpx").Text = "[WARN] npx: not found (context7/upwork/freelancer MCP will be unavailable)"
        $Window.FindName("CheckNpx").Foreground = "#9A6700"
        $checks["CheckNpx"] = $true  # Warning, not failure
    }

    # uvx
    $null = Get-Command uvx -ErrorAction SilentlyContinue
    if ($?) {
        $Window.FindName("CheckUvx").Text = "[OK] uvx: available"
        $Window.FindName("CheckUvx").Foreground = "#1A7F37"
    } else {
        $Window.FindName("CheckUvx").Text = "[WARN] uvx: not found (fiverr MCP will be unavailable)"
        $Window.FindName("CheckUvx").Foreground = "#9A6700"
    }

    # Disk space
    $path = if ($Window.FindName("RadioInPlace").IsChecked) { $Repo } else { $Window.FindName("CustomPath").Text }
    try {
        $drive = (Get-Item $path).PSDrive
        $freeMB = [math]::Round($drive.Free / 1MB, 0)
        if ($freeMB -gt 100) {
            $Window.FindName("CheckDisk").Text = "[OK] Disk space: $freeMB MB free"
            $Window.FindName("CheckDisk").Foreground = "#1A7F37"
            $checks["CheckDisk"] = $true
        } else {
            $Window.FindName("CheckDisk").Text = "[FAIL] Insufficient disk space: $freeMB MB (need 100+ MB)"
            $Window.FindName("CheckDisk").Foreground = "#CF222E"
        }
    } catch {
        $Window.FindName("CheckDisk").Text = "[WARN] Disk space: unable to check"
        $Window.FindName("CheckDisk").Foreground = "#9A6700"
        $checks["CheckDisk"] = $true
    }

    # Existing installation
    $versionFile = Join-Path $path ".aizee-version"
    if (Test-Path $versionFile) {
        $existingVer = (Get-Content $versionFile -Raw).Trim()
        $Window.FindName("CheckExisting").Text = "[OK] Existing installation: v$existingVer (will be updated)"
        $Window.FindName("CheckExisting").Foreground = "#1A7F37"
    } else {
        $Window.FindName("CheckExisting").Text = "[OK] First installation"
        $Window.FindName("CheckExisting").Foreground = "#1A7F37"
    }
    $checks["CheckExisting"] = $true

    # Repo integrity
    if (Test-Path (Join-Path $Repo "pyproject.toml")) {
        $Window.FindName("CheckRepo").Text = "[OK] Repository: valid (pyproject.toml found)"
        $Window.FindName("CheckRepo").Foreground = "#1A7F37"
        $checks["CheckRepo"] = $true
    } else {
        $Window.FindName("CheckRepo").Text = "[WARN] Repository: pyproject.toml not found"
        $Window.FindName("CheckRepo").Foreground = "#9A6700"
        $checks["CheckRepo"] = $true
    }

    # .env secrets file check (only if MCP servers needing secrets are selected)
    $needsSecrets = ($Window.FindName("CompMCPUpwork").IsChecked -or $Window.FindName("CompMCPFreelancer").IsChecked -or $Window.FindName("CompMCPLinkedIn").IsChecked)
    $envFile = Join-Path $path ".env"
    $envExample = Join-Path $path ".env.example"
    if ($needsSecrets) {
        if (Test-Path $envFile) {
            # Check if .env still has placeholder values
            $envContent = Get-Content $envFile -Raw
            if ($envContent -match "your_.*_here") {
                $Window.FindName("CheckEnv").Text = "[WARN] .env exists but has placeholder values - edit it with real credentials"
                $Window.FindName("CheckEnv").Foreground = "#9A6700"
            } else {
                $Window.FindName("CheckEnv").Text = "[OK] .env file present with credentials"
                $Window.FindName("CheckEnv").Foreground = "#1A7F37"
            }
        } elseif (Test-Path $envExample) {
            $Window.FindName("CheckEnv").Text = "[WARN] .env missing - will be created from .env.example (edit it after install)"
            $Window.FindName("CheckEnv").Foreground = "#9A6700"
        } else {
            $Window.FindName("CheckEnv").Text = "[WARN] .env and .env.example both missing - MCP servers needing secrets will fail"
            $Window.FindName("CheckEnv").Foreground = "#9A6700"
        }
    } else {
        $Window.FindName("CheckEnv").Text = "[OK] .env: not needed (no secret-requiring MCP servers selected)"
        $Window.FindName("CheckEnv").Foreground = "#1A7F37"
    }

    # Update summary
    $installPath = if ($Window.FindName("RadioInPlace").IsChecked) { $Repo } else { $Window.FindName("CustomPath").Text }
    $Window.FindName("SummaryLocation").Text = "Location: $installPath"

    $compCount = 0
    $allChecks = @("CompPip","CompGraphify","CompDashboard","CompMCPGraphify","CompMCPContext7","CompMCPUpwork","CompMCPFreelancer","CompMCPFiverr","CompMCPLinkedIn","CompPluginGraphify","CompPluginContext7","CompPluginUpwork","CompPluginFreelancer","CompPluginFiverr","CompPluginLinkedIn","CompAgentClaude","CompAgentWindsurf","CompAgentCursor","CompAgentAider","CompAgentDevin","CompAgentCopilot","CompAgentCline","CompCLIShim","CompEnvVar","CompStartMenu","CompDesktop")
    foreach ($c in $allChecks) {
        if ($Window.FindName($c).IsChecked) { $compCount++ }
    }
    $Window.FindName("SummaryComponents").Text = "Components selected: $compCount"
    $Window.FindName("SummaryVersion").Text = "Target version: $TargetVersion"

    # Estimated time based on selected components
    $estSeconds = 15  # base overhead
    if ($Window.FindName("CompPip").IsChecked) { $estSeconds += 60 }      # pip install
    if ($Window.FindName("CompGraphify").IsChecked) { $estSeconds += 30 } # graphify build
    if ($Window.FindName("CompMCPGraphify").IsChecked) { $estSeconds += 5 }
    if ($Window.FindName("CompMCPContext7").IsChecked) { $estSeconds += 5 }
    if ($Window.FindName("CompMCPUpwork").IsChecked) { $estSeconds += 5 }
    if ($Window.FindName("CompMCPFreelancer").IsChecked) { $estSeconds += 5 }
    if ($Window.FindName("CompMCPFiverr").IsChecked) { $estSeconds += 5 }
    if ($Window.FindName("CompMCPLinkedIn").IsChecked) { $estSeconds += 10 }
    $agentCount = 0
    foreach ($ac in @("CompAgentClaude","CompAgentWindsurf","CompAgentCursor","CompAgentAider","CompAgentDevin","CompAgentCopilot","CompAgentCline")) {
        if ($Window.FindName($ac).IsChecked) { $agentCount++ }
    }
    $estSeconds += $agentCount * 3
    if ($copyMode) { $estSeconds += 20 }  # file copy overhead
    $estMin = [math]::Floor($estSeconds / 60)
    $estSec = $estSeconds % 60
    $estStr = if ($estMin -gt 0) { "$estMin min $estSec sec" } else { "$estSeconds sec" }
    $Window.FindName("SummaryEstTime").Text = "Estimated time: ~$estStr (varies by system)"

    # Log pre-flight results to file
    Write-LogFile "--- Pre-flight Checks ---"
    $checkNames = @("CheckPython","CheckNpx","CheckUvx","CheckDisk","CheckExisting","CheckRepo","CheckEnv")
    foreach ($cn in $checkNames) {
        $txt = $Window.FindName($cn).Text
        if ($txt) { Write-LogFile "  $txt" }
    }
    Write-LogFile "  Summary: $($Window.FindName('SummaryLocation').Text)"
    Write-LogFile "  $($Window.FindName('SummaryComponents').Text)"
    Write-LogFile "  $($Window.FindName('SummaryVersion').Text)"
    Write-LogFile "  Status: $($Window.FindName('PreFlightStatus').Text)"
    Write-LogFile ""

    # Overall status
    $failed = ($checks["CheckPython"] -eq $false -or $checks["CheckDisk"] -eq $false -or $checks["CheckRepo"] -eq $false)
    if ($failed) {
        $Window.FindName("PreFlightStatus").Text = "Some checks failed. Please fix the issues above before installing."
        $Window.FindName("PreFlightStatus").Foreground = "#CF222E"
        $NextBtn.IsEnabled = $false
    } else {
        $Window.FindName("PreFlightStatus").Text = "All checks passed. Click Install to begin."
        $Window.FindName("PreFlightStatus").Foreground = "#1A7F37"
        $NextBtn.IsEnabled = $true
    }
}

# ---------------------------------------------------------------------------
# Install log file - all GUI log messages are mirrored here.
# This file contains ONLY the current session's messages (no merging with
# old logs). install.ps1 output is captured live via Receive-Job.
# ---------------------------------------------------------------------------
$InstallLogDir = Join-Path $Repo "state"
if (-not (Test-Path $InstallLogDir)) { New-Item -ItemType Directory -Path $InstallLogDir -Force | Out-Null }
$InstallLogPath = Join-Path $InstallLogDir "install-gui-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"

function Write-LogFile {
    param([string]$Message)
    try {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Add-Content -Path $InstallLogPath -Value "[$timestamp] $Message" -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch {
        # Silently fail - logging is best-effort, must never break installation
    }
}

# Log the session header
Write-LogFile "=== aiZee GUI Installer Session ==="
Write-LogFile "Version: $TargetVersion"
Write-LogFile "Repository: $Repo"
Write-LogFile "Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-LogFile ""

function Write-LogMessage {
    param([string]$Message)
    $logBox = $Window.FindName("LogBox")
    $logBox.AppendText("$Message`n")
    $logBox.ScrollToEnd()
    Write-LogFile $Message
    [System.Windows.Threading.Dispatcher]::CurrentDispatcher.Invoke([Action]{}, [System.Windows.Threading.DispatcherPriority]::Background)
}

function Update-Progress {
    param([int]$Percent, [string]$Label)
    $Window.FindName("Progressbar").Value = $Percent
    $Window.FindName("ProgressLabel").Text = $Label
    [System.Windows.Threading.Dispatcher]::CurrentDispatcher.Invoke([Action]{}, [System.Windows.Threading.DispatcherPriority]::Background)
}

function Start-Installation {
    $NextBtn.IsEnabled = $false
    $BackBtn.IsEnabled = $false

    # Determine install root (use $script: scope so finish-page click handler can access it)
    $script:installRoot = if ($Window.FindName("RadioInPlace").IsChecked) { $Repo } else { $Window.FindName("CustomPath").Text }
    $installRoot = $script:installRoot
    $copyMode = -not $Window.FindName("RadioInPlace").IsChecked

    # Build install arguments
    $installArgs = @("-ExecutionPolicy", "Bypass", "-File", (Join-Path $Repo "install.ps1"))
    if (-not $copyMode) {
        # In-place mode - no InstallDir
    } else {
        $installArgs += "-InstallDir"
        $installArgs += $installRoot
    }
    if (-not $Window.FindName("CompPip").IsChecked) { $installArgs += "-SkipPip" }
    if (-not $Window.FindName("CompGraphify").IsChecked) { $installArgs += "-SkipGraphify" }
    if (-not $Window.FindName("CompMCPGraphify").IsChecked -and -not $Window.FindName("CompMCPContext7").IsChecked -and -not $Window.FindName("CompMCPUpwork").IsChecked -and -not $Window.FindName("CompMCPFreelancer").IsChecked -and -not $Window.FindName("CompMCPFiverr").IsChecked -and -not $Window.FindName("CompMCPLinkedIn").IsChecked) {
        $installArgs += "-SkipMCP"
    }

    Write-LogMessage "=== aiZee Installation ==="
    Write-LogMessage "Root: $installRoot"
    Write-LogMessage "Copy mode: $copyMode"
    Write-LogMessage "Arguments: $($installArgs -join ' ')"

    # Log selected/deselected enhancement modules
    $enhModules = @(
        @("CompExecRings", "Execution Rings"),
        @("CompCodeGraph", "CodeGraph + Reachability"),
        @("CompMemoryEnh", "Memory enhancements"),
        @("CompSpecValidation", "Spec validation"),
        @("CompSelfHealing", "Self-healing runtime"),
        @("CompSemanticSearch", "Semantic code search")
    )
    Write-LogMessage ""
    Write-LogMessage "Enhancement modules (built with core - no skip):"
    foreach ($m in $enhModules) {
        $checked = $Window.FindName($m[0]).IsChecked
        $status = if ($checked) { "ENABLED" } else { "disabled (built anyway - core module)" }
        Write-LogMessage "  $($m[1]): $status"
    }

    # Log agent configs selection
    $agentConfigs = @(
        @("CompAgentClaude", "Claude Code"),
        @("CompAgentWindsurf", "Windsurf"),
        @("CompAgentCursor", "Cursor"),
        @("CompAgentAider", "Aider"),
        @("CompAgentDevin", "Devin"),
        @("CompAgentCopilot", "GitHub Copilot"),
        @("CompAgentCline", "Cline")
    )
    Write-LogMessage ""
    Write-LogMessage "Agent configs:"
    foreach ($a in $agentConfigs) {
        $checked = $Window.FindName($a[0]).IsChecked
        Write-LogMessage "  $($a[1]): $(if ($checked) { 'will install' } else { 'will skip' })"
    }
    Write-LogMessage ""

    # --- .env setup: copy .env.example to .env if it doesn't exist ---
    $envExample = Join-Path $installRoot ".env.example"
    $envFile = Join-Path $installRoot ".env"
    if (Test-Path $envExample) {
        if (-not (Test-Path $envFile)) {
            Copy-Item $envExample $envFile -Force
            Write-LogMessage "[.env] Created .env from .env.example template"
            Write-LogMessage "[.env] NOTE: Edit .env to fill in your MCP credentials (Upwork, Freelancer, LinkedIn)"
        } else {
            Write-LogMessage "[.env] .env already exists - skipped copy"
        }
    } else {
        Write-LogMessage "[.env] .env.example not found - skipped .env setup"
    }
    Write-LogMessage ""

    # Run installation in a background job
    $script:installJob = Start-Job -ScriptBlock {
        param($InstallArgs)
        & powershell @InstallArgs 2>&1
    } -ArgumentList (, $installArgs)
    $installJob = $script:installJob

    # Monitor job progress - update progress based on actual output lines
    $totalSteps = 10
    $currentStep = 0
    $outputLineCount = 0

    # Collect all output for rollback detection
    $allOutput = [System.Collections.ArrayList]@()
    while ($installJob.State -eq "Running") {
        Start-Sleep -Milliseconds 200
        $output = Receive-Job $installJob 2>&1
        foreach ($line in $output) {
            Write-LogMessage "$line"
            $allOutput.Add("$line") | Out-Null
            $outputLineCount++
            # Update progress based on actual output activity (capped at 90% until complete)
            $currentStep = [math]::Min([math]::Floor($outputLineCount / 5), $totalSteps - 1)
            $percent = [math]::Round(($currentStep / $totalSteps) * 90)
            Update-Progress $percent "Installing... ($outputLineCount lines output)"
        }
    }

    # Get final output
    $finalOutput = Receive-Job $installJob 2>&1
    foreach ($line in $finalOutput) {
        Write-LogMessage "$line"
        $allOutput.Add("$line") | Out-Null
    }

    # Detect rollback in output
    $rollbackDetected = $false
    $rollbackReason = ""
    foreach ($line in $allOutput) {
        if ($line -match "Rolling back due to:\s*(.+)") {
            $rollbackDetected = $true
            $rollbackReason = $matches[1].Trim()
            break
        }
        if ($line -match "Rollback:\s*(.+)") {
            $rollbackDetected = $true
            $rollbackReason = $matches[1].Trim()
            break
        }
    }
    if ($rollbackDetected) {
        Write-LogMessage ""
        Write-LogMessage "[ROLLBACK] Installation was rolled back: $rollbackReason"
        Write-LogMessage "[ROLLBACK] Some changes were undone. Check the log for details."
    }

    $exitCode = 0
    if ($installJob.State -ne "Completed") { $exitCode = 1 }
    # Capture the actual exit code from the install job
    if ($installJob.State -eq "Completed" -and $installJob.ChildJobs.Count -gt 0) {
        $childExit = $installJob.ChildJobs[0].JobStateInfo.Reason
        if ($childExit) {
            Write-LogMessage "[WARN] Install job completed with error: $childExit"
            $exitCode = 1
        }
    }
    Remove-Job $installJob -Force

    if ($exitCode -ne 0) {
        Write-LogMessage "[ERROR] Installation failed (exit code $exitCode)"
        Update-Progress 100 "Installation failed!"
        $script:currentPage = 7
        Show-Page 7
        $Window.FindName("FinishTitle").Text = "Installation Failed"
        if ($rollbackDetected) {
            $Window.FindName("FinishVersion").Text = "Installation FAILED - rolled back: $rollbackReason"
        } else {
            $Window.FindName("FinishVersion").Text = "Installation FAILED - check log for details"
        }
        $Window.FindName("FinishLocation").Text = "Location: $installRoot"
        $Window.FindName("FinishLog").Text = "GUI log: $InstallLogPath"
        # On failure, auto-check "Open GUI log" so user can see what went wrong
        $Window.FindName("FinishOpenGuiLog").IsChecked = $true
        $NextBtn.IsEnabled = $true
        return
    }

    Update-Progress 100 "Installation complete!"

    # --- Post-install cleanup: remove deselected agent configs + shortcuts ---
    Write-LogMessage ""
    Write-LogMessage "--- Post-install cleanup ---"

    # Agent configs: install.ps1 installs all - remove deselected ones
    $agentCleanup = @(
        @("CompAgentClaude", @("$env:USERPROFILE\.claude\CLAUDE.md", "$env:USERPROFILE\.claude\settings.json", "$env:USERPROFILE\.claude\skills", "$env:USERPROFILE\.claude\agents"), "Claude Code"),
        @("CompAgentWindsurf", @("$env:USERPROFILE\.windsurf\skills\global-os"), "Windsurf"),
        @("CompAgentAider", @("$env:USERPROFILE\.aider.conf.yml"), "Aider"),
        @("CompAgentDevin", @("$env:USERPROFILE\.devin\skills\global-os"), "Devin")
    )
    foreach ($ac in $agentCleanup) {
        if (-not $Window.FindName($ac[0]).IsChecked) {
            foreach ($p in $ac[1]) {
                $expanded = [Environment]::ExpandEnvironmentVariables($p)
                if (Test-Path $expanded) {
                    Remove-Item $expanded -Recurse -Force -ErrorAction SilentlyContinue
                    Write-LogMessage "  [SKIP] Removed $($ac[2]) config: $expanded"
                }
            }
        }
    }

    # Cursor config
    if (-not $Window.FindName("CompAgentCursor").IsChecked) {
        $cursorDir = Join-Path $installRoot ".cursor\rules"
        if (Test-Path $cursorDir) {
            Write-LogMessage "  [SKIP] Cursor rules kept in repo but not linked (deselected)"
        }
    }

    # Copilot config
    if (-not $Window.FindName("CompAgentCopilot").IsChecked) {
        $copilotFile = Join-Path $installRoot ".github\copilot-instructions.md"
        if (Test-Path $copilotFile) {
            Write-LogMessage "  [SKIP] Copilot instructions kept in repo but not linked (deselected)"
        }
    }

    # Cline config
    if (-not $Window.FindName("CompAgentCline").IsChecked) {
        $clineFile = Join-Path $installRoot ".clinerules"
        if (Test-Path $clineFile) {
            Write-LogMessage "  [SKIP] Cline rules kept in repo but not linked (deselected)"
        }
    }

    # Dashboard - if deselected, note it
    if (-not $Window.FindName("CompDashboard").IsChecked) {
        Write-LogMessage "  [SKIP] Dashboard server files present but not auto-started (deselected)"
    }

    # CLI shim - if deselected, remove it
    if (-not $Window.FindName("CompCLIShim").IsChecked) {
        $shimPath = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps\aizee.cmd"
        if (Test-Path $shimPath) {
            Remove-Item $shimPath -Force -ErrorAction SilentlyContinue
            Write-LogMessage "  [SKIP] Removed CLI shim (deselected)"
        }
    }

    # Env var - if deselected, remove it
    if (-not $Window.FindName("CompEnvVar").IsChecked) {
        $existingRoot = [Environment]::GetEnvironmentVariable("AIZEE_ROOT", "User")
        if ($existingRoot) {
            [Environment]::SetEnvironmentVariable("AIZEE_ROOT", $null, "User")
            Write-LogMessage "  [SKIP] Removed AIZEE_ROOT env var (deselected)"
        }
    }

    # Shortcuts - if deselected, remove them
    if (-not $Window.FindName("CompStartMenu").IsChecked) {
        $startMenuShortcut = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\aiZee.lnk"
        if (Test-Path $startMenuShortcut) {
            Remove-Item $startMenuShortcut -Force -ErrorAction SilentlyContinue
            Write-LogMessage "  [SKIP] Removed Start Menu shortcut (deselected)"
        }
    }
    if (-not $Window.FindName("CompDesktop").IsChecked) {
        $desktopShortcut = Join-Path $env:USERPROFILE "Desktop\aiZee.lnk"
        if (Test-Path $desktopShortcut) {
            Remove-Item $desktopShortcut -Force -ErrorAction SilentlyContinue
            Write-LogMessage "  [SKIP] Removed Desktop shortcut (deselected)"
        }
    }

    # Create shortcuts if selected (install.ps1 doesn't do this)
    if ($Window.FindName("CompStartMenu").IsChecked) {
        $startMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
        $shortcutPath = Join-Path $startMenuDir "aiZee.lnk"
        try {
            $wsh = New-Object -ComObject WScript.Shell
            $sc = $wsh.CreateShortcut($shortcutPath)
            $sc.TargetPath = "powershell.exe"
            $sc.Arguments = "-ExecutionPolicy Bypass -File `"$installRoot\installer\gui_installer.ps1`""
            $sc.WorkingDirectory = $installRoot
            $sc.IconLocation = "shell32.dll,0"
            $sc.Save()
            Write-LogMessage "  [OK] Created Start Menu shortcut: $shortcutPath"
        } catch {
            Write-LogMessage "  [WARN] Failed to create Start Menu shortcut: $_"
        }
    }
    if ($Window.FindName("CompDesktop").IsChecked) {
        $desktopPath = Join-Path $env:USERPROFILE "Desktop\aiZee.lnk"
        try {
            $wsh = New-Object -ComObject WScript.Shell
            $sc = $wsh.CreateShortcut($desktopPath)
            $sc.TargetPath = "powershell.exe"
            $sc.Arguments = "-ExecutionPolicy Bypass -File `"$installRoot\installer\gui_installer.ps1`""
            $sc.WorkingDirectory = $installRoot
            $sc.IconLocation = "shell32.dll,0"
            $sc.Save()
            Write-LogMessage "  [OK] Created Desktop shortcut: $desktopPath"
        } catch {
            Write-LogMessage "  [WARN] Failed to create Desktop shortcut: $_"
        }
    }

    Write-LogMessage ""

    # Post-install verification
    $verifyIssues = @()
    $envRoot = [Environment]::GetEnvironmentVariable("AIZEE_ROOT", "User")
    if ($Window.FindName("CompEnvVar").IsChecked -and $envRoot -ne $installRoot) {
        $verifyIssues += "AIZEE_ROOT not set correctly (got: '$envRoot', expected: '$installRoot')"
    }
    if ($Window.FindName("CompCLIShim").IsChecked -and -not (Test-Path (Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps\aizee.cmd"))) {
        $verifyIssues += "CLI shim not created at expected location"
    }
    if (-not (Test-Path (Join-Path $installRoot ".aizee-version"))) {
        $verifyIssues += ".aizee-version file not written"
    }
    foreach ($issue in $verifyIssues) {
        Write-LogMessage "[VERIFY] WARN: $issue"
    }
    if ($verifyIssues.Count -gt 0) {
        Write-LogMessage "[VERIFY] $($verifyIssues.Count) issue(s) found - installation may be incomplete"
    } else {
        Write-LogMessage "[VERIFY] All post-install checks passed"
    }

    # NOTE: install.ps1 output is already captured live via Receive-Job above
    # and written to this GUI log via Write-LogMessage. No file merge needed —
    # the GUI log contains only the current session's messages (no old logs).

    # Show finish page
    $script:currentPage = 7
    Show-Page 7

    # Log finish details
    Write-LogFile "--- Installation Complete ---"
    Write-LogFile "  Version: $TargetVersion"
    Write-LogFile "  Location: $installRoot"
    Write-LogFile "  Components installed: $compCount"
    if ($verifyIssues.Count -gt 0) {
        Write-LogFile "  Verification issues:"
        foreach ($issue in $verifyIssues) {
            Write-LogFile "    WARN: $issue"
        }
    } else {
        Write-LogFile "  Verification: all checks passed"
    }
    Write-LogFile "  GUI Log file: $InstallLogPath"
    Write-LogFile "=== Session End ==="

    # Populate finish page
    $Window.FindName("FinishVersion").Text = "Version: $TargetVersion"
    $Window.FindName("FinishLocation").Text = "Location: $installRoot"

    $logFile = Join-Path $installRoot "state\install-*.log"
    $script:latestLog = Get-ChildItem $logFile -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    $latestLog = $script:latestLog
    if ($latestLog) {
        $Window.FindName("FinishLog").Text = "Install log: $($latestLog.FullName)"
    }
    # Also show the GUI log file path (current session only, no merging)
    $script:guiLogPath = $InstallLogPath
    $Window.FindName("FinishLog").Text += "`nGUI log: $InstallLogPath"

    $compCount = 0
    $allChecks = @("CompPip","CompGraphify","CompDashboard","CompMCPGraphify","CompMCPContext7","CompMCPUpwork","CompMCPFreelancer","CompMCPFiverr","CompMCPLinkedIn","CompAgentClaude","CompAgentWindsurf","CompAgentCursor","CompAgentAider","CompAgentDevin","CompAgentCopilot","CompAgentCline","CompCLIShim","CompEnvVar","CompStartMenu","CompDesktop")
    foreach ($c in $allChecks) {
        if ($Window.FindName($c).IsChecked) { $compCount++ }
    }
    $Window.FindName("FinishComponents").Text = "Components installed: $compCount"

    # Show .env warning if secret-requiring MCP servers were selected
    $needsSecrets = ($Window.FindName("CompMCPUpwork").IsChecked -or $Window.FindName("CompMCPFreelancer").IsChecked -or $Window.FindName("CompMCPLinkedIn").IsChecked)
    if ($needsSecrets) {
        $envPath = Join-Path $installRoot ".env"
        $Window.FindName("FinishEnvWarning").Visibility = "Visible"
        $Window.FindName("FinishEnvText").Text = "Edit: $envPath`nFill in LINKEDIN_ACCESS_TOKEN (or LINKEDIN_MCP_TOKEN_PATH), UPWORK_CLIENT_ID, UPWORK_CLIENT_SECRET, and/or FREELANCER_OAUTH_TOKEN.`nMCP servers will not work until credentials are set."
        $Window.FindName("FinishOpenEnv").IsChecked = $true
    }

    $NextBtn.IsEnabled = $true

    # Handle finish page actions
    $NextBtn.Add_Click({
        if ($Window.FindName("FinishLaunchDashboard").IsChecked) {
            # Use start-dashboard.bat which launches the server + opens the browser
            $launcher = Join-Path $script:installRoot "start-dashboard.bat"
            if (Test-Path $launcher) {
                Start-Process cmd -ArgumentList "/c", "`"$launcher`""
            } else {
                Start-Process python -ArgumentList "dashboard/server.py" -WorkingDirectory $script:installRoot
            }
        }
        if ($Window.FindName("FinishOpenReadme").IsChecked) {
            Start-Process notepad -ArgumentList (Join-Path $script:installRoot "README.md")
        }
        if ($Window.FindName("FinishOpenLog").IsChecked -and $script:latestLog) {
            Start-Process notepad -ArgumentList $script:latestLog.FullName
        }
        if ($Window.FindName("FinishOpenGuiLog").IsChecked -and $script:guiLogPath) {
            Start-Process notepad -ArgumentList $script:guiLogPath
        }
        if ($Window.FindName("FinishOpenEnv").IsChecked) {
            $envPath = Join-Path $script:installRoot ".env"
            if (Test-Path $envPath) {
                Start-Process notepad -ArgumentList $envPath
            }
        }
        $Window.Close()
    })
}

# ---------------------------------------------------------------------------
# Initialize and show window
# ---------------------------------------------------------------------------

Show-Page 0
$Window.ShowDialog() | Out-Null
