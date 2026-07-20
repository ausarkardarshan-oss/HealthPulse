/* ==========================================================================
   HealthPulse dashboard behaviour. No page reloads: everything after login
   talks to the JSON endpoints defined in each Django app via fetch().
   ========================================================================== */

// ---------- CSRF helper (Django's csrftoken cookie) ----------
function getCookie(name) {
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  return match ? decodeURIComponent(match[2]) : null;
}
const CSRF_TOKEN = getCookie('csrftoken');

async function api(url, options = {}) {
  const opts = {
    method: options.method || 'GET',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
  };
  if (options.body) opts.body = JSON.stringify(options.body);
  const res = await fetch(url, opts);
  let data;
  try { data = await res.json(); } catch (e) { data = { ok: false, error: 'Unexpected server response.' }; }
  return data;
}

function toast(message, kind = 'error') {
  const el = document.createElement('div');
  el.className = `hp-flash hp-flash-${kind} animate__animated animate__fadeInDown`;
  el.style.position = 'fixed';
  el.style.top = '16px';
  el.style.right = '16px';
  el.style.zIndex = 9999;
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

document.addEventListener('DOMContentLoaded', () => {
  if (!window.HP_USER_ID) return; // not logged in - nothing to wire up

  initSidebarAndTabs();
  initDarkMode();
  initNotifications();
  initProfileMenu();
  initGlobalSearch();
  initCounters();
  initVitalsTab();
  initAppointmentsTab();
  initAnalyticsTab();
  if (window.HP_ROLE === 'doctor') initPatientsTab();
});

/* ---------------------------- Sidebar & Tabs ---------------------------- */
function initSidebarAndTabs() {
  const links = document.querySelectorAll('[data-tab]');
  links.forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const target = link.getAttribute('data-tab');
      document.querySelectorAll('.hp-nav-link').forEach(l => l.classList.remove('active'));
      document.querySelector(`.hp-nav-link[data-tab="${target}"]`)?.classList.add('active');
      document.querySelectorAll('.hp-tab').forEach(t => t.classList.remove('active'));
      const targetEl = document.getElementById(target);
      if (targetEl) {
        targetEl.classList.add('active');
        targetEl.classList.add('animate__animated', 'animate__fadeIn');
      }
      document.getElementById('hpSidebar')?.classList.remove('open');
      document.getElementById('profileMenu')?.classList.remove('show');
    });
  });

  document.getElementById('hpHamburger')?.addEventListener('click', () => {
    document.getElementById('hpSidebar')?.classList.toggle('open');
  });
}

/* ------------------------------ Dark mode -------------------------------- */
function initDarkMode() {
  const btn = document.getElementById('darkModeToggle');
  btn?.addEventListener('click', async () => {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    btn.querySelector('i').className = isDark ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
    // Persist via the settings endpoint (also updates email/sms checkboxes if present)
    const form = new FormData();
    form.append('dark_mode', isDark ? 'on' : 'off');
    if (document.querySelector('[name="notify_email"]')?.checked) form.append('notify_email', 'on');
    if (document.querySelector('[name="notify_sms"]')?.checked) form.append('notify_sms', 'on');
    form.append('csrfmiddlewaretoken', CSRF_TOKEN);
    await fetch('/accounts/settings/', { method: 'POST', body: form });
  });
}

/* ---------------------------- Notifications ------------------------------ */
function initNotifications() {
  const btn = document.getElementById('notifBtn');
  const panel = document.getElementById('notifPanel');

  btn?.addEventListener('click', (e) => {
    e.stopPropagation();
    panel.classList.toggle('show');
    if (panel.classList.contains('show')) loadNotifications();
  });

  document.getElementById('markAllReadBtn')?.addEventListener('click', async (e) => {
    e.stopPropagation();
    await api('/notifications/api/mark-all-read/', { method: 'POST', body: {} });
    loadNotifications();
  });

  document.addEventListener('click', (e) => {
    if (panel && !panel.contains(e.target) && e.target !== btn) panel.classList.remove('show');
  });

  loadNotifications();
  setInterval(loadNotifications, 30000); // poll every 30s
}

