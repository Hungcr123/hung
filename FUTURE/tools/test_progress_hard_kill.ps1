$ErrorActionPreference = 'Stop'
$base = 'http://127.0.0.1:8877'
$password = $env:FUTURE_TEST_PASSWORD
if (-not $password) { throw 'Set FUTURE_TEST_PASSWORD for this test only.' }
$runV = 'crash-v-' + [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
$runW = 'crash-w-' + ([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() + 1)
$opV = 'crash-op-v-' + [guid]::NewGuid().ToString('N')
$opW = 'crash-op-w-' + [guid]::NewGuid().ToString('N')
$stamp = [DateTime]::UtcNow.ToString('o').Replace('+00:00', 'Z')

@'
import sqlite3,json
from datetime import datetime,timezone
db=r"C:\server data\server2.db"
rows=[
    ("codexload001","Space_V","common/File 02 - {7}.Space_V","ftg-lesson-000002312"),
    ("codexload002","Space_W","common/Future lesson.Space_W","ftg-lesson-000000158"),
]
c=sqlite3.connect(db,timeout=30); c.execute("begin immediate")
for u,s,p,l in rows:
    st=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    c.execute("delete from lesson_progress where username=? and file_id=?",(u,l))
    c.execute("insert into lesson_progress_namespaces(username,space,updated_at_utc) values(?,?,?) on conflict(username,space) do update set updated_at_utc=excluded.updated_at_utc",(u,s,st))
    r={"path":p,"identity":l,"lesson_id":l,"file_id":l,"nodeIndex":4,"nodeCount":4,"complete":True,"completedRuns":3,"runId":"old-run","savedAt":st,"updatedAt":st,"_serverRevision":1,"state":{"runId":"old-run","complete":True,"completedRuns":3}}
    c.execute("insert into lesson_progress(username,space,progress_key,path,identity,file_id,node_index,node_count,learned_count,complete,server_revision,updated_at_utc,record_json) values(?,?,?,?,?,?,?,?,?,?,?,?,?)",(u,s,"old-key",p,l,l,4,4,4,1,1,st,json.dumps(r,separators=(",",":"))))
c.commit(); c.close()
'@ | python -

$tokenV = (Invoke-RestMethod "$base/auth/login" -Method Post -ContentType 'application/json' -Body (@{username='codexload001';password=$password} | ConvertTo-Json -Compress) -TimeoutSec 30).token
$tokenW = (Invoke-RestMethod "$base/auth/login" -Method Post -ContentType 'application/json' -Body (@{username='codexload002';password=$password} | ConvertTo-Json -Compress) -TimeoutSec 30).token
$bodyV = @{action='new_study';path='common/File 02 - {7}.Space_V';identity='ftg-lesson-000002312';lesson_id='ftg-lesson-000002312';nodeIndex=1;nodeCount=4;runId=$runV;activeRun=$true;complete=$false;completedRuns=3;savedAt=$stamp;syncOperationId=$opV;state=@{runId=$runV;activeRun=$true;complete=$false;completedRuns=3;nodeCount=4;savedAt=$stamp;syncOperationId=$opV}} | ConvertTo-Json -Depth 8 -Compress
$bodyW = @{action='new_study';path='common/Future lesson.Space_W';identity='ftg-lesson-000000158';lesson_id='ftg-lesson-000000158';nodeIndex=1;nodeCount=4;runId=$runW;activeRun=$true;complete=$false;completedRuns=3;savedAt=$stamp;syncOperationId=$opW;state=@{runId=$runW;activeRun=$true;complete=$false;completedRuns=3;nodeCount=4;savedAt=$stamp;syncOperationId=$opW}} | ConvertTo-Json -Depth 8 -Compress

function Send-NoRead($path, $token, $body) {
    $client = [System.Net.Sockets.TcpClient]::new('127.0.0.1', 8877)
    $bytes = [Text.Encoding]::UTF8.GetBytes($body)
    $head = "POST $path HTTP/1.1`r`nHost: 127.0.0.1:8877`r`nAuthorization: Bearer $token`r`nContent-Type: application/json`r`nContent-Length: $($bytes.Length)`r`nConnection: keep-alive`r`n`r`n"
    $stream = $client.GetStream()
    $headerBytes = [Text.Encoding]::ASCII.GetBytes($head)
    $stream.Write($headerBytes, 0, $headerBytes.Length)
    $stream.Write($bytes, 0, $bytes.Length)
    $stream.Flush()
    return $client
}

$healthBefore = Invoke-RestMethod "$base/health" -TimeoutSec 10
$clientV = Send-NoRead '/space-v/progress?response=compact-v1' $tokenV $bodyV
$clientW = Send-NoRead '/space-w/progress?response=compact-v1' $tokenW $bodyW
$env:CHECK_OP_V = $opV
$env:CHECK_OP_W = $opW
$committed = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 100
    $count = @'
import os,sqlite3
c=sqlite3.connect(r"C:\server data\server2.db")
n=c.execute("select count(*) from lesson_progress where username in ('codexload001','codexload002') and (record_json like ? or record_json like ?)",('%'+os.environ['CHECK_OP_V']+'%','%'+os.environ['CHECK_OP_W']+'%')).fetchone()[0]
print(n)
'@ | python -
    if ([int]$count -eq 2) { $committed = $true; break }
}
if (-not $committed) { throw 'V/W commits not observed before hard kill.' }

$oldPid = [int]$healthBefore.pid
Stop-Process -Id $oldPid -Force
$clientV.Close(); $clientW.Close()
$releaseDeadline = (Get-Date).AddSeconds(10)
do {
    Start-Sleep -Milliseconds 100
    $oldListeners = @(Get-NetTCPConnection -State Listen -LocalPort 8877 -ErrorAction SilentlyContinue)
} until ($oldListeners.Count -eq 0 -or (Get-Date) -gt $releaseDeadline)
if ($oldListeners.Count -ne 0) {
    throw "Old Server 2 listener still owns port 8877 after PID $oldPid was killed."
}
$python = (Get-Command python).Source
$newProcess = Start-Process -FilePath $python -ArgumentList @('FUTURE_SERVER_2.py','--replace-old') -WorkingDirectory 'C:\programe\write_html' -WindowStyle Hidden -PassThru
$deadline = (Get-Date).AddSeconds(50)
$healthAfter = $null
do {
    Start-Sleep -Milliseconds 500
    try { $healthAfter = Invoke-RestMethod "$base/health" -TimeoutSec 3 } catch { $healthAfter = $null }
} until (($healthAfter -and $healthAfter.warm_ready) -or (Get-Date) -gt $deadline)
if (-not $healthAfter) { throw 'Server did not recover after hard kill.' }
$newListeners = @(Get-NetTCPConnection -State Listen -LocalPort 8877 -ErrorAction SilentlyContinue)
if ($newListeners.Count -ne 1 -or [int]$newListeners[0].OwningProcess -ne [int]$healthAfter.pid) {
    throw "Port 8877 must have exactly one listener owned by the recovered Server 2 PID."
}

$writerBeforeRetry = [int]$healthAfter.sqlite_writer.tasks
$retryV = Invoke-WebRequest "$base/space-v/progress?response=compact-v1" -Method Post -Headers @{Authorization="Bearer $tokenV"} -ContentType 'application/json' -Body $bodyV -TimeoutSec 30
$retryW = Invoke-WebRequest "$base/space-w/progress?response=compact-v1" -Method Post -Headers @{Authorization="Bearer $tokenW"} -ContentType 'application/json' -Body $bodyW -TimeoutSec 30
$writerAfterRetry = Invoke-RestMethod "$base/health" -TimeoutSec 10
$env:CHECK_RUN_V = $runV
$env:CHECK_RUN_W = $runW
$rows = @'
import os,sqlite3,json
c=sqlite3.connect(r"C:\server data\server2.db")
out={}
for u,l,r in [('codexload001','ftg-lesson-000002312',os.environ['CHECK_RUN_V']),('codexload002','ftg-lesson-000000158',os.environ['CHECK_RUN_W'])]:
    rows=c.execute("select complete,server_revision,record_json from lesson_progress where username=? and file_id=?",(u,l)).fetchall()
    assert len(rows)==1,(u,rows)
    rec=json.loads(rows[0][2]); st=rec.get('state') or {}
    assert (rec.get('runId') or st.get('runId'))==r,(u,rec)
    assert int(rec.get('completedRuns',st.get('completedRuns',0)))==3,(u,rec)
    out[u]={'rows':len(rows),'complete':int(rows[0][0]),'revision':int(rows[0][1]),'run_id':r,'completedRuns':3}
print(json.dumps(out))
'@ | python -

$clearStamp = [DateTime]::UtcNow.ToString('o').Replace('+00:00', 'Z')
Invoke-RestMethod "$base/space-v/progress" -Method Post -Headers @{Authorization="Bearer $tokenV"} -ContentType 'application/json' -Body (@{action='clear';path='common/File 02 - {7}.Space_V';identity='ftg-lesson-000002312';lesson_id='ftg-lesson-000002312';expectedRunId=$runV;savedAt=$clearStamp} | ConvertTo-Json -Compress) -TimeoutSec 30 | Out-Null
Invoke-RestMethod "$base/space-w/progress" -Method Post -Headers @{Authorization="Bearer $tokenW"} -ContentType 'application/json' -Body (@{action='clear';path='common/Future lesson.Space_W';identity='ftg-lesson-000000158';lesson_id='ftg-lesson-000000158';expectedRunId=$runW;savedAt=$clearStamp} | ConvertTo-Json -Compress) -TimeoutSec 30 | Out-Null

[pscustomobject]@{
    HardKillAfterCommit = $committed
    OldPid = $oldPid
    OldQueue = $healthBefore.sqlite_writer.queue_depth
    NewPid = $healthAfter.pid
    WarmReady = $healthAfter.warm_ready
    Health = $healthAfter.ok
    Port8877Listeners = $newListeners.Count
    RetryV = $retryV.StatusCode
    RetryW = $retryW.StatusCode
    RetryWriterTasks = ([int]$writerAfterRetry.sqlite_writer.tasks - $writerBeforeRetry)
    Rows = ($rows | ConvertFrom-Json)
} | ConvertTo-Json -Depth 6
