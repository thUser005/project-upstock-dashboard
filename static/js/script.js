let allInstruments = [];
let selectedIndex = null;
let throttleTimer = null;
let instrumentsLoaded = false;
let selectedInstrument = null;
let liveLtp = 0;
let redirectingToToken = false;
let ltpSocket = null;
let balanceSocket = null;
let autoPriceEnabled = true;
let autoTradeMode = true;

const CACHE_KEY = "upstox_instruments_cache";
const CACHE_VERSION = "v2";

// Dummy values
let BALANCE = 0;

let indexSocket = null;
let niftySpot = 0;
let sensexSpot = 0;
let lastIndexPrice = 0; // 👈 add here

function roundToTick(price) {
  return Math.round(price / 0.05) * 0.05;
}
function updateRiskBox(entry, stopLoss, quantity) {
  const riskPerLot = (entry - stopLoss) * quantity;
  const risk = Math.round(riskPerLot);

  const riskEl = document.getElementById("riskValue");
  if (riskEl) {
    riskEl.innerHTML = `₹${formatNumber(risk)}`;
  }
}

function updateAutoTrade() {
  if (!autoTradeMode) return;
  if (!liveLtp || !selectedInstrument) return;

  const lotSize = parseInt(document.getElementById("lotSize").value) || 0;
  if (!lotSize || BALANCE <= 0) return;

  const targetProfit =
    parseInt(document.getElementById("targetProfitInput").value) || 1200;

  // ENTRY = LTP + 2
  let entry = liveLtp + 2;

  // -----------------------------
  // Decide reasonable target points
  // -----------------------------
  let targetPoints;
  if (entry <= 3) targetPoints = 4;
  else if (entry <= 10) targetPoints = 8;
  else targetPoints = 15;

  // -----------------------------
  // Required quantity for target
  // -----------------------------
  const requiredQty = Math.ceil(targetProfit / targetPoints);
  let lots = Math.ceil(requiredQty / lotSize);

  // Capital limit
  const maxLots = Math.floor(BALANCE / (entry * lotSize));
  if (lots > maxLots) lots = maxLots;
  if (lots < 1) return;

  const quantity = lots * lotSize;

  // -----------------------------
  // Prices (3:1 RR)
  // -----------------------------
  let target = entry + targetPoints;
  let stopLoss = entry - targetPoints / 3;

  // Safety
  if (stopLoss < 0.05) stopLoss = 0.05;

  // -----------------------------
  // ROUND TO TICK SIZE
  // -----------------------------
  entry = roundToTick(entry);
  target = roundToTick(target);
  stopLoss = roundToTick(stopLoss);

  // -----------------------------
  // APPLY VALUES
  // -----------------------------
  document.getElementById("entryPrice").value = entry.toFixed(2);
  document.getElementById("targetPrice").value = target.toFixed(2);
  document.getElementById("stopLossPrice").value = stopLoss.toFixed(2);

  document.getElementById("lotsInput").value = lots;
  syncQuantityFromLots();

  updateMarginCalculations();
  updateRiskBox(entry, stopLoss, quantity);
}

function connectIndexSocket() {
  if (indexSocket && indexSocket.readyState === WebSocket.OPEN) return;

  indexSocket = new WebSocket(getWsBaseUrl() + "/ws/index");

  indexSocket.onopen = function () {
    console.log("✅ Index socket connected");
  };

  indexSocket.onmessage = function (event) {
    const data = JSON.parse(event.data);

    if (data.exchange === "NSE") {
      niftySpot = data.price;
    }

    if (data.exchange === "BSE") {
      sensexSpot = data.price;
    }

    updateIndexPriceDisplay();
  };

  indexSocket.onerror = function (err) {
    console.error("❌ Index socket error", err);
  };

  indexSocket.onclose = function () {
    console.warn("⚠ Index socket closed, retrying...");
    setTimeout(connectIndexSocket, 3000);
  };
}

