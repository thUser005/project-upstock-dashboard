// ----------------------------
// LOAD LIVE BALANCE (WITH TOKEN REDIRECT)
// ----------------------------
async function loadLiveBalance() {
  try {
    const res = await fetch("/get-balance");
    const json = await res.json();

    // 🔴 Token expired or invalid → redirect
    if (json.status !== "success") {
      if (redirectingToToken) return;
      redirectingToToken = true;

      showToast("🔑 Session expired. Redirecting to token page...");
      setTimeout(() => {
        window.location.href = "/token";
      }, 2000);

      return;
    }

    // ✅ Success case
    const equity = json.data.data.equity;
    BALANCE = Math.floor(equity.available_margin);

    document.getElementById("availableBalance").innerHTML =
      `₹${formatNumber(BALANCE)}`;

    console.log("✅ Live Balance Loaded:", BALANCE);

    // Recalculate margins if instrument selected
    updateMarginCalculations();
  } catch (err) {
    console.error("Balance fetch failed:", err);
    showToast("⚠ Balance service unavailable");
  }
}


// Auto refresh balance every 30 seconds
setInterval(loadLiveBalance, 30000);
