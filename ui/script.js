// ==============================================
// 1. ГЛОБАЛЬНИЙ СТАН (STATE)
// ==============================================
const state = {
    botRunning: false,
    inventoryItems: [],
    activeSales: [],
    currentWeaponSkinsGrouped: {},
    sellModalTargetId: null,
    autosaveTimer: null
};
window.LOG_LEVEL = 'INFO';

// ==============================================
// 2. ІНІЦІАЛІЗАЦІЯ
// ==============================================
window.addEventListener('pywebviewready', async () => {
    addLog('OK', 'Зв\'язок з Python встановлено!');
    try {
        await initWeapons();
        await loadConfig();
        attachAutoSaveListeners();

        if (window.pywebview && window.pywebview.api) {
            await window.pywebview.api.start_price_polling();
        }
    } catch (e) {
        addLog('ERR', `Помилка при ініціалізації: ${e.message || e}`);
    }
});

function getHandshake() {
    const hs = document.getElementById('handshake-input')?.value.trim();
    if (!hs) addLog('WARN', 'Handshake не введено!');
    return hs;
}

// ==============================================
// 3. АВТОЗБЕРЕЖЕННЯ (DEBOUNCE)
// ==============================================
function gatherConfigFromUI() {
    const cfg = { botRunning: state.botRunning };
    
    const hs = document.getElementById('handshake-input')?.value.trim();
    if (hs) cfg.handshake = hs;

    cfg.tradeDelay = parseInt(document.getElementById('trade-delay')?.value) || 1000;
    cfg.orderHold = parseInt(document.getElementById('order-hold')?.value) || 3600;

    const modeInput = document.querySelector('input[name="mode"]:checked');
    if (modeInput) cfg.mode = modeInput.value;

    cfg.customPrice = parseFloat(document.getElementById('custom-price')?.value) || 0.01;
    cfg.outbidDelta = parseFloat(document.getElementById('outbid-delta')?.value) || 0.01;

    const skinId = document.getElementById('final-skin-id')?.textContent;
    if (skinId && skinId !== '—') cfg.skin = skinId;
    cfg.isStattrak = document.getElementById('is-stattrak')?.checked || false;

    cfg.telegram = {
        enabled: document.getElementById('tg-toggle')?.checked || false,
        token: document.getElementById('bot-token')?.value || '',
        chatId: document.getElementById('chat-id')?.value || '',
        notifyBuy: document.getElementById('tg-notify-buy')?.checked || false,
        notifySell: document.getElementById('tg-notify-sell')?.checked || false,
        notifyStatus: document.getElementById('tg-notify-status')?.checked || false
    };

    return cfg;
}

function autosaveConfig() {
    if (!window.pywebview || !window.pywebview.api) return;
    window.pywebview.api.save_config(gatherConfigFromUI()).catch(e => {
        addLog('ERR', `Помилка автозбереження: ${e.message || e}`);
    });
}

function attachAutoSaveListeners() {
    const triggerSave = () => {
        clearTimeout(state.autosaveTimer);
        state.autosaveTimer = setTimeout(autosaveConfig, 700);
    };

    document.querySelectorAll('input, select, textarea').forEach(el => {
        if (el.id?.startsWith('price-') || el.id === 'sell-price-input') return;
        el.addEventListener(el.type === 'checkbox' || el.tagName === 'SELECT' ? 'change' : 'input', triggerSave);
    });
    document.querySelectorAll('.radio-option').forEach(o => o.addEventListener('click', triggerSave));
}

// ==============================================
// 4. НАВІГАЦІЯ ТА UI
// ==============================================
function switchTab(tabId, btnElement) {
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));

    const targetPanel = document.getElementById('panel-' + tabId);
    if (targetPanel) targetPanel.classList.add('active');
    if (btnElement) btnElement.classList.add('active');
    
    if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.set_active_tab(tabId);
    }

    if (tabId === 'inventory') loadInventory();
    if (tabId === 'sales') loadSales();
}

function selectMode(el) {
    document.querySelectorAll('.radio-option').forEach(o => o.classList.remove('selected'));
    el.classList.add('selected');
    const radioInput = el.querySelector('input');
    if (radioInput) radioInput.checked = true;

    document.querySelectorAll('.param-group').forEach(group => group.style.display = 'none');
    const targetGroup = document.getElementById('group-' + (radioInput?.value || 'custom'));
    if (targetGroup) targetGroup.style.display = 'grid';
}

