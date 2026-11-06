(() => {
  "use strict";

  // Local dev talks to uvicorn on :2200; anything else uses the deployed API.
  const isLocal = ["localhost", "127.0.0.1", ""].includes(location.hostname);
  const API_BASE = isLocal ? "http://localhost:2200" : "https://mansik-santulan-score.onrender.com";
  let sessionId = null;

  const form = document.getElementById("predict-form");
  const submitBtn = document.getElementById("submit-btn");
  const resetBtn = document.getElementById("reset-btn");
  const errorRetryBtn = document.getElementById("error-retry-btn");

  const stateIdle = document.getElementById("state-idle");
  const stateLoading = document.getElementById("state-loading");
  const stateResult = document.getElementById("state-result");
  const stateError = document.getElementById("state-error");

  const scoreNumberEl = document.getElementById("score-number");
  const scoreBandEl = document.getElementById("score-band");
  const scoreContextEl = document.getElementById("score-context");
  const gaugeFill = document.getElementById("gauge-fill");
  const errorLabelEl = document.getElementById("error-label");
  const errorCopyEl = document.getElementById("error-copy");

  const GAUGE_ARC_LENGTH = 314; // approx pi * r(100)

  // ---------------------------------------------------------
  // Draw tick marks on both gauges (0..10, every 2 units)
  // ---------------------------------------------------------
  function drawTicks() {
    document.querySelectorAll(".gauge-ticks").forEach((g) => {
      g.innerHTML = "";
      const cx = 120, cy = 140, rOuter = 100, rInner = 90;
      for (let i = 0; i <= 10; i += 2) {
        const angle = Math.PI - (i / 10) * Math.PI; // 180deg -> 0deg
        const x1 = cx + rOuter * Math.cos(angle);
        const y1 = cy - rOuter * Math.sin(angle);
        const x2 = cx + rInner * Math.cos(angle);
        const y2 = cy - rInner * Math.sin(angle);
        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("x1", x1.toFixed(1));
        line.setAttribute("y1", y1.toFixed(1));
        line.setAttribute("x2", x2.toFixed(1));
        line.setAttribute("y2", y2.toFixed(1));
        g.appendChild(line);
      }
    });
  }
  drawTicks();

  // ---------------------------------------------------------
  // Segmented control (stress_level) wiring
  // ---------------------------------------------------------
  const segGroup = document.getElementById("stress_level_group");
  const stressHiddenInput = document.getElementById("stress_level");
  segGroup.querySelectorAll(".seg-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      segGroup.querySelectorAll(".seg-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      stressHiddenInput.value = btn.dataset.value;
      clearFieldError(stressHiddenInput);
    });
  });

  // ---------------------------------------------------------
  // Field-level error helpers
  // ---------------------------------------------------------
  function fieldWrapper(input) {
    return input.closest(".field");
  }

  function setFieldError(input, message) {
    const wrap = fieldWrapper(input);
    if (!wrap) return;
    wrap.classList.add("field-error");
    const msgEl = wrap.querySelector(".error-msg");
    if (msgEl) msgEl.textContent = message;
  }

  function clearFieldError(input) {
    const wrap = fieldWrapper(input);
    if (!wrap) return;
    wrap.classList.remove("field-error");
    const msgEl = wrap.querySelector(".error-msg");
    if (msgEl) msgEl.textContent = "";
  }

  function clearAllErrors() {
    form.querySelectorAll(".field").forEach((f) => f.classList.remove("field-error"));
    form.querySelectorAll(".error-msg").forEach((m) => (m.textContent = ""));
  }

  // ---------------------------------------------------------
  // Client-side validation mirroring the StudentData model
  // ---------------------------------------------------------
  function validate(payload) {
    const errors = [];

    const numericChecks = [
      ["age", 10, 100],
      ["avg_daily_usage_hours", 0, 24],
      ["daily_unlocks", 0, Infinity],
      ["study_hours", 0, 24],
      ["physical_activity_hours", 0, 24],
      ["sleep_hours_per_night", 0, 24],
    ];

    numericChecks.forEach(([key, min, max]) => {
      const input = document.getElementById(key);
      const val = payload[key];
      if (val === "" || val === null || Number.isNaN(val)) {
        errors.push([input, "This field is required."]);
      } else if (val < min || val > max) {
        errors.push([input, `Must be between ${min} and ${max === Infinity ? "0+" : max}.`]);
      }
    });

    ["gender", "country", "academic_level", "most_used_platform", "purpose_of_use"].forEach((key) => {
      const input = document.getElementById(key);
      if (!payload[key] || String(payload[key]).trim() === "") {
        errors.push([input, "This field is required."]);
      }
    });

    if (!payload.stress_level) {
      errors.push([stressHiddenInput, "Pick a stress level."]);
    }

    return errors;
  }

  // ---------------------------------------------------------
  // Gather form data into the exact StudentData shape
  // ---------------------------------------------------------
  function collectPayload() {
    const fd = new FormData(form);
    return {
      age: fd.get("age") === "" ? NaN : parseInt(fd.get("age"), 10),
      gender: fd.get("gender") || "",
      country: (fd.get("country") || "").trim(),
      academic_level: fd.get("academic_level") || "",
      most_used_platform: fd.get("most_used_platform") || "",
      purpose_of_use: fd.get("purpose_of_use") || "",
      avg_daily_usage_hours: fd.get("avg_daily_usage_hours") === "" ? NaN : parseFloat(fd.get("avg_daily_usage_hours")),
      daily_unlocks: fd.get("daily_unlocks") === "" ? NaN : parseInt(fd.get("daily_unlocks"), 10),
      study_hours: fd.get("study_hours") === "" ? NaN : parseFloat(fd.get("study_hours")),
      physical_activity_hours: fd.get("physical_activity_hours") === "" ? NaN : parseFloat(fd.get("physical_activity_hours")),
      sleep_hours_per_night: fd.get("sleep_hours_per_night") === "" ? NaN : parseFloat(fd.get("sleep_hours_per_night")),
      stress_level: fd.get("stress_level") || "",
    };
  }

  // ---------------------------------------------------------
  // UI state switching
  // ---------------------------------------------------------
  function showState(name) {
    [stateIdle, stateLoading, stateResult, stateError].forEach((el) => (el.hidden = true));
    ({ idle: stateIdle, loading: stateLoading, result: stateResult, error: stateError }[name]).hidden = false;
  }

  function setSubmitting(isSubmitting) {
    submitBtn.disabled = isSubmitting;
    submitBtn.classList.toggle("loading", isSubmitting);
  }

  function bandFor(score) {
    if (score < 4) {
      return {
        label: "Signal: strained",
        context: "Your responses suggest elevated strain right now. Small shifts in sleep or screen time can go a long way.",
      };
    }
    if (score < 7) {
      return {
        label: "Signal: balanced",
        context: "Your rhythm looks fairly steady, with some room to recover and reset.",
      };
    }
    return {
      label: "Signal: strong",
      context: "Your habits point to a well-supported, resilient baseline. Keep it up.",
    };
  }

  function renderResult(score, serverBand) {
    const clamped = Math.max(0, Math.min(10, score));
    const { label, context } = serverBand || bandFor(clamped);

    scoreNumberEl.textContent = score.toFixed(2);
    scoreBandEl.textContent = label;
    scoreContextEl.textContent = context;

    // reset then animate the arc fill on next frame
    gaugeFill.style.transition = "none";
    gaugeFill.style.strokeDashoffset = String(GAUGE_ARC_LENGTH);
    requestAnimationFrame(() => {
      gaugeFill.style.transition = "";
      const offset = GAUGE_ARC_LENGTH * (1 - clamped / 10);
      gaugeFill.style.strokeDashoffset = String(offset);
    });

    showState("result");
  }

  function renderError(label, copy) {
    errorLabelEl.textContent = label;
    errorCopyEl.textContent = copy;
    showState("error");
  }

  // ---------------------------------------------------------
  // Parse FastAPI / Pydantic 422 error responses into
  // field-level messages where possible
  // ---------------------------------------------------------
  function applyServerValidationErrors(detail) {
    if (!Array.isArray(detail)) return false;
    let matched = false;
    detail.forEach((err) => {
      const field = Array.isArray(err.loc) ? err.loc[err.loc.length - 1] : null;
      const input = field ? document.getElementById(field) : null;
      const target = field === "stress_level" ? stressHiddenInput : input;
      if (target) {
        setFieldError(target, err.msg || "Invalid value.");
        matched = true;
      }
    });
    return matched;
  }

  // ---------------------------------------------------------
  // Submit handler
  // ---------------------------------------------------------
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAllErrors();

    const payload = collectPayload();
    const clientErrors = validate(payload);

    if (clientErrors.length > 0) {
      clientErrors.forEach(([input, msg]) => input && setFieldError(input, msg));
      clientErrors[0][0]?.focus?.();
      return;
    }

    setSubmitting(true);
    showState("loading");

    try {
      const res = await fetch(`${API_BASE}/assess`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.status === 422) {
        const body = await res.json().catch(() => null);
        const matched = body && applyServerValidationErrors(body.detail);
        renderError(
          "Check your inputs",
          matched
            ? "The API rejected a few fields — details are marked on the form."
            : "The API rejected this submission. Please review your inputs and try again."
        );
        return;
      }

      if (!res.ok) {
        let detailMsg = `The API responded with status ${res.status}.`;
        const body = await res.json().catch(() => null);
        if (body && typeof body.detail === "string") detailMsg = body.detail;
        renderError("Prediction failed", detailMsg);
        return;
      }

      const data = await res.json();
      if (typeof data.predicted_mental_health_score !== "number") {
        renderError("Unexpected response", "The API responded, but the score was missing or malformed.");
        return;
      }

      renderResult(data.predicted_mental_health_score, {
        label: data.insights.band_label,
        context: data.insights.band_text,
      });
      sessionId = data.session_id;
      renderMindWell(data);
    } catch (err) {
      renderError(
        "Can't reach the server",
        `Couldn't connect to ${API_BASE}. If the server was idle it may take up to a minute to wake - please try again. (Local dev: uvicorn main:app --port 2200 --reload)`
      );
    } finally {
      setSubmitting(false);
    }
  });

  // live-clear errors as the user edits
  form.querySelectorAll("input, select").forEach((el) => {
    el.addEventListener("input", () => clearFieldError(el));
    el.addEventListener("change", () => clearFieldError(el));
  });

  resetBtn.addEventListener("click", () => {
    showState("idle");
    mindwell.hidden = true;
    sessionId = null;
    chatLog.innerHTML = "";
  });

  errorRetryBtn.addEventListener("click", () => {
    showState("idle");
  });
  // ---------------------------------------------------------
  // MindWell AI panel (insights, recommendations, plan, chat)
  // ---------------------------------------------------------
  const mindwell = document.getElementById("mindwell");
  const chatLog = document.getElementById("chat-log");
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const chatSend = document.getElementById("chat-send");

  // All dynamic text goes through textContent, never innerHTML.
  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }

  function fillList(id, items, emptyText) {
    const ul = document.getElementById(id);
    ul.replaceChildren();
    if (!items.length) ul.appendChild(el("li", "empty", emptyText));
    items.forEach((t) => ul.appendChild(typeof t === "string" ? el("li", "", t) : t));
  }

  function renderMindWell(data) {
    const ins = data.insights;
    document.getElementById("mw-disclaimer").textContent = ins.disclaimer;
    document.getElementById("mw-plain").textContent = ins.plain_language;
    fillList("mw-strengths", ins.strengths, "No clear strengths stood out in this set of answers.");
    fillList("mw-focus", ins.focus_areas, "Nothing flagged - nice work.");

    fillList("mw-whatif", ins.what_if.map((w) => {
      const li = el("li", "");
      li.append(`If ${w.change}: `, el("span", "delta", `${w.delta > 0 ? "+" : ""}${w.delta.toFixed(2)}`), " points in the model");
      return li;
    }), "Your habits already sit near the healthier end, so the model expects little change.");
    document.getElementById("mw-whatif-note").textContent = ins.what_if_note;
    document.getElementById("mw-band-note").textContent = ins.band_config_approved
      ? "" : "Score bands are a proposed, non-clinical framework (based on the training data's quartiles) and are awaiting approval.";

    const recs = document.getElementById("mw-recs");
    recs.replaceChildren();
    data.recommendations.forEach((r) => {
      const card = el("div", "rec-card");
      card.appendChild(el("h4", "", r.area === "social" ? "social media" : r.area));
      const ul = el("ul");
      r.tips.forEach((t) => ul.appendChild(el("li", "", t)));
      card.append(ul, el("span", "src", `Source: ${r.source}`));
      recs.appendChild(card);
    });

    const plan = document.getElementById("mw-plan");
    plan.replaceChildren();
    data.plan.forEach((d) => {
      const c = el("div", "day-card");
      c.append(el("span", "dno", `DAY ${d.day}`), el("h4", "", d.theme), el("p", "goal", d.daily_goal.replace(/^Day \d+: /, "")));
      const dl = el("dl");
      [["Sleep", d.sleep], ["Movement", d.activity], ["Study", d.study], ["Social media", d.social_media], ["Wellbeing", d.stress_note]]
        .forEach(([k, v]) => { dl.append(el("dt", "", k), el("dd", "", v)); });
      c.appendChild(dl);
      plan.appendChild(c);
    });

    chatLog.replaceChildren();
    addMsg("bot", "Hi, I'm MindWell AI. I can explain your score, suggest habit changes, or build a routine. I'm not a clinician or a substitute for professional help. What would you like to explore?");
    setTab("insights");
    mindwell.hidden = false;
    mindwell.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function setTab(name) {
    mindwell.querySelectorAll(".mw-tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
    mindwell.querySelectorAll(".mw-pane").forEach((p) => (p.hidden = p.dataset.pane !== name));
  }
  mindwell.querySelectorAll(".mw-tab").forEach((b) => b.addEventListener("click", () => setTab(b.dataset.tab)));

  function addMsg(role, text, extra) {
    const m = el("div", `msg ${role}${extra && extra.safety ? " safety" : ""}`);
    // render **bold** safely without innerHTML
    text.split(/(\*\*[^*]+\*\*)/).forEach((part) => {
      if (/^\*\*[^*]+\*\*$/.test(part)) m.appendChild(el("strong", "", part.slice(2, -2)));
      else m.appendChild(document.createTextNode(part));
    });
    if (extra && extra.sources && extra.sources.length && !extra.safety) {
      m.appendChild(el("span", "src", `Based on: ${extra.sources.join("; ")}`));
    }
    chatLog.appendChild(m);
    chatLog.scrollTop = chatLog.scrollHeight;
    return m;
  }

  async function sendChat(text) {
    text = text.trim();
    if (!text || !sessionId) return;
    addMsg("user", text);
    chatInput.value = "";
    chatSend.disabled = true;
    const pending = addMsg("bot", "Thinking...");
    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: text }),
      });
      const body = await res.json().catch(() => ({}));
      pending.remove();
      if (!res.ok) {
        addMsg("bot", body.detail || "Something went wrong. Please try again.");
      } else {
        addMsg("bot", body.reply, { sources: body.sources, safety: body.mode === "safety" });
      }
    } catch (e) {
      pending.remove();
      addMsg("bot", "I couldn't reach the server. Please try again in a moment.");
    } finally {
      chatSend.disabled = false;
      chatInput.focus();
    }
  }
  chatForm.addEventListener("submit", (e) => { e.preventDefault(); sendChat(chatInput.value); });
  document.querySelectorAll("#chat-chips .chip").forEach((c) => c.addEventListener("click", () => sendChat(c.textContent)));
})();