async function loadNotifications() {
  const data = await api('/notifications/api/list/');
  if (!data.ok) return;

  const badge = document.getElementById('notifBadge');
  if (data.unread_count > 0) {
    badge.style.display = 'inline-block';
    badge.textContent = data.unread_count > 9 ? '9+' : data.unread_count;
  } else {
    badge.style.display = 'none';
  }

  const list = document.getElementById('notifList');
  if (!data.notifications.length) {
    list.innerHTML = '<div class="hp-empty">No notifications yet.</div>';
    return;
  }
  list.innerHTML = data.notifications.map(n => `
    <div class="hp-notif-item ${n.is_read ? '' : 'unread'}" data-id="${n.id}">
      <strong>${escapeHtml(n.title)}</strong>
      <div>${escapeHtml(n.message)}</div>
      <small>${n.created_at}</small>
    </div>
  `).join('');

  list.querySelectorAll('.hp-notif-item').forEach(item => {
    item.addEventListener('click', async () => {
      await api(`/notifications/api/${item.dataset.id}/read/`, { method: 'POST', body: {} });
      item.classList.remove('unread');
      loadNotifications();
    });
  });
}

/* ------------------------------ Profile menu ------------------------------ */
function initProfileMenu() {
  const btn = document.getElementById('profileBtn');
  const menu = document.getElementById('profileMenu');
  btn?.addEventListener('click', (e) => { e.stopPropagation(); menu.classList.toggle('show'); });
  document.addEventListener('click', (e) => {
    if (menu && !menu.contains(e.target) && e.target !== btn) menu.classList.remove('show');
  });
}

/* ------------------------------ Global search ------------------------------ */
function initGlobalSearch() {
  const input = document.getElementById('globalSearch');
  const results = document.getElementById('searchResults');
  let timer;

  input?.addEventListener('input', () => {
    clearTimeout(timer);
    const q = input.value.trim();
    if (q.length < 2) { results.classList.remove('show'); return; }
    timer = setTimeout(async () => {
      const data = await api(`/api/search/?q=${encodeURIComponent(q)}`);
      if (!data.ok) return;
      renderSearchResults(data);
    }, 250);
  });

  document.addEventListener('click', (e) => {
    if (results && !results.contains(e.target) && e.target !== input) results.classList.remove('show');
  });
}

function renderSearchResults(data) {
  const results = document.getElementById('searchResults');
  let html = '';
  if (data.patients.length) {
    html += '<div class="hp-search-group-title">Patients</div>';
    html += data.patients.map(p => `<div class="hp-search-result-item"><i class="fa-solid fa-user"></i> ${escapeHtml(p.full_name)} — ${escapeHtml(p.phone)}</div>`).join('');
  }
  if (data.doctors.length) {
    html += '<div class="hp-search-group-title">Doctors</div>';
    html += data.doctors.map(d => `<div class="hp-search-result-item"><i class="fa-solid fa-user-doctor"></i> Dr. ${escapeHtml(d.full_name)} — ${escapeHtml(d.specialization)}</div>`).join('');
  }
  if (data.appointments.length) {
    html += '<div class="hp-search-group-title">Appointments</div>';
    html += data.appointments.map(a => `<div class="hp-search-result-item"><i class="fa-solid fa-calendar"></i> ${a.date} at ${a.time_slot} (${a.status})</div>`).join('');
  }
  if (!html) html = '<div class="hp-empty">No matches.</div>';
  results.innerHTML = html;
  results.classList.add('show');
}

/* ------------------------------ Animated counters ------------------------------ */
function initCounters() {
  document.querySelectorAll('.counter').forEach(el => {
    const target = parseInt(el.dataset.target || '0', 10);
    let current = 0;
    const step = Math.max(1, Math.ceil(target / 40));
    const timer = setInterval(() => {
      current += step;
      if (current >= target) { current = target; clearInterval(timer); }
      el.textContent = current;
    }, 20);
  });
}