function handleTgToggle(cb) {
    const container = document.getElementById('tg-fields');
    if (!container) return;
    const inputs = container.querySelectorAll('input');
    
    container.style.opacity = cb.checked ? '1' : '0.4';
    container.style.pointerEvents = cb.checked ? 'auto' : 'none';
    inputs.forEach(input => input.disabled = !cb.checked);
}

// ==============================================
// 5. ЛОГІКА БОТА ТА КОНФІГ
// ==============================================
async function loadConfig() {
    if (!window.pywebview || !window.pywebview.api) return;
    try {
        const config = await window.pywebview.api.load_config();
        if (!config) return;

        window.LOG_LEVEL = (config.logLevel || 'INFO').toUpperCase();
        highlightLogLevelBadge(window.LOG_LEVEL);

        if (config.handshake) document.getElementById('handshake-input').value = config.handshake;
        
        if (config.mode) {
            const radio = document.querySelector(`input[name="mode"][value="${config.mode}"]`);
            if (radio && radio.closest('.radio-option')) selectMode(radio.closest('.radio-option'));
        }

        state.botRunning = false;
        reflectBotState();
        window.pywebview.api.save_config({ botRunning: false });

        if (config.tradeDelay) document.getElementById('trade-delay').value = config.tradeDelay;
        if (config.orderHold) document.getElementById('order-hold').value = config.orderHold;
        if (config.customPrice) document.getElementById('custom-price').value = config.customPrice;
        if (config.outbidDelta) document.getElementById('outbid-delta').value = config.outbidDelta;

        if (config.telegram) {
            document.getElementById('bot-token').value = config.telegram.token || '';
            document.getElementById('chat-id').value = config.telegram.chatId || '';
            const tgToggle = document.getElementById('tg-toggle');
            if (tgToggle) {
                tgToggle.checked = !!config.telegram.enabled;
                handleTgToggle(tgToggle);
            }
            document.getElementById('tg-notify-buy').checked = !!config.telegram.notifyBuy;
            document.getElementById('tg-notify-sell').checked = !!config.telegram.notifySell;
            document.getElementById('tg-notify-status').checked = !!config.telegram.notifyStatus;
        }

        if (config.skin) document.getElementById('final-skin-id').textContent = String(config.skin);
        addLog('OK', 'Налаштування відновлено.');
    } catch (e) {
        addLog('ERR', `Помилка завантаження конфіга: ${e.message}`);
    }
}

async function toggleBot() {
    state.botRunning = !state.botRunning;
    reflectBotState();
    if (window.pywebview && window.pywebview.api) {
        try {
            await window.pywebview.api.toggle_bot_engine(state.botRunning);
            await window.pywebview.api.save_config({ botRunning: state.botRunning });
        } catch (e) {
            addLog('ERR', `Помилка: ${e.message}`);
        }
    }
}

function reflectBotState() {
    const btn = document.getElementById('start-btn');
    const statusPill = document.querySelector('.status-pill');
    if (state.botRunning) {
        if (btn) { btn.textContent = 'STOP'; btn.classList.add('running'); }
        if (statusPill) statusPill.innerHTML = '<div class="status-dot"></div> RUNNING';
        addLog('OK', 'Бот запущено');
    } else {
        if (btn) { btn.textContent = 'START'; btn.classList.remove('running'); }
        if (statusPill) statusPill.innerHTML = '<div class="status-dot"></div> CONNECTED';
        addLog('WARN', 'Бот зупинено');
    }
}

async function saveHandshake() {
    const handshake = getHandshake();
    if (!handshake) return;
    try {
        await window.pywebview.api.save_config({ handshake: handshake });
        addLog('OK', 'Handshake збережено.');
    } catch (e) {
        addLog('ERR', `Помилка збереження handshake: ${e.message}`);
    }
}

