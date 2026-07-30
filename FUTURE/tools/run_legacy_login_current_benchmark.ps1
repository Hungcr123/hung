$ErrorActionPreference = 'Stop'
$domains = @(
  'AI_HISTORY_DOCUMENTS','ANNOUNCEMENTS','APPEND_EVENTS','AUTH','CHAT','INVENTORY',
  'LEADERBOARD_DOCUMENTS','LEARNING_SUMMARY_DOCUMENTS','LESSON_FOLDER_LINKS','LESSON_IDENTITY',
  'LESSON_LAST_FILE','LESSON_PROGRESS','LESSON_TASK','LESSON_TASK_NOTICES','LESSON_TIME',
  'PDF_DRAWINGS','QMDICT_DOCUMENTS','QM_CITY_DOCUMENTS','SPACE_PDF_AI_DOCUMENTS',
  'SPACE_W_SPEAK_SKIP','USER_AUTH_DOCS','USER_PREFERENCES','VAULT_METADATA',
  'VIEWER_TOOL_DOCUMENTS','VOCABULARY','VOCAB_IMAGE_CACHE'
)
foreach ($domain in $domains) {
  Set-Item -Path "Env:FUTURE_DB_${domain}_BACKEND" -Value 'postgres'
}
$env:FUTURE_POSTGRES_ONLY = '1'
Remove-Item Env:FUTURE_DB_BACKEND, Env:FUTURE_POSTGRES_BACKEND -ErrorAction SilentlyContinue

$stdout = 'C:\Users\Admin\.codex\plans\server2_postgres_full_audit\checkpoint_007_legacy_harness_18877.out.log'
$stderr = 'C:\Users\Admin\.codex\plans\server2_postgres_full_audit\checkpoint_007_legacy_harness_18877.err.log'
Remove-Item $stdout, $stderr -ErrorAction SilentlyContinue

$old = Get-NetTCPConnection -LocalPort 18877 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($old) {
  Stop-Process -Id ([int]$old.OwningProcess) -Force -ErrorAction SilentlyContinue
  Start-Sleep -Milliseconds 800
}

$server = Start-Process -FilePath (Get-Command python).Source -ArgumentList @(
  'FUTURE_SERVER_2.py','--host','127.0.0.1','--port','18877','--no-browser','--no-tunnel','--no-preload'
) -WorkingDirectory 'C:\programe\write_html' -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden -PassThru

$deadline = (Get-Date).AddSeconds(90)
$health = $null
do {
  Start-Sleep -Milliseconds 1000
  try {
    $health = Invoke-RestMethod 'http://127.0.0.1:18877/health' -TimeoutSec 4
  } catch {
    $health = $null
  }
} until (($health -and $health.ok) -or $server.HasExited -or (Get-Date) -gt $deadline)
if (-not ($health -and $health.ok)) {
  throw "Server 18877 failed to become healthy."
}

try {
  python FUTURE\tools\benchmark_login_warmup_postgres.py --base http://127.0.0.1:18877 --port 18877 --prefix checkpoint_007_legacy_harness_current --output-dir C:\Users\Admin\.codex\plans\server2_postgres_full_audit --overwrite
}
finally {
  if ($server -and -not $server.HasExited) {
    Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
  }
  Start-Sleep -Milliseconds 1000
  $after = Get-NetTCPConnection -LocalPort 18877 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($after) {
    Stop-Process -Id ([int]$after.OwningProcess) -Force -ErrorAction SilentlyContinue
  }
}
