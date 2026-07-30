param(
  [int]$Seed = 2026073004,
  [int]$SamplesPerSpace = 2,
  [switch]$FullGate
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$runRoot = Join-Path $root "programe_cache\node_space_100_user_gate_18877"
$stdoutPath = Join-Path $root "programe_cache\node_space_dom_gate.out.log"
$stderrPath = Join-Path $root "programe_cache\node_space_dom_gate.err.log"
$gateOutput = "C:\Users\Admin\.codex\plans\node_space_100_user_gate_20260729.json"
$probeOutput = "C:\Users\Admin\.codex\plans\node_space_cold_probe_20260730.json"

try {
  Invoke-RestMethod "http://127.0.0.1:18877/health" -TimeoutSec 1 | Out-Null
  throw "Isolated port 18877 is already in use; stop the previous test run first."
} catch {
  if ($_.Exception.Message -like "Isolated port 18877*") { throw }
}
foreach ($logPath in @($stdoutPath, $stderrPath)) {
  if (Test-Path $logPath) { Clear-Content -LiteralPath $logPath }
}

$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$secretBytes = New-Object byte[] 32
$rng.GetBytes($secretBytes)
$rng.Dispose()
$secret = [Convert]::ToBase64String($secretBytes)
$env:FUTURE_LOAD_TEST_PASSWORD = $secret
$env:FUTURE_TEST_PASSWORD = $secret

$arguments = @("FUTURE\tools\test_node_space_100_user_gate.py", "--seed", "$Seed")
if ($FullGate) {
  $arguments += "--keep-manifest-server"
} else {
  $arguments += @("--cold-probe", "--keep-probe-server", "--probe-output", $probeOutput)
}

$process = $null
try {
  $process = Start-Process -FilePath "python" -ArgumentList $arguments -WorkingDirectory $root `
    -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -WindowStyle Hidden -PassThru
  $deadline = [DateTime]::UtcNow.AddMinutes($(if ($FullGate) { 30 } else { 5 }))
  do {
    Start-Sleep -Milliseconds 500
    $ready = (Test-Path $stdoutPath) -and (Select-String -Path $stdoutPath -Pattern "DOM_READY" -Quiet)
    if ($process.HasExited -and -not $ready) {
      throw "Gate harness exited before DOM_READY. See $stderrPath"
    }
  } while (-not $ready -and [DateTime]::UtcNow -lt $deadline)
  if (-not $ready) {
    throw "DOM_READY timeout. See $stdoutPath and $stderrPath"
  }

  $env:FUTURE_DOM_BASE = "http://127.0.0.1:18877"
  $env:FUTURE_DOM_USER = "codexgate000"
  $env:FUTURE_DOM_FIXTURES = $gateOutput
  $env:FUTURE_DOM_OUTPUT = Join-Path $runRoot "dom_result.json"
  $env:FUTURE_DOM_SAMPLES_PER_SPACE = "$SamplesPerSpace"
  & node (Join-Path $root "FUTURE\tools\test_node_space_dom_gate.cjs")
  if ($LASTEXITCODE -ne 0) {
    throw "DOM runner failed with exit code $LASTEXITCODE"
  }
  Wait-Process -Id $process.Id -Timeout 120
  if ($process.ExitCode -ne 0) {
    throw "Gate harness failed with exit code $($process.ExitCode). See $stderrPath"
  }
} finally {
  $env:FUTURE_LOAD_TEST_PASSWORD = $null
  $env:FUTURE_TEST_PASSWORD = $null
  $secret = $null
  [Array]::Clear($secretBytes, 0, $secretBytes.Length)
  if ($process -and -not $process.HasExited) {
    Stop-Process -Id $process.Id -Force
  }
  try {
    $health = Invoke-RestMethod "http://127.0.0.1:18877/health" -TimeoutSec 1
    $serverProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$health.pid)"
    if ($serverProcess.CommandLine -match "--port 18877") {
      Stop-Process -Id ([int]$health.pid) -Force
    }
  } catch {
  }
}