// ==============================================
// 6. ІНВЕНТАР ТА РИНОК
// ==============================================
async function loadInventory() {
    const handshake = getHandshake();
    if (!handshake || !window.pywebview?.api) return;

    addLog('INFO', 'Завантаження інвентарю...');
    try {
        const res = await window.pywebview.api.fetch_inventory(handshake);
        if (res && res.success) {
            state.inventoryItems = res.items || [];
            document.getElementById('inv-count').textContent = `${state.inventoryItems.length} шт.`;
            if (res.gold) document.getElementById('balance-display').textContent = `${Number(res.gold).toFixed(2)} G`;
            renderInventory();
            addLog('OK', `Інвентар завантажено.`);
        } else {
            addLog('ERR', `Помилка інвентаря: ${res?.error || 'невідома'}`);
        }
    } catch (e) {
        addLog('ERR', `Помилка: ${e.message}`);
    }
}

function renderInventory() {
    const grid = document.getElementById('inv-grid');
    if (!grid) return;
    grid.innerHTML = '';

    if (state.inventoryItems.length === 0) {
        grid.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text2); grid-column: 1/-1;">Інвентар порожній</div>';
        return;
    }

    state.inventoryItems.forEach(item => {
        const card = document.createElement('div');
        card.className = 'skin-card';
        const stickerStyle = item.stickers >= 4 ? 'color: #ffeb3b; font-weight: 800;' : 'color: var(--accent);';

        card.innerHTML = `
            <div class="skin-info">
                <div class="skin-name">${item.name || 'Unknown'}</div>
                <div class="skin-wear" style="${stickerStyle}">${item.stickers > 0 ? '🔥 ' + item.stickers : 'No Stickers'}</div>
                <div class="skin-sell-row">
                    <button onclick="getSmartPrice('${item.id}', '${item.def_id}')" class="btn btn-ghost btn-sm" style="padding: 6px; margin-right: 4px;" title="Смарт-ціна">🧠</button>
                    <input type="text" id="price-${item.id}" placeholder="0.00" style="width: 70px; padding: 6px 10px; font-size: 11px;">
                    <button onclick="sellItem('${item.id}')" class="btn btn-primary btn-sm" style="flex: 1; margin-left: 4px;">SELL</button>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

async function sellItem(itemId) {
    const handshake = getHandshake();
    if (!handshake) return;
    const priceInput = document.getElementById(`price-${itemId}`);
    const price = parseFloat(priceInput?.value);
    
    if (isNaN(price) || price <= 0) {
        addLog('WARN', 'Введіть коректну ціну!'); return;
    }

    try {
        const res = await window.pywebview.api.sell_item(handshake, Number(itemId), price);
        if (res && res.success) {
            addLog('OK', `Виставлено за ${price}G!`);
            if (priceInput) priceInput.value = '';
            setTimeout(loadInventory, 1000);
        } else {
            addLog('ERR', `Помилка продажу: ${res?.error}`);
        }
    } catch (e) {
        addLog('ERR', `Помилка: ${e.message}`);
    }
}

async function getSmartPrice(itemId, defId) {
    const handshake = getHandshake();
    if (!handshake) return;
    const priceInput = document.getElementById(`price-${itemId}`);
    if (priceInput) priceInput.placeholder = "⌛...";

    try {
        const res = await window.pywebview.api.get_smart_sell_price(handshake, defId);
        if (res && res.success) {
            if (priceInput) priceInput.value = res.price;
            addLog('OK', `Смарт-ціна: ${res.price} G (Найнижчий лот: ${res.lowest} G)`);
        } else {
            addLog('ERR', `Помилка розрахунку: ${res?.error}`);
            if (priceInput) priceInput.placeholder = "0.00";
        }
    } catch (e) {
        addLog('ERR', `Помилка: ${e.message}`);
    }
}

async function loadSales() {
    const handshake = getHandshake();
    if (!handshake || !window.pywebview?.api) return;

    addLog('INFO', 'Завантаження активних лотів...');
    try {
        const res = await window.pywebview.api.fetch_sales(handshake);
        if (res && res.success) {
            state.activeSales = res.sales || [];
            document.getElementById('sales-count').textContent = `${state.activeSales.length} шт.`;
            renderSales();
        } else {
            addLog('ERR', `Помилка ринку: ${res?.error}`);
        }
    } catch (e) {
        addLog('ERR', `Помилка: ${e.message}`);
    }
}

function renderSales() {
    const grid = document.getElementById('sales-grid');
    if (!grid) return;
    grid.innerHTML = '';

    if (state.activeSales.length === 0) {
        grid.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text2); grid-column: 1/-1;">Активних лотів немає</div>';
        return;
    }

    state.activeSales.forEach(lot => {
        const card = document.createElement('div');
        card.className = 'skin-card';
        card.innerHTML = `
            <div class="skin-info">
                <div class="skin-name">${lot.name || 'Unknown'}</div>
                <div class="skin-price" style="width: 80px; text-align: center;">${lot.price || '—'} G</div>
                <button onclick="cancelLot('${lot.id}')" class="btn btn-danger btn-sm" style="width: 110px;">СКАСУВАТИ</button>
            </div>
        `;
        grid.appendChild(card);
    });
}

async function cancelLot(reqId) {
    const handshake = getHandshake();
    if (!handshake) return;
    try {
        const res = await window.pywebview.api.cancel_sale(handshake, String(reqId));
        if (res && res.success) {
            addLog('OK', `Лот успішно скасовано!`);
            setTimeout(loadSales, 1000);
        }
    } catch (e) {
        addLog('ERR', `Помилка скасування: ${e.message}`);
    }
}

// ==============================================
// 7. СЕЛЕКТОР ЗБРОЇ
// ==============================================
async function initWeapons() {
    if (!window.pywebview?.api) return;
    const data = await window.pywebview.api.load_python_weapons();
    if (data && Object.keys(data).length > 0) {
        addLog('INFO', 'База зброї завантажена');
        renderWeaponSelector(data);
    }
}

function renderWeaponSelector(data) {
    const weaponSelect = document.getElementById('weapon-select');
    const skinSelect = document.getElementById('skin-name-select');
    if (!weaponSelect || !skinSelect) return;

    weaponSelect.innerHTML = '<option value="">-- Оберіть зброю --</option>';
    skinSelect.innerHTML = '<option value="">-- Спочатку оберіть зброю --</option>';

    for (let category in data) {
        const group = data[category];
        if (category === "GUNS") {
            for (let subCat in group) {
                for (let weaponName in group[subCat]) {
                    addOption(weaponSelect, weaponName, `${category} | ${weaponName}`, group[subCat][weaponName]);
                }
            }
        } else {
            for (let weaponName in group) {
                addOption(weaponSelect, weaponName, `${category} | ${weaponName}`, group[weaponName]);
            }
        }
    }

    weaponSelect.onchange = (e) => {
        const option = e.target.selectedOptions[0];
        if (!option || !option.value) {
            skinSelect.innerHTML = '<option value="">-- Спочатку оберіть зброю --</option>';
            return;
        }
        if (option.dataset.skins) renderSkinSelector(JSON.parse(option.dataset.skins));
    };

    // Відновлення після завантаження бази
    window.pywebview.api.load_config().then(cfg => {
        if (cfg && cfg.skin) {
            setTimeout(() => {
                for (const opt of weaponSelect.options) {
                    if (!opt.dataset.skins) continue;
                    try {
                        const list = JSON.parse(opt.dataset.skins);
                        if (list.some(s => String(s.id) === String(cfg.skin))) {
                            weaponSelect.value = opt.value;
                            weaponSelect.dispatchEvent(new Event('change', { bubbles: true }));
                            
                            setTimeout(() => {
                                for (let skinName in state.currentWeaponSkinsGrouped) {
                                    const group = state.currentWeaponSkinsGrouped[skinName];
                                    if ((group.normal && String(group.normal.id) === String(cfg.skin)) ||
                                        (group.st && String(group.st.id) === String(cfg.skin))) {
                                        skinSelect.value = skinName;
                                        if (document.getElementById('is-stattrak')) document.getElementById('is-stattrak').checked = !!cfg.isStattrak;
                                        updateSniperTarget();
                                        break;
                                    }
                                }
                            }, 100);
                            break;
                        }
                    } catch (e) {}
                }
            }, 200);
        }
    });
}

function addOption(select, value, text, skinsData) {
    const opt = document.createElement('option');
    opt.value = value; opt.text = text;
    opt.dataset.skins = JSON.stringify(skinsData);
    select.appendChild(opt);
}

function renderSkinSelector(skins) {
    const skinSelect = document.getElementById('skin-name-select');
    const stToggle = document.getElementById('is-stattrak');
    if (!skinSelect) return;

    skinSelect.innerHTML = '<option value="">-- Оберіть скін --</option>';
    if (stToggle) { stToggle.checked = false; stToggle.disabled = true; stToggle.style.opacity = '0.5'; }

    state.currentWeaponSkinsGrouped = {};
    skins.forEach(s => {
        if (!state.currentWeaponSkinsGrouped[s.skin]) state.currentWeaponSkinsGrouped[s.skin] = { normal: null, st: null };
        if (s.is_stattrak) state.currentWeaponSkinsGrouped[s.skin].st = s;
        else state.currentWeaponSkinsGrouped[s.skin].normal = s;
    });

    for (let skinName in state.currentWeaponSkinsGrouped) {
        const opt = document.createElement('option');
        opt.value = skinName; opt.text = skinName;
        skinSelect.appendChild(opt);
    }

    skinSelect.onchange = () => {
        const skinName = skinSelect.value;
        if (stToggle) {
            const skinData = state.currentWeaponSkinsGrouped[skinName];
            if (skinData && skinData.st) {
                stToggle.disabled = false; stToggle.style.opacity = '1';
            } else {
                stToggle.disabled = true; stToggle.checked = false; stToggle.style.opacity = '0.5';
            }
        }
        updateSniperTarget();
    };
}

function updateSniperTarget() {
    const skinSelect = document.getElementById('skin-name-select');
    const stToggle = document.getElementById('is-stattrak');
    const skinName = skinSelect?.value;

    if (!skinName) {
        document.getElementById('final-skin-id').textContent = '—';
        return;
    }

    const skinData = state.currentWeaponSkinsGrouped[skinName];
    let targetItem = (stToggle && stToggle.checked && !stToggle.disabled && skinData.st) ? skinData.st : (skinData.normal || skinData.st);

    if (targetItem) {
        const finalName = `${targetItem.is_stattrak ? "[ST] " : ""}${targetItem.skin}`;
        document.getElementById('final-skin-id').textContent = String(targetItem.id);
        if (document.getElementById('home-skin-name')) document.getElementById('home-skin-name').textContent = finalName;
        if (document.getElementById('home-skin-id')) document.getElementById('home-skin-id').textContent = String(targetItem.id);
        
        if (window.pywebview?.api) {
            window.pywebview.api.save_config({ skin: String(targetItem.id), skinName: finalName, isStattrak: !!targetItem.is_stattrak });
        }
    }
}

// ==============================================
// 8. СИСТЕМА ЛОГУВАННЯ
// ==============================================
// ВАЖЛИВО: Ця функція доступна глобально для Python!
window.addLog = function(type, message) {
    const logContainer = document.getElementById('log-console');
    if (!logContainer) return;

    const levels = { 'ALL': 0, 'INFO': 1, 'WARN': 2, 'ERROR': 3, 'OK': 1, 'ERR': 3 };
    if ((levels[type] || 1) < (levels[window.LOG_LEVEL] || 1)) return;

    const time = new Date().toLocaleTimeString();
    let color = '#fff';
    if (type === 'OK') color = '#4CAF50';
    if (type === 'ERR') color = '#ff4c4c';
    if (type === 'WARN') color = '#ffc107';
    if (type === 'INFO') color = '#2196F3';

    const logEntry = document.createElement('div');
    logEntry.className = 'log-line';
    logEntry.innerHTML = `<span class="log-time">[${time}]</span> <span style="color:${color}; font-weight:bold;">[${type}]</span> <span>${message}</span>`;
    
    logContainer.appendChild(logEntry);
    logContainer.scrollTop = logContainer.scrollHeight;
};

function clearLogs() {
    const c = document.getElementById('log-console');
    if (c) c.innerHTML = '';
}

function setLogLevel(level) {
    window.LOG_LEVEL = (level || 'ALL').toUpperCase();
    highlightLogLevelBadge(window.LOG_LEVEL);
    if (window.pywebview?.api) window.pywebview.api.save_config({ logLevel: window.LOG_LEVEL });
}

function highlightLogLevelBadge(level) {
    document.querySelectorAll('.log-level-badge').forEach(b => {
        if ((b.dataset.level || '').toUpperCase() === (level || '').toUpperCase()) b.classList.add('active');
        else b.classList.remove('active');
    });
}

// Додаємо кліки по бейджах логів
document.querySelectorAll('.log-level-badge').forEach(badge => {
    badge.addEventListener('click', () => setLogLevel(badge.dataset.level));
});