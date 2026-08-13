#requires -Version 5.1
# AI Global OS - Professional WPF GUI Installer for Windows
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
    $args = @()
    if ($InstallDir) { $args += "-InstallDir"; $args += $InstallDir }
    if ($SkipPip) { $args += "-SkipPip" }
    if ($SkipGraphify) { $args += "-SkipGraphify" }
    if ($SkipMCP) { $args += "-SkipMCP" }
    & powershell -ExecutionPolicy Bypass -File $installScript @args
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
        Title="AI Global OS Installer" Height="620" Width="820"
        WindowStartupLocation="CenterScreen" ResizeMode="CanMinimize"
        Background="#0D1117" WindowStyle="SingleBorderWindow">
    <Window.Resources>
        <Style x:Key="PageTitle" TargetType="TextBlock">
            <Setter Property="Foreground" Value="#58A6FF"/>
            <Setter Property="FontSize" Value="22"/>
            <Setter Property="FontWeight" Value="Bold"/>
            <Setter Property="Margin" Value="0,0,0,10"/>
        </Style>
        <Style x:Key="PageSubtitle" TargetType="TextBlock">
            <Setter Property="Foreground" Value="#8B949E"/>
            <Setter Property="FontSize" Value="13"/>
            <Setter Property="Margin" Value="0,0,0,20"/>
            <Setter Property="TextWrapping" Value="Wrap"/>
        </Style>
        <Style x:Key="BodyText" TargetType="TextBlock">
            <Setter Property="Foreground" Value="#C9D1D9"/>
            <Setter Property="FontSize" Value="13"/>
            <Setter Property="Margin" Value="0,5,0,5"/>
            <Setter Property="TextWrapping" Value="Wrap"/>
        </Style>
        <Style x:Key="NavButton" TargetType="Button">
            <Setter Property="Background" Value="#21262D"/>
            <Setter Property="Foreground" Value="#C9D1D9"/>
            <Setter Property="BorderBrush" Value="#30363D"/>
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
            <Setter Property="Foreground" Value="#C9D1D9"/>
            <Setter Property="FontSize" Value="13"/>
            <Setter Property="Margin" Value="0,6,0,6"/>
        </Style>
        <Style x:Key="RadioStyle" TargetType="RadioButton">
            <Setter Property="Foreground" Value="#C9D1D9"/>
            <Setter Property="FontSize" Value="13"/>
            <Setter Property="Margin" Value="0,6,0,6"/>
        </Style>
        <Style x:Key="LogBox" TargetType="TextBox">
            <Setter Property="Background" Value="#161B22"/>
            <Setter Property="Foreground" Value="#7EE787"/>
            <Setter Property="FontFamily" Value="Consolas"/>
            <Setter Property="FontSize" Value="11"/>
            <Setter Property="IsReadOnly" Value="True"/>
            <Setter Property="VerticalScrollBarVisibility" Value="Auto"/>
            <Setter Property="HorizontalScrollBarVisibility" Value="Auto"/>
            <Setter Property="BorderBrush" Value="#30363D"/>
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
                    <TextBlock Style="{StaticResource PageTitle}" Text="Welcome to AI Global OS"/>
                    <TextBlock Style="{StaticResource PageSubtitle}" Text="Sovereign AI engineering control plane - installer wizard"/>
                    <Border Background="#161B22" CornerRadius="8" Padding="20" Margin="0,10,0,10">
                        <StackPanel>
                            <TextBlock Style="{StaticResource BodyText}" Text="Version: $TargetVersion" FontWeight="Bold"/>
                            <TextBlock Style="{StaticResource BodyText}" Text="License: MIT"/>
                            <TextBlock Style="{StaticResource BodyText}" Text="Author: Moataz"/>
                            <TextBlock Style="{StaticResource BodyText}" Text=""/>
                            <TextBlock Style="{StaticResource BodyText}" Text="This wizard will:"/>
                            <TextBlock Style="{StaticResource BodyText}" Text="  1. Install AI Global OS core + dependencies"/>
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
                    <Border Background="#161B22" CornerRadius="4" Padding="15" Margin="0,0,0,15" Height="280">
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
                    <TextBlock Style="{StaticResource PageSubtitle}" Text="Choose where to install AI Global OS"/>
                    <RadioButton x:Name="RadioInPlace" Style="{StaticResource RadioStyle}" GroupName="Location" Content="In-place (use current repo location)" IsChecked="True" Margin="0,0,0,5"/>
                    <TextBlock Style="{StaticResource BodyText}" Text="The OS will run directly from the repository. Recommended for developers." Margin="20,0,0,10" Foreground="#8B949E"/>
                    <RadioButton x:Name="RadioCustom" Style="{StaticResource RadioStyle}" GroupName="Location" Content="Custom location (copy files)" IsChecked="False" Margin="0,0,0,5"/>
                    <StackPanel Orientation="Horizontal" Margin="20,0,0,10">
                        <TextBox x:Name="CustomPath" Width="450" Height="30" Background="#161B22" Foreground="#C9D1D9" BorderBrush="#30363D" VerticalContentAlignment="Center" Padding="8,0" Text="$env:LOCALAPPDATA\AI-Global-OS" IsEnabled="False"/>
                        <Button x:Name="BrowseBtn" Style="{StaticResource NavButton}" Content="Browse..." Margin="10,0,0,0" IsEnabled="False"/>
                    </StackPanel>
                    <TextBlock x:Name="DiskSpaceInfo" Style="{StaticResource BodyText}" Text="Disk space: checking..." Margin="0,10,0,0" Foreground="#8B949E"/>
                    <TextBlock x:Name="RepoPathInfo" Style="{StaticResource BodyText}" Text="" Margin="0,5,0,0" Foreground="#8B949E"/>
                </StackPanel>
            </ScrollViewer>

            <!-- Page 4: Component Selection -->
            <ScrollViewer x:Name="PageComponents" Visibility="Collapsed" VerticalScrollBarVisibility="Auto">
                <StackPanel>
                    <TextBlock Style="{StaticResource PageTitle}" Text="Component Selection"/>
                    <TextBlock Style="{StaticResource PageSubtitle}" Text="Choose which components to install"/>
                    <ScrollViewer VerticalScrollBarVisibility="Auto" MaxHeight="380">
                        <StackPanel>
                        <TextBlock Style="{StaticResource BodyText}" Text="Core (required)" FontWeight="Bold" Foreground="#58A6FF" Margin="0,0,0,5"/>
                        <CheckBox x:Name="CompCore" Style="{StaticResource CheckboxStyle}" Content="AI Global OS Core (runtime, memory, MCP server)" IsChecked="True" IsEnabled="False"/>
                        <CheckBox x:Name="CompPip" Style="{StaticResource CheckboxStyle}" Content="Python dependencies (pip install)" IsChecked="True"/>
                        <CheckBox x:Name="CompGraphify" Style="{StaticResource CheckboxStyle}" Content="Build knowledge graph (graphify update)" IsChecked="True"/>
                        <CheckBox x:Name="CompDashboard" Style="{StaticResource CheckboxStyle}" Content="Dashboard server" IsChecked="True"/>

                        <TextBlock Style="{StaticResource BodyText}" Text="MCP Servers" FontWeight="Bold" Foreground="#58A6FF" Margin="0,15,0,5"/>
                        <CheckBox x:Name="CompMCPGraphify" Style="{StaticResource CheckboxStyle}" Content="Graphify MCP (codebase knowledge graph)" IsChecked="True"/>
                        <CheckBox x:Name="CompMCPContext7" Style="{StaticResource CheckboxStyle}" Content="Context7 MCP (library docs - requires npx)" IsChecked="True"/>
                        <CheckBox x:Name="CompMCPUpwork" Style="{StaticResource CheckboxStyle}" Content="Upwork MCP (job search + proposals - requires npx + .env secrets)" IsChecked="True"/>
                        <CheckBox x:Name="CompMCPFreelancer" Style="{StaticResource CheckboxStyle}" Content="Freelancer MCP (project search + bidding - requires npx + .env secrets)" IsChecked="True"/>
                        <CheckBox x:Name="CompMCPFiverr" Style="{StaticResource CheckboxStyle}" Content="Fiverr MCP (gig search - read-only, requires uvx, no secrets needed)" IsChecked="True"/>
                        <CheckBox x:Name="CompMCPLinkedIn" Style="{StaticResource CheckboxStyle}" Content="LinkedIn MCP (content automation - requires Python + .env secrets)" IsChecked="True"/>

                        <TextBlock Style="{StaticResource BodyText}" Text="AIOS Plugins" FontWeight="Bold" Foreground="#58A6FF" Margin="0,15,0,5"/>
                        <CheckBox x:Name="CompPluginGraphify" Style="{StaticResource CheckboxStyle}" Content="Graphify plugin (graph topology queries)" IsChecked="True"/>
                        <CheckBox x:Name="CompPluginContext7" Style="{StaticResource CheckboxStyle}" Content="Context7 plugin (library docs proxy)" IsChecked="True"/>
                        <CheckBox x:Name="CompPluginUpwork" Style="{StaticResource CheckboxStyle}" Content="Upwork plugin (8 tools)" IsChecked="True"/>
                        <CheckBox x:Name="CompPluginFreelancer" Style="{StaticResource CheckboxStyle}" Content="Freelancer plugin (11 tools)" IsChecked="True"/>
                        <CheckBox x:Name="CompPluginFiverr" Style="{StaticResource CheckboxStyle}" Content="Fiverr plugin (5 read-only tools)" IsChecked="True"/>
                        <CheckBox x:Name="CompPluginLinkedIn" Style="{StaticResource CheckboxStyle}" Content="LinkedIn plugin (18 tools - draft/approve/publish)" IsChecked="True"/>

                        <TextBlock Style="{StaticResource BodyText}" Text="Agent Configs" FontWeight="Bold" Foreground="#58A6FF" Margin="0,15,0,5"/>
                        <CheckBox x:Name="CompAgentClaude" Style="{StaticResource CheckboxStyle}" Content="Claude Code (CLAUDE.md + settings + skills + agents)" IsChecked="True"/>
                        <CheckBox x:Name="CompAgentWindsurf" Style="{StaticResource CheckboxStyle}" Content="Windsurf (.windsurfrules + skills)" IsChecked="True"/>
                        <CheckBox x:Name="CompAgentCursor" Style="{StaticResource CheckboxStyle}" Content="Cursor (.cursor/rules)" IsChecked="True"/>
                        <CheckBox x:Name="CompAgentAider" Style="{StaticResource CheckboxStyle}" Content="Aider (.aider.conf.yml)" IsChecked="True"/>
                        <CheckBox x:Name="CompAgentDevin" Style="{StaticResource CheckboxStyle}" Content="Devin (.devin/skills)" IsChecked="True"/>
                        <CheckBox x:Name="CompAgentCopilot" Style="{StaticResource CheckboxStyle}" Content="GitHub Copilot (.github/copilot-instructions.md)" IsChecked="True"/>
                        <CheckBox x:Name="CompAgentCline" Style="{StaticResource CheckboxStyle}" Content="Cline (.clinerules)" IsChecked="True"/>

                        <TextBlock Style="{StaticResource BodyText}" Text="System Integration" FontWeight="Bold" Foreground="#58A6FF" Margin="0,15,0,5"/>
                        <CheckBox x:Name="CompCLIShim" Style="{StaticResource CheckboxStyle}" Content="CLI shim (ai-os command in PATH)" IsChecked="True"/>
                        <CheckBox x:Name="CompEnvVar" Style="{StaticResource CheckboxStyle}" Content="Set AGENT_OS_ROOT environment variable" IsChecked="True"/>
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
                    <Border Background="#161B22" CornerRadius="4" Padding="15" Margin="0,0,0,15">
                        <StackPanel>
                        <TextBlock Style="{StaticResource BodyText}" Text="Environment Variables" FontWeight="Bold" Foreground="#58A6FF" Margin="0,0,0,8"/>
                        <StackPanel Orientation="Horizontal" Margin="0,0,0,5">
                            <TextBlock Style="{StaticResource BodyText}" Text="AGENT_OS_ROOT:" Width="150"/>
                            <TextBlock x:Name="ConfigRoot" Style="{StaticResource BodyText}" Text="" FontWeight="Bold"/>
                        </StackPanel>
                        <StackPanel Orientation="Horizontal" Margin="0,0,0,5">
                            <TextBlock Style="{StaticResource BodyText}" Text="PYTHONIOENCODING:" Width="150"/>
                            <TextBlock Style="{StaticResource BodyText}" Text="utf-8" FontWeight="Bold"/>
                        </StackPanel>
                        <StackPanel Orientation="Horizontal" Margin="0,0,0,5">
                            <TextBlock Style="{StaticResource BodyText}" Text="Scope:" Width="150"/>
                            <ComboBox x:Name="EnvVarScope" Width="120" Background="#21262D" Foreground="#C9D1D9">
                                <ComboBoxItem Content="User" IsSelected="True"/>
                                <ComboBoxItem Content="Machine"/>
                            </ComboBox>
                        </StackPanel>

                        <TextBlock Style="{StaticResource BodyText}" Text="Installation Options" FontWeight="Bold" Foreground="#58A6FF" Margin="0,15,0,8"/>
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
                    <Border Background="#161B22" CornerRadius="4" Padding="15" Margin="0,0,0,15" MaxHeight="350">
                        <ScrollViewer VerticalScrollBarVisibility="Auto">
                            <StackPanel>
                                <TextBlock Style="{StaticResource BodyText}" Text="System Checks" FontWeight="Bold" Foreground="#58A6FF" Margin="0,0,0,10"/>
                                <TextBlock x:Name="CheckPython" Style="{StaticResource BodyText}" Text="[ ] Python 3.10+ ... checking"/>
                                <TextBlock x:Name="CheckNpx" Style="{StaticResource BodyText}" Text="[ ] npx (npm) ... checking"/>
                                <TextBlock x:Name="CheckUvx" Style="{StaticResource BodyText}" Text="[ ] uvx (uv) ... checking"/>
                                <TextBlock x:Name="CheckDisk" Style="{StaticResource BodyText}" Text="[ ] Disk space ... checking"/>
                                <TextBlock x:Name="CheckExisting" Style="{StaticResource BodyText}" Text="[ ] Existing installation ... checking"/>
                                <TextBlock x:Name="CheckRepo" Style="{StaticResource BodyText}" Text="[ ] Repository integrity ... checking"/>
                                <TextBlock x:Name="CheckEnv" Style="{StaticResource BodyText}" Text="[ ] .env secrets file ... checking"/>

                                <TextBlock Style="{StaticResource BodyText}" Text="" Margin="0,10,0,0"/>
                                <TextBlock Style="{StaticResource BodyText}" Text="Installation Summary" FontWeight="Bold" Foreground="#58A6FF" Margin="0,10,0,8"/>
                                <TextBlock x:Name="SummaryLocation" Style="{StaticResource BodyText}" Text=""/>
                                <TextBlock x:Name="SummaryComponents" Style="{StaticResource BodyText}" Text=""/>
                                <TextBlock x:Name="SummaryVersion" Style="{StaticResource BodyText}" Text=""/>
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
                    <TextBlock Style="{StaticResource PageSubtitle}" Text="Please wait while AI Global OS is being installed"/>
                    <ProgressBar x:Name="Progressbar" Height="25" Minimum="0" Maximum="100" Value="0" Margin="0,0,0,10" Foreground="#1F6FEB"/>
                    <TextBlock x:Name="ProgressLabel" Style="{StaticResource BodyText}" Text="Preparing..." Margin="0,0,0,10"/>
                    <TextBox x:Name="LogBox" Style="{StaticResource LogBox}" Height="320" Text=""/>
                </StackPanel>
            </ScrollViewer>

            <!-- Page 8: Finish -->
            <ScrollViewer x:Name="PageFinish" Visibility="Collapsed" VerticalScrollBarVisibility="Auto">
                <StackPanel>
                    <TextBlock x:Name="FinishTitle" Style="{StaticResource PageTitle}" Text="Installation Complete!"/>
                    <TextBlock Style="{StaticResource PageSubtitle}" Text="AI Global OS has been successfully installed"/>
                    <Border Background="#161B22" CornerRadius="8" Padding="20" Margin="0,10,0,15">
                        <StackPanel>
                            <TextBlock x:Name="FinishVersion" Style="{StaticResource BodyText}" Text="" FontWeight="Bold"/>
                            <TextBlock x:Name="FinishLocation" Style="{StaticResource BodyText}" Text=""/>
                            <TextBlock x:Name="FinishLog" Style="{StaticResource BodyText}" Text=""/>
                            <TextBlock x:Name="FinishComponents" Style="{StaticResource BodyText}" Text=""/>
                        </StackPanel>
                    </Border>
                    <Border x:Name="FinishEnvWarning" Background="#1C1208" CornerRadius="8" Padding="15" Margin="0,0,0,15" BorderBrush="#D29922" BorderThickness="1" Visibility="Collapsed">
                        <StackPanel>
                            <TextBlock Style="{StaticResource BodyText}" Text="Action required: edit .env file" FontWeight="Bold" Foreground="#D29922"/>
                            <TextBlock x:Name="FinishEnvText" Style="{StaticResource BodyText}" Text="" Foreground="#D29922"/>
                        </StackPanel>
                    </Border>
                    <TextBlock Style="{StaticResource BodyText}" Text="What would you like to do next?" Margin="0,10,0,10"/>
                    <CheckBox x:Name="FinishLaunchDashboard" Style="{StaticResource CheckboxStyle}" Content="Launch dashboard server" IsChecked="False"/>
                    <CheckBox x:Name="FinishOpenReadme" Style="{StaticResource CheckboxStyle}" Content="Open README" IsChecked="False"/>
                    <CheckBox x:Name="FinishOpenLog" Style="{StaticResource CheckboxStyle}" Content="Open installation log" IsChecked="False"/>
                    <CheckBox x:Name="FinishOpenEnv" Style="{StaticResource CheckboxStyle}" Content="Open .env file to fill in MCP credentials" IsChecked="False"/>
                </StackPanel>
            </ScrollViewer>
        </Grid>

        <!-- Navigation bar -->
        <Border Grid.Row="1" Background="#161B22" Padding="20,10" BorderBrush="#30363D" BorderThickness="0,1,0,0">
            <Grid>
                <Grid.ColumnDefinitions>
                    <ColumnDefinition Width="*"/>
                    <ColumnDefinition Width="Auto"/>
                    <ColumnDefinition Width="Auto"/>
                    <ColumnDefinition Width="Auto"/>
                </Grid.ColumnDefinitions>

                <!-- Step indicator -->
                <StackPanel Grid.Column="0" Orientation="Horizontal" VerticalAlignment="Center">
                    <TextBlock x:Name="Step1" Style="{StaticResource StepIndicator}" Text="1. Welcome" Foreground="#58A6FF"/>
                    <TextBlock Text=">" Foreground="#30363D" Margin="4,0,4,0"/>
                    <TextBlock x:Name="Step2" Style="{StaticResource StepIndicator}" Text="2. License" Foreground="#484F58"/>
                    <TextBlock Text=">" Foreground="#30363D" Margin="4,0,4,0"/>
                    <TextBlock x:Name="Step3" Style="{StaticResource StepIndicator}" Text="3. Location" Foreground="#484F58"/>
                    <TextBlock Text=">" Foreground="#30363D" Margin="4,0,4,0"/>
                    <TextBlock x:Name="Step4" Style="{StaticResource StepIndicator}" Text="4. Components" Foreground="#484F58"/>
                    <TextBlock Text=">" Foreground="#30363D" Margin="4,0,4,0"/>
                    <TextBlock x:Name="Step5" Style="{StaticResource StepIndicator}" Text="5. Config" Foreground="#484F58"/>
                    <TextBlock Text=">" Foreground="#30363D" Margin="4,0,4,0"/>
                    <TextBlock x:Name="Step6" Style="{StaticResource StepIndicator}" Text="6. Pre-flight" Foreground="#484F58"/>
                    <TextBlock Text=">" Foreground="#30363D" Margin="4,0,4,0"/>
                    <TextBlock x:Name="Step7" Style="{StaticResource StepIndicator}" Text="7. Install" Foreground="#484F58"/>
                    <TextBlock Text=">" Foreground="#30363D" Margin="4,0,4,0"/>
                    <TextBlock x:Name="Step8" Style="{StaticResource StepIndicator}" Text="8. Finish" Foreground="#484F58"/>
                </StackPanel>

                <Button Grid.Column="1" x:Name="BackBtn" Style="{StaticResource NavButton}" Content="Back" Margin="0,0,10,0"/>
                <Button Grid.Column="2" x:Name="NextBtn" Style="{StaticResource PrimaryButton}" Content="Next" Margin="0,0,10,0"/>
                <Button Grid.Column="3" x:Name="CancelBtn" Style="{StaticResource NavButton}" Content="Cancel"/>
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
            $stepIndicators[$i].Foreground = "#58A6FF"
        } elseif ($i -lt $PageIndex) {
            $stepIndicators[$i].Foreground = "#7EE787"
        } else {
            $stepIndicators[$i].Foreground = "#484F58"
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

function Next-Page {
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
        5 { Run-PreFlightChecks }
    }
}

