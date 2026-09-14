/**
 * app/static/js/charts.js — Dashboard Chart.js initialization
 *
 * Fetches data from JSON API endpoints and renders:
 * 1. Category spending doughnut chart
 * 2. Daily spending line chart
 * 3. Monthly comparison bar chart
 *
 * All API calls require authentication (Flask handles that server-side).
 * Charts gracefully handle empty data.
 */

(function () {
    "use strict";

    const CHART_DEFAULTS = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: {
                    font: { family: "Inter, sans-serif", size: 12 },
                    color: getComputedStyle(document.documentElement)
                        .getPropertyValue("--text-muted")
                        .trim(),
                    boxWidth: 12,
                    padding: 12,
                },
            },
            tooltip: {
                cornerRadius: 6,
                padding: 10,
                bodyFont: { family: "Inter, sans-serif" },
                titleFont: { family: "Inter, sans-serif", weight: "600" },
            },
        },
    };

    function getCssVar(name) {
        return getComputedStyle(document.documentElement)
            .getPropertyValue(name)
            .trim();
    }

    // ---- 1. Category Doughnut Chart ----
    async function initCategoryChart() {
        const canvas = document.getElementById("categoryChart");
        if (!canvas) return;

        try {
            const res = await fetch("/dashboard/api/category-spending");
            if (!res.ok) throw new Error("Failed to load");
            const data = await res.json();

            if (!data.labels || data.labels.length === 0) {
                showEmptyState(canvas, "No spending this month");
                return;
            }

            new Chart(canvas, {
                type: "doughnut",
                data: {
                    labels: data.labels,
                    datasets: [
                        {
                            data: data.data,
                            backgroundColor: data.colors,
                            borderWidth: 2,
                            borderColor: getCssVar("--surface"),
                            hoverOffset: 4,
                        },
                    ],
                },
                options: {
                    ...CHART_DEFAULTS,
                    cutout: "65%",
                    plugins: {
                        ...CHART_DEFAULTS.plugins,
                        legend: {
                            ...CHART_DEFAULTS.plugins.legend,
                            position: "bottom",
                        },
                        tooltip: {
                            ...CHART_DEFAULTS.plugins.tooltip,
                            callbacks: {
                                label: (ctx) => {
                                    const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                    const pct = ((ctx.raw / total) * 100).toFixed(1);
                                    return ` ₹${ctx.raw.toLocaleString("en-IN")} (${pct}%)`;
                                },
                            },
                        },
                    },
                },
            });
        } catch (err) {
            console.error("Category chart error:", err);
            showEmptyState(canvas, "Unable to load chart");
        }
    }

    // ---- 2. Daily Spending Line Chart ----
    async function initDailyChart() {
        const canvas = document.getElementById("dailyChart");
        if (!canvas) return;

        try {
            const res = await fetch("/dashboard/api/daily-spending");
            if (!res.ok) throw new Error("Failed to load");
            const data = await res.json();

            const primaryColor = getCssVar("--primary");

            new Chart(canvas, {
                type: "line",
                data: {
                    labels: data.labels,
                    datasets: [
                        {
                            label: "Daily Spending",
                            data: data.data,
                            borderColor: primaryColor,
                            backgroundColor: primaryColor + "20",
                            fill: true,
                            tension: 0.3,
                            pointRadius: 3,
                            pointHoverRadius: 5,
                            borderWidth: 2,
                        },
                    ],
                },
                options: {
                    ...CHART_DEFAULTS,
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: {
                                font: { size: 11 },
                                color: getCssVar("--text-muted"),
                                maxTicksLimit: 10,
                            },
                        },
                        y: {
                            beginAtZero: true,
                            grid: { color: getCssVar("--border") },
                            ticks: {
                                font: { size: 11 },
                                color: getCssVar("--text-muted"),
                                callback: (val) => "₹" + val.toLocaleString("en-IN"),
                            },
                        },
                    },
                    plugins: {
                        ...CHART_DEFAULTS.plugins,
                        legend: { display: false },
                        tooltip: {
                            ...CHART_DEFAULTS.plugins.tooltip,
                            callbacks: {
                                label: (ctx) =>
                                    ` ₹${ctx.raw.toLocaleString("en-IN")}`,
                            },
                        },
                    },
                },
            });
        } catch (err) {
            console.error("Daily chart error:", err);
            showEmptyState(canvas, "Unable to load chart");
        }
    }

    // ---- 3. Monthly Comparison Bar Chart ----
    async function initMonthlyChart() {
        const canvas = document.getElementById("monthlyChart");
        if (!canvas) return;

        try {
            const res = await fetch("/dashboard/api/monthly-comparison");
            if (!res.ok) throw new Error("Failed to load");
            const data = await res.json();

            const primaryColor = getCssVar("--primary");

            new Chart(canvas, {
                type: "bar",
                data: {
                    labels: data.labels,
                    datasets: [
                        {
                            label: "Monthly Spending",
                            data: data.data,
                            backgroundColor: data.labels.map((_, i) =>
                                i === data.labels.length - 1
                                    ? primaryColor
                                    : primaryColor + "60"
                            ),
                            borderRadius: 4,
                            borderSkipped: false,
                        },
                    ],
                },
                options: {
                    ...CHART_DEFAULTS,
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: { font: { size: 11 }, color: getCssVar("--text-muted") },
                        },
                        y: {
                            beginAtZero: true,
                            grid: { color: getCssVar("--border") },
                            ticks: {
                                font: { size: 11 },
                                color: getCssVar("--text-muted"),
                                callback: (val) => "₹" + val.toLocaleString("en-IN"),
                            },
                        },
                    },
                    plugins: {
                        ...CHART_DEFAULTS.plugins,
                        legend: { display: false },
                        tooltip: {
                            ...CHART_DEFAULTS.plugins.tooltip,
                            callbacks: {
                                label: (ctx) =>
                                    ` ₹${ctx.raw.toLocaleString("en-IN")}`,
                            },
                        },
                    },
                },
            });
        } catch (err) {
            console.error("Monthly chart error:", err);
            showEmptyState(canvas, "Unable to load chart");
        }
    }

    // ---- Insights page charts ----
    // Same charts but on the /insights page (different canvas IDs)
    async function initInsightsCategoryChart() {
        const canvas = document.getElementById("insightsCategoryChart");
        if (!canvas) return;

        try {
            const res = await fetch("/dashboard/api/category-spending");
            if (!res.ok) throw new Error("Failed to load");
            const data = await res.json();

            if (!data.labels || data.labels.length === 0) {
                showEmptyState(canvas, "No spending this month");
                return;
            }

            new Chart(canvas, {
                type: "doughnut",
                data: {
                    labels: data.labels,
                    datasets: [{
                        data: data.data,
                        backgroundColor: data.colors,
                        borderWidth: 2,
                        borderColor: getCssVar("--surface"),
                        hoverOffset: 4,
                    }],
                },
                options: {
                    ...CHART_DEFAULTS,
                    cutout: "60%",
                    plugins: {
                        ...CHART_DEFAULTS.plugins,
                        legend: { ...CHART_DEFAULTS.plugins.legend, position: "right" },
                        tooltip: {
                            ...CHART_DEFAULTS.plugins.tooltip,
                            callbacks: {
                                label: (ctx) => {
                                    const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                    const pct = ((ctx.raw / total) * 100).toFixed(1);
                                    return ` ₹${ctx.raw.toLocaleString("en-IN")} (${pct}%)`;
                                },
                            },
                        },
                    },
                },
            });
        } catch (err) {
            console.error("Insights category chart error:", err);
        }
    }

    async function initMonthlyBarChart() {
        const canvas = document.getElementById("monthlyBarChart");
        if (!canvas) return;

        try {
            const res = await fetch("/dashboard/api/monthly-comparison");
            if (!res.ok) throw new Error("Failed to load");
            const data = await res.json();

            const primaryColor = getCssVar("--primary");

            new Chart(canvas, {
                type: "bar",
                data: {
                    labels: data.labels,
                    datasets: [{
                        data: data.data,
                        backgroundColor: data.labels.map((_, i) =>
                            i === data.labels.length - 1 ? primaryColor : primaryColor + "60"
                        ),
                        borderRadius: 4,
                        borderSkipped: false,
                    }],
                },
                options: {
                    ...CHART_DEFAULTS,
                    scales: {
                        x: { grid: { display: false }, ticks: { color: getCssVar("--text-muted"), font: { size: 11 } } },
                        y: {
                            beginAtZero: true,
                            grid: { color: getCssVar("--border") },
                            ticks: {
                                color: getCssVar("--text-muted"),
                                font: { size: 11 },
                                callback: (val) => "₹" + val.toLocaleString("en-IN"),
                            },
                        },
                    },
                    plugins: { ...CHART_DEFAULTS.plugins, legend: { display: false } },
                },
            });
        } catch (err) {
            console.error("Monthly bar chart error:", err);
        }
    }

    // ---- Show empty state inside a chart canvas ----
    function showEmptyState(canvas, message) {
        const parent = canvas.parentElement;
        canvas.style.display = "none";
        const el = document.createElement("div");
        el.className = "empty-state";
        el.style.padding = "2rem 1rem";
        el.innerHTML = `<div class="empty-icon">📊</div><p>${message}</p>`;
        parent.appendChild(el);
    }

    // ---- Init ----
    document.addEventListener("DOMContentLoaded", () => {
        initCategoryChart();
        initDailyChart();
        initMonthlyChart();
        initInsightsCategoryChart();
        initMonthlyBarChart();
    });
})();