function updateIndexPriceDisplay() {
  const priceEl = document.getElementById("indexLivePrice");
  if (!priceEl) return;

  let price = selectedIndex === "NIFTY" ? niftySpot : sensexSpot;
  if (!price) return;

  priceEl.innerText = price.toFixed(2);

  if (lastIndexPrice) {
    if (price > lastIndexPrice) priceEl.style.color = "#00ff88"; // green
    if (price < lastIndexPrice) priceEl.style.color = "#ff5555"; // red
  }

  lastIndexPrice = price;
}

function updateDefaultOrderPrices() {
  if (!autoPriceEnabled) return; // 🔒 Lock if user edited
  if (!liveLtp || liveLtp <= 0) return;

  let entry = liveLtp + 3;
  let target = entry + 5;
  let stopLoss = entry - 20;

  // Dynamic SL for small premium options
  if (stopLoss <= 0 || stopLoss >= entry) {
    const dynamicSL = liveLtp * 0.2; // 20% of LTP
    stopLoss = entry - dynamicSL;
  }

  // Final safety clamp
  if (stopLoss < 0) stopLoss = 0.05;

  const entryEl = document.getElementById("entryPrice");
  const targetEl = document.getElementById("targetPrice");
  const slEl = document.getElementById("stopLossPrice");

  if (entryEl) entryEl.value = entry.toFixed(2);
  if (targetEl) targetEl.value = target.toFixed(2);
  if (slEl) slEl.value = stopLoss.toFixed(2);

  updateMarginCalculations();
}

function renderExpiryRadios(expiryList) {
  const container = document.getElementById("expiryFilters");
  if (!container) return;

  container.innerHTML = expiryList
    .map(
      (exp, i) => `
    <label class="me-3 text-light">
      <input type="radio" name="expiryRadio" value="${exp}" ${i === 0 ? "checked" : ""}>
      ${exp}
    </label>
  `,
    )
    .join("");

  // attach change listeners
  document.querySelectorAll('input[name="expiryRadio"]').forEach((radio) => {
    radio.addEventListener("change", function () {
      filterByExpiry(this.value);
    });
  });
}
function filterByExpiry(selectedExpiry) {
  // Apply filter on BOTH CE and PE tables
  ["ceBody", "peBody"].forEach((tableId) => {
    const table = document.getElementById(tableId);
    if (!table) return;

    table.querySelectorAll(".expiry-header").forEach((header) => {
      const exp = header.getAttribute("data-expiry");
      let row = header.nextElementSibling;

      if (exp === selectedExpiry) {
        header.style.display = "";
        while (row && !row.classList.contains("expiry-header")) {
          row.style.display = "";
          row = row.nextElementSibling;
        }
      } else {
        header.style.display = "none";
        while (row && !row.classList.contains("expiry-header")) {
          row.style.display = "none";
          row = row.nextElementSibling;
        }
      }
    });
  });
}

function getNearestExpiry(expiryList) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const validExpiries = expiryList
    .map((exp) => ({
      label: exp,
      date: new Date(exp),
    }))
    .filter((e) => e.date >= today) // remove expired
    .sort((a, b) => a.date - b.date); // nearest first

  return validExpiries.map((e) => e.label);
}

