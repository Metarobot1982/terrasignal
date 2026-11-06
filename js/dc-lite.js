/*
 * dc-lite.js — TERRASIGNAL page runtime
 * Renders a page template (<template id="dc-tpl">) with the page's Component class.
 * Supports {{hole}} text/attribute holes, <sc-if value>, <sc-for list as>, onClick="{{fn}}",
 * and setState() re-rendering. Pages listing data files in window.TS_DATA ({name: path}) get them
 * as this.data[name] and re-render once loaded; until then the page shows its built-in defaults.
 */
(function () {
  'use strict';

  class DCLogic {
    constructor(props) { this.props = props || {}; this.state = this.state || {}; }
    setState(patch) {
      Object.assign(this.state, patch || {});
      if (this.__render) this.__render();
    }
    renderVals() { return {}; }
  }
  window.DCLogic = DCLogic;

  var HOLE = /\{\{\s*([^}]+?)\s*\}\}/g;

  function lookup(expr, scopes) {
    expr = expr.trim();
    if (expr === 'true') return true;
    if (expr === 'false') return false;
    var parts = expr.split('.');
    for (var i = scopes.length - 1; i >= 0; i--) {
      var s = scopes[i];
      if (s && Object.prototype.hasOwnProperty.call(s, parts[0])) {
        var v = s[parts[0]];
        for (var j = 1; j < parts.length; j++) { v = v == null ? undefined : v[parts[j]]; }
        return v;
      }
    }
    return undefined;
  }

  function single(str) {
    var m = /^\s*\{\{\s*([^}]+?)\s*\}\}\s*$/.exec(str);
    return m ? m[1] : null;
  }

  function interpolate(str, scopes) {
    return str.replace(HOLE, function (_, e) {
      var v = lookup(e, scopes);
      return v == null ? '' : String(v);
    });
  }

  function processChildren(parent, scopes) {
    var kids = Array.prototype.slice.call(parent.childNodes);
    for (var i = 0; i < kids.length; i++) processNode(kids[i], scopes);
  }

  function unwrap(el) {
    var p = el.parentNode;
    while (el.firstChild) p.insertBefore(el.firstChild, el);
    p.removeChild(el);
  }

  function processNode(node, scopes) {
    if (node.nodeType === 3) {
      if (node.nodeValue.indexOf('{{') > -1) node.nodeValue = interpolate(node.nodeValue, scopes);
      return;
    }
    if (node.nodeType !== 1) return;
    var tag = node.localName;

    if (tag === 'sc-if') {
      var cond = lookup(single(node.getAttribute('value') || '') || 'false', scopes);
      if (cond) { processChildren(node, scopes); unwrap(node); }
      else node.parentNode.removeChild(node);
      return;
    }

    if (tag === 'sc-for') {
      var list = lookup(single(node.getAttribute('list') || '') || '', scopes) || [];
      var as = node.getAttribute('as') || 'item';
      var parent = node.parentNode;
      for (var k = 0; k < list.length; k++) {
        var frag = document.createDocumentFragment();
        for (var c = 0; c < node.childNodes.length; c++) frag.appendChild(node.childNodes[c].cloneNode(true));
        var scope = {}; scope[as] = list[k];
        processChildren(frag, scopes.concat([scope]));
        parent.insertBefore(frag, node);
      }
      parent.removeChild(node);
      return;
    }

    var attrs = Array.prototype.slice.call(node.attributes);
    for (var a = 0; a < attrs.length; a++) {
      var name = attrs[a].name, val = attrs[a].value;
      if (name.indexOf('hint-') === 0) { node.removeAttribute(name); continue; }
      if (name === 'onclick') {
        var fnExpr = single(val);
        node.removeAttribute(name);
        if (fnExpr) {
          var fn = lookup(fnExpr, scopes);
          if (typeof fn === 'function') node.addEventListener('click', fn);
        }
        continue;
      }
      if (val.indexOf('{{') > -1) {
        var only = single(val);
        if (only !== null) {
          var v = lookup(only, scopes);
          if (v === false || v == null) {
            if (name.indexOf('aria-') === 0) node.setAttribute(name, 'false');
            else node.setAttribute(name, '');
          } else node.setAttribute(name, String(v));
        } else node.setAttribute(name, interpolate(val, scopes));
      }
    }
    processChildren(tag === 'template' ? node.content : node, scopes);
  }

  function boot() {
    var tpl = document.getElementById('dc-tpl');
    var propsEl = document.getElementById('dc-props');
    var root = document.getElementById('dc-root');
    if (!tpl || !root) return;

    var props = {};
    var defs = {};
    if (propsEl) { try { defs = JSON.parse(propsEl.textContent || '{}'); } catch (e) { defs = {}; } }
    Object.keys(defs).forEach(function (k) {
      if (k.charAt(0) !== '$' && defs[k] && 'default' in defs[k]) props[k] = defs[k]['default'];
    });
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches && 'motion' in props) props.motion = false;

    var Comp = window.TSComponent || DCLogic;
    var comp = new Comp(props);
    comp.props = props;
    if (!comp.state) comp.state = {};

    function render() {
      var vals = {};
      try { vals = comp.renderVals() || {}; } catch (e) { console.error('[TERRASIGNAL] render error', e); }
      var frag = tpl.content.cloneNode(true);
      processChildren(frag, [vals]);
      var y = window.scrollY;
      root.replaceChildren(frag);
      window.scrollTo(0, y);
      if (typeof comp.afterRender === 'function') { try { comp.afterRender(root); } catch (e) { console.error(e); } }
    }
    comp.__render = render;
    window.TS = window.TS || {};
    window.TS.page = comp;
    render();
    var files = window.TS_DATA || null;
    if (files) {
      var keys = Object.keys(files);
      Promise.all(keys.map(function (k) { return window.TS.load(files[k]); })).then(function (vals) {
        var data = {}, got = false;
        keys.forEach(function (k, i) { if (vals[i]) { data[k] = vals[i]; got = true; } });
        if (got) { comp.data = data; render(); }
      });
    }
    if (location.hash) {
      var target = document.getElementById(location.hash.slice(1));
      if (target) target.scrollIntoView();
    }
  }

  window.TS = window.TS || {};
  window.TS.load = function (path) {
    return fetch(path, { cache: 'no-cache' }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
