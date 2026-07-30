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
$old = Get-NetTCPConnection -LocalPort 18877 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($old) {
  Stop-Process -Id ([int]$old.OwningProcess) -Force -ErrorAction SilentlyContinue
  Start-Sleep -Milliseconds 800
}
$stdout = 'C:\Users\Admin\.codex\plans\server2_postgres_full_audit\checkpoint_008_browser_server_18877.out.log'
$stderr = 'C:\Users\Admin\.codex\plans\server2_postgres_full_audit\checkpoint_008_browser_server_18877.err.log'
Remove-Item $stdout, $stderr -ErrorAction SilentlyContinue
$server = Start-Process -FilePath (Get-Command python).Source -ArgumentList @(
  'FUTURE_SERVER_2.py','--host','127.0.0.1','--port','18877','--no-browser','--no-tunnel','--no-preload'
) -WorkingDirectory 'C:\programe\write_html' -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden -PassThru
$deadline = (Get-Date).AddSeconds(90)
do {
  Start-Sleep -Milliseconds 1000
  try {
    $health = Invoke-RestMethod 'http://127.0.0.1:18877/health' -TimeoutSec 4
    if ($health.ok) { break }
  } catch {
  }
} until ($server.HasExited -or (Get-Date) -gt $deadline)
if ($server.HasExited) {
  throw "Server exited before health."
}
Write-Output $server.Id
