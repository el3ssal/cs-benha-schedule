/* app.js — selections + rendering (vanilla, snake_case identifiers). */

"use strict";

const STORAGE_KEY = "cs_benha_schedule_selection_v1";
const WEEKDAY_NAMES = {
  0: "الأحد",
  1: "الإثنين",
  2: "الثلاثاء",
  3: "الأربعاء",
  4: "الخميس",
  5: "الجمعة",
  6: "السبت",
};

const dom = {};
let schedule_data = null;
let current_selection = { level: "", cat: "", section: "" };

function escape_html(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function minutes_of(time_value) {
  const parts = String(time_value).split(":");
  return Number(parts[0]) * 60 + Number(parts[1]);
}

function get_dom() {
  for (const id of [
    "level_pills", "level_select",
    "cat_pills", "cat_select",
    "section_pills", "section_select",
    "selection_summary", "today_card", "week_grid",
    "full_week_toggle", "print_button", "share_button",
    "update_button", "update_dialog", "action_status", "meta_line",
  ]) {
    dom[id] = document.getElementById(id);
  }
}

function cat_of_student(student) {
  return student.level === "3" || student.level === "4"
    ? student.track
    : student.group;
}

function event_matches(event, selection) {
  if (event.level !== selection.level) return false;
  const event_cat = event.level === "3" || event.level === "4"
    ? event.track
    : event.group;
  return event_cat === selection.cat && event.section === selection.section;
}

function read_params() {
  const params = new URLSearchParams(window.location.search);
  return {
    level: params.get("level") || "",
    cat: params.get("cat") || "",
    section: params.get("section") || "",
  };
}

function load_stored() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { level: "", cat: "", section: "" };
    const parsed = JSON.parse(raw);
    return {
      level: String(parsed.level || ""),
      cat: String(parsed.cat || ""),
      section: String(parsed.section || ""),
    };
  } catch (err) {
    return { level: "", cat: "", section: "" };
  }
}

function persist_selection() {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(current_selection));
  } catch (err) { /* storage may be unavailable — selection still works */ }
  const params = new URLSearchParams();
  if (current_selection.level) params.set("level", current_selection.level);
  if (current_selection.cat) params.set("cat", current_selection.cat);
  if (current_selection.section) params.set("section", current_selection.section);
  const query = params.toString();
  window.history.replaceState(null, "", query ? "?" + query : window.location.pathname);
}

function fill_controls(select_el, pills_el, options, current_value, field_name) {
  select_el.innerHTML = "";
  pills_el.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "— اختر —";
  select_el.appendChild(placeholder);
  for (const option_value of options) {
    const option_el = document.createElement("option");
    option_el.value = option_value;
    option_el.textContent = option_value;
    if (option_value === current_value) option_el.selected = true;
    select_el.appendChild(option_el);

    const pill = document.createElement("button");
    pill.type = "button";
    pill.className = "pill";
    pill.textContent = option_value;
    pill.setAttribute("aria-pressed", option_value === current_value ? "true" : "false");
    pill.addEventListener("click", () => set_field(field_name, option_value));
    pills_el.appendChild(pill);
  }
}

function level_options() {
  const levels = [];
  for (const student of schedule_data.students) {
    if (!levels.includes(student.level)) levels.push(student.level);
  }
  return levels.sort();
}

function cat_options(level) {
  const cats = [];
  for (const student of schedule_data.students) {
    if (student.level !== level) continue;
    const cat = cat_of_student(student);
    if (!cats.includes(cat)) cats.push(cat);
  }
  const numeric = cats.every((cat) => /^\d+$/.test(cat));
  return numeric ? cats.sort((a, b) => Number(a) - Number(b)) : cats.sort();
}

function section_options(level, cat) {
  const sections = [];
  for (const student of schedule_data.students) {
    if (student.level !== level || cat_of_student(student) !== cat) continue;
    if (!sections.includes(student.section)) sections.push(student.section);
  }
  return sections.sort((a, b) => Number(a) - Number(b));
}

function set_field(field_name, value) {
  if (field_name === "level") {
    current_selection = { level: value, cat: "", section: "" };
  } else if (field_name === "cat") {
    current_selection = { level: current_selection.level, cat: value, section: "" };
  } else {
    current_selection = { level: current_selection.level, cat: current_selection.cat, section: value };
  }
  persist_selection();
  render_controls();
  render_results();
}

