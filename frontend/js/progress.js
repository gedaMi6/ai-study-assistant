async function loadProgress() {

    try {

        const response = await fetch("/progress");

        if (!response.ok) {
            throw new Error("Failed to load progress.");
        }

        const data = await response.json();

        renderProgress(data);

    } catch (error) {

        console.error(error);

        document.getElementById("topicPerformance").innerHTML = `
            <div class="progress-empty-card">
                <div class="empty-icon">!</div>
                <h3>Unable to load progress</h3>
                <p>Please refresh the page and try again.</p>
            </div>
        `;
    }
}


function renderProgress(data) {

    const overall = data.overall;

    const average = Number(
        overall.average_percentage || 0
    );

    const totalQuestions = Number(
        overall.total_questions || 0
    );

    const totalCorrect = Number(
        overall.total_correct || 0
    );

    document.getElementById("totalAttempts").textContent =
        overall.total_attempts;

    document.getElementById("totalQuestions").textContent =
        totalQuestions;

    document.getElementById("totalCorrect").textContent =
        totalCorrect;

    document.getElementById("heroPercentage").textContent =
        `${average}%`;

    const accuracy = totalQuestions > 0
        ? Math.round((totalCorrect / totalQuestions) * 100)
        : 0;

    document.getElementById("accuracyPercentage").textContent =
        `${accuracy}%`;

    updatePerformanceHero(average);

    updateScoreRing(average);

    renderTopics(data.topics);

    renderWeakTopics(data.weak_topics);

    renderRecommendations(data.recommendations);
}


function updatePerformanceHero(percentage) {

    const title = document.getElementById(
        "performanceTitle"
    );

    const message = document.getElementById(
        "performanceMessage"
    );

    if (percentage === 0) {

        title.textContent =
            "Start your learning journey.";

        message.textContent =
            "Complete your first quiz to begin tracking your progress.";

    } else if (percentage < 60) {

        title.textContent =
            "Time to strengthen your foundation.";

        message.textContent =
            "Review your weaker topics and keep practicing.";

    } else if (percentage < 80) {

        title.textContent =
            "You're making solid progress.";

        message.textContent =
            "Keep practicing to turn developing topics into strengths.";

    } else if (percentage < 90) {

        title.textContent =
            "You're doing really well.";

        message.textContent =
            "Your understanding is strong. Keep pushing toward mastery.";

    } else {

        title.textContent =
            "Excellent work.";

        message.textContent =
            "You're showing a very strong understanding of your study material.";
    }
}


function updateScoreRing(percentage) {

    const ring = document.getElementById(
        "scoreRing"
    );

    const radius = 52;

    const circumference =
        2 * Math.PI * radius;

    const offset =
        circumference -
        (percentage / 100) * circumference;

    ring.style.strokeDasharray =
        circumference;

    ring.style.strokeDashoffset =
        offset;
}


function renderTopics(topics) {

    const container =
        document.getElementById(
            "topicPerformance"
        );

    if (!topics.length) {

        container.innerHTML = `
            <div class="progress-empty-card">

                <div class="empty-icon">📚</div>

                <h3>Your topic map is waiting</h3>

                <p>
                    Complete a quiz to see your performance by topic.
                </p>

            </div>
        `;

        return;
    }


    container.innerHTML = topics.map(
        (topic, index) => {

            const percentage =
                Math.max(
                    0,
                    Math.min(
                        100,
                        Number(topic.percentage || 0)
                    )
                );

            const status =
                escapeHtml(topic.status || "developing");

            const level =
                escapeHtml(topic.level || "Developing");

            return `
                <div
                    class="topic-performance-card"
                    style="animation-delay: ${index * 70}ms"
                >

                    <div class="topic-card-top">

                        <div class="topic-name-wrap">

                            <div class="topic-dot ${status}"></div>

                            <strong>
                                ${escapeHtml(topic.topic)}
                            </strong>

                        </div>

                        <strong class="topic-percentage">
                            ${percentage}%
                        </strong>

                    </div>


                    <div class="topic-progress-track">

                        <div
                            class="topic-progress-fill ${status}"
                            style="width: ${percentage}%"
                        ></div>

                    </div>


                    <div class="topic-card-bottom">

                        <span>
                            ${topic.correct_answers}
                            /
                            ${topic.questions_answered}
                            correct
                        </span>

                        <span class="topic-level ${status}">
                            ${level}
                        </span>

                    </div>

                </div>
            `;
        }
    ).join("");
}


function renderWeakTopics(weakTopics) {

    const container =
        document.getElementById(
            "weakTopics"
        );

    if (!weakTopics.length) {

        container.innerHTML = `
            <div class="progress-success">

                <div class="success-circle">
                    ✓
                </div>

                <div>

                    <strong>
                        No weak topics
                    </strong>

                    <p>
                        Keep completing quizzes to maintain your progress.
                    </p>

                </div>

            </div>
        `;

        return;
    }


    container.innerHTML = weakTopics.map(
        (topic, index) => {

            return `
                <div
                    class="weak-topic-card"
                    style="animation-delay: ${index * 70}ms"
                >

                    <div class="weak-topic-icon">
                        !
                    </div>

                    <div>

                        <strong>
                            ${escapeHtml(topic)}
                        </strong>

                        <p>
                            Needs more practice
                        </p>

                    </div>

                </div>
            `;
        }
    ).join("");
}


function renderRecommendations(recommendations) {

    const container =
        document.getElementById(
            "recommendations"
        );

    if (!recommendations.length) {

        container.innerHTML = `
            <div class="progress-empty-small">

                <span>→</span>

                <p>
                    Complete more quizzes to receive
                    personalized recommendations.
                </p>

            </div>
        `;

        return;
    }


    container.innerHTML = recommendations.map(
        (recommendation, index) => {

            return `
                <div
                    class="recommendation-card"
                    style="animation-delay: ${index * 70}ms"
                >

                    <div class="recommendation-number">
                        ${index + 1}
                    </div>

                    <p>
                        ${escapeHtml(recommendation)}
                    </p>

                </div>
            `;
        }
    ).join("");
}


function escapeHtml(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


loadProgress();
