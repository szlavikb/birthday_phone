/* =================================================================
   Mobilválasztó – app.js
   Vanilla JS SPA: table / cards / compare views + detail drawer
   ================================================================= */

const App = (() => {
  /* ---------------------------------------------------------------
     State
  --------------------------------------------------------------- */
  let state = {
    view: 'table',          // 'table' | 'cards' | 'compare'
    phones: [],
    descriptions: [],       // [{column_key, label, description}]
    appState: { favorites: [], winner: null },
    compareSelected: [],    // max 3 phone ids
    sortCol: null,
    sortDir: 'asc',
    activeDescKey: null,    // for desc modal
    drawerPhoneId: null,
  };

  /* ---------------------------------------------------------------
     Bootstrap
  --------------------------------------------------------------- */
  async function init() {
    const [phonesRes, descRes, stateRes] = await Promise.all([
      fetch('/api/phones'),
      fetch('/api/descriptions'),
      fetch('/api/state'),
    ]);
    state.phones       = await phonesRes.json();
    state.descriptions = await descRes.json();
    state.appState     = await stateRes.json();
    renderView();
    updateWinnerBanner();
  }

  /* ---------------------------------------------------------------
     View switching
  --------------------------------------------------------------- */
  function setView(v) {
    state.view = v;
    document.querySelectorAll('.tab').forEach(t =>
      t.classList.toggle('active', t.dataset.view === v)
    );
    document.getElementById('compareSelectorBar')
      .classList.toggle('hidden', v !== 'compare');
    renderView();
  }

  function renderView() {
    if (state.view === 'table')        renderTable(state.phones);
    else if (state.view === 'cards')   renderCards(state.phones);
    else if (state.view === 'compare') renderComparePage();
  }

  /* ---------------------------------------------------------------
     Helpers
  --------------------------------------------------------------- */
  function isFav(id)    { return state.appState.favorites.includes(String(id)); }
  function isWinner(id) { return String(state.appState.winner) === String(id); }

  function descFor(key) {
    const d = state.descriptions.find(d => d.column_key === key);
    return d ? d.description : '';
  }
  function labelFor(key) {
    const d = state.descriptions.find(d => d.column_key === key);
    return d ? d.label : key;
  }

  function oisLabel(val) {
    if (val === true || val === 1 || val === '1') return '<span class="ois-yes">✓ Van</span>';
    return '<span class="ois-no">✗ Nincs</span>';
  }

  function escHtml(s) {
    if (s == null) return '–';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /* ---------------------------------------------------------------
     TABLE VIEW
  --------------------------------------------------------------- */
  const TABLE_COLS = [
    { key: 'name',        label: 'Modell',       field: 'name' },
    { key: 'price',       label: 'Ár',           field: 'price' },
    { key: 'battery',     label: 'Akkumulátor',  field: 'battery' },
    { key: 'sensor_size', label: 'Szenzorméret', field: 'sensor_size' },
    { key: 'aperture',    label: 'Rekesz',       field: 'aperture' },
    { key: 'ois',         label: 'OIS',          field: 'ois' },
    { key: 'max_zoom',    label: 'Max. zoom',    field: 'max_zoom' },
    { key: 'max_video',   label: 'Max. videó',   field: 'max_video' },
    { key: 'storage',     label: 'ROM / RAM',    field: 'storage' },
    { key: 'height',      label: 'Ma. (mm)',     field: 'height' },
    { key: 'width',       label: 'Sz. (mm)',     field: 'width' },
    { key: 'thickness',   label: 'V. (mm)',      field: 'thickness' },
  ];

  function renderTable(phones) {
    const sorted = sortedPhones(phones);
    const main = document.getElementById('mainContent');

    const headCells = TABLE_COLS.map(col => {
      const isSorted = state.sortCol === col.key;
      const icon = isSorted ? (state.sortDir === 'asc' ? '▲' : '▼') : '⇅';
      return `<th class="${isSorted ? 'sorted' : ''}">
        <div class="th-inner">
          <span onclick="App._sortBy('${col.key}')">${escHtml(col.label)} <span class="sort-icon">${icon}</span></span>
          <button class="info-btn" title="Mi ez?" onclick="App.openDescModal('${col.key}', event)">?</button>
        </div>
      </th>`;
    }).join('');

    const bodyRows = sorted.map(p => {
      const winner  = isWinner(p.id);
      const fav     = isFav(p.id);
      const isRef   = p.is_reference;
      const rowCls  = [winner ? 'is-winner' : '', fav ? 'is-favorite' : ''].filter(Boolean).join(' ');

      const nameCell = `<td class="phone-name-cell" style="min-width:190px">
        ${winner ? '<span class="trophy-badge">🏆</span>' : ''}
        ${escHtml(p.name)}
        ${isRef ? '<span class="ref-badge">⚠️ Ref.</span>' : ''}
      </td>`;

      const cells = TABLE_COLS.slice(1).map(col => {
        let val = p[col.field];
        if (col.key === 'ois') return `<td>${oisLabel(val)}</td>`;
        return `<td>${escHtml(val ?? '–')}</td>`;
      }).join('');

      return `<tr class="${rowCls}" onclick="App.openDrawer('${p.id}')">${nameCell}${cells}</tr>`;
    }).join('');

    main.innerHTML = `
      <div class="table-wrapper">
        <table>
          <thead><tr>${headCells}</tr></thead>
          <tbody>${bodyRows}</tbody>
        </table>
      </div>`;
  }

  function sortedPhones(phones) {
    if (!state.sortCol) return [...phones];
    return [...phones].sort((a, b) => {
      let av = a[state.sortCol], bv = b[state.sortCol];
      // reference always last
      if (a.is_reference) return 1;
      if (b.is_reference) return -1;
      if (av == null) return 1;
      if (bv == null) return -1;
      const cmp = typeof av === 'number'
        ? av - bv
        : String(av).localeCompare(String(bv), 'hu');
      return state.sortDir === 'asc' ? cmp : -cmp;
    });
  }

  function _sortBy(col) {
    if (state.sortCol === col) {
      state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc';
    } else {
      state.sortCol = col;
      state.sortDir = 'asc';
    }
    renderView();
  }

  /* ---------------------------------------------------------------
     CARDS VIEW
  --------------------------------------------------------------- */
  async function renderCards(phones) {
    const main = document.getElementById('mainContent');

    // Load first image for each phone
    const imageMap = {};
    await Promise.all(phones.filter(p => !p.is_reference).map(async p => {
      const imgs = await fetch(`/api/phones/${encodeURIComponent(p.name)}/images`).then(r => r.json());
      imageMap[p.id] = imgs[0] || null;
    }));

    const cards = phones.map(p => {
      const winner = isWinner(p.id);
      const fav    = isFav(p.id);
      const isRef  = p.is_reference;
      const imgSrc = imageMap[p.id];

      const badges = [
        winner ? '<span class="card-badge badge-winner">🏆 Nyertes</span>' : '',
        fav    ? '<span class="card-badge badge-fav">♥ Kedvenc</span>'     : '',
        isRef  ? '<span class="card-badge badge-ref">⚠️ Referencia</span>' : '',
      ].filter(Boolean).join('');

      const imgSlot = isRef
        ? `<div class="card-image-slot"><span class="no-img">📱</span></div>`
        : imgSrc
          ? `<div class="card-image-slot"><img src="${escHtml(imgSrc)}" alt="" /></div>`
          : `<div class="card-image-slot"><span class="no-img">📷</span></div>`;

      return `<div class="phone-card ${winner ? 'is-winner' : ''}" onclick="App.openDrawer('${p.id}')">
        <div class="card-top">
          <div class="card-name">${escHtml(p.name)}</div>
          <div class="card-badges">${badges}</div>
        </div>
        ${imgSlot}
        <div class="card-specs">
          <div class="spec-item">
            <span class="spec-label">Akkumulátor</span>
            <span class="spec-value">${escHtml(p.battery)}</span>
          </div>
          <div class="spec-item">
            <span class="spec-label">Szenzor</span>
            <span class="spec-value">${escHtml(p.sensor_size)}</span>
          </div>
          <div class="spec-item">
            <span class="spec-label">Rekesz</span>
            <span class="spec-value">${escHtml(p.aperture)}</span>
          </div>
          <div class="spec-item">
            <span class="spec-label">OIS</span>
            <span class="spec-value">${p.ois ? '✓' : '✗'}</span>
          </div>
          <div class="spec-item">
            <span class="spec-label">Zoom</span>
            <span class="spec-value">${escHtml(p.max_zoom) || '–'}</span>
          </div>
          <div class="spec-item">
            <span class="spec-label">Videó</span>
            <span class="spec-value">${escHtml(p.max_video)}</span>
          </div>
        </div>
        ${p.price ? `<div class="card-price">${escHtml(p.price)}</div>` : ''}
      </div>`;
    }).join('');

    const addCard = `<button class="phone-card add-phone-card" onclick="App.openPhoneModal()">
        <div class="add-card-icon">＋</div>
        <div class="add-card-label">Új telefon hozzáadása</div>
      </button>`;
    main.innerHTML = `<div class="cards-grid">${cards}${addCard}</div>`;
  }

  /* ---------------------------------------------------------------
     COMPARE VIEW
  --------------------------------------------------------------- */
  async function renderComparePage() {
    updateCompareSelectorChips();
    const selected = state.compareSelected;
    const main = document.getElementById('mainContent');

    if (selected.length === 0) {
      main.innerHTML = `
        <div class="compare-empty">
          <div class="big-icon">📊</div>
          <p>Válassz 2–3 telefont a fenti listából az összehasonlításhoz.</p>
        </div>`;
      return;
    }

    const phones = selected.map(id => state.phones.find(p => String(p.id) === String(id))).filter(Boolean);
    const cols = phones.length;

    // Fetch images for all non-reference phones in parallel
    const imageMap = {};
    await Promise.all(phones.map(async p => {
      if (p.is_reference) { imageMap[p.id] = []; return; }
      imageMap[p.id] = await fetch(`/api/phones/${encodeURIComponent(p.name)}/images`).then(r => r.json()).catch(() => []);
    }));

    // Compute best values across selected phones
    const bestMap = _computeBestMap(phones);

    const columns = phones.map(p => buildCompareCol(p, imageMap[p.id] || [], bestMap)).join('');

    main.innerHTML = `
      <div class="compare-grid" style="grid-template-columns: repeat(${cols}, 1fr);">
        ${columns}
      </div>`;

    // Wire up scroll-dot sync for each gallery
    phones.forEach(p => {
      const scroll = document.getElementById(`cmpGallery-${p.id}`);
      if (!scroll) return;
      scroll.addEventListener('scroll', () => {
        const idx = Math.round(scroll.scrollLeft / scroll.clientWidth);
        document.querySelectorAll(`#cmpDots-${p.id} .gallery-dot`).forEach((d, i) =>
          d.classList.toggle('active', i === idx)
        );
      });
    });
  }

  function buildCompareCol(p, images = [], bestMap = {}) {
    const winner = isWinner(p.id);
    const fav    = isFav(p.id);
    const isRef  = p.is_reference;

    const specs = [
      ['battery',     'Akkumulátor',  'battery'],
      ['sensor_size', 'Szenzorméret', 'sensor_size'],
      ['aperture',    'Rekesz',       'aperture'],
      ['ois',         'OIS',          'ois'],
      ['max_zoom',    'Max. zoom',    'max_zoom'],
      ['max_video',   'Max. videó',   'max_video'],
      ['storage',     'ROM / RAM',    'storage'],
      ['height',      'Ma. (mm)',     'height'],
      ['width',       'Sz. (mm)',     'width'],
      ['thickness',   'V. (mm)',      'thickness'],
    ].map(([field, label, colKey]) => {
      let val = p[field];
      if (field === 'ois') val = val ? '✓ Van' : '✗ Nincs';
      const isBest = bestMap[field] != null && String(bestMap[field]) === String(p.id);
      return `<div class="compare-spec">
        <span class="cs-label">
          ${label}
          <button class="info-btn" onclick="App.openDescModal('${colKey}', event)" title="Mi ez?">?</button>
        </span>
        <span class="cs-value${isBest ? ' best-value' : ''}">
          ${isBest ? '⭐ ' : ''}${escHtml(val ?? '–')}
        </span>
      </div>`;
    }).join('');

    let proConHtml = '';
    if (isRef) {
      proConHtml = `<div class="no-pro-con">⚠️ Referencia modell – nincs pro/kontra elemzés.</div>`;
    } else if (p.pro_con && p.pro_con.length > 0) {
      const pros = p.pro_con.filter(i => i.type === 'pro');
      const cons = p.pro_con.filter(i => i.type === 'con');
      const proItems = pros.map(i => `<div class="pro-item pro"><span class="icon">✅</span><span>${escHtml(i.text)}</span></div>`).join('');
      const conItems = cons.map(i => `<div class="pro-item con"><span class="icon">❌</span><span>${escHtml(i.text)}</span></div>`).join('');
      proConHtml = `
        <div class="pro-con-list">
          ${proItems}${conItems}
        </div>`;
    } else {
      proConHtml = `<div class="no-pro-con">Nincs elérhető pro/kontra adat.</div>`;
    }

    const recFor = p.recommended_for
      ? `<div class="compare-section">
           <div class="compare-section-title">🎯 Kinek ajánlott</div>
           <div class="recommended-for">${escHtml(p.recommended_for)}</div>
         </div>`
      : '';

    const winnerBtn = !isRef
      ? `<button class="btn-icon ${winner ? 'active' : ''}" title="${winner ? 'Nyertes törlése' : 'Nyertessé tenni'}"
           onclick="App.toggleWinner('${p.id}', event)">🏆</button>`
      : '';
    const favBtn = !isRef
      ? `<button class="btn-icon ${fav ? 'fav-active' : ''}" title="${fav ? 'Kedvencből eltávolít' : 'Kedvencekhez adja'}"
           onclick="App.toggleFavorite('${p.id}', event)">♥</button>`
      : '';

    // Gallery HTML
    let galleryHtml = '';
    if (!isRef) {
      if (images.length > 0) {
        const slides = images.map((src, i) =>
          `<div class="gallery-slide" style="min-height:160px;max-height:160px">
            <img src="${escHtml(src)}" alt="" style="min-height:160px;max-height:160px" />
          </div>`
        ).join('');
        const dots = images.length > 1
          ? `<div class="gallery-dots" id="cmpDots-${p.id}">${images.map((_, i) => `<div class="gallery-dot ${i===0?'active':''}" onclick="App._cmpScrollTo('${p.id}',${i})"></div>`).join('')}</div>`
          : '';
        galleryHtml = `
          <div class="cmp-gallery">
            <div class="gallery-scroll" id="cmpGallery-${p.id}" style="min-height:160px;max-height:160px">${slides}</div>
            ${dots}
          </div>`;
      } else {
        galleryHtml = `<div class="cmp-gallery-empty"><span>📷</span><span>Nincs kép</span></div>`;
      }
    }

    return `
      <div class="compare-col ${winner ? 'is-winner' : ''}">
        ${galleryHtml}
        <div class="compare-col-header">
          <div class="compare-col-name">${escHtml(p.name)}</div>
          ${p.price ? `<div class="compare-col-price">${escHtml(p.price)}</div>` : ''}
          ${winner || fav || isRef ? `<div class="compare-col-badges">
            ${winner ? '<span class="card-badge badge-winner">🏆 Nyertes</span>' : ''}
            ${fav    ? '<span class="card-badge badge-fav">♥ Kedvenc</span>'     : ''}
            ${isRef  ? '<span class="ref-badge">⚠️ Referencia</span>'           : ''}
          </div>` : ''}
          <div class="compare-col-actions">
            ${winnerBtn}${favBtn}
            <button class="btn-icon" title="Részletek" onclick="App.openDrawer('${p.id}', event)">🔍</button>
          </div>
        </div>
        <div class="compare-section">
          <div class="compare-section-title">Specifikációk</div>
          <div class="compare-spec-row">${specs}</div>
        </div>
        <div class="compare-section">
          <div class="compare-section-title">Pro / Kontra</div>
          ${proConHtml}
        </div>
        ${recFor}
      </div>`;
  }

  function updateCompareSelectorChips() {
    const bar   = document.getElementById('compareSelectorBar');
    const chips = document.getElementById('compareSelectorChips');
    if (!bar || !chips) return;

    chips.innerHTML = state.phones.map(p => {
      const sel = state.compareSelected.includes(String(p.id));
      const fav = isFav(p.id);
      return `<button class="chip ${sel ? 'selected' : ''} ${fav ? 'chip-fav' : ''}" onclick="App.toggleCompareSelect('${p.id}')">
        ${fav ? '<span class="chip-fav-dot">♥</span>' : ''}${escHtml(p.name)}
        ${sel ? '<span class="chip-remove">✕</span>' : ''}
      </button>`;
    }).join('');
  }

  function toggleCompareSelect(id) {
    const sid = String(id);
    const idx = state.compareSelected.indexOf(sid);
    if (idx >= 0) {
      state.compareSelected.splice(idx, 1);
    } else {
      // For compare, load pro_con if not present
      const phone = state.phones.find(p => String(p.id) === sid);
      if (phone && !phone.is_reference && !phone.pro_con) {
        fetch(`/api/phones/${sid}`)
          .then(r => r.json())
          .then(detail => {
            Object.assign(phone, detail);
            state.compareSelected.push(sid);
            renderComparePage();
          });
        return;
      }
      state.compareSelected.push(sid);
    }
    renderComparePage();
  }

  // ---------------------------------------------------------------
  // BEST VALUE SCORING HELPERS
  // ---------------------------------------------------------------
  function _extractNum(s, pattern) {
    const m = String(s ?? '').match(pattern);
    return m ? parseFloat(m[1]) : null;
  }
  function _scoreBattery(v)    { const n = _extractNum(v, /(\d+)\s*mAh/i);       return n ?? 0; }
  function _scoreSensor(v)     { const n = _extractNum(v, /1\/(\d+\.?\d*)/);     return n != null ? -n : -999; }
  function _scoreAperture(v)   { const n = _extractNum(v, /f\/(\d+\.?\d*)/i);   return n != null ? -n : -999; }
  function _scoreOis(v)        { return (v === true || v === 1) ? 1 : 0; }
  function _scoreZoom(v) {
    const s = String(v ?? '').toLowerCase();
    if (!s || s.includes('nincs') || s === '–') return 0;
    const m = s.match(/(\d+)×/);
    return m ? parseInt(m[1]) : 1;
  }
  function _scoreVideo(v) {
    const s = String(v ?? '').toLowerCase();
    if (s.includes('8k') && s.includes('120')) return 10;
    if (s.includes('8k'))                      return 9;
    if (s.includes('4k') && s.includes('120')) return 8;
    if (s.includes('4k') && s.includes('60'))  return 7;
    if (s.includes('4k'))                      return 6;
    if (s.includes('1080') && s.includes('60'))return 4;
    if (s.includes('1080'))                    return 3;
    return 0;
  }
  function _scoreRAM(v) {
    const m = String(v ?? '').match(/(\d+)\s*GB\s*RAM/i);
    return m ? parseInt(m[1]) : 0;
  }
  function _scoreThickness(v) { return v != null ? -parseFloat(v) : -999; }

  function _computeBestMap(phones) {
    const SCORERS = {
      battery:     _scoreBattery,
      sensor_size: _scoreSensor,
      aperture:    _scoreAperture,
      ois:         _scoreOis,
      max_zoom:    _scoreZoom,
      max_video:   _scoreVideo,
      storage:     _scoreRAM,
      thickness:   _scoreThickness,
    };
    const best = {};
    for (const [field, scorer] of Object.entries(SCORERS)) {
      let topScore = -Infinity, topId = null, tie = false;
      for (const p of phones) {
        const s = scorer(p[field]);
        if (s > topScore) { topScore = s; topId = String(p.id); tie = false; }
        else if (s === topScore && topScore > -Infinity) { tie = true; }
      }
      best[field] = tie ? null : topId;
    }
    return best;
  }

  function _cmpScrollTo(phoneId, index) {
    const scroll = document.getElementById(`cmpGallery-${phoneId}`);
    if (!scroll) return;
    scroll.scrollTo({ left: index * scroll.clientWidth, behavior: 'smooth' });
  }

  function clearCompareSelection() {
    state.compareSelected = [];
    renderComparePage();
  }

  /* ---------------------------------------------------------------
     DETAIL DRAWER
  --------------------------------------------------------------- */
  async function openDrawer(phoneId, event) {
    if (event) { event.stopPropagation(); }
    state.drawerPhoneId = String(phoneId);

    const phone = state.phones.find(p => String(p.id) === String(phoneId));
    if (!phone) return;

    // Fetch full detail (with pro_con) if not a reference
    let detail = phone;
    if (!phone.is_reference && !phone.pro_con) {
      detail = await fetch(`/api/phones/${phoneId}`).then(r => r.json());
      Object.assign(phone, detail);
    }

    const isRef  = phone.is_reference;
    const winner = isWinner(phone.id);
    const fav    = isFav(phone.id);

    // Header
    document.getElementById('drawerTitle').innerHTML = `
      <h2>${escHtml(phone.name)} ${winner ? '🏆' : ''}</h2>
      ${phone.price ? `<div class="drawer-price">${escHtml(phone.price)}</div>` : ''}
    `;

    const actions = !isRef ? `
      <button class="btn-icon ${winner ? 'active' : ''}" title="${winner ? 'Nyertes törlése' : 'Nyertessé tenni'}"
        onclick="App.toggleWinner('${phone.id}')">🏆</button>
      <button class="btn-icon ${fav ? 'fav-active' : ''}" title="${fav ? 'Kedvencből eltávolít' : 'Kedvencekhez'}"
        onclick="App.toggleFavorite('${phone.id}')">♥</button>
      <button class="btn-icon" title="Szerkesztés" onclick="App.openPhoneModal('${phone.id}')">✏️</button>
    ` : '<span class="ref-badge">⚠️ Referencia</span>';
    document.getElementById('drawerActions').innerHTML = actions;

    // Body
    document.getElementById('drawerBody').innerHTML = buildDrawerBody(phone);

    // Gallery
    if (!isRef) await refreshGallery(phone.name);

    // Show
    document.getElementById('drawerOverlay').classList.remove('hidden');
    document.getElementById('detailDrawer').classList.remove('hidden');
  }

  function buildDrawerBody(phone) {
    const isRef = phone.is_reference;

    // Specs
    const specRows = [
      ['battery',     'Akkumulátor',  phone.battery],
      ['sensor_size', 'Szenzorméret', phone.sensor_size],
      ['aperture',    'Rekesz',       phone.aperture],
      ['ois',         'OIS',          phone.ois ? '✓ Van' : '✗ Nincs'],
      ['max_zoom',    'Max. zoom',    phone.max_zoom || '–'],
      ['max_video',   'Max. videó',   phone.max_video],
      ['storage',     'ROM / RAM',    phone.storage],
      ['height',      'Magasság',     phone.height ? `${phone.height} mm` : '–'],
      ['width',       'Szélesség',    phone.width   ? `${phone.width} mm` : '–'],
      ['thickness',   'Vastagság',    phone.thickness ? `${phone.thickness} mm` : '–'],
    ].map(([, label, val]) =>
      `<div class="spec-item-d"><span class="sil">${label}</span><span class="siv">${escHtml(val)}</span></div>`
    ).join('');

    // Pro/con
    let proConSection = '';
    if (!isRef) {
      const pros = (phone.pro_con || []).filter(i => i.type === 'pro');
      const cons = (phone.pro_con || []).filter(i => i.type === 'con');
      const proList = pros.map(i => `<div class="pro-item pro"><span class="icon">✅</span><span>${escHtml(i.text)}</span></div>`).join('');
      const conList = cons.map(i => `<div class="pro-item con"><span class="icon">❌</span><span>${escHtml(i.text)}</span></div>`).join('');
      proConSection = `
        <div class="drawer-section">
          <div class="drawer-section-title">Pro / Kontra</div>
          <div class="pro-con-list">${proList}${conList || '<div class="no-pro-con">–</div>'}</div>
        </div>`;
    }

    // Recommended for
    const recSection = phone.recommended_for ? `
      <div class="drawer-section">
        <div class="drawer-section-title">🎯 Kinek ajánlott</div>
        <div class="recommended-for">${escHtml(phone.recommended_for)}</div>
      </div>` : '';

    // Link
    const linkSection = phone.link ? `
      <div class="drawer-section">
        <a href="${escHtml(phone.link)}" target="_blank" rel="noopener" class="btn-secondary btn-sm">
          🔗 Termékoldalra
        </a>
      </div>` : '';

    // Gallery placeholder
    const gallerySection = !isRef ? `
      <div class="gallery-section" id="gallerySection">
        <div class="gallery-scroll" id="galleryScroll"></div>
        <div class="gallery-dots" id="galleryDots"></div>
        <div class="gallery-upload-bar">
          <span class="gallery-count" id="galleryCount">–</span>
          <button class="btn-primary btn-sm" onclick="App.triggerUpload('${escHtml(phone.name)}')">📷 Kép feltöltése</button>
        </div>
      </div>` : '';

    return `
      ${gallerySection}
      <div class="drawer-section">
        <div class="drawer-section-title">Specifikációk</div>
        <div class="specs-grid">${specRows}</div>
      </div>
      ${proConSection}
      ${recSection}
      ${linkSection}
    `;
  }

  async function refreshGallery(phoneName) {
    const scroll = document.getElementById('galleryScroll');
    const dots   = document.getElementById('galleryDots');
    const count  = document.getElementById('galleryCount');
    if (!scroll) return;

    const imgs = await fetch(`/api/phones/${encodeURIComponent(phoneName)}/images`).then(r => r.json());

    if (imgs.length === 0) {
      scroll.innerHTML = `<div class="gallery-empty"><span class="gi">📷</span><p>Még nincs feltöltött kép</p></div>`;
      dots.innerHTML = '';
      if (count) count.textContent = '0 kép';
      return;
    }

    scroll.innerHTML = imgs.map((src, i) =>
      `<div class="gallery-slide" data-index="${i}">
        <img src="${escHtml(src)}" alt="Kép ${i + 1}" />
        <button class="delete-img-btn" onclick="App.deleteImage('${escHtml(phoneName)}', '${escHtml(src.split('/').pop())}', event)">🗑</button>
      </div>`
    ).join('');

    dots.innerHTML = imgs.map((_, i) =>
      `<div class="gallery-dot ${i === 0 ? 'active' : ''}" onclick="App.scrollToSlide(${i})"></div>`
    ).join('');

    if (count) count.textContent = `${imgs.length} kép`;

    // Update dots on scroll
    scroll.onscroll = () => {
      const idx = Math.round(scroll.scrollLeft / scroll.clientWidth);
      document.querySelectorAll('.gallery-dot').forEach((d, i) =>
        d.classList.toggle('active', i === idx)
      );
    };
  }

  function scrollToSlide(index) {
    const scroll = document.getElementById('galleryScroll');
    if (!scroll) return;
    scroll.scrollTo({ left: index * scroll.clientWidth, behavior: 'smooth' });
  }

  function triggerUpload(phoneName) {
    const input = document.getElementById('fileUploadInput');
    input.onchange = () => uploadImages(phoneName, input.files);
    input.value = '';
    input.click();
  }

  async function uploadImages(phoneName, files) {
    if (!files || files.length === 0) return;
    const fd = new FormData();
    for (const f of files) fd.append('images', f);
    await fetch(`/api/phones/${encodeURIComponent(phoneName)}/images`, {
      method: 'POST',
      body: fd,
    });
    await refreshGallery(phoneName);
    // Refresh card view image if active
    if (state.view === 'cards') renderCards(state.phones);
  }

  async function deleteImage(phoneName, filename, event) {
    event.stopPropagation();
    if (!confirm('Törlöd ezt a képet?')) return;
    await fetch(`/api/phones/${encodeURIComponent(phoneName)}/images/${encodeURIComponent(filename)}`, {
      method: 'DELETE',
    });
    await refreshGallery(phoneName);
    if (state.view === 'cards') renderCards(state.phones);
  }

  function closeDrawer() {
    document.getElementById('drawerOverlay').classList.add('hidden');
    document.getElementById('detailDrawer').classList.add('hidden');
    state.drawerPhoneId = null;
  }

  /* ---------------------------------------------------------------
     FAVORITES & WINNER
  --------------------------------------------------------------- */
  async function toggleFavorite(id, event) {
    if (event) event.stopPropagation();
    const sid = String(id);
    const favs = state.appState.favorites.map(String);
    const idx = favs.indexOf(sid);
    if (idx >= 0) favs.splice(idx, 1);
    else favs.push(sid);
    state.appState.favorites = favs;
    await fetch('/api/state', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ favorites: favs }),
    });
    renderView();
    // Re-render drawer actions if open
    if (state.drawerPhoneId === sid) openDrawer(sid);
  }

  async function toggleWinner(id, event) {
    if (event) event.stopPropagation();
    const sid = String(id);
    const newWinner = isWinner(sid) ? null : sid;
    state.appState.winner = newWinner;
    await fetch('/api/state', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ winner: newWinner }),
    });
    updateWinnerBanner();
    renderView();
    if (state.drawerPhoneId === sid) openDrawer(sid);
  }

  async function clearWinner() {
    state.appState.winner = null;
    await fetch('/api/state', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ winner: null }),
    });
    updateWinnerBanner();
    renderView();
  }

  function updateWinnerBanner() {
    const banner = document.getElementById('winnerBanner');
    const text   = document.getElementById('winnerBannerText');
    const w = state.appState.winner;
    if (!w) { banner.classList.add('hidden'); return; }
    const phone = state.phones.find(p => String(p.id) === String(w));
    if (!phone) { banner.classList.add('hidden'); return; }
    text.textContent = `Nyertes: ${phone.name}`;
    banner.classList.remove('hidden');
  }

  /* ---------------------------------------------------------------
     COLUMN DESCRIPTION MODAL
  --------------------------------------------------------------- */
  function openDescModal(colKey, event) {
    if (event) event.stopPropagation();
    state.activeDescKey = colKey;
    const d = state.descriptions.find(d => d.column_key === colKey);
    document.getElementById('descModalTitle').textContent = d ? d.label : colKey;
    document.getElementById('descModalText').textContent  = d ? d.description : '–';
    document.getElementById('descModalOverlay').classList.remove('hidden');
    document.getElementById('descModal').classList.remove('hidden');
  }

  function closeDescModal() {
    document.getElementById('descModalOverlay').classList.add('hidden');
    document.getElementById('descModal').classList.add('hidden');
    state.activeDescKey = null;
  }

  /* ---------------------------------------------------------------
     PHONE EDITOR MODAL
  --------------------------------------------------------------- */
  async function openPhoneModal(phoneId) {
    const modal = document.getElementById('phoneModal');
    const overlay = document.getElementById('phoneModalOverlay');
    const deleteBtn = document.getElementById('pmDeleteBtn');

    // Reset form
    document.getElementById('pmPhoneId').value = '';
    document.getElementById('pmName').value = '';
    document.getElementById('pmPrice').value = '';
    document.getElementById('pmLink').value = '';
    document.getElementById('pmSensorSize').value = '';
    document.getElementById('pmAperture').value = '';
    document.getElementById('pmOis').checked = false;
    document.getElementById('pmMaxZoom').value = '';
    document.getElementById('pmMaxVideo').value = '';
    document.getElementById('pmBattery').value = '';
    document.getElementById('pmStorage').value = '';
    document.getElementById('pmHeight').value = '';
    document.getElementById('pmWidth').value = '';
    document.getElementById('pmThickness').value = '';
    document.getElementById('pmPros').value = '';
    document.getElementById('pmCons').value = '';
    document.getElementById('pmRecommendedFor').value = '';
    deleteBtn.classList.add('hidden');

    if (phoneId) {
      document.getElementById('phoneModalTitle').textContent = 'Telefon szerkesztése';
      deleteBtn.classList.remove('hidden');

      // Load full details if needed
      let phone = state.phones.find(p => String(p.id) === String(phoneId));
      if (phone && !phone.pro_con) {
        phone = await fetch(`/api/phones/${phoneId}`).then(r => r.json());
        const existing = state.phones.find(p => String(p.id) === String(phoneId));
        if (existing) Object.assign(existing, phone);
      }
      if (!phone) return;

      document.getElementById('pmPhoneId').value = phone.id;
      document.getElementById('pmName').value = phone.name || '';
      document.getElementById('pmPrice').value = phone.price || '';
      document.getElementById('pmLink').value = phone.link || '';
      document.getElementById('pmSensorSize').value = phone.sensor_size || '';
      document.getElementById('pmAperture').value = phone.aperture || '';
      document.getElementById('pmOis').checked = !!phone.ois;
      document.getElementById('pmMaxZoom').value = phone.max_zoom || '';
      document.getElementById('pmMaxVideo').value = phone.max_video || '';
      document.getElementById('pmBattery').value = phone.battery || '';
      document.getElementById('pmStorage').value = phone.storage || '';
      document.getElementById('pmHeight').value = phone.height ?? '';
      document.getElementById('pmWidth').value = phone.width ?? '';
      document.getElementById('pmThickness').value = phone.thickness ?? '';
      const pros = (phone.pro_con || []).filter(i => i.type === 'pro').map(i => i.text);
      const cons = (phone.pro_con || []).filter(i => i.type === 'con').map(i => i.text);
      document.getElementById('pmPros').value = pros.join('\n');
      document.getElementById('pmCons').value = cons.join('\n');
      document.getElementById('pmRecommendedFor').value = phone.recommended_for || '';
    } else {
      document.getElementById('phoneModalTitle').textContent = 'Új telefon hozzáadása';
    }

    overlay.classList.remove('hidden');
    modal.classList.remove('hidden');
    document.getElementById('pmName').focus();
  }

  function closePhoneModal() {
    document.getElementById('phoneModal').classList.add('hidden');
    document.getElementById('phoneModalOverlay').classList.add('hidden');
  }

  async function savePhone() {
    const id = document.getElementById('pmPhoneId').value;
    const name = document.getElementById('pmName').value.trim();
    if (!name) { alert('A modell neve kötelező!'); return; }

    const pros = document.getElementById('pmPros').value.split('\n').map(s => s.trim()).filter(Boolean);
    const cons = document.getElementById('pmCons').value.split('\n').map(s => s.trim()).filter(Boolean);

    const payload = {
      name,
      price:           document.getElementById('pmPrice').value.trim(),
      link:            document.getElementById('pmLink').value.trim(),
      sensor_size:     document.getElementById('pmSensorSize').value.trim(),
      aperture:        document.getElementById('pmAperture').value.trim(),
      ois:             document.getElementById('pmOis').checked,
      max_zoom:        document.getElementById('pmMaxZoom').value.trim(),
      max_video:       document.getElementById('pmMaxVideo').value.trim(),
      battery:         document.getElementById('pmBattery').value.trim(),
      storage:         document.getElementById('pmStorage').value.trim(),
      height:          document.getElementById('pmHeight').value || null,
      width:           document.getElementById('pmWidth').value || null,
      thickness:       document.getElementById('pmThickness').value || null,
      recommended_for: document.getElementById('pmRecommendedFor').value.trim(),
      pros,
      cons,
    };

    const url    = id ? `/api/phones/${id}` : '/api/phones';
    const method = id ? 'PUT' : 'POST';
    const res    = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(err.error || 'Mentési hiba!');
      return;
    }

    const saved = await res.json();
    saved.is_reference = false;

    if (id) {
      // Update in local state
      const idx = state.phones.findIndex(p => String(p.id) === String(id));
      if (idx >= 0) {
        state.phones[idx] = { ...state.phones[idx], ...saved };
        // Preserve pro_con list
        const pros2 = pros.map(t => ({ type: 'pro', text: t }));
        const cons2 = cons.map(t => ({ type: 'con', text: t }));
        state.phones[idx].pro_con = [...pros2, ...cons2];
      }
    } else {
      // Insert before reference phone
      const refIdx = state.phones.findIndex(p => p.is_reference);
      if (refIdx >= 0) state.phones.splice(refIdx, 0, saved);
      else state.phones.push(saved);
    }

    closePhoneModal();
    renderView();
  }

  async function deletePhone() {
    const id = document.getElementById('pmPhoneId').value;
    if (!id) return;
    const phone = state.phones.find(p => String(p.id) === String(id));
    if (!confirm(`Biztosan törlöd: „${phone?.name}"?`)) return;

    const res = await fetch(`/api/phones/${id}`, { method: 'DELETE' });
    if (!res.ok) { alert('Törlési hiba!'); return; }

    state.phones = state.phones.filter(p => String(p.id) !== String(id));
    // Remove from compare/favorites/winner if present
    state.compareSelected = state.compareSelected.filter(x => x !== String(id));
    state.appState.favorites = state.appState.favorites.filter(x => x !== String(id));
    if (String(state.appState.winner) === String(id)) {
      state.appState.winner = null;
      await fetch('/api/state', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ winner: null }) });
    }
    closePhoneModal();
    closeDrawer();
    renderView();
    updateWinnerBanner();
  }

  /* ---------------------------------------------------------------
     Public API
  --------------------------------------------------------------- */
  return {
    init,
    setView,
    openDrawer,
    closeDrawer,
    toggleFavorite,
    toggleWinner,
    clearWinner,
    clearCompareSelection,
    toggleCompareSelect,
    openPhoneModal,
    closePhoneModal,
    savePhone,
    deletePhone,
    openDescModal,
    closeDescModal,
    triggerUpload,
    deleteImage,
    scrollToSlide,
    _sortBy,
    _cmpScrollTo,
  };
})();

document.addEventListener('DOMContentLoaded', () => App.init());