// ----------------------------
// HELPER FUNCTIONS
// ----------------------------
function formatNumber(num) {
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function connectLtpSocket(callback) {
  if (ltpSocket && ltpSocket.readyState === WebSocket.OPEN) {
    if (callback) callback();
    return;
  }

  ltpSocket = new WebSocket(getWsBaseUrl() + "/ws/ltp");
  ltpSocket.onopen = function () {
    console.log("✅ LTP Socket Connected");
    if (callback) callback();
  };

  ltpSocket.onmessage = function (event) {
    const data = JSON.parse(event.data);

    if (data.ltp) {
      liveLtp = data.ltp;

      document.getElementById("liveLtpDisplay").innerHTML =
        `₹${liveLtp.toFixed(2)}`;
      document.getElementById("ltpValue").innerHTML = `₹${liveLtp.toFixed(2)}`;

      if (autoTradeMode) {
        updateAutoTrade();
      }

      updateMarginCalculations();
    }
  };

  ltpSocket.onerror = function (err) {
    console.error("❌ LTP Socket Error:", err);
  };
}

function connectBalanceSocket() {
  if (balanceSocket && balanceSocket.readyState === WebSocket.OPEN) return;

  balanceSocket = new WebSocket(getWsBaseUrl() + "/ws/balance");

  balanceSocket.onopen = function () {
    console.log("✅ Balance Socket Connected");
  };

  balanceSocket.onmessage = function (event) {
    const data = JSON.parse(event.data);

    // ✅ Successful balance update
    if (data.status === "success") {
      BALANCE = data.balance;

      document.getElementById("availableBalance").innerHTML =
        `₹${formatNumber(BALANCE)}`;

      updateMarginCalculations();
    }

    // 🔴 Token expired
    if (data.status === "error") {
      if (redirectingToToken) return;
      redirectingToToken = true;

      showToast("🔑 Session expired. Redirecting to token page...");
      setTimeout(() => {
        window.location.href = "/token";
      }, 2000);
    }
  };

  balanceSocket.onerror = function (err) {
    console.error("❌ Balance Socket Error:", err);
    showToast("⚠ Balance connection lost");
  };

  balanceSocket.onclose = function () {
    console.warn("⚠ Balance socket closed, retrying...");
    setTimeout(connectBalanceSocket, 3000);
  };
}

// ----------------------------
// LOAD INSTRUMENTS
// ----------------------------
async function loadInstruments() {
  const today = new Date().toISOString().split("T")[0];

  const cacheRaw = localStorage.getItem(CACHE_KEY);
  if (cacheRaw) {
    const cache = JSON.parse(cacheRaw);
    if (cache.version === CACHE_VERSION && cache.date === today) {
      allInstruments = cache.data;
      instrumentsLoaded = true;
      return;
    }
  }

  // ✅ REAL API FETCH
  const res = await fetch("/instruments/all");
  const json = await res.json();

  allInstruments = json.data;
  instrumentsLoaded = true;

  localStorage.setItem(
    CACHE_KEY,
    JSON.stringify({
      version: CACHE_VERSION,
      date: today,
      data: allInstruments,
    }),
  );
}

function syncQuantityFromLots() {
  const lotSize = parseInt(document.getElementById("lotSize").value) || 0;
  const lots = parseInt(document.getElementById("lotsInput").value) || 0;

  const quantity = lotSize * lots;
  document.getElementById("quantityInput").value = quantity;

  updateMarginCalculations();
}

// ----------------------------
// BUTTON HANDLING
// ----------------------------
document.getElementById("btnNifty").onclick = () => {
  selectedIndex = "NIFTY";
  highlightButton("btnNifty");
  showToast("NIFTY 50 selected");
  // Auto-search if there's already input
  const searchText = document.getElementById("searchBox").value.trim();
  if (searchText) {
    searchInstrument(searchText);
  }
};

document.getElementById("btnSensex").onclick = () => {
  selectedIndex = "SENSEX";
  highlightButton("btnSensex");
  showToast("SENSEX selected");
  // Auto-search if there's already input
  const searchText = document.getElementById("searchBox").value.trim();
  if (searchText) {
    searchInstrument(searchText);
  }
};

function highlightButton(id) {
  const niftyBtn = document.getElementById("btnNifty");
  const sensexBtn = document.getElementById("btnSensex");
  const label = document.getElementById("selectedIndexLabel");

  niftyBtn.classList.remove("active");
  sensexBtn.classList.remove("active");

  if (id === "btnNifty") {
    niftyBtn.classList.add("active");
    selectedIndex = "NIFTY";
  } else {
    sensexBtn.classList.add("active");
    selectedIndex = "SENSEX";
  }

  label.innerText = selectedIndex;

  // 🔥 update price instantly on switch
  updateIndexPriceDisplay();
}

// ----------------------------
// TOAST
// ----------------------------
function showToast(msg) {
  document.getElementById("toastMsg").innerText = msg;
  const toast = new bootstrap.Toast(document.getElementById("indexToast"));
  toast.show();
}

// ----------------------------
// AUTO INDEX DETECT - FIXED
// ----------------------------
function autoSelectIndexFromStrike(keyword) {
  if (selectedIndex) return;

  // Extract numeric value from keyword
  const numMatch = keyword.match(/\d+/g);
  if (!numMatch) return;

  // Take the first number found
  const num = parseInt(numMatch[0]);
  if (!num || isNaN(num)) return;

  if (num < 50000) {
    selectedIndex = "NIFTY";
    highlightButton("btnNifty");
    showToast("Auto selected NIFTY index");
  } else {
    selectedIndex = "SENSEX";
    highlightButton("btnSensex");
    showToast("Auto selected SENSEX index");
  }
}

// ----------------------------
// SEARCH - FIXED
// ----------------------------
document.getElementById("searchBox").addEventListener("input", function () {
  if (throttleTimer) clearTimeout(throttleTimer);
  throttleTimer = setTimeout(() => {
    searchInstrument(this.value.trim());
  }, 400);
});

function searchInstrument(keyword) {
  const ceBody = document.getElementById("ceBody");
  const peBody = document.getElementById("peBody");

  if (!instrumentsLoaded) return;

  if (!keyword) {
    ceBody.innerHTML = peBody.innerHTML = `
      <tr>
        <td colspan="4" class="text-center text-muted py-5">
          Start typing to search...
        </td>
      </tr>`;
    return;
  }

  // Auto detect index from strike
  autoSelectIndexFromStrike(keyword);

  if (!selectedIndex) {
    ceBody.innerHTML = peBody.innerHTML = `
      <tr>
        <td colspan="4" class="text-center text-muted py-5">
          <span style="color: #ff9500">
            Please select an index (NIFTY/SENSEX) or enter a strike price
          </span>
        </td>
      </tr>`;
    return;
  }

  // 🔹 Filter instruments
  let results = allInstruments.filter((item) => {
    if (item.name !== selectedIndex) return false;

    const isNumeric = /^\d+$/.test(keyword);
    if (isNumeric) {
      const searchNum = parseInt(keyword);
      return item.strike_price.toString().includes(searchNum.toString());
    }

    return item.trading_symbol.toUpperCase().includes(keyword.toUpperCase());
  });

  // 🔹 Separate CE & PE
  const ceList = results.filter((x) => x.instrument_type === "CE");
  const peList = results.filter((x) => x.instrument_type === "PE");

  // 🔹 Group by expiry
  const ceGrouped = groupByExpiry(ceList);
  const peGrouped = groupByExpiry(peList);

  // 🔹 Sort expiry nearest first (weekly/monthly priority)
  let expiryList = Object.keys(ceGrouped);
  expiryList = getNearestExpiry(expiryList);

  // 🔹 Render tables
  ceBody.innerHTML = renderExpiryTables(ceGrouped);
  peBody.innerHTML = renderExpiryTables(peGrouped);

  // 🔹 Render expiry radios
  renderExpiryRadios(expiryList);

  // 🔹 Auto-select newest expiry
  if (expiryList.length) {
    filterByExpiry(expiryList[0]);
  }
}

function renderRow(inst) {
  const isSelected =
    selectedInstrument === inst.instrument_key ? "selected" : "";
  return `
    <tr class="instrument-row ${isSelected}"
        onclick="selectInstrument('${inst.instrument_key}', ${inst.lot_size}, '${inst.trading_symbol}')">
      <td class="fw-bold text-light">${inst.strike_price}</td>
      <td class="text-light">${new Date(inst.expiry).toLocaleDateString("en-IN", { day: "2-digit", month: "short" })}</td>
      <td class="fw-bold" style="color: #ff9500">${inst.lot_size}</td>
      <td>
        <button class="btn btn-sm" style="background: linear-gradient(135deg, #4361ee, #3a56d4); color: white; border: none;">
          Select
        </button>
      </td>
    </tr>
  `;
}

function groupByExpiry(list) {
  const groups = {};

  list.forEach((inst) => {
    const exp = new Date(inst.expiry).toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });

    if (!groups[exp]) groups[exp] = [];
    groups[exp].push(inst);
  });

  return groups;
}

