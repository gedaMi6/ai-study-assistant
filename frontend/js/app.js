document.addEventListener("DOMContentLoaded", () => {

    const uploadButton =
        document.querySelector(".dashboard-upload-button");

    const documentsList =
        document.getElementById("documentsList");

    const documentCount =
        document.getElementById("documentCount");

    const quizCount =
        document.getElementById("quizCount");

    const questionCount =
        document.getElementById("questionCount");

    const progressPercentage =
        document.getElementById("progressPercentage");

    const summarySection =
        document.getElementById("summarySection");

    const summaryTitle =
        document.getElementById("summaryTitle");

    const summaryContent =
        document.getElementById("summaryContent");


    // =========================
    // HTML ESCAPING
    // =========================

    function escapeHtml(text) {

        const div =
            document.createElement("div");

        div.textContent =
            text ?? "";

        return div.innerHTML;
    }


    // =========================
    // MARKDOWN
    // =========================

    function renderMarkdown(text) {

        if (
            typeof marked === "undefined" ||
            typeof DOMPurify === "undefined"
        ) {
            return escapeHtml(text)
                .replace(/\n/g, "<br>");
        }

        const rawHtml =
            marked.parse(text || "");

        return DOMPurify.sanitize(rawHtml);
    }


    // =========================
    // LOAD PROGRESS
    // =========================

    async function loadDashboardProgress() {

        try {

            const response =
                await fetch("/progress");

            if (!response.ok) {
                throw new Error(
                    "Failed to load progress."
                );
            }

            const data =
                await response.json();

            const overall =
                data.overall || {};

            if (quizCount) {
                quizCount.textContent =
                    overall.total_attempts ?? 0;
            }

            if (questionCount) {
                questionCount.textContent =
                    overall.total_questions ?? 0;
            }

            if (progressPercentage) {
                progressPercentage.textContent =
                    `${overall.average_percentage ?? 0}%`;
            }

        } catch (error) {

            console.error(
                "Dashboard progress error:",
                error
            );

        }
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

                const errorMessage =
                    data.detail ||
                    data.message ||
                    `Failed to load documents. Status: ${response.status}`;

                throw new Error(errorMessage);
            }


            const documents =
                data.documents || [];


            if (documentCount) {

                documentCount.textContent =
                    documents.length;
            }


            if (documents.length === 0) {

                documentsList.innerHTML = `

                    <div class="dashboard-empty-card">

                        <div class="dashboard-empty-icon">
                            📚
                        </div>

                        <h3>
                            No study materials yet
                        </h3>

                        <p>
                            Upload a PDF or PowerPoint to begin
                            building your study library.
                        </p>

                        <button
                            class="primary-button empty-upload-button"
                        >
                            Upload Material
                        </button>

                    </div>
                `;

                const emptyUploadButton =
                    documentsList.querySelector(
                        ".empty-upload-button"
                    );

                if (emptyUploadButton) {

                    emptyUploadButton.addEventListener(
                        "click",
                        () => uploadButton.click()
                    );
                }

                return;
            }


            documentsList.innerHTML =
                documents.map(doc => {

                    const filename =
                        escapeHtml(
                            doc.filename ||
                            "Unnamed document"
                        );

                    const documentId =
                        escapeHtml(
                            doc.id || ""
                        );

                    const chunkCount =
                        Number(
                            doc.chunk_count || 0
                        );


                    return `

                        <article
                            class="dashboard-document-card"
                        >

                            <div
                                class="document-card-icon"
                            >
                                📄
                            </div>


                            <div
                                class="document-card-content"
                            >

                                <span
                                    class="document-type"
                                >
                                    STUDY MATERIAL
                                </span>

                                <h3>
                                    ${filename}
                                </h3>

                                <p>
                                    ${chunkCount}
                                    indexed chunks
                                </p>

                            </div>


                            <button
                                type="button"
                                class="document-summary-button summary-button"
                                data-document-id="${documentId}"
                            >
                                Generate Summary
                                <span>→</span>
                            </button>

                        </article>
                    `;

                }).join("");


            document
                .querySelectorAll(".summary-button")
                .forEach(button => {

                    button.addEventListener(
                        "click",
                        () => {

                            const documentId =
                                button.dataset.documentId;

                            generateSummary(
                                documentId,
                                button
                            );
                        }
                    );
                });


        } catch (error) {

            console.error(
                "Document loading error:",
                error
            );


            documentsList.innerHTML = `

                <div class="dashboard-error-card">

                    <div>
                        ⚠
                    </div>

                    <h3>
                        Unable to load documents
                    </h3>

                    <p>
                        ${escapeHtml(error.message)}
                    </p>

                </div>
            `;
        }
    }


    // =========================
    // GENERATE SUMMARY
    // =========================

    async function generateSummary(
        documentId,
        button
    ) {

        if (!documentId) {
            return;
        }


        button.disabled = true;

        button.innerHTML =
            "Generating...";


        summarySection.style.display =
            "block";

        summaryTitle.textContent =
            "Generating Summary...";


        summaryContent.innerHTML = `

            <div class="summary-loading">

                <div class="summary-loading-spinner"></div>

                <h3>
                    AI is reading your material
                </h3>

                <p>
                    Extracting the important concepts for you...
                </p>

            </div>
        `;


        summarySection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });


        try {

            const response =
                await fetch(
                    `/documents/${encodeURIComponent(documentId)}/summary`
                );


            const data =
                await response.json();


            if (!response.ok) {

                throw new Error(
                    data.detail ||
                    data.message ||
                    "Failed to generate summary."
                );
            }


            summaryTitle.textContent =
                data.filename ||
                "Document Summary";


            summaryContent.innerHTML =
                renderMarkdown(
                    data.summary ||
                    "No summary was returned."
                );


        } catch (error) {

            console.error(
                "Summary error:",
                error
            );


            summaryTitle.textContent =
                "Summary Error";


            summaryContent.innerHTML = `

                <div class="summary-error">

                    <strong>
                        Unable to generate summary
                    </strong>

                    <p>
                        ${escapeHtml(error.message)}
                    </p>

                </div>
            `;

        } finally {

            button.disabled = false;

            button.innerHTML =
                "Generate Summary <span>→</span>";
        }
    }


    // =========================
    // UPLOAD DOCUMENT
    // =========================

    if (uploadButton) {

        uploadButton.addEventListener(
            "click",
            () => {

                const input =
                    document.createElement("input");


                input.type =
                    "file";

                input.accept =
                    ".pdf,application/pdf,.pptx";


                input.addEventListener(
                    "change",
                    async () => {

                        const file =
                            input.files[0];

                        if (!file) {
                            return;
                        }


                        const fileName =
                            file.name.toLowerCase();


                        if (
                            !fileName.endsWith(".pdf") &&
                            !fileName.endsWith(".pptx")
                        ) {

                            alert(
                                "Please select a PDF or PowerPoint (.pptx) file."
                            );

                            return;
                        }


                        uploadButton.disabled =
                            true;

                        uploadButton.textContent =
                            "Uploading...";


                        const formData =
                            new FormData();


                        formData.append(
                            "file",
                            file
                        );


                        try {

                            const response =
                                await fetch(
                                    "/documents/upload",
                                    {
                                        method: "POST",
                                        body: formData
                                    }
                                );


                            const data =
                                await response.json();


                            if (!response.ok) {

                                throw new Error(
                                    data.detail ||
                                    data.message ||
                                    `Upload failed. Status: ${response.status}`
                                );
                            }


                            alert(
                                `Document uploaded successfully!\n\n` +
                                `File: ${data.filename || file.name}\n` +
                                `Chunks created: ${data.chunks_created ?? "Unknown"}`
                            );


                            await loadDocuments();


                        } catch (error) {

                            console.error(
                                "Upload error:",
                                error
                            );


                            alert(
                                `Failed to upload document.\n\n` +
                                `${error.message}`
                            );

                        } finally {

                            uploadButton.disabled =
                                false;

                            uploadButton.textContent =
                                "Upload Study Material";
                        }
                    }
                );


                input.click();
            }
        );
    }


    // =========================
    // INITIAL LOAD
    // =========================

    loadDocuments();

    loadDashboardProgress();

});
