/* data.js — load + minimal-validate data/schedule.json (no frameworks). */

"use strict";

const TOP_KEYS = ["days", "events", "students", "pages"];

async function load_schedule(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("تعذر تحميل بيانات الجدول (خطأ " + response.status + ")");
  }
  const data = await response.json();
  const missing = TOP_KEYS.filter((key) => !(key in data));
  if (missing.length > 0) {
    throw new Error("بيانات الجدول ناقصة: " + missing.join(", "));
  }
  if (!Array.isArray(data.events) || !Array.isArray(data.students)) {
    throw new Error("بنية بيانات الجدول غير صالحة");
  }
  return data;
}

async function load_meta(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    return null;
  }
  return response.json();
}
