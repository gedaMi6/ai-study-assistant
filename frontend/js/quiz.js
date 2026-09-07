document.addEventListener("DOMContentLoaded", () => {

    const documentSelect =
        document.getElementById("documentSelect");

    const questionCount =
        document.getElementById("questionCount");

    const generateButton =
        document.getElementById("generateQuizButton");

    const quizStatus =
        document.getElementById("quizStatus");

    const quizSection =
        document.getElementById("quizSection");

    const quizTitle =
        document.getElementById("quizTitle");

    const quizSubtitle =
        document.getElementById("quizSubtitle");

    const quizContainer =
        document.getElementById("quizContainer");

    const quizResult =
        document.getElementById("quizResult");

    const scoreText =
        document.getElementById("scoreText");

    const scoreMessage =
        document.getElementById("scoreMessage");

    const retryButton =
        document.getElementById("retryButton");


    let currentQuiz = [];
    let currentQuizId = null;


    // =========================
    // HTML ESCAPING
    // =========================

    function escapeHtml(text) {

        const div =
            document.createElement("div");

        div.textContent = text ?? "";

        return div.innerHTML;

    }


    // =========================
    // LOAD DOCUMENTS
    // =========================

    async function loadDocuments() {

        try {

            const response =
                await fetch("/documents");

            const data =
                await response.json();

            if (!response.ok) {

                throw new Error(
                    data.detail ||
                    data.message ||
                    "Failed to load documents."
                );

            }

            const documents =
                data.documents || [];

            documentSelect.innerHTML = "";

            if (documents.length === 0) {

                documentSelect.innerHTML = `
                    <option value="">
                        No study materials available
                    </option>
                `;

                generateButton.disabled = true;

                quizStatus.textContent =
                    "Upload a study document first.";

                return;

            }

            documents.forEach(doc => {

                const option =
                    document.createElement("option");

                option.value =
                    doc.id;

                option.textContent =
                    doc.filename;

                documentSelect.appendChild(option);

            });

            generateButton.disabled = false;

            quizStatus.textContent = "";

        } catch (error) {

            console.error(
                "Document loading error:",
                error
            );

            documentSelect.innerHTML = `
                <option value="">
                    Unable to load documents
                </option>
            `;

            generateButton.disabled = true;

            quizStatus.textContent =
                error.message;

        }

    }


    // =========================
    // GENERATE QUIZ
    // =========================

    async function generateQuiz() {

        const documentId =
            documentSelect.value;

        const count =
            Number(questionCount.value);

        if (!documentId) {

            quizStatus.textContent =
                "Please select a study document.";

            return;

        }

        generateButton.disabled = true;

        generateButton.textContent =
            "Generating Quiz...";

        quizStatus.textContent =
            "AI is creating your quiz. This may take a moment...";

        quizSection.style.display =
            "block";

        quizResult.style.display =
            "none";

        quizContainer.innerHTML = `
            <div class="feature-card">
                <h3>Generating your quiz...</h3>

                <p>
                    The AI is reading your study material
                    and creating questions.
                </p>
            </div>
        `;

        quizSection.scrollIntoView({
            behavior: "smooth"
        });

        try {

            const response =
                await fetch(
                    "/quiz/generate",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({
                            document_id:
                                documentId,

                            question_count:
                                count
                        })
                    }
                );

            const data =
                await response.json();

            if (!response.ok) {

                throw new Error(
                    data.detail ||
                    data.message ||
                    "Quiz generation failed."
                );

            }

            currentQuiz =
                data.quiz || [];

            currentQuizId =
                data.quiz_id || null;

            if (
                currentQuiz.length === 0 ||
                !currentQuizId
            ) {

                throw new Error(
                    "The server did not return a valid quiz."
                );

            }

            quizTitle.textContent =
                data.filename ||
                "Your Quiz";

            quizSubtitle.textContent =
                `${currentQuiz.length} questions generated from your study material.`;

            renderQuiz();

            quizStatus.textContent =
                "Quiz generated successfully.";

        } catch (error) {

            console.error(
                "Quiz generation error:",
                error
            );

            quizContainer.innerHTML = `
                <div class="feature-card">

                    <h3>
                        Unable to generate quiz
                    </h3>

                    <p>
                        ${escapeHtml(error.message)}
                    </p>

                </div>
            `;

            quizStatus.textContent =
                error.message;

        } finally {

            generateButton.disabled =
                false;

            generateButton.textContent =
                "Generate Quiz";

        }

    }


    // =========================
    // RENDER QUIZ
    // =========================

    function renderQuiz() {

        quizContainer.innerHTML = "";

        currentQuiz.forEach(
            (question, index) => {

                const card =
                    document.createElement("div");

                card.className =
                    "feature-card quiz-question";

                const options =
                    question.options || [];

                card.innerHTML = `

                    <span class="eyebrow">
                        QUESTION ${index + 1}
                    </span>

                    <h3>
                        ${escapeHtml(
                            question.question
                        )}
                    </h3>

                    <div class="quiz-options">

                        ${options.map(
                            (option, optionIndex) => `

                            <button
                                type="button"
                                class="quiz-option"
                                data-question="${index}"
                                data-option="${optionIndex}"
                            >

                                <span class="option-letter">
                                    ${String.fromCharCode(
                                        65 + optionIndex
                                    )}
                                </span>

                                <span>
                                    ${escapeHtml(option)}
                                </span>

                            </button>

                        `
                        ).join("")}

                    </div>

                    <div
                        class="quiz-explanation"
                        id="explanation-${index}"
                        style="display: none;"
                    >
                    </div>

                `;

                quizContainer.appendChild(card);

            }
        );

        const submitButton =
            document.createElement("button");

        submitButton.type =
            "button";

        submitButton.className =
            "primary-button";

        submitButton.textContent =
            "Submit Quiz";

        submitButton.id =
            "submitQuizButton";

        quizContainer.appendChild(
            submitButton
        );

        document
            .querySelectorAll(".quiz-option")
            .forEach(button => {

                button.addEventListener(
                    "click",
                    selectOption
                );

            });

        submitButton.addEventListener(
            "click",
            submitQuiz
        );

    }


    // =========================
    // SELECT OPTION
    // =========================

    function selectOption(event) {

        const button =
            event.currentTarget;

        const questionIndex =
            Number(
                button.dataset.question
            );

        document
            .querySelectorAll(
                `.quiz-option[data-question="${questionIndex}"]`
            )
            .forEach(option => {

                option.classList.remove(
                    "selected"
                );

            });

        button.classList.add(
            "selected"
        );

    }


    // =========================
    // SUBMIT QUIZ
    // =========================

    async function submitQuiz() {

        if (!currentQuizId) {

            scoreMessage.textContent =
                "This quiz is no longer available.";

            quizResult.style.display =
                "block";

            return;

        }

        const answers = [];

        currentQuiz.forEach(
            (question, index) => {

                const selected =
                    document.querySelector(
                        `.quiz-option[data-question="${index}"].selected`
                    );

                let selectedAnswer = null;

                if (selected) {

                    selectedAnswer =
                        Number(
                            selected.dataset.option
                        );

                }

                answers.push({
                    question_index: index,
                    selected_answer: selectedAnswer
                });

            }
        );

        const submitButton =
            document.getElementById(
                "submitQuizButton"
            );

        if (submitButton) {

            submitButton.disabled =
                true;

            submitButton.textContent =
                "Submitting...";

        }

        try {

            const response =
                await fetch(
                    "/quiz/submit",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({
                            quiz_id:
                                currentQuizId,

                            answers:
                                answers
                        })
                    }
                );

            const data =
                await response.json();

            if (!response.ok) {

                throw new Error(
                    data.detail ||
                    "Failed to save quiz attempt."
                );

            }

            displayResults(data);

            console.log(
                "Quiz attempt saved:",
                data
            );

        } catch (error) {

            console.error(
                "Quiz submission error:",
                error
            );

            scoreMessage.textContent =
                `The quiz could not be saved: ${error.message}`;

            if (submitButton) {

                submitButton.disabled =
                    false;

                submitButton.textContent =
                    "Submit Quiz";

            }

        }

    }


    // =========================
    // DISPLAY SERVER RESULTS
    // =========================

    function displayResults(data) {

        const results =
            data.results || [];

        results.forEach(result => {

            const questionIndex =
                result.question_index;

            const selectedButton =
                document.querySelector(
                    `.quiz-option[data-question="${questionIndex}"][data-option="${result.selected_answer}"]`
                );

            const correctButton =
                document.querySelector(
                    `.quiz-option[data-question="${questionIndex}"][data-option="${result.correct_answer}"]`
                );

            if (selectedButton) {

                if (result.is_correct) {

                    selectedButton.classList.add(
                        "correct"
                    );

                } else {

                    selectedButton.classList.add(
                        "incorrect"
                    );

                }

            }

            if (correctButton) {

                correctButton.classList.add(
                    "correct"
                );

            }

            const explanation =
                document.getElementById(
                    `explanation-${questionIndex}`
                );

            if (explanation) {

                explanation.innerHTML = `
                    <strong>
                        Explanation:
                    </strong>

                    ${escapeHtml(
                        result.explanation
                    )}
                `;

                explanation.style.display =
                    "block";

            }

        });

        scoreText.textContent =
            `${data.score} / ${data.total_questions} Correct`;

        const percentage =
            Number(data.percentage);

        if (percentage >= 80) {

            scoreMessage.textContent =
                `Excellent work! You scored ${percentage}%.`;

        } else if (percentage >= 60) {

            scoreMessage.textContent =
                `Good effort! You scored ${percentage}%. Keep practicing.`;

        } else {

            scoreMessage.textContent =
                `You scored ${percentage}%. Review the material and try again.`;

        }

        quizResult.style.display =
            "block";

        quizResult.scrollIntoView({
            behavior: "smooth"
        });

        const submitButton =
            document.getElementById(
                "submitQuizButton"
            );

        if (submitButton) {

            submitButton.disabled =
                true;

            submitButton.textContent =
                "Quiz Submitted";

        }

        document
            .querySelectorAll(".quiz-option")
            .forEach(button => {

                button.disabled =
                    true;

            });

    }


    // =========================
    // RETRY QUIZ
    // =========================

    if (retryButton) {

        retryButton.addEventListener(
            "click",
            async () => {

                quizResult.style.display =
                    "none";

                // Generate a completely new quiz.
                // This creates a new server-side quiz ID.
                await generateQuiz();

            }
        );

    }


    // =========================
    // GENERATE BUTTON
    // =========================

    if (generateButton) {

        generateButton.addEventListener(
            "click",
            generateQuiz
        );

    }


    // =========================
    // INITIALIZE
    // =========================

    loadDocuments();

});
