/* ============================================================
   Heartfulness NGO – Main JavaScript
   ============================================================ */

/* ── Chart colour palette ────────────────────────────────── */
const CHART_COLORS = [
  '#2563EB','#10B981','#F59E0B','#EF4444','#8B5CF6',
  '#06B6D4','#EC4899','#84CC16','#F97316','#6366F1'
];

/* ── Theme helpers ───────────────────────────────────────── */
function isDark() {
  return document.documentElement.getAttribute('data-theme') === 'dark';
}

function toggleTheme() {
  const next = isDark() ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  // update icon
  const icon = document.getElementById('themeIcon');
  if (icon) icon.className = next === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
  // persist to server
  fetch('/set-theme?theme=' + next).catch(() => {});
}

/* ── Sidebar toggle ──────────────────────────────────────── */
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const main    = document.getElementById('mainContent');
  if (!sidebar) return;
  sidebar.classList.toggle('collapsed');
  if (main) main.classList.toggle('sidebar-collapsed');
}

/* ── DOMContentLoaded ────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function () {

  /* Confirm dialogs */
  document.querySelectorAll('[data-confirm]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      if (!confirm(this.getAttribute('data-confirm'))) {
        e.preventDefault(); e.stopPropagation();
      }
    });
  });

  /* Auto-hide success/info flash messages after 5 s */
  document.querySelectorAll('.alert:not(.alert-danger)').forEach(function (a) {
    setTimeout(function () {
      a.style.transition = 'opacity 0.4s';
      a.style.opacity = '0';
      setTimeout(function () { a.remove(); }, 400);
    }, 5000);
  });

  /* Attendance checkbox → badge sync */
  document.querySelectorAll('.att-checkbox').forEach(function (cb) {
    cb.addEventListener('change', function () {
      updateRowBadge(this);
      updatePresentCount();
    });
  });

  /* Init present-count on attendance page */
  if (document.getElementById('memberList')) updatePresentCount();
});

/* ── Attendance helpers ──────────────────────────────────── */
function selectAllPresent() {
  document.querySelectorAll('.att-checkbox').forEach(function (cb) {
    cb.checked = true; updateRowBadge(cb);
  });
  updatePresentCount();
}
function selectAllAbsent() {
  document.querySelectorAll('.att-checkbox').forEach(function (cb) {
    cb.checked = false; updateRowBadge(cb);
  });
  updatePresentCount();
}
function updateRowBadge(cb) {
  const badge = cb.closest('.attendance-row').querySelector('.badge-present,.badge-absent');
  if (!badge) return;
  badge.className = cb.checked ? 'badge-present' : 'badge-absent';
  badge.textContent = cb.checked ? 'Present' : 'Absent';
}
function updatePresentCount() {
  const all     = document.querySelectorAll('.att-checkbox');
  const present = Array.from(all).filter(c => c.checked).length;
  const el      = document.getElementById('presentCount');
  if (el) el.textContent = present + ' / ' + all.length + ' Present';
}
function filterMembers(q) {
  q = q.toLowerCase();
  document.querySelectorAll('.member-row').forEach(function (row) {
    const name = (row.dataset.name || '').toLowerCase();
    const id   = (row.dataset.id   || '').toLowerCase();
    row.style.display = (name.includes(q) || id.includes(q)) ? '' : 'none';
  });
}