function renderExpiryTables(groupedData) {
  if (!Object.keys(groupedData).length) {
    return `
      <tr>
        <td colspan="4" class="text-center text-muted py-4">
          No instruments found
        </td>
      </tr>
    `;
  }

  let html = "";

  const sortedExpiries = Object.keys(groupedData).sort(
    (a, b) => new Date(b) - new Date(a), // newest first
  );

  sortedExpiries.forEach((expiry) => {
    html += `
      <tr class="table-secondary expiry-header" data-expiry="${expiry}">
        <td colspan="4" class="fw-bold text-dark text-center">
          Expiry: ${expiry}
        </td>
      </tr>
    `;

    groupedData[expiry].forEach((inst) => {
      html += renderRow(inst);
    });
  });

  return html;
}

function resetTradingCalculator() {
  document.getElementById("ltpValue").innerHTML = "₹0.00";
  document.getElementById("liveLtpDisplay").innerHTML = "₹0.00";
  document.getElementById("maxLots").innerHTML = "0";
  document.getElementById("positionValue").innerHTML = "₹0";
  document.getElementById("capitalPercent").innerHTML = "0%";
  document.getElementById("capitalBar").style.width = "0%";

  document.getElementById("pnlBody").innerHTML = `
    <tr>
      <td colspan="3" class="text-center py-4">
        <span class="text-muted">Select an instrument to view P&L</span>
      </td>
    </tr>
  `;
}

