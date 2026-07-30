$path = "C:\programe\write_html\FUTURE\web\css_parts\10_pdf_mode_core.css"
$append = @"

    /* AI notice layer - container for hitboxes, transparent to clicks except hitbox children */
    .ft-pdf-ai-notice-layer {
      position: absolute;
      inset: 0;
      pointer-events: none;
      z-index: 5;
    }
    .ft-pdf-ai-notice-layer .ft-pdf-ai-notice-hitbox {
      pointer-events: auto;
    }
    .ft-pdf-ai-notice-hitbox {
      position: absolute;
      border: 1px dashed rgba(70, 240, 215, 0.4);
      background: rgba(70, 240, 215, 0.06);
      border-radius: 4px;
      cursor: pointer;
      overflow: visible;
    }
    .ft-pdf-ai-notice-hitbox.is-active {
      border-color: rgba(255, 213, 132, 0.85);
      background: rgba(255, 213, 132, 0.12);
    }
    .ft-pdf-ai-notice-layer.is-admin-visible .ft-pdf-ai-notice-hitbox {
      border-color: rgba(255, 176, 72, 0.7);
    }
    .ft-pdf-ai-notice-mini-fireball {
      position: absolute;
      left: 50%;
      top: 50%;
      width: 30px;
      height: 30px;
      transform: translate(-50%, -50%);
      pointer-events: none;
    }
    .ft-pdf-ai-notice-mini-fireball .ft-world-fireball {
      width: 30px;
      height: 30px;
    }
"@
Add-Content -LiteralPath $path -Value $append -Encoding UTF8
Write-Output ("New size: {0}" -f (Get-Item $path).Length)
