(function () {
    const source = document.getElementById("analytics-chart-data");
    if (!source || typeof Chart === "undefined") {
        return;
    }

    const data = JSON.parse(source.textContent);
    const palette = ["#2f8f46", "#5f9fcd", "#d89a1d", "#a45aa5", "#cc6f4b", "#466a9f", "#7aa65a"];
    const gridColor = "rgba(100, 112, 103, 0.18)";
    const labelColor = "#647067";

    Chart.defaults.font.family = '"Segoe UI", Tahoma, sans-serif';
    Chart.defaults.color = labelColor;
    Chart.defaults.plugins.legend.labels.boxWidth = 12;
    Chart.defaults.plugins.legend.labels.boxHeight = 12;
    Chart.defaults.plugins.tooltip.backgroundColor = "#223127";
    Chart.defaults.plugins.tooltip.padding = 12;
    Chart.defaults.plugins.tooltip.cornerRadius = 10;

    const qualityCanvas = document.getElementById("eventQualityChart");
    if (qualityCanvas && data.quality && data.quality.labels.length) {
        new Chart(qualityCanvas, {
            type: "line",
            data: {
                labels: data.quality.labels,
                datasets: [{
                    label: "Качество мероприятия",
                    data: data.quality.values,
                    borderColor: "#2f8f46",
                    backgroundColor: "rgba(47, 143, 70, 0.14)",
                    borderWidth: 3,
                    pointBackgroundColor: "#ffffff",
                    pointBorderColor: "#2f8f46",
                    pointBorderWidth: 3,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    tension: 0.28,
                    fill: true,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { intersect: false, mode: "index" },
                scales: {
                    y: {
                        beginAtZero: true,
                        suggestedMax: 1,
                        grid: { color: gridColor },
                        ticks: { precision: 2 },
                    },
                    x: {
                        grid: { display: false },
                        ticks: { maxRotation: 35, minRotation: 0 },
                    },
                },
            },
        });
    }

    const durationCanvas = document.getElementById("durationGroupChart");
    if (durationCanvas && data.duration) {
        new Chart(durationCanvas, {
            type: "doughnut",
            data: {
                labels: data.duration.labels,
                datasets: [{
                    label: "Мероприятия",
                    data: data.duration.values,
                    backgroundColor: palette,
                    borderColor: "#ffffff",
                    borderWidth: 3,
                    hoverOffset: 8,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "58%",
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: { padding: 16 },
                    },
                },
            },
        });
    }

    const employeeQualityCanvas = document.getElementById("employeeQualityChart");
    if (employeeQualityCanvas && data.employeeQuality && data.employeeQuality.labels.length) {
        new Chart(employeeQualityCanvas, {
            type: "line",
            data: {
                labels: data.employeeQuality.labels,
                datasets: data.employeeQuality.datasets.map((dataset, index) => ({
                    label: dataset.label,
                    data: dataset.data,
                    borderColor: palette[index % palette.length],
                    backgroundColor: palette[index % palette.length] + "24",
                    borderWidth: 3,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    tension: 0.25,
                    spanGaps: true,
                })),
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { intersect: false, mode: "index" },
                scales: {
                    y: {
                        suggestedMin: -0.4,
                        suggestedMax: 1,
                        grid: { color: gridColor },
                        ticks: { precision: 2 },
                    },
                    x: {
                        grid: { display: false },
                    },
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: (context) => `${context.dataset.label}: ${context.parsed.y ?? 0}`,
                        },
                    },
                },
            },
        });
    }
})();
