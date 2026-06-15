"use strict";

const $ = (sel) => document.querySelector(sel);
let selectedId = null;

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url} -> ${r.status}`);
  return r.json();
}

function badge(kind, text) {
  return `<span class="badge b-${kind}">${text}</span>`;
}
function modBadge(m) { return badge(m === "Pass" ? "pass" : "fail", m); }
function triageBadge(t) {
  const map = { needs_review: ["review", "needs review"], auto_approve: ["approve", "auto approve"], auto_remove: ["remove", "auto remove"] };
  const [k, label] = map[t] || ["review", t];
  return badge(k, label);
}
function conf(v) {
  return `<div class="conf" title="${(v * 100).toFixed(0)}%"><i style="width:${(v * 100).toFixed(0)}%"></i></div>`;
}
function truncate(s, n) { return s.length > n ? s.slice(0, n - 1) + "…" : s; }
function esc(s) { return (s || "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c])); }

async function loadStats() {
  const s = await getJSON("/api/stats");
  const kpis = [
    { val: s.total, lbl: "comments classified" },
    { val: s.estimated_minutes_saved + " min", lbl: `est. moderator time saved (@${s.seconds_per_comment_assumed}s/comment)`, hero: true },
    { val: s.auto_handled_pct + "%", lbl: `auto-handled (${s.auto_handled} of ${s.total})` },
    { val: s.needs_review, lbl: "in human review queue" },
    { val: s.moderation.Fail, lbl: "flagged Fail" },
    { val: (s.baseline_agreement_rate * 100).toFixed(0) + "%", lbl: `agree w/ keyword rules (${s.disagreements} differ)` },
  ];
  $("#kpis").innerHTML = kpis.map((k) =>
    `<div class="kpi ${k.hero ? "hero" : ""}"><div class="val">${k.val}</div><div class="lbl">${k.lbl}</div></div>`
  ).join("");
}

function queryString() {
  const p = new URLSearchParams();
  const m = $("#f-moderation").value; if (m) p.set("moderation", m);
  const u = $("#f-usertype").value; if (u) p.set("user_type", u);
  const b = $("#f-bucket").value; if (b) p.set("bucket", b);
  if ($("#f-disagree").checked) p.set("disagreement", "true");
  const q = $("#f-q").value.trim(); if (q) p.set("q", q);
  return p.toString();
}

async function loadRows() {
  const items = await getJSON("/api/comments?" + queryString());
  const tbody = $("#rows");
  $("#empty").style.display = items.length ? "none" : "block";
  tbody.innerHTML = items.map((c) => `
    <tr data-id="${c.comment.id}" class="${c.comment.id === selectedId ? "selected" : ""}">
      <td><div>${esc(truncate(c.comment.body, 90))}</div><div class="flags">${esc(c.comment.author || "")} · ${esc(c.comment.post_title || "")}</div></td>
      <td>${modBadge(c.llm.moderation)}</td>
      <td>${c.llm.user_type}</td>
      <td>${conf(c.confidence)}</td>
      <td>${triageBadge(c.triage)}</td>
      <td>${c.disagreement ? '<span class="warn" title="LLM and keyword baseline disagree">●</span>' : ""}</td>
    </tr>`).join("");
  tbody.querySelectorAll("tr").forEach((tr) =>
    tr.addEventListener("click", () => showDetail(tr.dataset.id)));
}

async function showDetail(id) {
  selectedId = id;
  document.querySelectorAll("#rows tr").forEach((tr) =>
    tr.classList.toggle("selected", tr.dataset.id === id));
  const c = await getJSON("/api/comments/" + encodeURIComponent(id));
  const flags = c.llm.flags.length ? c.llm.flags.map((f) => `<code>${f}</code>`).join(" ") : '<span class="muted">none</span>';
  const dis = c.disagreement;
  $("#detail").innerHTML = `
    <h3>${esc(c.comment.author || "unknown")} <span class="muted" style="font-weight:400">· ${esc(c.comment.post_title || "")}</span></h3>
    <div class="muted">id ${c.comment.id} · ${esc(c.comment.timestamp || "")}</div>
    <div class="body">${esc(c.comment.body)}</div>
    <div style="margin-bottom:10px">Triage: ${triageBadge(c.triage)} ${dis ? '&nbsp; <span class="warn">⚠ disagrees with keyword baseline</span>' : ""}</div>
    <div class="cols">
      <div class="card ${dis ? "disagree" : ""}">
        <h4>LLM (mock)</h4>
        <div>${modBadge(c.llm.moderation)} &nbsp; ${conf(c.llm.moderation_confidence)}</div>
        <div class="reason">${esc(c.llm.moderation_reason)}</div>
        <div style="margin-top:10px"><b>${c.llm.user_type}</b> ${conf(c.llm.user_type_confidence)}</div>
        <div class="reason">${esc(c.llm.user_type_reason)}</div>
        <div class="reason" style="margin-top:10px">flags: ${flags}</div>
      </div>
      <div class="card">
        <h4>Keyword baseline</h4>
        <div>${modBadge(c.baseline.moderation)}</div>
        <div class="reason">matched terms: ${c.baseline.matched_terms.length ? c.baseline.matched_terms.map((t) => `<code>${esc(t)}</code>`).join(" ") : '<span class="muted">none</span>'}</div>
        <div style="margin-top:10px"><b>${c.baseline.user_type}</b></div>
        <div class="reason">rules can't read intent, sarcasm, or negation</div>
      </div>
    </div>`;
}

async function refreshAll() { await Promise.all([loadStats(), loadRows()]); }

["f-moderation", "f-usertype", "f-bucket"].forEach((id) =>
  $("#" + id).addEventListener("change", loadRows));
$("#f-disagree").addEventListener("change", loadRows);
$("#f-q").addEventListener("input", () => { clearTimeout(window._t); window._t = setTimeout(loadRows, 200); });

refreshAll();
