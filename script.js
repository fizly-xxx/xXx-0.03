// ── ВКЛАДКИ (НАВИГАЦИЯ) ──
function switchTab(id, btn) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
  document.getElementById('panel-' + id).classList.add('active');
  btn.classList.add('active');
}

// ── ЛОГИКА РАДИО-КНОПОК (ВКЛАДКА SETTINGS) ──
function selectMode(el) {
  document.querySelectorAll('.radio-option').forEach(o => o.classList.remove('selected'));
  el.classList.add('selected');

  const mode = el.querySelector('input').value;
  
  document.querySelectorAll('.param-group').forEach(group => {
    group.style.display = 'none';
  });
  
  const targetGroup = document.getElementById('group-' + mode);
  if (targetGroup) {
    targetGroup.style.display = 'grid';
  }
}

// ── ТУМБЛЕР TELEGRAM ──
function handleTgToggle(cb) {
  const fields = document.getElementById('tg-fields');
  fields.style.opacity = cb.checked ? '1' : '0.4';
  fields.style.pointerEvents = cb.checked ? 'auto' : 'none';
}

// ── СТАРТ / СТОП БОТА ──
let botRunning = false;
function toggleBot() {
  botRunning = !botRunning;
  const btn = document.getElementById('start-btn');
  if (botRunning) {
    btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg> STOP`;
    btn.classList.remove('btn-primary');
    btn.classList.add('btn-danger');
    addLog('OK', 'Bot started — monitoring market');
    document.querySelector('.status-pill').innerHTML = '<div class="status-dot"></div> RUNNING';
  } else {
    btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg> START`;
    btn.classList.remove('btn-danger');
    btn.classList.add('btn-primary');
    addLog('WARN', 'Bot stopped by user');
    document.querySelector('.status-pill').innerHTML = '<div class="status-dot"></div> CONNECTED';
  }
}

// ── ТОКЕН HANDSHAKE ──
function saveHandshake() {
  const v = document.getElementById('handshake-input').value.trim();
  if (!v) return;
  addLog('OK', `Handshake saved: ${v.substring(0,12)}…`);
  saveConfig(); // Зберігаємо відразу
}

// ── ИНВЕНТАРЬ ──
// Скіни видалено, масив порожній
const skins = [];
document.getElementById('inv-count').textContent = skins.length + ' items';

function renderInventory() {
  const grid = document.getElementById('inv-grid');
  if (skins.length === 0) {
    grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text3); padding: 40px 0; font-size: 11px;">Inventory is empty</div>';
    return;
  }
  
  grid.innerHTML = skins.map((s, i) => `
    <div class="skin-card">
      <div class="skin-img">
        ${s.emoji}
        <div class="skin-rarity ${s.rarity}"></div>
      </div>
      <div class="skin-info">
        <div class="skin-name">${s.name}</div>
        <div class="skin-wear">${s.wear}</div>
        <div class="skin-sell-row">
          <div class="skin-price">${s.price}</div>
          <button class="btn btn-ghost btn-sm" onclick="openSellModal(${i})">Sell</button>
        </div>
      </div>
    </div>
  `).join('');
}
renderInventory();

// ── МОДАЛЬНОЕ ОКНО ──
let currentSkinIdx = null;
function openSellModal(idx) {
  currentSkinIdx = idx;
  const skin = skins[idx];
  document.getElementById('modal-skin-name').textContent = skin.name + ' · ' + skin.wear;
  document.getElementById('modal-market-price').textContent = skin.price;
  document.getElementById('sell-price-input').value = skin.price.replace('$', '');
  updateReceive();
  document.getElementById('sell-modal').classList.add('open');
  document.getElementById('sell-price-input').focus();
}
function closeModal() {
  document.getElementById('sell-modal').classList.remove('open');
  currentSkinIdx = null;
}
function updateReceive() {
  const v = parseFloat(document.getElementById('sell-price-input').value);
  document.getElementById('modal-receive').textContent = isNaN(v) ? '—' : '$' + (v * 0.87).toFixed(2);
}
document.getElementById('sell-price-input').addEventListener('input', updateReceive);

function confirmSell() {
  if (currentSkinIdx === null) return;
  const skin = skins[currentSkinIdx];
  const price = document.getElementById('sell-price-input').value;
  addLog('OK', `Listed "${skin.name}" for $${price}`);
  closeModal();
}

document.getElementById('sell-modal').addEventListener('click', function(e) {
  if (e.target === this) closeModal();
});

// ── ЛОГИ ──
const logData = [
  { level: 'INFO', msg: 'TradeBot UI initialized' },
  { level: 'INFO', msg: 'Awaiting python backend connection...' }
];

