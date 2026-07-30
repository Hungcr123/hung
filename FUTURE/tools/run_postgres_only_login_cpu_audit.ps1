param(
    [string]$Output = "C:\Users\Admin\.codex\plans\postgres_only_login_cpu_audit_20260730.json"
)

$ErrorActionPreference = "Stop"
$isolatedRoot = "C:\programe\write_html\programe_cache\lesson_complete_isolated_18877"
$postgresData = Join-Path $isolatedRoot "postgres"
$runtimeRoot = Join-Path $isolatedRoot "runtime_postgres_audit_20260730"
$qmlRoot = Join-Path $isolatedRoot "qml_postgres_audit_20260730"
$serverDataRoot = Join-Path $isolatedRoot "server-data"
$stdoutPath = Join-Path $isolatedRoot "server_audit_18877.out.log"
$stderrPath = Join-Path $isolatedRoot "server_audit_18877.err.log"
$testPassword = ([guid]::NewGuid().ToString("N") + "A9!")
$serverProcess = $null

New-Item -ItemType Directory -Force -Path $runtimeRoot, $qmlRoot | Out-Null
$env:FUTURE_PG_DSN = "postgresql://future_server2_app@127.0.0.1:55432/future_server2_copy"
$env:FUTURE_SERVER_DATA_ROOT = $serverDataRoot
$env:FUTURE_RUNTIME_ROOT = $runtimeRoot
$env:FUTURE_QMLEARN_ROOT = $qmlRoot
$env:FUTURE_SKIP_POSTGRES_SERVICE_START = "1"
$env:FUTURE_POSTGRES_ONLY = "1"
$env:FUTURE_ISOLATED_AUDIT_PASSWORD = $testPassword

try {
    @'
import os
import FUTURE_SERVER_2
from FUTURE import server_app as app
from FUTURE.tools.benchmark_login_cpu_baseline_20260727 import password_hash

app.postgres_upsert_user_auth_credential(
    "hung",
    password_hash(os.environ["FUTURE_ISOLATED_AUDIT_PASSWORD"]),
    "isolated-postgres-audit-20260730",
)
print("isolated_credential_ready")
'@ | python -

    $serverProcess = Start-Process `
        -FilePath "C:\Program Files\Python311\python.exe" `
        -ArgumentList "FUTURE_SERVER_2.py", "--replace-old", "--no-browser", "--no-tunnel", "--host", "127.0.0.1", "--port", "18877" `
        -WorkingDirectory "C:\programe\write_html" `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutPath `
        -RedirectStandardError $stderrPath `
        -PassThru

    $deadline = (Get-Date).AddSeconds(180)
    $health = $null
    do {
        Start-Sleep -Milliseconds 500
        try {
            $health = Invoke-RestMethod "http://127.0.0.1:18877/health?view=dashboard-v1" -TimeoutSec 5
        } catch {
            $health = $null
        }
    } while ((Get-Date) -lt $deadline -and -not ($health.ready -and $health.warm_ready))
    if (-not ($health.ready -and $health.warm_ready)) {
        throw "Isolated Server 2 did not become warm-ready."
    }

    $env:FUTURE_LOGIN_BENCH_PASSWORDS_JSON = ConvertTo-Json @{ hung = $testPassword } -Compress
    $env:FUTURE_LOGIN_LOAD_PASSWORD = $testPassword
    python FUTURE\tools\benchmark_login_cpu_baseline_20260727.py `
        --idle-seconds 10 `
        --settle-seconds 10 `
        --skip-dashboard `
        --output $Output
} finally {
    if ($serverProcess -and -not $serverProcess.HasExited) {
        Stop-Process -Id $serverProcess.Id
    }
    Start-Sleep -Seconds 2
    & "C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe" -D $postgresData -m fast stop -w | Out-Null
}
