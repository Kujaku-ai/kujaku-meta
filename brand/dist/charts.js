/*
 * charts.js — brand chart interactivity helper.
 *
 * OPT-IN: add data-chart-interactive to any .chart <svg> element.
 * Brand wires up:
 *   - vertical crosshair (1px --ink-faint dashed) following mouse X
 *   - point highlight: nearest data point gets a hover ring
 *   - tooltip above the hovered point showing x/y values
 *   - multi-series: non-hovered series dim to 0.3 opacity
 *
 * CONTRACT — consumer provides data via the polyline's own points
 *   attribute (already present for rendering), plus optional
 *   data-xlabel and data-ylabel attributes to name the axes in
 *   the tooltip text.
 *
 * Brand does NOT own: sort state, zoom/pan, real-time updates,
 * data fetching. Brand ships the HOVER affordance, not the chart
 * logic. Same contract as .nav-masthead .is-hidden (brand ships
 * the CSS, consumer owns the trigger).
 *
 * No dependencies. Vanilla DOM + SVG only.
 */

(function () {
  'use strict';

  var SVG_NS = 'http://www.w3.org/2000/svg';

  function init() {
    document.querySelectorAll('svg[data-chart-interactive]').forEach(wireUp);
  }

  function wireUp(svg) {
    var tooltip = createTooltip(svg);
    var crosshair = createCrosshair(svg);
    var polylines = Array.prototype.slice.call(svg.querySelectorAll('polyline'));
    var series = polylines.map(parsePoints);

    svg.addEventListener('mousemove', function (evt) {
      var pt = toSvgCoords(svg, evt);
      var nearest = findNearest(series, pt);
      if (!nearest) return;
      updateCrosshair(crosshair, nearest.x, svg);
      updateTooltip(tooltip, nearest, evt);
      dimOtherSeries(polylines, nearest.series);
    });

    svg.addEventListener('mouseleave', function () {
      crosshair.style.display = 'none';
      tooltip.style.display = 'none';
      polylines.forEach(function (p) { p.style.opacity = ''; });
    });
  }

  function parsePoints(polyline) {
    var raw = polyline.getAttribute('points') || '';
    var pts = raw.trim().split(/[\s,]+/).map(Number);
    var points = [];
    for (var i = 0; i + 1 < pts.length; i += 2) {
      points.push({ x: pts[i], y: pts[i + 1], series: polyline });
    }
    return { polyline: polyline, points: points };
  }

  function toSvgCoords(svg, evt) {
    var pt = svg.createSVGPoint();
    pt.x = evt.clientX;
    pt.y = evt.clientY;
    return pt.matrixTransform(svg.getScreenCTM().inverse());
  }

  function findNearest(allSeries, mousePt) {
    var best = null;
    var bestDist = Infinity;
    allSeries.forEach(function (s) {
      s.points.forEach(function (p) {
        var d = Math.abs(p.x - mousePt.x);
        if (d < bestDist) {
          bestDist = d;
          best = p;
        }
      });
    });
    return best;
  }

  function createTooltip(svg) {
    var parent = svg.parentElement;
    if (getComputedStyle(parent).position === 'static') {
      parent.style.position = 'relative';
    }
    var existing = parent.querySelector('.chart-tooltip');
    if (existing) return existing;
    var tip = document.createElement('div');
    tip.className = 'chart-tooltip';
    tip.style.position = 'absolute';
    tip.style.display = 'none';
    tip.style.pointerEvents = 'none';
    parent.appendChild(tip);
    return tip;
  }

  function createCrosshair(svg) {
    var existing = svg.querySelector('.chart-crosshair');
    if (existing) return existing;
    var line = document.createElementNS(SVG_NS, 'line');
    line.setAttribute('class', 'chart-crosshair');
    line.setAttribute('y1', '0');
    var h = (svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.height) || 300;
    line.setAttribute('y2', String(h));
    line.style.display = 'none';
    svg.appendChild(line);
    return line;
  }

  function updateCrosshair(line, x) {
    line.setAttribute('x1', String(x));
    line.setAttribute('x2', String(x));
    line.style.display = 'block';
  }

  function updateTooltip(tip, point, evt) {
    var xLabel = point.series.dataset.xlabel || 'x';
    var yLabel = point.series.dataset.ylabel || 'y';
    tip.textContent = xLabel + ': ' + point.x.toFixed(1) + ' · ' + yLabel + ': ' + point.y.toFixed(2);
    tip.style.left = (evt.offsetX + 12) + 'px';
    tip.style.top = (evt.offsetY - 28) + 'px';
    tip.style.display = 'block';
  }

  function dimOtherSeries(allPolylines, hovered) {
    allPolylines.forEach(function (p) {
      p.style.opacity = (p === hovered) ? '1' : '0.3';
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
