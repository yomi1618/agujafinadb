"use strict";
/* Aguja Fina - GUI. Habla con la API del mismo servidor (rutas relativas). */
const $ = (s, r = document) => r.querySelector(s);
const esc = v => String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const money = v => "$" + Number(v || 0).toFixed(2);
const fdate = s => (s ? String(s).slice(0, 10) : "");
const hoy = () => new Date().toLocaleDateString("sv-SE");
const nombre = c => [c.nombre, c.apellido].filter(Boolean).join(" ");
const app = $("#app"), dlg = $("#modal");
let draft = null, avisoAbono = null, prefill = "";

/* ---------- API ---------- */
function setStatus(ok) {
  const p = $("#api-status");
  p.className = "pill " + (ok ? "ok" : "off");
  p.textContent = ok ? "Conectado" : "Sin conexión";
}
async function api(path, method = "GET", body) {
  let r;
  try {
    r = await fetch(path, { method, headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined });
    setStatus(true);
  } catch {
    setStatus(false);
    throw { status: 0, data: { error: "No hay conexión con el servidor. Revisa que la API esté encendida." } };
  }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw { status: r.status, data };
  return data;
}

/* Traduce los errores de la API (y los nombres de restricciones de MySQL) a español */
const REGLAS = {
  uq_cliente_tipo_cliente_telefono: "Ya existe un cliente de ese tipo con ese teléfono.",
  uq_cliente_tipo_identificacion_numero_identificacion: "Ya existe un cliente con esa identificación.",
  ck_cliente_apellido_tipo: "La persona necesita apellido; la empresa no lleva apellido.",
  ck_cliente_cedula_persona: "La cédula solo aplica a personas.",
  ck_cliente_identificacion: "Identificación inválida: cédula de 10 dígitos o RUC de 13, junto con su tipo.",
  ck_cliente_ciudad_direccion: "Si hay dirección, la ciudad es obligatoria.",
  ck_pedido_descuento: "El descuento debe ser 0 o estar entre 5 y 10 %.",
  ck_pago_monto_positivo: "El monto debe ser mayor que cero.",
  ck_precio_servicio_rango: "El precio mínimo debe ser mayor que cero y no mayor que el máximo.",
  uq_precio_servicio_id_prenda_id_servicio_descripcion_arreglo: "Esa descripción ya existe para esta prenda y servicio.",
  uq_servicio_nombre_servicio: "Ya existe un servicio con ese nombre.",
  uq_prenda_tipo_prenda: "Ya existe una prenda con ese nombre."
};
function msg(e) {
  const d = e.data || {};
  if (e.status === 409) {
    const k = Object.keys(REGLAS).find(k => (d.detalle || "").includes(k));
    return k ? REGLAS[k] : (d.detalle || "").includes("foreign key") ? "No se puede eliminar: está en uso (tiene precios o pedidos asociados)." : (d.error || "Operación no permitida.");
  }
  if (e.status === 400) {
    const x = d.error;
    if (typeof x === "string") return x;
    if (x && typeof x === "object") return Object.entries(x).map(([k, v]) => `${k}: ${[].concat(v).join(" ")}`).join(". ");
  }
  return d.error || e.message || "Ocurrió un error inesperado.";
}

/* ---------- Piezas comunes ---------- */
function toast(t, tipo = "ok") {
  const d = document.createElement("div");
  d.className = "toast " + (tipo === "ok" ? "" : "err");
  d.textContent = t;
  $("#toasts").append(d);
  setTimeout(() => d.remove(), 6000);
}
function modal(titulo, cuerpo, onOk, onOpen) {
  dlg.innerHTML = `<form class="stack"><h2 id="modal-title">${esc(titulo)}</h2>${cuerpo}<p class="form-error" role="alert"></p><div class="row end"><button type="button" class="btn ghost" data-close>Cancelar</button><button class="btn accent">Aceptar</button></div></form>`;
  const f = $("form", dlg), er = $(".form-error", dlg);
  $("[data-close]", dlg).onclick = () => dlg.close();
  f.onsubmit = async ev => {
    ev.preventDefault();
    er.textContent = "";
    try { await onOk(f); dlg.close(); } catch (e) { er.textContent = e.data ? msg(e) : e.message; }
  };
  dlg.showModal();
  if (onOpen) onOpen(f);
  const first = f.querySelector("select,input");
  if (first) first.focus();
}
const loading = () => { app.onclick = null; app.innerHTML = '<div class="skeleton" aria-busy="true"></div>'.repeat(3); };
const fail = e => (app.innerHTML = `<div class="alert danger" role="alert">${esc(msg(e))}</div><a class="btn ghost" href="#/">Volver al inicio</a>`);
const alertaDeuda = d => (Number(d) > 0 ? `<p class="alert warn" role="status"><strong>Deuda:</strong> ${money(d)} por prendas ya entregadas.</p>` : "");
const ctx = (c, d) => `<div class="ctx"><div><p class="crumbs"><a href="#/">Inicio</a> / <a href="#/cliente/${c.id_cliente}">Ficha del cliente</a></p><h1>${esc(nombre(c))}</h1><p class="data">${esc(c.telefono)} (${esc(c.tipo_cliente)})</p></div>${alertaDeuda(d)}</div>`;
async function cargaCliente(id) {
  const [c, d] = await Promise.all([api("/clientes/" + id), api(`/clientes/${id}/deuda`)]);
  return [c, d.saldo_pendiente];
}

