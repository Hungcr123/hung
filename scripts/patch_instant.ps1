$path = "C:\programe\write_html\FUTURE\web\js_parts\19_pdf_speak_chrome.js"
$content = Get-Content -LiteralPath $path -Raw

$old = "        if (options.instant) {`n          index = full.length;`n          paintTypedText();`n          actor.classList.remove(`"is-speaking`", `"is-jumping`");`n          if (pdfAiNoticeFireballState) {`n            pdfAiNoticeFireballState.typedOnce = true;`n          }`n          syncPdfAiNoticeBubbleCounter(actor);`n          schedulePdfAiNoticeFireballJump(actor);`n          pdfAiNoticeFireballMoveTimer = window.setTimeout(movePdfAiNoticeFireball, 10000);`n          return;`n        }"
$new = "        if (options.instant) {`n          index = full.length;`n          paintTypedText();`n          actor.classList.remove(`"is-speaking`", `"is-jumping`");`n          if (pdfAiNoticeFireballState) {`n            pdfAiNoticeFireballState.typedOnce = true;`n          }`n          syncPdfAiNoticeBubbleCounter(actor);`n          const instantState = pdfAiNoticeFireballState;`n          const instantPages = instantState && Array.isArray(instantState.pages) ? instantState.pages : [];`n          if (instantPages.length > 1 && noticePdfAiDisplayMode(instantState && instantState.notice) !== `"full`") {`n            pdfAiNoticeFireballMoveTimer = window.setTimeout(() => showPdfAiNoticeFireballPage(1), 3000);`n            return;`n          }`n          schedulePdfAiNoticeFireballJump(actor);`n          pdfAiNoticeFireballMoveTimer = window.setTimeout(movePdfAiNoticeFireball, 10000);`n          return;`n        }"
if ($content.Contains($old)) {
  $content = $content.Replace($old, $new)
  Write-Output "Patch applied"
} else {
  Write-Output "Patch NOT found"
}

Set-Content -LiteralPath $path -Value $content -Encoding UTF8 -NoNewline
Write-Output ("Done. New size: {0}" -f (Get-Item $path).Length)