function render_controls() {
  const levels = level_options();
  if (current_selection.level && !levels.includes(current_selection.level)) {
    current_selection.level = "";
  }
  fill_controls(dom.level_select, dom.level_pills, levels, current_selection.level, "level");

  const cats = current_selection.level ? cat_options(current_selection.level) : [];
  if (current_selection.cat && !cats.includes(current_selection.cat)) {
    current_selection.cat = "";
  }
  fill_controls(dom.cat_select, dom.cat_pills, cats, current_selection.cat, "cat");

  const sections = current_selection.cat
    ? section_options(current_selection.level, current_selection.cat)
    : [];
  if (current_selection.section && !sections.includes(current_selection.section)) {
    current_selection.section = "";
  }
  fill_controls(dom.section_select, dom.section_pills, sections, current_selection.section, "section");

  const parts = [];
  if (current_selection.level) parts.push("المستوى " + escape_html(current_selection.level));
  if (current_selection.cat) parts.push(escape_html(current_selection.cat));
  if (current_selection.section) parts.push("سكشن " + escape_html(current_selection.section));
  dom.selection_summary.innerHTML = parts.length > 0
    ? "اختيارك الحالي: <strong>" + parts.join(" · ") + "</strong>"
    : "اختر المستوى ثم المجموعة/التخصص ثم السكشن لعرض جدولك.";
}

function event_card_html(event) {
  return (
    '<div class="event">' +
    '<div class="event-time"><span class="time">' +
    escape_html(event.start) + " - " + escape_html(event.end) +
    "</span></div>" +
    '<p class="event-text">' + escape_html(event.text) + "</p>" +
    "</div>"
  );
}

function events_for_day(day_name) {
  return schedule_data.events
    .filter((event) => event.day === day_name && event_matches(event, current_selection))
    .sort((a, b) => minutes_of(a.start) - minutes_of(b.start));
}

function render_results() {
  if (!current_selection.section) {
    dom.today_card.innerHTML = "<h2>مواعيد اليوم</h2><p class=\"state\">أكمل اختيارك أعلاه لعرض مواعيدك.</p>";
    dom.week_grid.innerHTML = "";
    return;
  }
  const today_name = WEEKDAY_NAMES[new Date().getDay()];
  const today_events = today_name === "الجمعة" ? [] : events_for_day(today_name);
  let today_html = "<h2>مواعيد اليوم (" + escape_html(today_name) + ")</h2>";
  if (today_events.length === 0) {
    today_html += "<p class=\"state\">لا توجد محاضرات اليوم.</p>";
  } else {
    today_html += today_events.map(event_card_html).join("");
  }
  dom.today_card.innerHTML = today_html;

  const show_all = dom.full_week_toggle.checked;
  const today_index = schedule_data.days.indexOf(today_name);
  let week_html = "";
  for (const day_name of schedule_data.days) {
    if (!show_all && today_index >= 0 && schedule_data.days.indexOf(day_name) < today_index) {
      continue;
    }
    const day_events = events_for_day(day_name);
    week_html += '<article class="card day-card"><h3>' + escape_html(day_name) + "</h3>";
    week_html += day_events.length === 0
      ? '<p class="state">لا توجد محاضرات.</p>'
      : day_events.map(event_card_html).join("");
    week_html += "</article>";
  }
  dom.week_grid.innerHTML = week_html;
}

function render_meta(meta) {
  if (!meta) {
    dom.meta_line.textContent = "تعذر تحميل بيانات التحديث.";
    return;
  }
  const date_part = String(meta.generated_at || "").slice(0, 10);
  dom.meta_line.textContent =
    "آخر تحديث: " + date_part +
    " · " + meta.events_count + " محاضرة · " + meta.students_count + " سكشن";
}

function bind_static_events() {
  dom.level_select.addEventListener("change", (ev) => set_field("level", ev.target.value));
  dom.cat_select.addEventListener("change", (ev) => set_field("cat", ev.target.value));
  dom.section_select.addEventListener("change", (ev) => set_field("section", ev.target.value));
  dom.full_week_toggle.addEventListener("change", render_results);
  dom.print_button.addEventListener("click", () => window.print());
  dom.update_button.addEventListener("click", () => dom.update_dialog.showModal());
  dom.share_button.addEventListener("click", async () => {
    const share_url = window.location.href;
    const share_data = { title: document.title, text: "جدولي الدراسي", url: share_url };
    try {
      if (navigator.share) {
        await navigator.share(share_data);
        dom.action_status.textContent = "";
      } else if (navigator.clipboard) {
        await navigator.clipboard.writeText(share_url);
        dom.action_status.textContent = "نُسخ رابط اختيارك — شاركه مع زملائك.";
      } else {
        dom.action_status.textContent = share_url;
      }
    } catch (err) {
      dom.action_status.textContent = "";
    }
  });
}

function register_service_worker() {
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("./sw.js").catch(() => {});
    });
  }
}

async function init_app() {
  get_dom();
  bind_static_events();
  try {
    schedule_data = await load_schedule("./data/schedule.json");
  } catch (err) {
    dom.today_card.innerHTML =
      "<h2>مواعيد اليوم</h2><p class=\"state-error\">" + escape_html(err.message) + "</p>";
    dom.week_grid.innerHTML = "";
    return;
  }
  const from_params = read_params();
  current_selection = from_params.level ? from_params : load_stored();
  render_controls();
  render_results();
  load_meta("./data/meta.json").then(render_meta).catch(() => render_meta(null));
  register_service_worker();
}

document.addEventListener("DOMContentLoaded", init_app);