/* ------------------------------ Vitals tab ------------------------------ */
function initVitalsTab() {
  const form = document.getElementById('vitalsForm');
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = Object.fromEntries(new FormData(form).entries());
    Object.keys(payload).forEach(k => { if (payload[k] === '') delete payload[k]; });
    const data = await api('/vitals/api/add/', { method: 'POST', body: payload });
    if (!data.ok) { toast(data.error); return; }
    toast('Vitals saved.', 'success');
    form.reset();
    loadVitalsSummary();
  });

  loadVitalsSummary();
}

async function loadVitalsSummary() {
  const data = await api('/vitals/api/summary/');
  if (!data.ok) return;

  const cards = document.getElementById('vitalsSummaryCards');
  if (cards) {
    const l = data.latest;
    cards.innerHTML = !l ? '<p class="text-muted">No readings yet — add your first one above.</p>' : `
      <div class="hp-stat-card grad-blue"><i class="fa-solid fa-heart-pulse"></i><div class="hp-stat-value">${l.bp_systolic ?? '--'}/${l.bp_diastolic ?? '--'}</div><div class="hp-stat-label">Latest BP</div></div>
      <div class="hp-stat-card grad-red"><i class="fa-solid fa-droplet"></i><div class="hp-stat-value">${l.sugar ?? '--'}</div><div class="hp-stat-label">Sugar (mg/dL)</div></div>
      <div class="hp-stat-card grad-green"><i class="fa-solid fa-weight-scale"></i><div class="hp-stat-value">${l.weight ?? '--'}</div><div class="hp-stat-label">Weight (kg)</div></div>
      <div class="hp-stat-card grad-orange"><i class="fa-solid fa-wave-square"></i><div class="hp-stat-value">${l.heart_rate ?? '--'}</div><div class="hp-stat-label">Heart Rate (bpm)</div></div>
    `;
  }

  const body = document.getElementById('vitalsHistoryBody');
  if (body) {
    if (!data.history.length) {
      body.innerHTML = '<tr><td colspan="7" class="text-muted">No history yet.</td></tr>';
    } else {
      body.innerHTML = data.history.map(h => `
        <tr>
          <td>${h.recorded_at}</td>
          <td>${h.bp_systolic ?? '--'}/${h.bp_diastolic ?? '--'}</td>
          <td>${h.sugar ?? '--'}</td>
          <td>${h.weight ?? '--'}</td>
          <td>${h.heart_rate ?? '--'}</td>
          <td>${h.temperature ?? '--'}</td>
          <td><span class="hp-pill hp-pill-${h.status}">${h.status}</span></td>
        </tr>
      `).join('');
    }
  }
}

/* ------------------------------ Appointments tab ------------------------------ */
function initAppointmentsTab() {
  const doctorSelect = document.getElementById('doctorSelect');
  const dateInput = document.getElementById('apptDate');
  const slotGrid = document.getElementById('slotGrid');
  const bookingForm = document.getElementById('bookingForm');
  let selectedSlot = null;

  if (dateInput) {
    const today = new Date().toISOString().split('T')[0];
    dateInput.min = today;
  }

  async function refreshSlots() {
    if (!doctorSelect?.value || !dateInput?.value) return;
    selectedSlot = null;
    slotGrid.innerHTML = '<span class="text-muted">Loading slots...</span>';
    const data = await api(`/appointments/api/check-slot/?doctor_id=${doctorSelect.value}&date=${dateInput.value}`);
    if (!data.ok) { slotGrid.innerHTML = `<span class="text-muted">${escapeHtml(data.error)}</span>`; return; }
    slotGrid.innerHTML = data.slots.map(s => `
      <button type="button" class="hp-slot-btn ${s.available ? '' : 'taken'}" data-time="${s.time}" ${s.available ? '' : 'disabled'}>${s.time}</button>
    `).join('');
    slotGrid.querySelectorAll('.hp-slot-btn:not(.taken)').forEach(btn => {
      btn.addEventListener('click', () => {
        slotGrid.querySelectorAll('.hp-slot-btn').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        selectedSlot = btn.dataset.time;
      });
    });
  }

  doctorSelect?.addEventListener('change', refreshSlots);
  dateInput?.addEventListener('change', refreshSlots);

  bookingForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!selectedSlot) { toast('Pick an available time slot first.'); return; }
    const payload = Object.fromEntries(new FormData(bookingForm).entries());
    payload.time_slot = selectedSlot;
    const data = await api('/appointments/api/book/', { method: 'POST', body: payload });
    if (!data.ok) { toast(data.error); return; }
    toast('Appointment booked!', 'success');
    bookingForm.reset();
    slotGrid.innerHTML = '<span class="text-muted">Choose a doctor and date to see available slots.</span>';
    loadAppointments('upcoming');
  });

  document.querySelectorAll('#tab-appointments .hp-pill-btn[data-status]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#tab-appointments .hp-pill-btn[data-status]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      loadAppointments(btn.dataset.status);
    });
  });

  loadAppointments('upcoming');
}

