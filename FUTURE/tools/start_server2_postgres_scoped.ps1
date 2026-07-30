$ErrorActionPreference = 'Stop'

$postgresService = 'postgresql-x64-17'
try {
    $service = Get-Service -Name $postgresService -ErrorAction Stop
    if ($service.Status -ne 'Running') {
        Start-Service -Name $postgresService
        $deadline = (Get-Date).AddSeconds(25)
        do {
            Start-Sleep -Milliseconds 250
            $service.Refresh()
        } until ($service.Status -eq 'Running' -or (Get-Date) -gt $deadline)
        if ($service.Status -ne 'Running') {
            throw "PostgreSQL service $postgresService did not reach Running."
        }
    }
}
catch {
    throw "Cannot start required PostgreSQL service ${postgresService}: $($_.Exception.Message)"
}

$domains = @(
    'AI_HISTORY_DOCUMENTS',
    'ANNOUNCEMENTS',
    'APPEND_EVENTS',
    'AUTH',
    'CHAT',
    'INVENTORY',
    'LEADERBOARD_DOCUMENTS',
    'LEARNING_SUMMARY_DOCUMENTS',
    'LESSON_FOLDER_LINKS',
    'LESSON_IDENTITY',
    'LESSON_LAST_FILE',
    'LESSON_PROGRESS',
    'LESSON_TASK',
    'LESSON_TASK_NOTICES',
    'LESSON_TIME',
    'PDF_DRAWINGS',
    'QMDICT_DOCUMENTS',
    'QM_CITY_DOCUMENTS',
    'SPACE_PDF_AI_DOCUMENTS',
    'SPACE_W_SPEAK_SKIP',
    'USER_AUTH_DOCS',
    'USER_PREFERENCES',
    'VAULT_METADATA',
    'VIEWER_TOOL_DOCUMENTS',
    'VOCABULARY',
    'VOCAB_IMAGE_CACHE'
)

foreach ($domain in $domains) {
    Set-Item -Path "Env:FUTURE_DB_${domain}_BACKEND" -Value 'postgres'
}

Set-Item -Path Env:FUTURE_POSTGRES_ONLY -Value '1'
Remove-Item Env:FUTURE_DB_BACKEND -ErrorAction SilentlyContinue
Remove-Item Env:FUTURE_POSTGRES_BACKEND -ErrorAction SilentlyContinue
Remove-Item Env:FUTURE_DISABLE_AUTH_LIMITS_FOR_BENCHMARK -ErrorAction SilentlyContinue
Remove-Item Env:FUTURE_TEST_PASSWORD -ErrorAction SilentlyContinue

if (-not $env:FUTURE_PG_DSN) {
    throw 'FUTURE_PG_DSN is required for PostgreSQL scoped Server 2 startup.'
}

$old = Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -match 'FUTURE_SERVER_2.py' -and $_.Name -match 'python' } |
    Select-Object -First 1 -ExpandProperty ProcessId
if ($old) {
    Stop-Process -Id ([int]$old) -Force
}

$deadline = (Get-Date).AddSeconds(15)
do {
    Start-Sleep -Milliseconds 200
    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort 8877 -ErrorAction SilentlyContinue)
} until ($listeners.Count -eq 0 -or (Get-Date) -gt $deadline)
if ($listeners.Count) {
    throw '8877 listener did not release.'
}

$stdout = 'C:\Users\Admin\.codex\plans\server2_postgres_scoped_start.out.log'
$stderr = 'C:\Users\Admin\.codex\plans\server2_postgres_scoped_start.err.log'
Remove-Item $stdout, $stderr -ErrorAction SilentlyContinue

$python = (Get-Command python).Source
$process = Start-Process -FilePath $python `
    -ArgumentList @('FUTURE_SERVER_2.py', '--replace-old') `
    -WorkingDirectory 'C:\programe\write_html' `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -WindowStyle Hidden `
    -PassThru

$health = $null
$lastError = ''
$limit = (Get-Date).AddSeconds(75)
do {
    Start-Sleep -Milliseconds 750
    try {
        $health = Invoke-RestMethod 'http://127.0.0.1:8877/health' -TimeoutSec 4
    }
    catch {
        $lastError = $_.Exception.Message
        $health = $null
    }
} until (($health -and $health.ok) -or $process.HasExited -or (Get-Date) -gt $limit)

[pscustomobject]@{
    StartedPid = $process.Id
    HasExited = $process.HasExited
    ExitCode = if ($process.HasExited) { $process.ExitCode } else { $null }
    HealthPid = if ($health) { $health.pid } else { 0 }
    Ok = if ($health) { $health.ok } else { $false }
    WarmReady = if ($health) { $health.warm_ready } else { $false }
    Postgres = if ($health) { $health.postgres } else { $null }
    SqliteWriter = if ($health) { $health.sqlite_writer } else { $null }
    LastError = $lastError
    Stdout = $stdout
    Stderr = $stderr
} | ConvertTo-Json -Depth 8
