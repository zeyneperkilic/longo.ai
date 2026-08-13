/**
 * LongoPass Kişisel Sağlık Künyesi — chatbot gibi yüzen buton + panel
 *
 * <script>
 *   window.LongopassMedicalIdConfig = { userId: '...', userLevel: 3 };
 * </script>
 * <script src="https://longo-ai.onrender.com/widget/medical-id-form.js"></script>
 */
(function () {
  'use strict';

  if (window.__LP_MEDICAL_ID_FORM_LOADED__) return;
  window.__LP_MEDICAL_ID_FORM_LOADED__ = true;

  var cfg = window.LongopassMedicalIdConfig || {};
  var API_BASE = (cfg.apiBase || 'https://longo-ai.onrender.com').replace(/\/$/, '');
  var FLOATING = cfg.floating !== false;
  var USER_ID = String(cfg.userId || window.longoRealUserId || window.longoCurrentUserId || '');
  var USER_LEVEL = Number(
    cfg.userLevel != null ? cfg.userLevel : window.longoUserLevel != null ? window.longoUserLevel : 0
  );
  var USERNAME = cfg.username || 'longopass';
  var PASSWORD = cfg.password || '123456';

  var state = {
    schema: null,
    form: {},
    token: null,
    url: null,
    qrImageUrl: null,
    formUpdatedAt: null,
    saving: false,
    message: '',
    error: '',
    open: false,
    loaded: false,
  };

  function authHeaders() {
    return {
      'Content-Type': 'application/json',
      username: USERNAME,
      password: PASSWORD,
      'x-user-id': USER_ID,
      'x-user-level': String(USER_LEVEL || 1),
    };
  }

  function injectStyles() {
    if (document.getElementById('lp-medical-id-styles')) return;
    var style = document.createElement('style');
    style.id = 'lp-medical-id-styles';
    style.textContent = [
      '#lp-medical-id-widget{position:fixed;bottom:110px;right:20px;z-index:9998;font-family:Segoe UI,system-ui,-apple-system,sans-serif;}',
      '#lp-medical-id-widget *{box-sizing:border-box;}',
      '#lp-medical-id-fab{width:64px;height:64px;border-radius:50%;border:0;cursor:pointer;background:linear-gradient(135deg,#174A70,#1F6F9F);color:#fff;box-shadow:0 8px 28px rgba(23,74,112,.35);display:flex;align-items:center;justify-content:center;font-size:1.6rem;transition:transform .2s,box-shadow .2s;}',
      '#lp-medical-id-fab:hover{transform:translateY(-2px);box-shadow:0 12px 32px rgba(23,74,112,.45);}',
      '#lp-medical-id-fab.active{background:linear-gradient(135deg,#1F6F9F,#25B8C7);}',
      '#lp-medical-id-tooltip{position:absolute;right:76px;bottom:14px;transform:none;background:#174A70;color:#fff;padding:9px 12px;border-radius:14px;font-size:.8rem;font-weight:600;white-space:nowrap;box-shadow:0 4px 15px rgba(23,74,112,.4);pointer-events:none;opacity:1;z-index:10000;border:2px solid #4A7C9A;text-align:center;}',
      '#lp-medical-id-tooltip::after{content:"";position:absolute;right:-7px;top:50%;transform:translateY(-50%);border-width:7px 0 7px 8px;border-style:solid;border-color:transparent transparent transparent #174A70;}',
      '#lp-medical-id-widget.open #lp-medical-id-tooltip{display:none;}',
      '#lp-medical-id-panel{position:fixed;bottom:110px;right:96px;width:min(440px,calc(100vw - 40px));max-height:min(78vh,720px);background:#fff;border:1px solid #D7EAF2;border-radius:18px;box-shadow:0 20px 50px rgba(22,59,89,.18);display:none;flex-direction:column;overflow:hidden;z-index:9999;}',
      '#lp-medical-id-panel.open{display:flex;}',
      '#lp-medical-id-panel-header{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;background:linear-gradient(90deg,#174A70,#1F6F9F);color:#fff;flex-shrink:0;}',
      '#lp-medical-id-panel-header h3{margin:0;font-size:1rem;font-weight:700;}',
      '#lp-medical-id-close{background:rgba(255,255,255,.15);border:0;color:#fff;width:32px;height:32px;border-radius:8px;cursor:pointer;font-size:1rem;}',
      '#lp-medical-id-panel-body{overflow-y:auto;padding:0;flex:1;-webkit-overflow-scrolling:touch;}',      '.lp-mid{font-family:inherit;color:#163B59;}',
      '.lp-mid-card{background:#fff;border:0;border-radius:0;box-shadow:none;padding:16px;margin:0;}',
      '.lp-mid-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:12px;}',
      '.lp-mid-title{margin:0;font-size:1.1rem;color:#174A70;font-weight:800;}',
      '.lp-mid-sub{margin:4px 0 0;color:#2F526B;font-size:.85rem;}',
      '.lp-mid-badge{background:#DFF3FA;border:1px solid #BFDCE8;color:#174A70;border-radius:999px;padding:5px 10px;font-size:.7rem;font-weight:700;}',
      '.lp-mid-sec{border-top:1px solid #EEF5F9;padding-top:12px;margin-top:12px;}',
      '.lp-mid-sec h3{margin:0 0 8px;font-size:.95rem;color:#174A70;}',
      '.lp-mid-grid{display:grid;grid-template-columns:1fr;gap:8px;}',
      '.lp-mid-field{display:flex;flex-direction:column;gap:4px;}',
      '.lp-mid-field.full{grid-column:1/-1;}',
      '.lp-mid-field label{font-size:.78rem;font-weight:600;color:#2F526B;}',
      '.lp-mid-field input,.lp-mid-field select,.lp-mid-field textarea{width:100%;border:1px solid #D7EAF2;border-radius:10px;padding:9px 11px;font-size:.9rem;color:#163B59;background:#fff;}',
      '.lp-mid-field textarea{min-height:68px;resize:vertical;}',
      '.lp-mid-list-item{border:1px dashed #D7EAF2;border-radius:10px;padding:10px;margin-bottom:8px;background:#F7FBFD;}',
      '.lp-mid-list-actions{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap;}',
      '.lp-mid-btn{border:0;border-radius:10px;padding:9px 13px;font-weight:700;cursor:pointer;font-size:.85rem;}',
      '.lp-mid-btn-primary{background:linear-gradient(90deg,#174A70,#1F6F9F,#25B8C7);color:#fff;width:100%;}',
      '.lp-mid-btn-secondary{background:#DFF3FA;color:#174A70;border:1px solid #BFDCE8;}',
      '.lp-mid-btn-danger{background:#FFF1F0;color:#B42318;border:1px solid #F5C2C0;}',
      '.lp-mid-btn:disabled{opacity:.6;cursor:not-allowed;}',
      '.lp-mid-msg{padding:10px 12px;border-radius:10px;margin:0 0 10px;font-size:.85rem;}',
      '.lp-mid-msg.ok{background:#EAF8F0;border:1px solid #B7E4C7;color:#1B4332;}',
      '.lp-mid-msg.err{background:#FFF1F0;border:1px solid #F5C2C0;color:#B42318;}',
      '.lp-mid-qr{display:flex;flex-direction:column;gap:12px;align-items:center;text-align:center;padding-top:8px;border-top:1px solid #EEF5F9;margin-top:12px;}',
      '.lp-mid-qr img{width:140px;height:140px;border:1px solid #D7EAF2;border-radius:12px;}',
      '.lp-mid-hint{font-size:.78rem;color:#2F526B;margin:0;}',
      '.lp-mid-locked{padding:24px 16px;text-align:center;color:#2F526B;font-size:.9rem;}',
      '@media (max-width:520px){#lp-medical-id-panel{left:10px;right:10px;width:auto;bottom:100px;max-height:65vh;}#lp-medical-id-tooltip{right:76px;left:auto;max-width:140px;white-space:normal;}}',
    ].join('');
    document.head.appendChild(style);
  }

  function createShell() {
    if (document.getElementById('lp-medical-id-widget')) return;
    var html =
      '<div id="lp-medical-id-widget">' +
      '<div id="lp-medical-id-tooltip">Sağlık künyenizi doldurun</div>' +
      '<button type="button" id="lp-medical-id-fab" aria-label="Sağlık künyenizi doldurun" title="Sağlık künyenizi doldurun">🪪</button>' +
      '<div id="lp-medical-id-panel" role="dialog" aria-label="Kişisel Sağlık Künyesi">' +
      '<div id="lp-medical-id-panel-header">' +
      '<h3>Kişisel Sağlık Künyesi</h3>' +
      '<button type="button" id="lp-medical-id-close" aria-label="Kapat">✕</button>' +
      '</div>' +
      '<div id="lp-medical-id-panel-body">' +
      '<div id="lp-medical-id-root"></div>' +
      '</div></div></div>';
    document.body.insertAdjacentHTML('beforeend', html);

    document.getElementById('lp-medical-id-fab').addEventListener('click', togglePanel);
    document.getElementById('lp-medical-id-close').addEventListener('click', closePanel);
  }

  function getRoot() {
    return document.getElementById('lp-medical-id-root');
  }

  function openPanel() {
    state.open = true;
    var panel = document.getElementById('lp-medical-id-panel');
    var fab = document.getElementById('lp-medical-id-fab');
    var wrap = document.getElementById('lp-medical-id-widget');
    if (panel) panel.classList.add('open');
    if (fab) fab.classList.add('active');
    if (wrap) wrap.classList.add('open');
    if (USER_ID && USER_LEVEL >= 2) {
      if (!state.loaded) loadData();
      else refreshForm();
    }
  }

  function closePanel() {
    state.open = false;
    var panel = document.getElementById('lp-medical-id-panel');
    var fab = document.getElementById('lp-medical-id-fab');
    var wrap = document.getElementById('lp-medical-id-widget');
    if (panel) panel.classList.remove('open');
    if (fab) fab.classList.remove('active');
    if (wrap) wrap.classList.remove('open');
  }

  function togglePanel() {
    if (state.open) closePanel();
    else openPanel();
  }

  window.lpMedicalIdToggle = togglePanel;
  window.lpMedicalIdClose = closePanel;

  function getSectionValue(sectionId) {
    if (!state.form[sectionId]) {
      var sec = (state.schema && state.schema.sections || []).find(function (s) {
        return s.id === sectionId;
      });
      state.form[sectionId] = sec && sec.type === 'list' ? [] : {};
    }
    return state.form[sectionId];
  }

  function api(path, options) {
    options = options || {};
    return fetch(API_BASE + path, {
      method: options.method || 'GET',
      headers: authHeaders(),
      body: options.body ? JSON.stringify(options.body) : undefined,
    }).then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok) {
          var detail = (data && data.detail) || res.statusText || 'İstek başarısız';
          throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
        }
        return data;
      });
    });
  }

  function collectFormFromDom(root) {
    var form = {};
    (state.schema.sections || []).forEach(function (section) {
      if (section.type === 'list') {
        var items = [];
        root.querySelectorAll('[data-list="' + section.id + '"] .lp-mid-list-item').forEach(function (itemEl) {
          var row = {};
          (section.item_fields || []).forEach(function (f) {
            var input = itemEl.querySelector('[data-key="' + f.key + '"]');
            if (input && input.value) row[f.key] = input.value;
          });
          if (Object.keys(row).length) items.push(row);
        });
        form[section.id] = items;
      } else {
        var obj = {};
        (section.fields || []).forEach(function (f) {
          var input = root.querySelector('[data-section="' + section.id + '"][data-key="' + f.key + '"]');
          if (input && input.value !== '') obj[f.key] = input.value;
        });
        form[section.id] = obj;
      }
    });
    state.form = form;
    return form;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function escapeAttr(s) {
    return escapeHtml(s).replace(/'/g, '&#39;');
  }

  function fieldControl(sectionId, field, value) {
    var val = value == null ? '' : String(value);
    var common = ' data-section="' + sectionId + '" data-key="' + field.key + '" ';
    if (field.type === 'textarea') {
      return '<textarea' + common + '>' + escapeHtml(val) + '</textarea>';
    }
    if (field.type === 'select') {
      var opts = (field.options || [])
        .map(function (o) {
          return (
            '<option value="' +
            escapeHtml(o) +
            '"' +
            (o === val ? ' selected' : '') +
            '>' +
            escapeHtml(o) +
            '</option>'
          );
        })
        .join('');
      return '<select' + common + '><option value="">Seçin</option>' + opts + '</select>';
    }
    var type =
      field.type === 'number' ? 'number' : field.type === 'email' ? 'email' : field.type === 'date' ? 'date' : 'text';
    return '<input type="' + type + '"' + common + ' value="' + escapeAttr(val) + '" />';
  }

  function renderListSection(section) {
    var items = getSectionValue(section.id);
    if (!Array.isArray(items) || !items.length) items = [{}];
    var html = '<div class="lp-mid-sec" data-list="' + section.id + '"><h3>' + escapeHtml(section.title) + '</h3>';
    items.forEach(function (item, idx) {
      html += '<div class="lp-mid-list-item" data-index="' + idx + '">';
      (section.item_fields || []).forEach(function (f) {
        html +=
          '<div class="lp-mid-field"><label>' +
          escapeHtml(f.label) +
          '</label>' +
          fieldControl(section.id, f, item[f.key]) +
          '</div>';
      });
      html +=
        '<div class="lp-mid-list-actions"><button type="button" class="lp-mid-btn lp-mid-btn-danger" data-action="remove-item" data-section="' +
        section.id +
        '" data-index="' +
        idx +
        '">Sil</button></div></div>';
    });
    html +=
      '<button type="button" class="lp-mid-btn lp-mid-btn-secondary" data-action="add-item" data-section="' +
      section.id +
      '">+ Ekle</button></div>';
    return html;
  }

  function renderFieldsSection(section) {
    var values = getSectionValue(section.id) || {};
    var html = '<div class="lp-mid-sec"><h3>' + escapeHtml(section.title) + '</h3><div class="lp-mid-grid">';
    (section.fields || []).forEach(function (f) {
      html +=
        '<div class="lp-mid-field"><label>' +
        escapeHtml(f.label) +
        (f.required ? ' *' : '') +
        '</label>' +
        fieldControl(section.id, f, values[f.key]) +
        '</div>';
    });
    html += '</div></div>';
    return html;
  }

  function render() {
    var root = getRoot();
    if (!root) return;

    if (!USER_ID) {
      root.innerHTML = '<div class="lp-mid-locked">Kişisel Sağlık Künyesi için giriş yapmanız gerekiyor.</div>';
      return;
    }
    if (USER_LEVEL < 2) {
      root.innerHTML =
        '<div class="lp-mid-locked">Kişisel Sağlık Künyesi Essential / Ultimate üyeliklerde aktiftir.</div>';
      return;
    }
    if (!state.schema) {
      root.innerHTML = '<div class="lp-mid-locked">Yükleniyor…</div>';
      return;
    }

    var sectionsHtml = (state.schema.sections || [])
      .map(function (s) {
        return s.type === 'list' ? renderListSection(s) : renderFieldsSection(s);
      })
      .join('');

    var msg = '';
    if (state.error) msg = '<div class="lp-mid-msg err">' + escapeHtml(state.error) + '</div>';
    else if (state.message) msg = '<div class="lp-mid-msg ok">' + escapeHtml(state.message) + '</div>';

    var qrBlock = '';
    if (state.qrImageUrl) {
      qrBlock =
        '<div class="lp-mid-qr">' +
        '<img src="' +
        escapeAttr(state.qrImageUrl) +
        '" alt="QR" />' +
        '<p class="lp-mid-hint">QR kodunuz sabittir. Künye şifresi: <strong>1234</strong></p>' +
        (state.url
          ? '<a class="lp-mid-hint" href="' + escapeAttr(state.url) + '" target="_blank" rel="noopener">Künyeyi görüntüle</a>'
          : '') +
        '</div>';
    }

    var hasSaved = !!(state.token || state.formUpdatedAt);
    var saveLabel = state.saving
      ? 'Kaydediliyor…'
      : hasSaved
        ? 'Güncelle'
        : 'Kaydet';
    var editHint = hasSaved
      ? 'Kayıtlı künyenizi istediğiniz zaman düzenleyebilirsiniz. Güncelleme QR kodunu değiştirmez.'
      : 'Bilgilerinizi kaydedin. Daha sonra istediğiniz zaman düzenleyebilirsiniz.';

    root.innerHTML =
      '<div class="lp-mid"><div class="lp-mid-card">' +
      msg +
      '<p class="lp-mid-sub" style="margin:0 0 12px;">' +
      escapeHtml(editHint) +
      (state.formUpdatedAt
        ? '<br><span style="font-size:.75rem;opacity:.85;">Son güncelleme: ' +
          escapeHtml(formatUpdatedAt(state.formUpdatedAt)) +
          '</span>'
        : '') +
      '</p>' +
      sectionsHtml +
      '<div class="lp-mid-list-actions" style="margin-top:14px;">' +
      '<button type="button" class="lp-mid-btn lp-mid-btn-primary" data-action="save"' +
      (state.saving ? ' disabled' : '') +
      '>' +
      saveLabel +
      '</button></div>' +
      qrBlock +
      '</div></div>';

    bindEvents(root);
  }

  function bindEvents(root) {
    root.querySelectorAll('[data-action="add-item"]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        collectFormFromDom(root);
        var sid = btn.getAttribute('data-section');
        var list = getSectionValue(sid);
        if (!Array.isArray(list)) list = [];
        list.push({});
        state.form[sid] = list;
        render();
      });
    });
    root.querySelectorAll('[data-action="remove-item"]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        collectFormFromDom(root);
        var sid = btn.getAttribute('data-section');
        var idx = Number(btn.getAttribute('data-index'));
        var list = getSectionValue(sid);
        if (Array.isArray(list)) {
          list.splice(idx, 1);
          if (!list.length) list.push({});
          state.form[sid] = list;
        }
        render();
      });
    });
    var saveBtn = root.querySelector('[data-action="save"]');
    if (saveBtn) saveBtn.addEventListener('click', function () { save(root); });
  }

  function formatUpdatedAt(iso) {
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return String(iso);
      var pad = function (n) { return n < 10 ? '0' + n : '' + n; };
      return (
        pad(d.getDate()) +
        '.' +
        pad(d.getMonth() + 1) +
        '.' +
        d.getFullYear() +
        ' ' +
        pad(d.getHours()) +
        ':' +
        pad(d.getMinutes())
      );
    } catch (e) {
      return String(iso);
    }
  }

  function applyFormPayload(existing, created) {
    if (existing && existing.form && typeof existing.form === 'object') {
      state.form = existing.form;
    }
    if (existing && existing.form_updated_at) {
      state.formUpdatedAt = existing.form_updated_at;
    }
    if (created && created.token) {
      state.token = created.token;
      state.url = created.url;
      state.qrImageUrl = created.qr_image_url;
    } else if (existing && existing.token) {
      state.token = existing.token;
      state.url = API_BASE + '/m/' + existing.token;
      state.qrImageUrl = API_BASE + '/ai/medical-id/qr/' + existing.token;
    }
  }

  function save(root) {
    collectFormFromDom(root);
    state.saving = true;
    state.error = '';
    state.message = '';
    render();
    api('/ai/medical-id/form', { method: 'POST', body: { form: state.form } })
      .then(function (data) {
        state.token = data.token;
        state.url = data.url;
        state.qrImageUrl = data.qr_image_url;
        state.formUpdatedAt = new Date().toISOString();
        state.message = 'Güncellendi. QR kodunuz aynı kaldı.';
        state.saving = false;
        render();
      })
      .catch(function (err) {
        state.saving = false;
        state.error = err.message || 'Kayıt başarısız';
        render();
      });
  }

  function refreshForm() {
    api('/ai/medical-id/form')
      .then(function (existing) {
        applyFormPayload(existing || {}, null);
        render();
      })
      .catch(function () {});
  }

  function loadData() {
    state.loaded = true;
    render();
    Promise.all([
      api('/ai/medical-id/form-schema'),
      api('/ai/medical-id/form'),
      api('/ai/medical-id/create', { method: 'POST', body: {} }).catch(function () { return null; }),
    ])
      .then(function (results) {
        state.schema = results[0];
        applyFormPayload(results[1] || {}, results[2]);
        render();
      })
      .catch(function (err) {
        state.error = err.message || 'Form yüklenemedi';
        state.schema = { title: 'Kişisel Sağlık Künyesi', sections: [] };
        render();
      });
  }

  function bootstrap() {
    injectStyles();
    if (FLOATING) {
      createShell();
      if (USER_ID && USER_LEVEL >= 2) {
        // Buton her zaman görünür; form panel açılınca yüklenir
      } else if (!USER_ID || USER_LEVEL < 2) {
        // Giriş yoksa butonu gizle veya tıklayınca mesaj göster
        createShell();
      }
    } else {
      var el = document.getElementById('lp-medical-id-root');
      if (!el) {
        el = document.createElement('div');
        el.id = 'lp-medical-id-root';
        document.body.appendChild(el);
      }
      if (USER_ID && USER_LEVEL >= 2) loadData();
      else render();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootstrap);
  } else {
    bootstrap();
  }
})();