function formatTime() {
  return new Date().toLocaleTimeString('en-US', { hour12: false, hour:'2-digit', minute:'2-digit', second:'2-digit' });
}

function addLog(level, msg) {
  const c = document.getElementById('log-console');
  const line = document.createElement('div');
  line.className = 'log-line';
  line.innerHTML = `<span class="log-time">${formatTime()}</span><span class="log-tag ${level}">${level}</span><span class="log-msg${level === 'OK' || level === 'ERR' ? ' highlight' : ''}">${msg}</span>`;
  c.appendChild(line);
  c.scrollTop = c.scrollHeight;
}

function clearLogs() {
  document.getElementById('log-console').innerHTML = '';
  addLog('INFO', 'Console cleared');
}

// Заполнение начальных логов
logData.forEach(l => addLog(l.level, l.msg));

// ── КОНФІГУРАЦІЯ ТА АВТОЗБЕРЕЖЕННЯ ──
function collectConfig() {
  return {
    tradeDelay: document.getElementById('trade-delay')?.value,
    orderHold: document.getElementById('order-hold')?.value,
    skin: document.getElementById('skin-select')?.value,
    handshake: document.getElementById('handshake-input')?.value,
    
    mode: document.querySelector('input[name="mode"]:checked')?.value,
    customPrice: document.getElementById('custom-price')?.value,
    minPrice: document.getElementById('min-price')?.value,
    maxPrice: document.getElementById('max-price')?.value,
    outbidDelta: document.getElementById('outbid-delta')?.value,
    outbidDelay: document.getElementById('outbid-delay')?.value,
    
    telegramEnabled: document.getElementById('tg-toggle')?.checked,
    botToken: document.getElementById('bot-token')?.value,
    chatId: document.getElementById('chat-id')?.value,
    tgNotify: document.getElementById('tg-notify')?.value,
    tgFormat: document.getElementById('tg-format')?.value
  };
}

async function saveConfig() {
  const config = collectConfig();
  // Перевірка, чи запущено через Python (щоб не ламалось в браузері)
  if (window.pywebview && window.pywebview.api) {
    await window.pywebview.api.save_config(config); 
    // addLog('INFO', 'Settings auto-saved'); // Можна розкоментувати, якщо потрібен лог
  } else {
    console.log("Auto-save: pywebview not found. Config:", config);
  }
}

async function loadConfig() {
  if (window.pywebview && window.pywebview.api) {
    const config = await window.pywebview.api.load_config(); 
    if (!config || Object.keys(config).length === 0) return;

    if (config.tradeDelay) document.getElementById('trade-delay').value = config.tradeDelay;
    if (config.orderHold) document.getElementById('order-hold').value = config.orderHold;
    if (config.skin) document.getElementById('skin-select').value = config.skin;
    if (config.handshake) document.getElementById('handshake-input').value = config.handshake;

    if (config.mode) {
      const modeRadio = document.querySelector(`input[name="mode"][value="${config.mode}"]`);
      if (modeRadio) {
        modeRadio.checked = true;
        selectMode(modeRadio.closest('.radio-option'));
      }
    }

    if (config.customPrice) document.getElementById('custom-price').value = config.customPrice;
    if (config.minPrice) document.getElementById('min-price').value = config.minPrice;
    if (config.maxPrice) document.getElementById('max-price').value = config.maxPrice;
    if (config.outbidDelta) document.getElementById('outbid-delta').value = config.outbidDelta;
    if (config.outbidDelay) document.getElementById('outbid-delay').value = config.outbidDelay;

    if (config.botToken) document.getElementById('bot-token').value = config.botToken;
    if (config.chatId) document.getElementById('chat-id').value = config.chatId;
    if (config.tgNotify) document.getElementById('tg-notify').value = config.tgNotify;
    if (config.tgFormat) document.getElementById('tg-format').value = config.tgFormat;

    if (config.telegramEnabled !== undefined) {
      const tg = document.getElementById('tg-toggle');
      if (tg) {
        tg.checked = config.telegramEnabled;
        handleTgToggle(tg);
      }
    }
    addLog('OK', 'Config loaded successfully');
  }
}

function enableAutoSave(){
  document.querySelectorAll('input,select,textarea').forEach(el=>{
    el.addEventListener('input', ()=>{
      clearTimeout(el._t);
      el._t = setTimeout(saveConfig, 800); // Зберігає через 800мс після останнього вводу
    });
    el.addEventListener('change', saveConfig);
  });
}

// Ініціалізація
window.addEventListener('DOMContentLoaded', ()=>{
  enableAutoSave();
});

window.addEventListener('pywebviewready', function() {
  loadConfig();
});