#!/usr/bin/env node
// Focused source regression for the durable Space_PDF/Picture Clear All path.
const fs = require('fs');

const sourcePath = 'FUTURE/web/js_parts/19_pdf_speak_chrome.js';
const source = fs.readFileSync(sourcePath, 'utf8');

function section(startMarker, endMarker) {
  const start = source.indexOf(startMarker);
  const end = source.indexOf(endMarker, start + startMarker.length);
  if (start < 0 || end < 0) throw new Error(`missing section: ${startMarker}`);
  return source.slice(start, end);
}

const clearCanvas = section('const clearPdfPenCanvas =', 'const pdfDrawingLayerKey =');
const removeLayer = section('const removePdfDrawingLayer =', 'const loadPdfDrawingLayer =');
const clearAll = section('const clearPdfPenLayer =', 'const loadPdfCompactToolbarSettings =');

if (!clearCanvas.includes('return removePdfDrawingLayer(options);')) {
  throw new Error('canvas clear does not await/return durable removal');
}
if (clearAll.indexOf('clearPdfPenCanvas({ ...clearOptions, forgetStorage: true') < 0) {
  throw new Error('Clear All is not wired to durable clear');
}
const animationIndex = clearAll.indexOf('animationPromise = runPdfPenEraserAnimation');
const clearPromiseIndex = clearAll.indexOf('const clearPromise = clearPdfPenCanvas');
if (animationIndex < 0 || clearPromiseIndex < 0 || clearPromiseIndex < animationIndex) {
  throw new Error('Clear All must start the backend delete in the click turn');
}
if (!clearAll.includes('ft-pdf-clear-animation') || !clearAll.includes('sourceCanvas')) {
  throw new Error('Clear All animation must run on a snapshot so new strokes stay on the live canvas');
}
if (clearAll.includes('if (animated)') || clearAll.includes('No pen drawing found to clear.')) {
  throw new Error('Clear All still skips storage deletion when animation finds no visible drawing');
}
const waitIndex = removeLayer.indexOf('await Promise.resolve(pdfDrawingSavePromise)');
const baseRevisionIndex = removeLayer.indexOf('const baseRevision =', waitIndex);
const requestIndex = removeLayer.indexOf('const clearRequest = fetchAuthJson(');
if (waitIndex < 0 || baseRevisionIndex < waitIndex || requestIndex < baseRevisionIndex) {
  throw new Error('clear is not serialized behind pending save before revision/request');
}
if (!removeLayer.includes('retryCount: 1')) {
  throw new Error('clear conflict retry is missing');
}
if (!removeLayer.includes('scope.mode === "local-image"') || !removeLayer.includes('pdfDrawingLayerMetaKey(scope.page, scope)')) {
  throw new Error('local-image clear leaves stale local metadata');
}
if (!removeLayer.includes('clearLocalCopies') || !removeLayer.includes('legacyKey')) {
  throw new Error('Clear All must remove canonical and legacy local drawing keys');
}
if (!source.includes('if (pdfPenClearing)')) {
  throw new Error('new strokes are not serialized behind Clear All');
}
if (!source.includes('ft-pdf-clear-animation') || !source.includes('pdfPenClearing = false')) {
  throw new Error('new strokes are not released after the durable clear ACK');
}
console.log('pdf_drawing_clear_all_frontend=ok durable_no_visible_canvas=ok save_before_clear=ok conflict_retry=ok');