/* ---------- Buscador global (barra superior) ---------- */
const bBtn = $("#btn-buscar"), bPan = $("#panel-buscar"), bq = $("#bq"), bres = $("#bres");
const norm = s => String(s ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
/* 0 = el nombre empieza por lo escrito; 1 = una palabra del nombre empieza por eso; -1 = no coincide */
function rank(c, q) {
  const t = c.telefono || "";
  if (/^\d+$/.test(q)) return t.startsWith(q) ? 0 : q.length >= 3 && t.includes(q) ? 1 : -1;
  const n = norm(nombre(c));
  return n.startsWith(q) ? 0 : (" " + n).includes(" " + q) ? 1 : -1;
}
function panel(abrir, foco = true) {
  bPan.hidden = !abrir;
  bBtn.setAttribute("aria-expanded", abrir);
  if (abrir) { bq.focus(); bq.select(); buscar(); } else if (foco) bBtn.focus();
}
async function buscar() {
  const txt = bq.value.trim(), q = norm(txt);
  if (!q) { bres.innerHTML = '<p class="muted">Escribe un nombre o un teléfono. Salen primero los que empiezan por lo que escribes.</p>'; return; }
  bres.innerHTML = '<div class="skeleton"></div>';
  try {
    const l = (await api("/clientes/buscar?q=" + encodeURIComponent(txt))).map(c => [rank(c, q), c]).filter(x => x[0] >= 0)
      .sort((a, b) => a[0] - b[0] || nombre(a[1]).localeCompare(nombre(b[1]), "es")).map(x => x[1]);
    if (bq.value.trim() !== txt) return; /* llegó tarde: ya se escribió otra cosa */
    bres.innerHTML = l.length
      ? `<ul class="list">${l.map(c => `<li><a class="item" href="#/cliente/${c.id_cliente}"><span><strong>${esc(nombre(c))}</strong> <span class="badge">${esc(c.tipo_cliente)}</span></span><span class="data">${esc(c.telefono)}</span>${c.alerta_deuda ? `<span class="badge warn">Debe ${money(c.saldo_pendiente)}</span>` : ""}</a></li>`).join("")}</ul>`
      : `<div class="empty"><p>No hay clientes con «${esc(txt)}».</p><a class="btn" data-nuevo href="#/cliente/nuevo">Registrar nuevo cliente</a></div>`;
  } catch (e) { bres.innerHTML = `<div class="alert danger" role="alert">${esc(msg(e))}</div>`; }
}
let tBus = 0;
bBtn.onclick = () => panel(bPan.hidden);
bq.oninput = () => { clearTimeout(tBus); tBus = setTimeout(buscar, 250); };
bPan.addEventListener("keydown", e => { if (e.key === "Escape") panel(false); });
bPan.addEventListener("click", e => { if (e.target.closest("[data-nuevo]")) prefill = bq.value.trim(); if (e.target.closest("a")) panel(false, false); });

/* ---------- Inicio y Catálogo ---------- */
const plural = (n, u, p) => `${n} ${n === 1 ? u : p || u + "s"}`;
const rango = l => { if (!l.length) return ""; const mn = Math.min(...l.map(x => +x.precio_minimo)), mx = Math.max(...l.map(x => +x.precio_maximo)); return mn === mx ? money(mn) : `${money(mn)} a ${money(mx)}`; };
const resumen = t => `<p class="alert info" role="status">${t}</p>`;
const ok = (t, fn) => async f => { await fn(f); toast(t); route(); };
const porNombre = (a, b) => a.localeCompare(b, "es");

async function inicio() {
  const [pr, sv, ps, d] = await Promise.all([api("/prendas"), api("/servicios"), api("/precios-servicio"), api("/clientes/con-deuda")]);
  const tot = d.reduce((s, x) => s + Number(x.saldo_pendiente), 0);
  app.innerHTML = `<h1>Inicio</h1><div class="cards"><a class="tile" href="#/catalogo"><h2>Catálogo</h2><p>${plural(pr.length, "prenda")}, ${plural(sv.length, "servicio")} y ${plural(ps.length, "precio")}.</p></a><a class="tile" href="#/saldos"><h2>Saldos pendientes</h2><p>${d.length ? `${plural(d.length, "cliente")} con deuda, ${money(tot)} en total.` : "Ningún cliente tiene deuda ahora."}</p></a></div><p class="muted">Para atender a alguien usa «Buscar» en la barra superior.</p>`;
}

/* ---------- Catálogo en cascada: prendas > servicios > descripciones ---------- */
function nombreModal(titulo, valor, ayuda, fn) {
  modal(titulo, `${ayuda ? `<p class="muted">${ayuda}</p>` : ""}<label><span class="lbl">Nombre</span><input name="n" maxlength="80" value="${esc(valor)}"></label>`,
    ok("Guardado.", async f => { const n = f.n.value.trim(); if (!n) throw { message: "Escribe un nombre." }; await fn(n); }));
}
async function borrar(url, que) {
  if (!confirm(`¿Eliminar ${que}?`)) return;
  try { await api(url, "DELETE"); toast("Eliminado."); route(); } catch (e) { toast(msg(e), "err"); }
}
const camposPrecio = (d = {}) => `<label><span class="lbl">Descripción</span><input name="d" maxlength="120" value="${esc(d.descripcion_arreglo)}"></label><div class="grid12"><label class="c6"><span class="lbl">Precio mínimo</span><input name="mn" type="number" step="0.01" min="0.01" value="${d.precio_minimo ?? ""}"></label><label class="c6"><span class="lbl">Precio máximo</span><input name="mx" type="number" step="0.01" min="0.01" value="${d.precio_maximo ?? ""}"></label></div>`;
function leerPrecio(f) {
  const d = f.d.value.trim(), mn = Number(f.mn.value), mx = Number(f.mx.value);
  if (!d) throw { message: "Escribe la descripción." };
  if (!(mn > 0) || mx < mn) throw { message: "El mínimo debe ser mayor que cero y no mayor que el máximo." };
  return { descripcion_arreglo: d, precio_minimo: mn, precio_maximo: mx };
}

async function catalogo() {
  const [pr, sv, ps] = await Promise.all([api("/prendas"), api("/servicios"), api("/precios-servicio")]);
  pr.sort((a, b) => porNombre(a.tipo_prenda, b.tipo_prenda));
  app.innerHTML = `<p class="crumbs"><a href="#/">Inicio</a> / Catálogo</p><div class="row"><h1 class="grow">Catálogo</h1><button class="btn accent" data-a="nueva" type="button">Nueva prenda</button></div>` +
    resumen(`Hay ${plural(pr.length, "prenda")}, ${plural(sv.length, "servicio")} y ${plural(ps.length, "precio")}.`) +
    (pr.length ? `<ul class="list">${pr.map(p => { const l = ps.filter(x => x.id_prenda === p.id_prenda); return `<li class="item"><a class="grow" href="#/catalogo/${p.id_prenda}"><strong>${esc(p.tipo_prenda)}</strong><br><span class="muted">${plural(new Set(l.map(x => x.id_servicio)).size, "servicio")}, ${plural(l.length, "descripción", "descripciones")}</span></a><button class="btn ghost" data-a="ren" data-i="${p.id_prenda}" type="button">Renombrar</button><button class="btn ghost" data-a="del" data-i="${p.id_prenda}" type="button">Eliminar</button></li>`; }).join("")}</ul>` : '<p class="empty">Todavía no hay prendas. Agrega la primera.</p>');
  app.onclick = ev => {
    const b = ev.target.closest("[data-a]"); if (!b) return;
    const id = +b.dataset.i, p = pr.find(x => x.id_prenda === id);
    if (b.dataset.a === "nueva") nombreModal("Nueva prenda", "", "", n => api("/prendas", "POST", { tipo_prenda: n }));
    else if (b.dataset.a === "ren") nombreModal("Renombrar prenda", p.tipo_prenda, "", n => api("/prendas/" + id, "PUT", { tipo_prenda: n }));
    else borrar("/prendas/" + id, `la prenda «${p.tipo_prenda}»`);
  };
}

async function catalogoPrenda(id) {
  const [p, sv, ps] = await Promise.all([api("/prendas/" + id), api("/servicios"), api("/precios-servicio?id_prenda=" + id)]);
  const nom = Object.fromEntries(sv.map(s => [s.id_servicio, s.nombre_servicio]));
  const ids = [...new Set(ps.map(x => x.id_servicio))].sort((a, b) => porNombre(nom[a], nom[b]));
  app.innerHTML = `<p class="crumbs"><a href="#/">Inicio</a> / <a href="#/catalogo">Catálogo</a> / ${esc(p.tipo_prenda)}</p><div class="row"><h1 class="grow">${esc(p.tipo_prenda)}</h1><button class="btn accent" data-a="add" type="button">Agregar servicio</button></div>` +
    resumen(`${plural(ids.length, "servicio")} y ${plural(ps.length, "descripción", "descripciones")}${ps.length ? `, con precios de ${rango(ps)}` : ""}.`) +
    (ids.length ? `<ul class="list">${ids.map(s => { const l = ps.filter(x => x.id_servicio === s); return `<li><a class="item" href="#/catalogo/${id}/${s}"><span><strong>${esc(nom[s])}</strong><br><span class="muted">${plural(l.length, "descripción", "descripciones")}</span></span><span class="data">${rango(l)}</span></a></li>`; }).join("")}</ul>` : '<p class="empty">Esta prenda todavía no tiene servicios. Agrega el primero.</p>');
  app.onclick = ev => {
    if (!ev.target.closest("[data-a]")) return;
    const libres = sv.filter(s => !ids.includes(s.id_servicio)).sort((a, b) => porNombre(a.nombre_servicio, b.nombre_servicio));
    modal("Agregar servicio a " + p.tipo_prenda,
      `<label><span class="lbl">Servicio</span><select name="s">${libres.map(s => `<option value="${s.id_servicio}">${esc(s.nombre_servicio)}</option>`).join("")}<option value="">Servicio nuevo…</option></select></label><label id="wn"><span class="lbl">Nombre del servicio nuevo</span><input name="n" maxlength="80"></label>` + camposPrecio(),
      ok("Servicio agregado.", async f => {
        const pr = leerPrecio(f); let sid = Number(f.s.value);
        if (!sid) { const n = f.n.value.trim(); if (!n) throw { message: "Escribe el nombre del servicio." }; sid = (await api("/servicios", "POST", { nombre_servicio: n })).id_servicio; }
        await api("/precios-servicio", "POST", { id_prenda: id, id_servicio: sid, ...pr });
      }),
      f => { const t = () => { $("#wn").hidden = !!f.s.value; }; f.s.onchange = t; t(); });
  };
}

async function catalogoServicio(id, sid) {
  const [p, s, ps] = await Promise.all([api("/prendas/" + id), api("/servicios/" + sid), api(`/precios-servicio?id_prenda=${id}&id_servicio=${sid}`)]);
  ps.sort((a, b) => porNombre(a.descripcion_arreglo, b.descripcion_arreglo));
  app.innerHTML = `<p class="crumbs"><a href="#/">Inicio</a> / <a href="#/catalogo">Catálogo</a> / <a href="#/catalogo/${id}">${esc(p.tipo_prenda)}</a> / ${esc(s.nombre_servicio)}</p><div class="row"><h1 class="grow">${esc(s.nombre_servicio)} en ${esc(p.tipo_prenda)}</h1><button class="btn ghost" data-a="ren" type="button">Renombrar servicio</button><button class="btn accent" data-a="add" type="button">Agregar descripción</button></div>` +
    resumen(ps.length ? `${plural(ps.length, "descripción", "descripciones")}, con precios de ${rango(ps)}.` : "Este servicio ya no tiene descripciones en esta prenda.") +
    (ps.length ? `<div class="tbl"><table><thead><tr><th>Descripción</th><th>Mínimo</th><th>Máximo</th><th></th></tr></thead><tbody>${ps.map(x => `<tr><td>${esc(x.descripcion_arreglo)}</td><td class="num">${money(x.precio_minimo)}</td><td class="num">${money(x.precio_maximo)}</td><td><button class="btn ghost" data-a="edit" data-i="${x.id_precio}" type="button">Editar</button> <button class="btn ghost" data-a="del" data-i="${x.id_precio}" type="button">Eliminar</button></td></tr>`).join("")}</tbody></table></div>` : "");
  app.onclick = ev => {
    const b = ev.target.closest("[data-a]"); if (!b) return;
    const x = ps.find(y => y.id_precio === +b.dataset.i);
    if (b.dataset.a === "add") modal("Agregar descripción", camposPrecio(), ok("Descripción agregada.", f => api("/precios-servicio", "POST", { id_prenda: id, id_servicio: sid, ...leerPrecio(f) })));
    else if (b.dataset.a === "edit") modal("Editar descripción", camposPrecio(x), ok("Cambios guardados.", f => api("/precios-servicio/" + x.id_precio, "PUT", leerPrecio(f))));
    else if (b.dataset.a === "del") borrar("/precios-servicio/" + x.id_precio, `la descripción «${x.descripcion_arreglo}»`);
    else nombreModal("Renombrar servicio", s.nombre_servicio, "El cambio se aplica en todas las prendas que usan este servicio.", n => api("/servicios/" + sid, "PUT", { nombre_servicio: n }));
  };
}

/* ---------- S2 Cliente nuevo ---------- */
async function clienteForm(id) {
  const edit = Number.isInteger(id), base = edit ? await api("/clientes/" + id) : {};
  const pre = prefill; prefill = "";
  const esTel = /^\d/.test(pre) ? pre : "", nom = esTel ? "" : pre;
  app.innerHTML = `<h1>${edit ? "Editar cliente" : "Cliente nuevo"}</h1><form id="f" class="grid12" novalidate>
  <label class="c3"><span class="lbl">Tipo *</span><select name="tipo_cliente"><option value="persona">Persona</option><option value="empresa">Empresa</option></select></label>
  <label class="c6"><span class="lbl" id="l-nom">Nombre *</span><input name="nombre" value="${esc(nom)}"></label>
  <label class="c3" id="w-ap"><span class="lbl">Apellido *</span><input name="apellido"></label>
  <label class="c6"><span class="lbl">Teléfono *</span><input name="telefono" inputmode="tel" value="${esc(esTel)}"></label>
  <label class="c6"><span class="lbl">Email</span><input name="email" type="email"></label>
  <label class="c3"><span class="lbl">Tipo de identificación</span><select name="tipo_identificacion"><option value="">Sin identificación</option><option value="cedula">Cédula</option><option value="ruc">RUC</option></select></label>
  <label class="c3"><span class="lbl">Número</span><input name="numero_identificacion" inputmode="numeric"></label>
  <label class="c6"><span class="lbl">Dirección</span><input name="direccion"></label>
  <label class="c6"><span class="lbl">Ciudad</span><input name="ciudad"></label>
  <div id="dup" class="c12" aria-live="polite"></div><p class="form-error c12" role="alert"></p>
  <div class="c12 row end"><a class="btn ghost" href="${edit ? "#/cliente/" + id : "#/"}">Cancelar</a><button class="btn accent">Guardar cliente</button></div></form>`;
  const f = $("#f"), dup = $("#dup"), er = $(".form-error");
  if (edit) Object.entries(base).forEach(([k, v]) => { if (f[k] && v != null && k !== "fecha_registro") f[k].value = v; });
  let bloq = false;
  const tipo = () => {
    const per = f.tipo_cliente.value === "persona";
    $("#w-ap").hidden = !per;
    $("#l-nom").textContent = per ? "Nombre *" : "Razón social *";
    if (!per) f.apellido.value = "";
  };
  const chk = async () => {
    const tel = f.telefono.value.trim();
    dup.innerHTML = ""; bloq = false;
    if (!tel) return;
    try {
      const l = (await api("/clientes/buscar?q=" + encodeURIComponent(tel))).filter(c => c.telefono === tel && c.id_cliente !== id);
      const mismo = l.find(c => c.tipo_cliente === f.tipo_cliente.value), otro = l.find(c => c !== mismo);
      if (mismo) { bloq = true; dup.innerHTML = `<p class="alert danger">Ya existe ${esc(nombre(mismo))} con este teléfono. <a href="#/cliente/${mismo.id_cliente}">Abrir ficha</a></p>`; }
      else if (otro) dup.innerHTML = `<p class="alert info">Ya existe ${esc(nombre(otro))} (${esc(otro.tipo_cliente)}) con este teléfono${otro.alerta_deuda ? ` y debe ${money(otro.saldo_pendiente)}` : ""}. Puedes continuar.</p>`;
    } catch { /* el aviso es opcional */ }
  };
  f.tipo_cliente.onchange = () => { tipo(); chk(); };
  f.telefono.onchange = chk;
  tipo();
  f.onsubmit = async ev => {
    ev.preventDefault();
    er.textContent = "";
    const v = Object.fromEntries(new FormData(f).entries());
    Object.keys(v).forEach(k => { v[k] = v[k].trim(); if (!v[k]) { if (edit) v[k] = null; else delete v[k]; } });
    const per = v.tipo_cliente === "persona";
    const falta = !v.nombre ? "El nombre es obligatorio." : !v.telefono ? "El teléfono es obligatorio." : per && !v.apellido ? "El apellido es obligatorio para personas."
      : !!v.tipo_identificacion !== !!v.numero_identificacion ? "Indica tipo y número de identificación, o ninguno." : v.direccion && !v.ciudad ? "Si hay dirección, indica la ciudad." : "";
    if (falta) { er.textContent = falta; return; }
    if (bloq) { er.textContent = "Ya existe un cliente de este tipo con ese teléfono."; return; }
    try { const c = await api(edit ? "/clientes/" + id : "/clientes", edit ? "PUT" : "POST", v); toast("Cliente guardado."); location.hash = "#/cliente/" + c.id_cliente; }
    catch (e) { er.textContent = msg(e); }
  };
}

/* ---------- S3 Ficha del cliente ---------- */
async function ficha(id) {
  const [c, d, act, peds] = await Promise.all([api("/clientes/" + id), api(`/clientes/${id}/deuda`), api(`/clientes/${id}/pedidos?estado=activo`), api("/pedidos?id_cliente=" + id)]);
  const fechas = Object.fromEntries(peds.map(p => [p.id_pedido, fdate(p.fecha_hora_recepcion)]));
  const lin = await Promise.all(act.map(p => api(`/pedidos/${p.id_pedido}/lineas`)));
  const card = (p, l) => `<li><a class="item" href="#/pedido/${p.id_pedido}"><span><strong>Pedido #${p.id_pedido}</strong> <span class="badge ${p.estado === "entregado" ? "ok" : ""}">${esc(p.estado)}</span>${l ? `<br><span class="muted">${esc(l.map(x => `${x.tipo_prenda}: ${x.descripcion_arreglo}`).join("; "))}</span>` : ""}</span><span class="data">${fechas[p.id_pedido] || ""}<br>${p.lineas_entregadas}/${p.lineas_total} entregadas</span><span class="data">Total ${money(p.total_neto)}<br>Pagado ${money(p.monto_pagado)}<br>Saldo ${money(p.saldo_total_pendiente)}</span></a></li>`;
  app.innerHTML = ctx(c, d.saldo_pendiente) + `<div class="row"><a class="btn accent" href="#/cliente/${id}/pedido-nuevo">Nuevo pedido</a><a class="btn ghost" href="#/cliente/${id}/editar">Editar cliente</a></div><h2>Pedidos activos</h2>` +
    (act.length ? `<ul class="list">${act.map((p, i) => card(p, lin[i])).join("")}</ul>` : '<p class="empty">Este cliente no tiene pedidos activos.</p>') +
    `<details id="hist"><summary>Pedidos entregados</summary><div id="hist-body"></div></details>`;
  let cargado = false;
  $("#hist").ontoggle = async ev => {
    if (!ev.target.open || cargado) return;
    cargado = true;
    const b = $("#hist-body");
    b.innerHTML = '<div class="skeleton"></div>';
    try { const l = await api(`/clientes/${id}/pedidos?estado=entregado`); b.innerHTML = l.length ? `<ul class="list">${l.map(p => card(p, null)).join("")}</ul>` : '<p class="empty">Todavía no hay pedidos entregados.</p>'; }
    catch (e) { cargado = false; b.innerHTML = `<div class="alert danger" role="alert">${esc(msg(e))}</div>`; }
  };
}

/* ---------- S4 Nuevo pedido ---------- */
function modalLinea(prendas, onAdd) {
  modal("Agregar línea", `<label><span class="lbl">Prenda</span><select name="prenda"><option value="">Elige una prenda</option>${prendas.map(p => `<option value="${p.id_prenda}">${esc(p.tipo_prenda)}</option>`).join("")}</select></label>
  <label><span class="lbl">Servicio</span><select name="servicio" disabled></select></label>
  <label><span class="lbl">Descripción</span><select name="desc" disabled></select></label>
  <p id="rango" class="muted" aria-live="polite"></p>
  <label><span class="lbl">Precio acordado</span><input name="precio" type="number" step="0.01" disabled></label>
  <label><span class="lbl">Fecha estimada de entrega</span><input name="fecha" type="date" min="${hoy()}"></label>
  <label class="check"><input name="repuesto" type="checkbox"> Usa repuesto</label>
  <label><span class="lbl">Notas (color, patrón)</span><input name="notas" maxlength="255"></label>`,
  async f => {
    const o = f.desc.selectedOptions[0];
    if (!o || !o.value) throw { message: "Elige prenda, servicio y descripción." };
    const precio = Number(f.precio.value), mn = Number(o.dataset.min), mx = Number(o.dataset.max);
    if (!(precio >= mn && precio <= mx)) throw { message: `El precio debe estar entre ${money(mn)} y ${money(mx)}.` };
    if (!f.fecha.value || f.fecha.value < hoy()) throw { message: "Indica una fecha de entrega que no sea anterior a hoy." };
    onAdd({ id_precio: Number(o.value), etiqueta: `${f.prenda.selectedOptions[0].text}: ${f.servicio.selectedOptions[0].text}, ${o.text}`, precio, fecha: f.fecha.value, repuesto: f.repuesto.checked, notas: f.notas.value.trim() });
  },
  f => {
    const llena = (sel, items, vacio) => { sel.innerHTML = `<option value="">${vacio}</option>` + items; sel.disabled = !items; };
    f.prenda.onchange = async () => {
      llena(f.desc, "", ""); f.precio.disabled = true; $("#rango").textContent = "";
      if (!f.prenda.value) return llena(f.servicio, "", "");
      try { const s = await api(`/prendas/${f.prenda.value}/servicios`); llena(f.servicio, s.map(x => `<option value="${x.id_servicio}">${esc(x.nombre_servicio)}</option>`).join(""), "Elige un servicio"); }
      catch (e) { $(".form-error", dlg).textContent = msg(e); }
    };
    f.servicio.onchange = async () => {
      f.precio.disabled = true; $("#rango").textContent = "";
      if (!f.servicio.value) return llena(f.desc, "", "");
      try { const s = await api(`/prendas/${f.prenda.value}/servicios/${f.servicio.value}/descripciones`); llena(f.desc, s.map(x => `<option value="${x.id_precio}" data-min="${x.precio_minimo}" data-max="${x.precio_maximo}">${esc(x.descripcion_arreglo)}</option>`).join(""), "Elige una descripción"); }
      catch (e) { $(".form-error", dlg).textContent = msg(e); }
    };
    f.desc.onchange = () => {
      const o = f.desc.selectedOptions[0];
      if (!o || !o.value) { f.precio.disabled = true; $("#rango").textContent = ""; return; }
      $("#rango").textContent = `Rango permitido: ${money(o.dataset.min)} a ${money(o.dataset.max)}.`;
      Object.assign(f.precio, { disabled: false, min: o.dataset.min, max: o.dataset.max, value: o.dataset.min });
    };
  });
}
async function pedidoNuevo(idc) {
  const [[c, deuda], prendas] = await Promise.all([cargaCliente(idc), api("/prendas")]);
  if (!draft || draft.idc !== idc) draft = { idc, lineas: [], desc: 0, obs: "", monto: "", metodo: "efectivo" };
  app.innerHTML = ctx(c, deuda) + `<h2>Nuevo pedido</h2><div class="split"><div class="stack">
  <div><div id="lineas" aria-live="polite"></div><button class="btn" id="add" type="button">Agregar línea</button></div>
  <label><span class="lbl">Observaciones del pedido (opcional)</span><input id="obs" maxlength="255" value="${esc(draft.obs)}"></label>
  <div class="grid12"><label class="c6 check"><input id="usaDesc" type="checkbox" ${draft.desc ? "checked" : ""}> Aplicar descuento</label><label class="c6"><span class="lbl">Descuento (5 a 10 %)</span><input id="desc" type="number" min="5" max="10" step="0.01" value="${draft.desc || ""}" ${draft.desc ? "" : "disabled"}></label>
  <label class="c6"><span class="lbl">Abono (opcional)</span><input id="monto" type="number" min="0" step="0.01" value="${esc(draft.monto)}"></label>
  <label class="c6"><span class="lbl">Método del abono</span><select id="metodo"><option value="efectivo">Efectivo</option><option value="transferencia">Transferencia</option><option value="cheque">Cheque</option></select></label></div>
  <p class="form-error" role="alert" id="err"></p></div>
  <aside class="aside" aria-label="Resumen del pedido"><div id="res"></div><button class="btn accent full mt" id="guardar" type="button">Guardar pedido</button></aside></div>`;
  $("#metodo").value = draft.metodo;
  const calc = () => { const sub = draft.lineas.reduce((s, l) => s + l.precio, 0), dsc = Math.round(sub * draft.desc) / 100, tot = sub - dsc, ab = Number(draft.monto) || 0; return { sub, dsc, tot, ab }; };
  const pintar = () => {
    const { sub, dsc, tot, ab } = calc();
    $("#lineas").innerHTML = draft.lineas.length
      ? `<div class="tbl"><table><thead><tr><th>Línea</th><th>Precio</th><th>Entrega</th><th></th></tr></thead><tbody>${draft.lineas.map((l, i) => `<tr><td>${esc(l.etiqueta)}${l.repuesto ? ' <span class="badge">repuesto</span>' : ""}${l.notas ? `<br><span class="muted">${esc(l.notas)}</span>` : ""}</td><td class="num">${money(l.precio)}</td><td class="num">${l.fecha}</td><td><button type="button" class="btn ghost" data-q="${i}">Quitar</button></td></tr>`).join("")}</tbody></table></div>`
      : '<p class="empty">Este pedido todavía no tiene líneas. Agrega la primera.</p>';
    $("#res").innerHTML = `<h3>Resumen</h3><div class="sum"><span>Subtotal</span><span class="num">${money(sub)}</span></div><div class="sum"><span>Descuento</span><span class="num">-${money(dsc)}</span></div><div class="sum total"><span>Total</span><span class="num">${money(tot)}</span></div><div class="sum"><span>Abono</span><span class="num">${money(ab)}</span></div><div class="sum"><span>Saldo</span><span class="num">${money(tot - ab)}</span></div>`;
    $("#guardar").disabled = !draft.lineas.length;
  };
  $("#add").onclick = () => modalLinea(prendas, l => { draft.lineas.push(l); pintar(); });
  $("#lineas").onclick = ev => { const i = ev.target.dataset.q; if (i !== undefined) { draft.lineas.splice(i, 1); pintar(); } };
  $("#obs").oninput = ev => (draft.obs = ev.target.value);
  $("#usaDesc").onchange = ev => { $("#desc").disabled = !ev.target.checked; if (!ev.target.checked) { $("#desc").value = ""; draft.desc = 0; } else { $("#desc").value = 5; draft.desc = 5; } pintar(); };
  $("#desc").oninput = ev => { draft.desc = Number(ev.target.value) || 0; pintar(); };
  $("#monto").oninput = ev => { draft.monto = ev.target.value; pintar(); };
  $("#metodo").onchange = ev => (draft.metodo = ev.target.value);
  $("#guardar").onclick = async () => {
    const er = $("#err"), { tot, ab } = calc(), b = $("#guardar");
    er.textContent = "";
    if (draft.desc && (draft.desc < 5 || draft.desc > 10)) { er.textContent = "El descuento debe estar entre 5 y 10 %."; return; }
    if (ab > tot) { er.textContent = "El abono no puede superar el total del pedido."; return; }
    b.disabled = true;
    try {
      const r = await api("/pedidos", "POST", { id_cliente: idc, descuento_porcentaje: draft.desc, observaciones_pedido: draft.obs.trim() || undefined,
        detalles: draft.lineas.map(l => ({ id_precio: l.id_precio, precio_acordado: l.precio, fecha_entrega_estimada: l.fecha, usa_repuesto: l.repuesto, notas: l.notas || undefined })) });
      const id = r.pedido.id_pedido, metodo = draft.metodo;
      draft = null;
      if (ab > 0) {
        try { await api("/pagos", "POST", { id_pedido: id, monto: ab, tipo_pago: "adelanto", metodo_pago: metodo }); toast("Pedido y abono guardados."); }
        catch { avisoAbono = { id, monto: ab, metodo }; }
      } else toast("Pedido guardado.");
      location.hash = "#/pedido/" + id;
    } catch (e) { er.textContent = msg(e); b.disabled = false; }
  };
  pintar();
}

/* ---------- S5 Detalle del pedido ---------- */
function pagar(id, saldo, tipo, pre = {}) {
  modal("Registrar pago", `<p class="muted">Saldo pendiente: ${money(saldo)}</p><label><span class="lbl">Monto</span><input name="monto" type="number" step="0.01" min="0.01" max="${saldo}" value="${pre.monto || ""}"></label><label><span class="lbl">Método</span><select name="metodo"><option value="efectivo">Efectivo</option><option value="transferencia">Transferencia</option><option value="cheque">Cheque</option></select></label>`,
  async f => {
    const m = Number(f.monto.value);
    if (!(m > 0) || m > saldo) throw { message: `El monto debe ser mayor que cero y no superar ${money(saldo)}.` };
    await api("/pagos", "POST", { id_pedido: id, monto: m, tipo_pago: tipo, metodo_pago: f.metodo.value });
    avisoAbono = null; toast("Pago registrado."); route();
  }, f => { if (pre.metodo) f.metodo.value = pre.metodo; });
}
async function pedido(id) {
  const [p, r, l, pg, en] = await Promise.all([api("/pedidos/" + id), api(`/pedidos/${id}/resumen`), api(`/pedidos/${id}/lineas`), api("/pagos?id_pedido=" + id), api("/entregas?id_pedido=" + id)]);
  const [c, d] = await cargaCliente(p.id_cliente);
  const todo = r.lineas_entregadas === r.lineas_total, saldo = Number(r.saldo_total_pendiente), tipo = todo ? "saldo_final" : "adelanto";
  const retry = avisoAbono && avisoAbono.id === id ? `<div class="alert danger" role="alert">El pedido se guardó, pero el abono de ${money(avisoAbono.monto)} no se registró. <button class="btn" id="reint" type="button">Reintentar abono</button></div>` : "";
  app.innerHTML = ctx(c, d) + retry + `<h2>Pedido #${id} <span class="badge ${r.estado === "entregado" ? "ok" : ""}">${esc(r.estado)}</span></h2><p class="muted">Recibido el ${fdate(p.fecha_hora_recepcion)}${p.observaciones_pedido ? `. ${esc(p.observaciones_pedido)}` : ""}</p>
  <div class="split"><div><div class="tbl"><table><thead><tr><th>Línea</th><th>Precio</th><th>Entrega estimada</th><th>Estado</th></tr></thead><tbody>${l.map(x => `<tr><td>${esc(x.tipo_prenda)}: ${esc(x.nombre_servicio)}, ${esc(x.descripcion_arreglo)}${x.usa_repuesto ? ' <span class="badge">repuesto</span>' : ""}${x.notas ? `<br><span class="muted">${esc(x.notas)}</span>` : ""}</td><td class="num">${money(x.precio_acordado)}</td><td class="num">${x.fecha_entrega_estimada}</td><td>${x.entregada ? `Entregada (entrega #${x.id_entrega})` : "Pendiente"}</td></tr>`).join("")}</tbody></table></div>
  <h3>Pagos</h3>${pg.length ? `<ul class="list">${pg.map(x => `<li class="item"><span>${esc(x.tipo_pago === "adelanto" ? "Adelanto" : "Saldo final")} (${esc(x.metodo_pago)})</span><span class="data">${fdate(x.fecha_hora_pago)}</span><span class="num">${money(x.monto)}</span></li>`).join("")}</ul>` : '<p class="muted">Todavía no hay pagos.</p>'}
  <h3>Entregas</h3>${en.length ? `<ul class="list">${en.map(x => `<li class="item"><span>Entrega #${x.id_entrega}: ${esc(l.filter(y => y.id_entrega === x.id_entrega).map(y => y.tipo_prenda).join(", "))}${x.observaciones_entrega ? `<br><span class="muted">${esc(x.observaciones_entrega)}</span>` : ""}${x.motivo_deuda ? `<br><span class="muted">Motivo de deuda: ${esc(x.motivo_deuda)}</span>` : ""}</span><span class="data">${fdate(x.fecha_hora_entrega)}</span></li>`).join("")}</ul>` : '<p class="muted">Todavía no hay entregas.</p>'}</div>
  <aside class="aside" aria-label="Resumen del pedido"><h3>Resumen</h3><div class="sum"><span>Subtotal</span><span class="num">${money(r.subtotal)}</span></div><div class="sum"><span>Descuento</span><span class="num">-${money(r.descuento_monto)}</span></div><div class="sum total"><span>Total neto</span><span class="num">${money(r.total_neto)}</span></div><div class="sum"><span>Pagado</span><span class="num">${money(r.monto_pagado)}</span></div><div class="sum"><span>Saldo pendiente</span><span class="num">${money(saldo)}</span></div>${Number(r.deuda_exigible) > 0 ? `<div class="sum deuda"><span>Deuda por prendas entregadas</span><span class="num">${money(r.deuda_exigible)}</span></div>` : ""}
  <div class="stack mt"><button class="btn" id="pagar" type="button" ${saldo > 0 ? "" : "disabled"}>Registrar pago</button>${todo ? "" : `<a class="btn accent" href="#/pedido/${id}/entrega">Entregar prendas</a>`}</div></aside></div>`;
  $("#pagar").onclick = () => pagar(id, saldo, tipo);
  const re = $("#reint"); if (re) re.onclick = () => pagar(id, saldo, "adelanto", avisoAbono);
}

/* ---------- S6 Entrega ---------- */
async function entrega(id) {
  const [p, r, l] = await Promise.all([api("/pedidos/" + id), api(`/pedidos/${id}/resumen`), api(`/pedidos/${id}/lineas`)]);
  const [c, d] = await cargaCliente(p.id_cliente);
  const pend = l.filter(x => !x.entregada);
  if (!pend.length) { app.innerHTML = ctx(c, d) + `<p class="empty">Todas las prendas de este pedido ya fueron entregadas.</p><a class="btn" href="#/pedido/${id}">Volver al pedido</a>`; return; }
  app.innerHTML = ctx(c, d) + `<h2>Entrega del pedido #${id}</h2><form id="f" class="split"><div class="stack">
  <fieldset class="stack plain"><legend class="lbl">Prendas que se entregan</legend>${l.map(x => `<label class="check"><input type="checkbox" name="lin" value="${x.id_detalle}" ${x.entregada ? "disabled" : ""}> <span>${esc(x.tipo_prenda)}: ${esc(x.descripcion_arreglo)} <span class="num">${money(x.precio_acordado)}</span>${x.entregada ? ` <span class="badge ok">Entregada (entrega #${x.id_entrega})</span>` : ""}</span></label>`).join("")}</fieldset>
  <div><button class="btn ghost" type="button" id="todas">Seleccionar todas las pendientes</button></div>
  <label><span class="lbl">Observaciones de la entrega (qué prendas se llevan)</span><input name="obs" maxlength="255"></label>
  <div class="grid12"><label class="c6"><span class="lbl">Pago al entregar (opcional)</span><input name="monto" type="number" min="0" step="0.01"></label><label class="c6"><span class="lbl">Método</span><select name="metodo"><option value="efectivo">Efectivo</option><option value="transferencia">Transferencia</option><option value="cheque">Cheque</option></select></label></div>
  <div><button class="btn ghost" type="button" id="cobrar">Cobrar saldo completo</button></div>
  <label id="w-mot" hidden><span class="lbl">Motivo de la deuda *</span><input name="motivo" maxlength="255"></label><p class="form-error" role="alert" id="err"></p></div>
  <aside class="aside" aria-label="Resumen de la entrega"><h3>Resumen</h3><div id="res"></div><button class="btn accent full mt" id="ok" disabled>Confirmar entrega</button></aside></form>`;
  const f = $("#f"), subt = Number(r.subtotal), dmon = Number(r.descuento_monto);
  let forzar = false;
  const checks = () => [...f.querySelectorAll('[name=lin]:not(:disabled)')];
  const calc = () => {
    const sel = checks().filter(x => x.checked).map(x => Number(x.value));
    const ent = l.filter(x => x.entregada || sel.includes(x.id_detalle)).reduce((s, x) => s + Number(x.precio_acordado), 0);
    const todas = l.every(x => x.entregada || sel.includes(x.id_detalle));
    const dEnt = todas ? dmon : subt ? Math.round(dmon * (ent / subt) * 100) / 100 : 0;
    const pagado = Number(r.monto_pagado) + (Number(f.monto.value) || 0);
    return { sel, ent, dEnt, pagado, deuda: Math.max(ent - dEnt - pagado, 0), saldo: Number(r.total_neto) - pagado };
  };
  const pintar = () => {
    const k = calc();
    $("#res").innerHTML = `<div class="sum"><span>Prendas por entregar</span><span class="num">${k.sel.length}</span></div><div class="sum"><span>Total del pedido</span><span class="num">${money(r.total_neto)}</span></div><div class="sum"><span>Pagado con esta entrega</span><span class="num">${money(k.pagado)}</span></div><div class="sum total"><span>Saldo del pedido</span><span class="num">${money(k.saldo)}</span></div>${k.deuda > 0 ? `<div class="sum deuda"><span>Deuda tras entregar</span><span class="num">${money(k.deuda)}</span></div>` : ""}`;
    $("#w-mot").hidden = !(k.deuda > 0 || forzar);
    $("#ok").disabled = !k.sel.length;
  };
  f.addEventListener("input", pintar);
  $("#todas").onclick = () => { checks().forEach(x => (x.checked = true)); pintar(); };
  $("#cobrar").onclick = () => { f.monto.value = Math.max(Number(r.saldo_total_pendiente), 0).toFixed(2); pintar(); };
  f.onsubmit = async ev => {
    ev.preventDefault();
    const k = calc(), er = $("#err"), mot = f.motivo.value.trim(), monto = Number(f.monto.value) || 0;
    er.textContent = "";
    if (!$("#w-mot").hidden && !mot) { er.textContent = "Escribe el motivo de la deuda."; return; }
    const body = { lineas: k.sel, observaciones_entrega: f.obs.value.trim() || undefined, motivo_deuda: mot || undefined };
    if (monto > 0) body.pago = { monto, metodo_pago: f.metodo.value };
    if (k.deuda > 0 && !confirm(`Esta entrega deja una deuda de ${money(k.deuda)}. ¿Confirmas?`)) return;
    $("#ok").disabled = true;
    try { await api(`/pedidos/${id}/entregas`, "POST", body); toast("Entrega registrada."); location.hash = "#/pedido/" + id; }
    catch (e) { er.textContent = msg(e); if (e.status === 400 && /motivo_deuda/.test(JSON.stringify(e.data))) { forzar = true; pintar(); } $("#ok").disabled = false; }
  };
  pintar();
}

/* ---------- S7 Saldos pendientes ---------- */
async function saldos() {
  const l = await api("/clientes/con-deuda");
  app.innerHTML = "<h1>Saldos pendientes</h1>" + (l.length
    ? `<div class="tbl"><table><thead><tr><th>Cliente</th><th>Tipo</th><th>Teléfono</th><th>Saldo</th></tr></thead><tbody>${l.map(c => `<tr><td><a href="#/cliente/${c.id_cliente}">${esc(nombre(c))}</a></td><td>${esc(c.tipo_cliente)}</td><td class="num">${esc(c.telefono)}</td><td class="num">${money(c.saldo_pendiente)}</td></tr>`).join("")}</tbody></table></div>`
    : '<p class="empty">Ningún cliente tiene saldo pendiente.</p>');
}

/* ---------- Rutas ---------- */
const rutas = [[/^#\/$/, inicio], [/^#\/catalogo$/, catalogo], [/^#\/catalogo\/(\d+)$/, catalogoPrenda], [/^#\/catalogo\/(\d+)\/(\d+)$/, catalogoServicio], [/^#\/cliente\/nuevo$/, clienteForm], [/^#\/cliente\/(\d+)\/editar$/, clienteForm], [/^#\/cliente\/(\d+)$/, ficha], [/^#\/cliente\/(\d+)\/pedido-nuevo$/, pedidoNuevo],
  [/^#\/pedido\/(\d+)$/, pedido], [/^#\/pedido\/(\d+)\/entrega$/, entrega], [/^#\/saldos$/, saldos]];
async function route() {
  const h = location.hash || "#/";
  if (h === "#app") return;
  for (const [re, fn] of rutas) {
    const m = h.match(re);
    if (!m) continue;
    document.querySelectorAll(".nav a").forEach(a => a.classList.toggle("on", a.getAttribute("href") === (h.startsWith("#/catalogo") ? "#/catalogo" : h === "#/saldos" ? "#/saldos" : "#/")));
    loading();
    try { await fn(...m.slice(1).map(Number)); } catch (e) { fail(e); }
    return;
  }
  location.hash = "#/";
}
addEventListener("hashchange", route);
route();