async function loadAppointments(status) {
  const timeline = document.getElementById('appointmentsTimeline');
  if (!timeline) return;
  const data = await api('/appointments/api/list/');
  if (!data.ok) { timeline.innerHTML = `<p class="text-muted">${escapeHtml(data.error)}</p>`; return; }

  const items = data.appointments[status] || [];
  if (!items.length) {
    timeline.innerHTML = `<p class="text-muted">No ${status} appointments.</p>`;
    return;
  }

  timeline.innerHTML = items.map(a => `
    <div class="hp-timeline-item">
      <div>
        <strong>${window.HP_ROLE === 'doctor' ? escapeHtml(a.patient_name) : 'Dr. ' + escapeHtml(a.doctor_name)}</strong>
        <div class="meta">${a.date} · ${a.time_slot} ${a.reason ? '· ' + escapeHtml(a.reason) : ''}</div>
      </div>
      <div class="hp-timeline-actions">
        <span class="hp-pill hp-pill-${a.status}">${a.status}</span>
        ${a.status === 'upcoming' ? `<button data-cancel="${a.id}">Cancel</button>` : ''}
      </div>
    </div>
  `).join('');

  timeline.querySelectorAll('[data-cancel]').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm('Cancel this appointment?')) return;
      const data = await api(`/appointments/api/${btn.dataset.cancel}/cancel/`, { method: 'POST', body: {} });
      if (!data.ok) { toast(data.error); return; }
      toast('Appointment cancelled.', 'success');
      loadAppointments(status);
    });
  });
}

/* ------------------------------ Analytics tab (Chart.js) ------------------------------ */
let hpCharts = {};

function initAnalyticsTab() {
  document.querySelectorAll('.period-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      loadCharts(btn.dataset.period);
    });
  });

  document.querySelector('[data-tab="tab-analytics"]')?.addEventListener('click', () => loadCharts('30d'));
}

async function loadCharts(period) {
  const data = await api(`/vitals/api/chart/?period=${period}`);
  if (!data.ok) return;

  renderChart('bpChart', data.labels, [
    { label: 'Systolic', data: data.series.bp_systolic, color: '#2f6fed' },
    { label: 'Diastolic', data: data.series.bp_diastolic, color: '#7c5cff' },
  ]);
  renderChart('sugarChart', data.labels, [{ label: 'Sugar (mg/dL)', data: data.series.sugar, color: '#ef5c6e' }]);
  renderChart('weightChart', data.labels, [{ label: 'Weight (kg)', data: data.series.weight, color: '#1fae7a' }]);
  renderChart('hrChart', data.labels, [{ label: 'Heart Rate (bpm)', data: data.series.heart_rate, color: '#ff9142' }]);
}

function renderChart(canvasId, labels, datasets) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  if (hpCharts[canvasId]) hpCharts[canvasId].destroy();
  hpCharts[canvasId] = new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: datasets.map(d => ({
        label: d.label, data: d.data, borderColor: d.color, backgroundColor: d.color + '22',
        tension: 0.35, fill: true, pointRadius: 3,
      })),
    },
    options: {
      responsive: true,
      animation: { duration: 700 },
      plugins: { legend: { display: datasets.length > 1 } },
      scales: { y: { beginAtZero: false } },
    },
  });
}

/* ------------------------------ Patients tab (doctor only) ------------------------------ */
function initPatientsTab() {
  const searchInput = document.getElementById('patientSearchInput');
  let timer;
  searchInput?.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(() => loadPatients(searchInput.value.trim()), 250);
  });

  document.getElementById('closePatientDetail')?.addEventListener('click', () => {
    document.getElementById('patientDetailPanel').style.display = 'none';
  });

  loadPatients('');
}

