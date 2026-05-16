(function () {
    const source = document.getElementById("event-rating-chart-data");
    const canvas = document.getElementById("eventRatingChart");
    if (!source || !canvas || typeof Chart === "undefined") {
        return;
    }

    const data = JSON.parse(source.textContent);
    Chart.defaults.font.family = '"Segoe UI", Tahoma, sans-serif';
    Chart.defaults.color = "#647067";

    new Chart(canvas, {
        type: "bar",
        data: {
            labels: data.labels,
            datasets: [{
                label: "Количество оценок",
                data: data.counts,
                backgroundColor: "rgba(47, 143, 70, 0.82)",
                borderColor: "#236a34",
                borderWidth: 1,
                borderRadius: 8,
                maxBarThickness: 48,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { precision: 0 },
                    grid: { color: "rgba(100, 112, 103, 0.18)" },
                },
                x: {
                    grid: { display: false },
                },
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "#223127",
                    padding: 12,
                    cornerRadius: 10,
                },
            },
        },
    });
})();
