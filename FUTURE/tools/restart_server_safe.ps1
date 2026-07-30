$ErrorActionPreference = 'Stop'

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
    throw 'FUTURE_PG_DSN is required for PostgreSQL-only Server 2 startup.'
}

$old = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'FUTURE_SERVER_2.py' -and $_.Name -match 'python' } | Select-Object -First 1 -ExpandProperty ProcessId
if ($old) { Stop-Process -Id ([int]$old) -Force }
$deadline = (Get-Date).AddSeconds(10)
do {
    Start-Sleep -Milliseconds 100
    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort 8877 -ErrorAction SilentlyContinue)
} until ($listeners.Count -eq 0 -or (Get-Date) -gt $deadline)
if ($listeners.Count) { throw '8877 listener did not release.' }
$python = (Get-Command python).Source
Start-Process -FilePath $python -ArgumentList @('FUTURE_SERVER_2.py', '--replace-old') -WorkingDirectory 'C:\programe\write_html' -WindowStyle Hidden | Out-Null
$limit = (Get-Date).AddSeconds(50)
$health = $null
do {
    Start-Sleep -Milliseconds 500
    try { $health = Invoke-RestMethod 'http://127.0.0.1:8877/health' -TimeoutSec 3 } catch { $health = $null }
} until (($health -and $health.warm_ready) -or (Get-Date) -gt $limit)
if (-not $health) { throw 'health unavailable after restart.' }
$listenersAfter = @(Get-NetTCPConnection -State Listen -LocalPort 8877 -ErrorAction SilentlyContinue)
[pscustomobject]@{
    OldPid = $old
    NewPid = $health.pid
    Port8877Listeners = $listenersAfter.Count
    WarmReady = $health.warm_ready
    Health = $health.ok
    SqliteWriter = $health.sqlite_writer
    Postgres = $health.postgres
} | ConvertTo-Json -Compress
