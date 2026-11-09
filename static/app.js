const form = document.getElementById("waterForm");
const predictBtn = document.getElementById("predictBtn");
const resetBtn = document.getElementById("resetBtn");
const placeholder = document.getElementById("resultPlaceholder");
const resultContent = document.getElementById("resultContent");
const errorBox = document.getElementById("errorBox");
const toast = document.getElementById("toast");
const menuButton = document.getElementById("mobileMenu");
const sidebar = document.getElementById("sidebar");

const defaults = {
  ph: 7.0, Hardness: 150, Solids: 15000, Chloramines: 7,
  Sulfate: 300, Conductivity: 400, Organic_carbon: 10,
  Trihalomethanes: 60, Turbidity: 4
};

function showToast(message) {
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 3000);
}

if (menuButton && sidebar) {
  menuButton.addEventListener("click", () => sidebar.classList.toggle("sidebar-open"));
}

function showError(message) {
  if (!errorBox) return;
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
  if (placeholder) placeholder.classList.add("hidden");
  if (resultContent) resultContent.classList.add("hidden");
}

function percent(value) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`;
}

if (form && predictBtn) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (errorBox) errorBox.classList.add("hidden");
    predictBtn.disabled = true;
    predictBtn.querySelector("span").textContent = "Analyzing…";

    const formData = new FormData(form);
    const payload = {};
    for (const key of Object.keys(defaults)) {
      const raw = formData.get(key);
      if (raw === null || String(raw).trim() === "" || !Number.isFinite(Number(raw))) {
        showError(`Please ${key} ke liye valid number enter karo.`);
        predictBtn.disabled = false;
        predictBtn.querySelector("span").textContent = "Run AI analysis";
        return;
      }
      payload[key] = Number(raw);
    }

    try {
      const response = await fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Prediction request failed.");

      placeholder?.classList.add("hidden");
      errorBox?.classList.add("hidden");
      resultContent?.classList.remove("hidden");
      resultContent?.classList.toggle("negative", data.prediction === 0);

      document.getElementById("resultLabel").textContent = "MODEL PREDICTION";
      document.getElementById("resultTitle").textContent =
        data.prediction === 1 ? "Potable class" : "Not potable class";
      document.getElementById("resultDescription").textContent =
        data.prediction === 1
          ? "The trained model assigned this sample to class 1."
          : "The trained model assigned this sample to class 0.";

      const probs = data.probabilities || {};
      const p1 = Number(probs["1"] || 0);
      const p0 = Number(probs["0"] || 0);
      document.getElementById("class1Value").textContent = percent(p1);
      document.getElementById("class0Value").textContent = percent(p0);
      const class1Bar = document.getElementById("class1Bar");
      const class0Bar = document.getElementById("class0Bar");

      [class1Bar, class0Bar].forEach((bar) => {
        if (!bar) return;
        bar.classList.remove("animate-bar");
        bar.style.transition = "none";
        bar.style.width = "0%";
      });

      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          if (class1Bar) {
            class1Bar.style.transition = "";
            class1Bar.style.width = `${Math.min(100, p1 * 100)}%`;
            class1Bar.classList.add("animate-bar");
          }
          if (class0Bar) {
            class0Bar.style.transition = "";
            class0Bar.style.width = `${Math.min(100, p0 * 100)}%`;
            class0Bar.classList.add("animate-bar");
          }
        });
      });
      showToast("Prediction complete — saved to your history.");
    } catch (error) {
      showError(`${error.message} Check that the model file exists and the Flask server is running.`);
    } finally {
      predictBtn.disabled = false;
      predictBtn.querySelector("span").textContent = "Run AI analysis";
    }
  });
}

if (resetBtn && form) {
  resetBtn.addEventListener("click", () => {
    window.setTimeout(() => {
      placeholder?.classList.remove("hidden");
      resultContent?.classList.add("hidden");
      errorBox?.classList.add("hidden");
    }, 0);
  });
}

if (window.aquaChartData && document.getElementById("historyChart") && window.Chart) {
  const ctx = document.getElementById("historyChart");
  const labels = window.aquaChartData.labels || [];
  const values = window.aquaChartData.values || [];
  new Chart(ctx, {
    type: "line",
    data: {
      labels: labels.map((label, i) => `${i + 1}. ${label}`),
      datasets: [{
        label: "Predicted class (0 or 1)",
        data: values,
        borderColor: "#4ee4df",
        backgroundColor: "rgba(78,228,223,.10)",
        borderWidth: 2,
        pointRadius: 4,
        pointBackgroundColor: values.map(v => v === 1 ? "#63e6be" : "#ff8294"),
        fill: true,
        tension: .25
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: "#a6bad0", font: { family: "DM Sans" } } }
      },
      scales: {
        x: { ticks: { color: "#8298b0", maxRotation: 45 }, grid: { color: "rgba(152,185,220,.08)" } },
        y: { min: 0, max: 1, ticks: { stepSize: 1, color: "#8298b0" }, grid: { color: "rgba(152,185,220,.08)" } }
      }
    }
  });
}
