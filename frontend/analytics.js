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
       renderSentimentChart(
    data.rolling_sentiment || [],
    data.sentiment_timeline || []
);
        renderAggressionChart(data.aggression_scores);
        renderWordCloud(data.top_words);
        renderWinPredictor(data.win_score);
        renderLongestStreak(data.longest_streak);
        renderTopicDrift(
    data.topic_drift_score
);
        renderJudgeEvaluation(data.judge_decision);

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


function renderSentimentChart(
    rollingTimeline,
    sentimentTimeline
) {

    if (
        !rollingTimeline ||
        rollingTimeline.length === 0
    ) {
        return;
    }

    const labels =
        rollingTimeline.map(
            item => item.turn
        );

    const rollingValues =
        rollingTimeline.map(
            item => item.value
        );

    const rawValues =
        sentimentTimeline.map(
            item => item.sentiment
        );

    const ctx = document
        .getElementById("sentimentChart")
        .getContext("2d");

    if (sentimentChart) {
        sentimentChart.destroy();
    }

    sentimentChart = new Chart(ctx, {

        type: "line",

        data: {

            labels,

            datasets: [

                {
                    label:
                        "Rolling Average",

                    data:
                        rollingValues,

                    borderWidth: 3,

                    tension: 0.3
                },

                {
                    label:
                        "Raw Sentiment",

                    data:
                        rawValues,

                    borderWidth: 2,

                    tension: 0.1
                }
            ]
        },

        options: {

            responsive: true,

            maintainAspectRatio:
                false,

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
        color: "random-light",
        backgroundColor: "transparent"
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

function renderJudgeEvaluation(decision) {
    const cardEl = document.getElementById("judgeEvaluationCard");
    const winnerEl = document.getElementById("judge-winner");
    const summaryEl = document.getElementById("judge-summary");
    const gradesEl = document.getElementById("judgeGrades");

    if (!cardEl) return;

    if (!decision || !decision.winner) {
        cardEl.style.display = "none";
        return;
    }

    winnerEl.textContent = `Winner: ${decision.winner}`;
    summaryEl.textContent = decision.decision_summary || "";

    if (gradesEl) {
        gradesEl.innerHTML = "";
        const evaluations = decision.evaluations || [];
        evaluations.forEach(evalData => {
            const pName = evalData.participant || "";
            const modelScores = [
                `Logical Consistency: ${evalData.logical_consistency?.score || 0}/10`,
                `Rebuttal: ${evalData.rebuttal_effectiveness?.score || 0}/10`,
                `Persuasiveness: ${evalData.persuasiveness?.score || 0}/10`,
                `Rhetorical Style: ${evalData.evidence_rhetorical_style?.score || 0}/10`
            ].join(", ");

            const item = document.createElement("div");
            item.style.cssText = "font-size: 0.78rem; border-bottom: 1px dashed rgba(255,255,255,0.05); padding-bottom: 0.5rem;";
            item.innerHTML = `
                <div style="font-weight: 600; color: #fff; margin-top: 0.25rem;">${pName}</div>
                <div style="color: #bbb; font-size: 0.74rem; margin-top: 0.15rem; line-height: 1.3;">${modelScores}</div>
            `;
            gradesEl.appendChild(item);
        });
    }

    cardEl.style.display = "block";
}