// ----------------------------
// INSTRUMENT SELECTION
// ----------------------------
function selectInstrument(token, lotSize, tradingSymbol) {
  autoPriceEnabled = true;
  selectedInstrument = token;

  document.getElementById("instrumentToken").value = token;
  document.getElementById("lotSize").value = lotSize;
  document.getElementById("insInput").value = tradingSymbol;

  connectLtpSocket(() => {
    ltpSocket.send(
      JSON.stringify({
        action: "subscribe",
        instrument_key: token,
        trading_symbol: tradingSymbol,
      }),
    );
  });

  // Default 1 lot
  document.getElementById("lotsInput").value = 1;
  syncQuantityFromLots();

  // Auto-fill prices after LTP arrives
  setTimeout(() => {
    updateDefaultOrderPrices();
  }, 800);

  updateMarginCalculations();
  searchInstrument(document.getElementById("searchBox").value);
}

// ----------------------------
// P&L TABLE
// ----------------------------
function generatePnLTable(quantity, entryPrice) {
  const tbody = document.getElementById("pnlBody");
  let rows = "";

  [5, 10, 15, 20, 25].forEach((p) => {
    const price = entryPrice + p;
    const profit = p * quantity;

    rows += `
      <tr class="profit-glow">
        <td class="fw-bold">${price.toFixed(2)}</td>
        <td class="profit-text fw-bold">+${p}</td>
        <td class="profit-text fw-bold">+₹${formatNumber(profit)}</td>
      </tr>
    `;
  });

  [5, 10, 15, 20, 25].forEach((p) => {
    const price = entryPrice - p;
    const loss = p * quantity;

    rows += `
      <tr class="loss-glow">
        <td class="fw-bold">${price.toFixed(2)}</td>
        <td class="loss-text fw-bold">-${p}</td>
        <td class="loss-text fw-bold">-₹${formatNumber(loss)}</td>
      </tr>
    `;
  });

  tbody.innerHTML = rows;
}

// ----------------------------
// MARGIN CALCULATIONS
// ----------------------------

