async function loadGradeBar() {

    const container = document.getElementById("gradeBar");

    if (!container) {
        return;
    }

    try {

        const response = await fetch("/progress/grades");

        if (!response.ok) {
            throw new Error("Failed to load released exam grades.");
        }

        const data = await response.json();

        renderGradeBar(data.grades || []);

    } catch (error) {

        console.error("Grade Bar error:", error);

        container.innerHTML = `
            <div class="progress-empty-card">
                <div class="empty-icon">⚠️</div>
                <h3>Unable to load exam grades</h3>
                <p>
                    Please refresh the page and try again.
                </p>
            </div>
        `;

    }

}


function renderGradeBar(grades) {

    const container = document.getElementById("gradeBar");

    if (!container) {
        return;
    }

    if (!grades.length) {

        container.innerHTML = `
            <div class="progress-empty-card">
                <div class="empty-icon">📝</div>
                <h3>No released exam grades yet</h3>
                <p>
                    Your exam grade will appear here when your teacher releases it.
                </p>
            </div>
        `;

        return;
    }

    container.innerHTML = grades.map(grade => {

        const percentage = Math.max(
            0,
            Math.min(100, Number(grade.percentage || 0))
        );

        return `
            <div class="grade-bar-card">

                <div class="grade-bar-header">

                    <div>

                        <strong>
                            ${escapeHtml(grade.exam_title || "Exam")}
                        </strong>

                        <span>
                            ${escapeHtml(
                                grade.submitted_at || ""
                            )}
                        </span>

                    </div>

                    <div class="grade-bar-score">

                        <strong>
                            ${grade.score}/${grade.total_questions}
                        </strong>

                        <span>
                            ${percentage}%
                        </span>

                    </div>

                </div>


                <div class="grade-meter">

                    <div class="grade-meter-scale">
                        <span>0</span>
                        <span>25</span>
                        <span>50</span>
                        <span>75</span>
                        <span>100</span>
                    </div>

                    <div class="grade-meter-line">

                        <div
                            class="grade-meter-value"
                            style="width: ${percentage}%"
                        ></div>

                    </div>

                    <div
                        class="grade-meter-marker"
                        style="left: ${percentage}%"
                    >
                        <span>${percentage}%</span>
                    </div>

                </div>


                <div class="grade-bar-footer">

                    <span>
                        🔓 Released
                    </span>

                    <span>
                        Teacher released result
                    </span>

                </div>

            </div>
        `;

    }).join("");

}


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

    renderRecommendations(data.recommendations || [], data.weak_topics || []);

    renderStudyFocus(data.study_focus);
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

            const trend =
                topic.trend || "new";

            const improvement =
                topic.improvement !== null &&
                topic.improvement !== undefined
                    ? Number(topic.improvement)
                    : null;

            let improvementHtml = "";

            if (trend === "improving" && improvement !== null) {

                improvementHtml = `
                    <span class="topic-improvement improving">
                        ↑ +${Math.abs(improvement)}% improvement
                    </span>
                `;

            } else if (trend === "declining" && improvement !== null) {

                improvementHtml = `
                    <span class="topic-improvement declining">
                        ↓ ${improvement}% since previous quiz
                    </span>
                `;

            } else if (trend === "stable" && improvement !== null) {

                improvementHtml = `
                    <span class="topic-improvement stable">
                        → 0% since previous quiz
                    </span>
                `;

            } else {

                improvementHtml = `
                    <span class="topic-improvement new">
                        First attempt
                    </span>
                `;

            }

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

                        <div class="topic-card-meta">

                            <span class="topic-level ${status}">
                                ${level}
                            </span>

                            ${improvementHtml}

                        </div>

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
                <button
                    type="button"
                    class="weak-topic-card"
                    data-topic="${escapeHtml(topic)}"
                    style="animation-delay: ${index * 70}ms"
                    title="Practice ${escapeHtml(topic)}"
                >

                    <div class="weak-topic-icon">
                        !
                    </div>

                    <div>

                        <strong>
                            ${escapeHtml(topic)}
                        </strong>

                        <p>
                            Needs more practice · Click to practice
                        </p>

                    </div>

                </button>
            `;
        }
    ).join("");

    container.querySelectorAll(".weak-topic-card").forEach(card => {

        const activate = () =>
            openTopicQuiz(card.dataset.topic);

        card.addEventListener("click", activate);

        card.addEventListener("keydown", event => {

            if (
                event.key === "Enter" ||
                event.key === " "
            ) {
                event.preventDefault();
                activate();
            }

        });

    });
}


function renderStudyFocus(studyFocus) {

    const container =
        document.getElementById("studyFocus");

    if (!container) {
        return;
    }

    if (!studyFocus) {

        container.innerHTML = `
            <div class="progress-empty-card">

                <div class="empty-icon">✦</div>

                <h3>Your AI study focus is not ready yet</h3>

                <p>
                    Complete a quiz to identify the topic that needs the most review.
                </p>

            </div>
        `;

        return;
    }

    const topic =
        escapeHtml(studyFocus.topic || "Unknown topic");

    const performance =
        Math.max(
            0,
            Math.min(
                100,
                Number(studyFocus.performance || 0)
            )
        );

    const priority =
        escapeHtml(studyFocus.priority || "Medium");

    const reason =
        escapeHtml(studyFocus.reason || "");

    const nextStep =
        escapeHtml(studyFocus.next_step || "");

    const review =
        typeof studyFocus.review === "string"
            ? studyFocus.review
            : "";

    const sources =
        Array.isArray(studyFocus.review_sources)
            ? studyFocus.review_sources
            : [];

    const priorityClass =
        priority.toLowerCase();

    let reviewHtml;

    if (review.trim()) {

        if (
            typeof marked !== "undefined" &&
            typeof DOMPurify !== "undefined"
        ) {
            reviewHtml =
                DOMPurify.sanitize(
                    marked.parse(review)
                );
        } else {
            reviewHtml = escapeHtml(
                review
                    .replace(/^#{1,6}\s+/gm, "")
                    .replace(/^[-*_]{3,}\s*$/gm, "")
                    .replace(/^\s*[-*+]\s+/gm, "• ")
                    .replace(/^\s*\d+\.\s+/gm, "")
                    .replace(/\|/g, " ")
                    .replace(/\*\*/g, "")
                    .replace(/\*/g, "")
            ).replace(/\n/g, "<br>");
        }

    } else {

        reviewHtml = `
            <div class="ai-review-unavailable">

                <strong>
                    Full review is not available yet.
                </strong>

                <p>
                    Your weakest topic has been identified.
                    The complete AI review will appear when AI generation is available.
                </p>

            </div>
        `;
    }

    const sourcesHtml =
        sources.length
            ? `
                <div class="ai-focus-sources">

                    <span class="ai-focus-subtitle">
                        STUDY SOURCES
                    </span>

                    <ul>
                        ${sources.map(source => `
                            <li>
                                ${escapeHtml(String(source))}
                            </li>
                        `).join("")}
                    </ul>

                </div>
            `
            : "";

    container.innerHTML = `
        <div class="ai-study-focus-card">

            <div class="ai-focus-header">

                <div class="ai-focus-title-wrap">

                    <div class="ai-focus-icon">
                        ✦
                    </div>

                    <div>

                        <span class="ai-focus-label">
                            YOUR AI STUDY FOCUS
                        </span>

                        <h3>
                            ${topic}
                        </h3>

                    </div>

                </div>

                <span class="ai-focus-priority ${priorityClass}">
                    ${priority}
                </span>

            </div>


            <div class="ai-focus-performance">

                <div class="ai-focus-performance-top">

                    <span>Your performance</span>

                    <strong>
                        ${performance.toFixed(1)}%
                    </strong>

                </div>

                <div class="ai-focus-progress-track">

                    <div
                        class="ai-focus-progress-fill"
                        style="width: ${performance}%"
                    ></div>

                </div>

            </div>


            <div class="ai-focus-reason">

                <span class="ai-focus-subtitle">
                    WHY YOU SHOULD REVIEW THIS
                </span>

                <p>
                    ${reason}
                </p>

            </div>


            <div class="ai-focus-review">

                <div class="ai-focus-review-header">

                    <span class="ai-focus-subtitle">
                        FULL TOPIC REVIEW
                    </span>

                    <span class="ai-focus-review-badge">
                        ALL DOCUMENTS
                    </span>

                </div>

                <div class="ai-focus-review-content">
                    ${reviewHtml}
                </div>

            </div>


            ${sourcesHtml}


            ${
                nextStep
                    ? `
                        <div class="ai-focus-next-step">

                            <span class="ai-focus-subtitle">
                                NEXT STEP
                            </span>

                            <p>
                                ${nextStep}
                            </p>

                        </div>
                    `
                    : ""
            }

        </div>
    `;
}




function openTopicQuiz(topic) {

    const cleanTopic =
        String(topic || "").trim();

    if (!cleanTopic) {
        return;
    }

    window.location.href =
        `/quiz.html?topic=${encodeURIComponent(cleanTopic)}`;
}


function renderRecommendations(
    recommendations,
    weakTopics = []
) {

    const container =
        document.getElementById(
            "recommendations"
        );

    if (!recommendations.length) {

        container.innerHTML = `
            <div class="progress-empty-card">

                <div class="empty-icon">
                    ✦
                </div>

                <h3>
                    No recommendations yet
                </h3>

                <p>
                    Complete a quiz to receive personalized next steps.
                </p>

            </div>
        `;

        return;
    }

    container.innerHTML = recommendations.map(
        (recommendation, index) => {

            const topic =
                weakTopics[index] || "";

            return `
                <button
                    type="button"
                    class="recommendation-card"
                    data-topic="${escapeHtml(topic)}"
                    style="animation-delay: ${index * 70}ms"
                    title="${
                        topic
                            ? `Practice ${escapeHtml(topic)}`
                            : "View next step"
                    }"
                >

                    <div class="recommendation-number">
                        ${index + 1}
                    </div>

                    <p>
                        ${escapeHtml(recommendation)}
                    </p>

                </button>
            `;
        }
    ).join("");

    container
        .querySelectorAll(".recommendation-card")
        .forEach(card => {

            const activate = () => {

                const topic =
                    card.dataset.topic;

                if (topic) {
                    openTopicQuiz(topic);
                }

            };

            card.addEventListener(
                "click",
                activate
            );

            card.addEventListener(
                "keydown",
                event => {

                    if (
                        event.key === "Enter" ||
                        event.key === " "
                    ) {
                        event.preventDefault();
                        activate();
                    }

                }
            );

        });
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
loadGradeBar();
