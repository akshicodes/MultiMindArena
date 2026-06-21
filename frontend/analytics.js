console.log("Analytics JS loaded");

function getSessionId() {
    const sessionId =
        localStorage.getItem(
            "activeSessionId"
        );

    if (
        !sessionId ||
        sessionId === "null"
    ) {
        return null;
    }

    return sessionId;
}

let messageChart = null;
let sentimentChart = null;
let aggressionChart = null;

async function loadAnalytics() {
    try {
        const sessionId = getSessionId();

if (!sessionId) {
    console.error(
        "No active session found"
    );
    return;
}

const response = await fetch(
    `/sessions/${sessionId}/analytics`
);

        const data = await response.json();
        console.log("Analytics Data:", data);

        if (!response.ok) {
    console.log("Analytics not ready yet");
    return;
}

        // Session ID
        document.getElementById("session-id").innerText =
            data.session_id;

        // Total Messages
        const counts =
    data.message_counts || {};

const totalMessages =
    Object.values(counts)
        .reduce((a, b) => a + b, 0);

        document.getElementById("total-messages")
            .innerText = totalMessages;

        // Message Leaderboard Chart
        renderMessageChart(data.message_counts);
        renderSentimentChart(data.avg_sentiment);
        renderAggressionChart(data.aggression_scores);
        renderWordCloud(data.top_words);
        renderWinPredictor(data.win_score);
        renderLongestStreak(data.longest_streak);
        renderTopicDrift(
    data.topic_drift_score
);

    } catch (err) {
        console.error("Analytics Error:", err);
    }
}

function renderMessageChart(messageCounts) {

    const labels = Object.keys(messageCounts);
    const counts = Object.values(messageCounts);

    const ctx = document
        .getElementById("messageChart")
        .getContext("2d");

    // Destroy old chart if auto-refresh happens
    if (messageChart) {
        messageChart.destroy();
    }

    messageChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "Messages",
                data: counts,
                borderWidth: 1
            }]
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    beginAtZero: true
                }
            }
        }
    });
}

function renderSentimentChart(sentiments) {

    const labels = Object.keys(sentiments);
    const values = Object.values(sentiments);

    const ctx = document
        .getElementById("sentimentChart")
        .getContext("2d");

    if (sentimentChart) {
        sentimentChart.destroy();
    }

    sentimentChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "Average Sentiment",
                data: values,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    min: -1,
                    max: 1
                }
            }
        }
    });
}

function renderAggressionChart(scores) {

    const labels = Object.keys(scores);
    const values = Object.values(scores);

    const ctx = document
        .getElementById("aggressionChart")
        .getContext("2d");

    if (aggressionChart) {
        aggressionChart.destroy();
    }

    aggressionChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "Aggression Score",
                data: values,
                borderWidth: 1
            }]
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });
}

function renderWordCloud(words) {

    const list = words.map(item => [
        item.word,
        item.count * 10
    ]);

    WordCloud(
    document.getElementById("wordCloudCanvas"),
    {
        list: list,
        gridSize: 12,
        weightFactor: 1.5,
        minSize: 12,
        rotateRatio: 0.5,
        backgroundColor: "white"
    }
);
}

function renderWinPredictor(winScores) {

    const entries = Object.entries(winScores);

    entries.sort((a, b) => b[1] - a[1]);

    const leader = entries[0];

    document.getElementById(
        "leader-name"
    ).innerText =
        `${leader[0]} (${leader[1]} points)`;
}

function renderLongestStreak(streaks) {

    const entries = Object.entries(streaks);

    entries.sort((a, b) => b[1] - a[1]);

    const winner = entries[0];

    document.getElementById(
        "streak-leader"
    ).innerText =
        `${winner[0]} (${winner[1]} turns)`;
}

function renderTopicDrift(score) {

    const percent =
        Math.round(score * 100);

    document.getElementById(
        "topic-drift-text"
    ).innerText =
        `Topic Drift: ${percent}%`;

    document.getElementById(
        "topic-drift-bar"
    ).value = percent;
}

loadAnalytics();

// Auto refresh every 10 seconds
setInterval(() => {
    loadAnalytics();
}, 10000);