function updateMarginCalculations() {
  if (!selectedInstrument || liveLtp <= 0) {
    resetTradingCalculator();
    return;
  }

  const lotSize = parseInt(document.getElementById("lotSize").value) || 0;
  const lots = parseInt(document.getElementById("lotsInput").value) || 0;
  const quantity =
    parseInt(document.getElementById("quantityInput").value) || 0;
  const entryPrice =
    parseFloat(document.getElementById("entryPrice").value) || liveLtp;

  // ✅ Full premium required for GTT
  const capitalRequired = entryPrice * quantity;

  document.getElementById("positionValue").innerHTML =
    `₹${formatNumber(capitalRequired.toFixed(0))}`;

  // ✅ Max lots based on full premium
  const maxLots = Math.floor(BALANCE / (entryPrice * lotSize));
  document.getElementById("maxLots").innerHTML = maxLots;

  // ✅ Capital utilization based on full premium
  const capitalUtilization = (capitalRequired / BALANCE) * 100;
  document.getElementById("capitalPercent").innerHTML =
    `${capitalUtilization.toFixed(1)}%`;
  document.getElementById("capitalBar").style.width =
    `${Math.min(capitalUtilization, 100)}%`;

  generatePnLTable(quantity, entryPrice);
}

// ----------------------------
// INITIALIZE
// ----------------------------
document.addEventListener("DOMContentLoaded", function () {
  loadInstruments();
  connectBalanceSocket();
  connectIndexSocket(); // 👈 index live price

  highlightButton("btnNifty");
  resetTradingCalculator();

  // 🤖 Enable Auto Trade by default
  autoTradeMode = true;
  autoPriceEnabled = true;

  const autoToggle = document.getElementById("autoTradeToggle");
  if (autoToggle) autoToggle.checked = true;

  // 🔁 Recalculate auto trade when target profit changes
  const targetProfitEl = document.getElementById("targetProfitInput");
  if (targetProfitEl) {
    targetProfitEl.addEventListener("input", () => {
      if (autoTradeMode) updateAutoTrade();
    });
  }

  // 🔒 Switch to Manual mode if user edits any price / lot field
  ["entryPrice", "targetPrice", "stopLossPrice", "lotsInput"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("input", () => {
        autoTradeMode = false;
        autoPriceEnabled = false;

        const entry =
          parseFloat(document.getElementById("entryPrice").value) || 0;
        const stopLoss =
          parseFloat(document.getElementById("stopLossPrice").value) || 0;
        const qty =
          parseInt(document.getElementById("quantityInput").value) || 0;

        if (entry && stopLoss && qty) {
          updateRiskBox(entry, stopLoss, qty);
        }

        const toggle = document.getElementById("autoTradeToggle");
        if (toggle) toggle.checked = false;

        showToast("✍ Manual Trade Mode Enabled");
      });
    }
  });
});
 
document
  .getElementById("gttForm")
  .addEventListener("submit", async function (e) {
    e.preventDefault(); // ❌ stop page refresh

    const form = e.target;
    const formData = new FormData(form);

    try {
      const res = await fetch("/place-gtt", {
        method: "POST",
        body: formData,
      });

      const json = await res.json();

      if (json.status === "success") {
        showToast("✅ GTT Order Placed: " + json.gtt_order_id);
      } else {
        showToast("❌ " + json.message);
      }
    } catch (err) {
      console.error(err);
      showToast("⚠ Server error while placing GTT");
    }
  });

// ----------------------------
// CLEAN DISCONNECT HANDLING
// ----------------------------

window.addEventListener("beforeunload", function () {
  try {
    if (ltpSocket && ltpSocket.readyState === WebSocket.OPEN) {
      ltpSocket.send(
        JSON.stringify({
          action: "unsubscribe",
          instrument_key: selectedInstrument,
        }),
      );
      ltpSocket.close();
    }

    if (indexSocket && indexSocket.readyState === WebSocket.OPEN) {
      indexSocket.close();
    }

    if (balanceSocket && balanceSocket.readyState === WebSocket.OPEN) {
      balanceSocket.close();
    }
  } catch (err) {
    console.warn("Socket cleanup failed", err);
  }
});

document
  .getElementById("autoTradeToggle")
  .addEventListener("change", function () {
    autoTradeMode = this.checked;

    if (autoTradeMode) {
      autoPriceEnabled = true;
      updateAutoTrade();
      showToast("🤖 Auto Trade Mode Enabled");
    } else {
      autoPriceEnabled = false;
      showToast("✍ Manual Trade Mode Enabled");
    }
  });