function Back-Page {
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

$NextBtn.Add_Click({ Next-Page })
$BackBtn.Add_Click({ Back-Page })
$CancelBtn.Add_Click({
    $result = [System.Windows.MessageBox]::Show("Are you sure you want to cancel the installation?", "Cancel", "YesNo", "Question")
    if ($result -eq "Yes") { $Window.Close() }
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

function Run-PreFlightChecks {
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
            $Window.FindName("CheckPython").Foreground = "#7EE787"
            $checks["CheckPython"] = $true
        } else {
            $Window.FindName("CheckPython").Text = "[FAIL] Python 3.10+ required (found: $pv)"
            $Window.FindName("CheckPython").Foreground = "#F85149"
        }
    } catch {
        $Window.FindName("CheckPython").Text = "[FAIL] Python not found on PATH"
        $Window.FindName("CheckPython").Foreground = "#F85149"
    }

    # npx
    $null = Get-Command npx -ErrorAction SilentlyContinue
    if ($?) {
        $Window.FindName("CheckNpx").Text = "[OK] npx: available"
        $Window.FindName("CheckNpx").Foreground = "#7EE787"
        $checks["CheckNpx"] = $true
    } else {
        $Window.FindName("CheckNpx").Text = "[WARN] npx: not found (context7/upwork/freelancer MCP will be unavailable)"
        $Window.FindName("CheckNpx").Foreground = "#D29922"
        $checks["CheckNpx"] = $true  # Warning, not failure
    }

    # uvx
    $null = Get-Command uvx -ErrorAction SilentlyContinue
    if ($?) {
        $Window.FindName("CheckUvx").Text = "[OK] uvx: available"
        $Window.FindName("CheckUvx").Foreground = "#7EE787"
    } else {
        $Window.FindName("CheckUvx").Text = "[WARN] uvx: not found (fiverr MCP will be unavailable)"
        $Window.FindName("CheckUvx").Foreground = "#D29922"
    }

    # Disk space
    $path = if ($Window.FindName("RadioInPlace").IsChecked) { $Repo } else { $Window.FindName("CustomPath").Text }
    try {
        $drive = (Get-Item $path).PSDrive
        $freeMB = [math]::Round($drive.Free / 1MB, 0)
        if ($freeMB -gt 100) {
            $Window.FindName("CheckDisk").Text = "[OK] Disk space: $freeMB MB free"
            $Window.FindName("CheckDisk").Foreground = "#7EE787"
            $checks["CheckDisk"] = $true
        } else {
            $Window.FindName("CheckDisk").Text = "[FAIL] Insufficient disk space: $freeMB MB (need 100+ MB)"
            $Window.FindName("CheckDisk").Foreground = "#F85149"
        }
    } catch {
        $Window.FindName("CheckDisk").Text = "[WARN] Disk space: unable to check"
        $Window.FindName("CheckDisk").Foreground = "#D29922"
        $checks["CheckDisk"] = $true
    }

    # Existing installation
    $versionFile = Join-Path $path ".aios-version"
    if (Test-Path $versionFile) {
        $existingVer = (Get-Content $versionFile -Raw).Trim()
        $Window.FindName("CheckExisting").Text = "[OK] Existing installation: v$existingVer (will be updated)"
        $Window.FindName("CheckExisting").Foreground = "#7EE787"
    } else {
        $Window.FindName("CheckExisting").Text = "[OK] First installation"
        $Window.FindName("CheckExisting").Foreground = "#7EE787"
    }
    $checks["CheckExisting"] = $true

    # Repo integrity
    if (Test-Path (Join-Path $Repo "pyproject.toml")) {
        $Window.FindName("CheckRepo").Text = "[OK] Repository: valid (pyproject.toml found)"
        $Window.FindName("CheckRepo").Foreground = "#7EE787"
        $checks["CheckRepo"] = $true
    } else {
        $Window.FindName("CheckRepo").Text = "[WARN] Repository: pyproject.toml not found"
        $Window.FindName("CheckRepo").Foreground = "#D29922"
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
                $Window.FindName("CheckEnv").Foreground = "#D29922"
            } else {
                $Window.FindName("CheckEnv").Text = "[OK] .env file present with credentials"
                $Window.FindName("CheckEnv").Foreground = "#7EE787"
            }
        } elseif (Test-Path $envExample) {
            $Window.FindName("CheckEnv").Text = "[WARN] .env missing - will be created from .env.example (edit it after install)"
            $Window.FindName("CheckEnv").Foreground = "#D29922"
        } else {
            $Window.FindName("CheckEnv").Text = "[WARN] .env and .env.example both missing - MCP servers needing secrets will fail"
            $Window.FindName("CheckEnv").Foreground = "#D29922"
        }
    } else {
        $Window.FindName("CheckEnv").Text = "[OK] .env: not needed (no secret-requiring MCP servers selected)"
        $Window.FindName("CheckEnv").Foreground = "#7EE787"
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

    # Overall status
    $failed = ($checks["CheckPython"] -eq $false -or $checks["CheckDisk"] -eq $false -or $checks["CheckRepo"] -eq $false)
    if ($failed) {
        $Window.FindName("PreFlightStatus").Text = "Some checks failed. Please fix the issues above before installing."
        $Window.FindName("PreFlightStatus").Foreground = "#F85149"
        $NextBtn.IsEnabled = $false
    } else {
        $Window.FindName("PreFlightStatus").Text = "All checks passed. Click Install to begin."
        $Window.FindName("PreFlightStatus").Foreground = "#7EE787"
        $NextBtn.IsEnabled = $true
    }
}