async function loadPatients(query) {
  const body = document.getElementById('patientsTableBody');
  if (!body) return;
  const data = await api(`/patients/api/list/?q=${encodeURIComponent(query)}`);
  if (!data.ok) { body.innerHTML = `<tr><td colspan="6" class="text-muted">${escapeHtml(data.error)}</td></tr>`; return; }

  if (!data.patients.length) {
    body.innerHTML = '<tr><td colspan="6" class="text-muted">No patients found.</td></tr>';
    return;
  }

  body.innerHTML = data.patients.map(p => `
    <tr>
      <td>${escapeHtml(p.full_name)}</td>
      <td>${escapeHtml(p.phone)}</td>
      <td>${escapeHtml(p.email)}</td>
      <td>${p.gender}</td>
      <td>${p.dob}</td>
      <td><button class="hp-btn-primary" style="padding:6px 12px;font-size:.78rem;" data-view="${p.django_user_id}">View</button></td>
    </tr>
  `).join('');

  body.querySelectorAll('[data-view]').forEach(btn => {
    btn.addEventListener('click', () => loadPatientDetail(btn.dataset.view));
  });
}

async function loadPatientDetail(userId) {
  const data = await api(`/patients/api/${userId}/`);
  if (!data.ok) { toast(data.error); return; }

  const panel = document.getElementById('patientDetailPanel');
  document.getElementById('patientDetailName').textContent = data.patient.full_name;

  const vitalsRows = data.vitals_history.map(v => `
    <tr><td>${v.recorded_at}</td><td>${v.bp_systolic ?? '--'}/${v.bp_diastolic ?? '--'}</td><td>${v.sugar ?? '--'}</td><td>${v.weight ?? '--'}</td><td><span class="hp-pill hp-pill-${v.status}">${v.status}</span></td></tr>
  `).join('') || '<tr><td colspan="5" class="text-muted">No vitals recorded.</td></tr>';

  const apptRows = data.appointments.map(a => `
    <tr><td>${a.date}</td><td>${a.time_slot}</td><td>${escapeHtml(a.reason || '—')}</td><td><span class="hp-pill hp-pill-${a.status}">${a.status}</span></td></tr>
  `).join('') || '<tr><td colspan="4" class="text-muted">No appointments yet.</td></tr>';

  document.getElementById('patientDetailBody').innerHTML = `
    <p class="text-muted">${escapeHtml(data.patient.phone)} · ${escapeHtml(data.patient.email)} · DOB ${data.patient.dob}</p>
    <h5 class="mt-3">Vitals history</h5>
    <div class="table-responsive"><table class="table hp-table"><thead><tr><th>Date</th><th>BP</th><th>Sugar</th><th>Weight</th><th>Status</th></tr></thead><tbody>${vitalsRows}</tbody></table></div>
    <h5 class="mt-3">Appointment history</h5>
    <div class="table-responsive"><table class="table hp-table"><thead><tr><th>Date</th><th>Time</th><th>Reason</th><th>Status</th></tr></thead><tbody>${apptRows}</tbody></table></div>
    <div class="mt-3">
      <label>Add a note on the most recent appointment</label>
      <div style="display:flex;gap:8px;">
        <input type="text" id="doctorNoteInput" class="form-control hp-input" placeholder="Note for this patient">
        <button class="hp-btn-primary" id="saveDoctorNoteBtn" data-user="${userId}">Save</button>
      </div>
    </div>
  `;
  panel.style.display = 'block';
  panel.scrollIntoView({ behavior: 'smooth' });

  document.getElementById('saveDoctorNoteBtn')?.addEventListener('click', async (e) => {
    const note = document.getElementById('doctorNoteInput').value.trim();
    if (!note) return;
    const res = await api(`/patients/api/${e.target.dataset.user}/note/`, { method: 'POST', body: { note } });
    if (!res.ok) { toast(res.error); return; }
    toast('Note saved.', 'success');
  });
}

/* ------------------------------ utils ------------------------------ */
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str).replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
}
