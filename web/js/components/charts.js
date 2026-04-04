export function renderBarChart(canvas, labels, values, color) {
  if (!canvas || !labels.length) return;
  canvas.width = canvas.offsetWidth || 500;
  const ctx = canvas.getContext("2d");
  const W = canvas.width;
  const H = canvas.height;
  ctx.clearRect(0, 0, W, H);

  const pad = { top: 16, right: 8, bottom: 28, left: 32 };
  const chartW = W - pad.left - pad.right;
  const chartH = H - pad.top - pad.bottom;
  const max = Math.max(...values, 1);
  const barW = chartW / labels.length;

  ctx.fillStyle = "rgba(255,255,255,0.04)";
  [0.25, 0.5, 0.75, 1].forEach(pct => {
    const y = pad.top + chartH - pct * chartH;
    ctx.fillRect(pad.left, y, chartW, 1);
    ctx.fillStyle = "rgba(255,255,255,0.2)";
    ctx.font = "9px Inter";
    ctx.fillText(Math.round(max * pct), 0, y + 3);
    ctx.fillStyle = "rgba(255,255,255,0.04)";
  });

  values.forEach((v, i) => {
    const h = (v / max) * chartH;
    const x = pad.left + i * barW + 3;
    const y = pad.top + chartH - h;
    const alpha = 0.5 + 0.5 * (v / max);
    ctx.fillStyle = color;
    ctx.globalAlpha = alpha;
    ctx.beginPath();
    ctx.roundRect(x, y, Math.max(barW - 6, 4), h, [3, 3, 0, 0]);
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.fillStyle = "rgba(255,255,255,0.35)";
    ctx.font = "9px Inter";
    ctx.textAlign = "center";
    ctx.fillText(String(labels[i]), x + (barW - 6) / 2, pad.top + chartH + 16);
  });
}