function Log-Message {
    param([string]$Message)
    $logBox = $Window.FindName("LogBox")
    $logBox.AppendText("$Message`n")
    $logBox.ScrollToEnd()
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

    # Determine install root
    $installRoot = if ($Window.FindName("RadioInPlace").IsChecked) { $Repo } else { $Window.FindName("CustomPath").Text }
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

    Log-Message "=== AI Global OS Installation ==="
    Log-Message "Root: $installRoot"
    Log-Message "Copy mode: $copyMode"
    Log-Message "Arguments: $($installArgs -join ' ')"
    Log-Message ""

    # --- .env setup: copy .env.example to .env if it doesn't exist ---
    $envExample = Join-Path $installRoot ".env.example"
    $envFile = Join-Path $installRoot ".env"
    if (Test-Path $envExample) {
        if (-not (Test-Path $envFile)) {
            Copy-Item $envExample $envFile -Force
            Log-Message "[.env] Created .env from .env.example template"
            Log-Message "[.env] NOTE: Edit .env to fill in your MCP credentials (Upwork, Freelancer, LinkedIn)"
        } else {
            Log-Message "[.env] .env already exists - skipped copy"
        }
    } else {
        Log-Message "[.env] .env.example not found - skipped .env setup"
    }
    Log-Message ""

    # Run installation in a background job
    $installJob = Start-Job -ScriptBlock {
        param($Args)
        & powershell @Args 2>&1
    } -ArgumentList $installArgs

    # Monitor job progress
    $totalSteps = 10
    $currentStep = 0

    while ($installJob.State -eq "Running") {
        Start-Sleep -Milliseconds 200
        $output = Receive-Job $installJob 2>&1
        foreach ($line in $output) {
            Log-Message "$line"
        }
        $currentStep = [math]::Min($currentStep + 1, $totalSteps - 1)
        $percent = [math]::Round(($currentStep / $totalSteps) * 100)
        Update-Progress $percent "Installing... (step $currentStep / $totalSteps)"
    }

    # Get final output
    $finalOutput = Receive-Job $installJob 2>&1
    foreach ($line in $finalOutput) {
        Log-Message "$line"
    }

    $exitCode = 0
    if ($installJob.State -ne "Completed") { $exitCode = 1 }
    Remove-Job $installJob -Force

    Update-Progress 100 "Installation complete!"

    # Show finish page
    $script:currentPage = 7
    Show-Page 7

    # Populate finish page
    $Window.FindName("FinishVersion").Text = "Version: $TargetVersion"
    $Window.FindName("FinishLocation").Text = "Location: $installRoot"

    $logFile = Join-Path $installRoot "state\install-*.log"
    $latestLog = Get-ChildItem $logFile -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latestLog) {
        $Window.FindName("FinishLog").Text = "Log: $($latestLog.FullName)"
    }

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
        $Window.FindName("FinishEnvText").Text = "Edit: $envPath`nFill in UPWORK_CLIENT_ID, UPWORK_CLIENT_SECRET, FREELANCER_OAUTH_TOKEN, and/or LINKEDIN_ACCESS_TOKEN.`nMCP servers will not work until credentials are set."
        $Window.FindName("FinishOpenEnv").IsChecked = $true
    }

    $NextBtn.IsEnabled = $true

    # Handle finish page actions
    $NextBtn.Add_Click({
        if ($Window.FindName("FinishLaunchDashboard").IsChecked) {
            Start-Process python -ArgumentList "dashboard/server.py" -WorkingDirectory $installRoot
        }
        if ($Window.FindName("FinishOpenReadme").IsChecked) {
            Start-Process notepad -ArgumentList (Join-Path $installRoot "README.md")
        }
        if ($Window.FindName("FinishOpenLog").IsChecked -and $latestLog) {
            Start-Process notepad -ArgumentList $latestLog.FullName
        }
        if ($Window.FindName("FinishOpenEnv").IsChecked) {
            $envPath = Join-Path $installRoot ".env"
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
