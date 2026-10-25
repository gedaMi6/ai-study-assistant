"use strict";

document.addEventListener("DOMContentLoaded", () => {
    const $ = (id) => document.getElementById(id);

    const form = $("generateFlashcards");
    const documentSelect = $("flashDocument");
    const titleInput = $("flashTitle");
    const topicInput = $("flashTopic");
    const countInput = $("flashCount");
    const status = $("flashStatus");
    const decksContainer = $("flashDecks");
    const studySection = $("studySection");
    const studyTitle = $("studyTitle");
    const studyProgress = $("studyProgress");
    const flashCard = $("flashCard");
    const flashSideLabel = $("flashSideLabel");
    const flashCardText = $("flashCardText");
    const flashTopicLabel = $("flashTopicLabel");
    const flashDueLabel = $("flashDueLabel");
    const reviewButtons = $("reviewButtons");
    const reviewStatus = $("reviewStatus");

    let activeSet = null;
    let cards = [];
    let cardIndex = 0;
    let answerVisible = false;
    let reviewBusy = false;

    function escapeHTML(value) {
        return String(value ?? "").replace(/[&<>"']/g, (char) => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        })[char]);
    }

    async function api(url, options = {}) {
        const response = await fetch(url, options);
        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            const message = data.detail || data.message || `Request failed (${response.status})`;
            throw new Error(typeof message === "string" ? message : JSON.stringify(message));
        }

        return data;
    }

    function setStatus(message, isError = false) {
        if (!status) return;
        status.textContent = message;
        status.classList.toggle("is-error", isError);
    }

    function normalizeList(data, key) {
        if (Array.isArray(data)) return data;
        if (Array.isArray(data?.[key])) return data[key];
        return [];
    }

    async function loadDocuments() {
        try {
            const data = await api("/documents");
            const documents = normalizeList(data, "documents");

            documentSelect.innerHTML = '<option value="">Choose a document...</option>';

            documents.forEach((doc) => {
                const option = document.createElement("option");
                option.value = doc.id;
                option.textContent = doc.filename || doc.title || "Untitled document";
                documentSelect.appendChild(option);
            });

            if (!documents.length) {
                setStatus("No study documents found. Upload a document first.", true);
            }
        } catch (error) {
            setStatus(`Could not load documents: ${error.message}`, true);
        }
    }

    function getSetId(deck) {
        return deck.id ?? deck.set_id;
    }

    async function loadDecks() {
        decksContainer.innerHTML = '<p class="flashcards-muted">Loading your decks...</p>';

        try {
            const data = await api("/flashcards/sets");
            const decks = normalizeList(data, "sets");

            if (!decks.length) {
                decksContainer.innerHTML =
                    '<p class="flashcards-empty">No flashcard decks yet. Generate your first deck above.</p>';
                return;
            }

            decksContainer.innerHTML = decks.map((deck) => {
                const id = escapeHTML(getSetId(deck));
                const title = escapeHTML(deck.title || "Untitled deck");
                const source = escapeHTML(deck.filename || deck.document_filename || "Study document");
                const count = Number(deck.card_count ?? deck.cards_count ?? 0);
                const due = Number(deck.due_count ?? 0);

                return `
                    <article class="flashcards-deck">
                        <div class="flashcards-deck-icon" aria-hidden="true">▤</div>
                        <div class="flashcards-deck-info">
                            <h3>${title}</h3>
                            <p>${source}</p>
                            <div class="flashcards-deck-meta">
                                <span>${count} cards</span>
                                <span>${due} due</span>
                            </div>
                        </div>
                        <button class="flashcards-study-button"
                            type="button" data-study-set="${id}">Study deck</button>
                    </article>`;
            }).join("");
        } catch (error) {
            decksContainer.innerHTML =
                `<p class="flashcards-empty">Could not load decks: ${escapeHTML(error.message)}</p>`;
        }
    }

    async function generateDeck(event) {
        event.preventDefault();

        const documentId = documentSelect.value;
        if (!documentId) {
            setStatus("Choose a document before generating cards.", true);
            return;
        }

        const button = $("generateFlashcards");
        if (button) {
            button.disabled = true;
            button.textContent = "Generating...";
        }

        setStatus("AI is creating your flashcards. This may take a moment.");

        try {
            const result = await api("/flashcards/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    document_id: documentId,
                    card_count: Number(countInput.value || 10),
                    topic: topicInput.value.trim() || null,
                    title: titleInput.value.trim() || null
                })
            });

            setStatus("Your flashcard deck is ready.");
            await loadDecks();

            const newSetId = result.set_id ?? result.id ?? result.set?.id;
            if (newSetId) await studyDeck(newSetId);
        } catch (error) {
            setStatus(`Generation failed: ${error.message}`, true);
        } finally {
            if (button) {
                button.disabled = false;
                button.textContent = "Generate flashcards";
            }
        }
    }

    function showCurrentCard() {
        if (cardIndex >= cards.length) {
            flashSideLabel.textContent = "Session complete";
            flashCardText.textContent = "You've reviewed every card in this deck.";
            flashTopicLabel.textContent = "";
            flashDueLabel.textContent = "Nice work. Your review schedule has been updated.";
            studyProgress.textContent = `${cards.length} of ${cards.length} cards reviewed`;
            reviewButtons.hidden = true;
            flashCard.classList.add("is-complete");
            return;
        }

        const card = cards[cardIndex];
        answerVisible = false;

        flashCard.classList.remove("is-complete");
        flashSideLabel.textContent = "Question";
        flashCardText.textContent = card.question || "No question available";
        flashTopicLabel.textContent = card.topic || "General";
        flashDueLabel.textContent = "Tap the card to reveal the answer";
        studyProgress.textContent = `Card ${cardIndex + 1} of ${cards.length}`;
        reviewButtons.hidden = true;
        reviewStatus.textContent = "";
        flashCard.setAttribute("aria-label", "Reveal answer");
    }

    async function studyDeck(setId) {
        try {
            const result = await api(`/flashcards/sets/${encodeURIComponent(setId)}`);
            activeSet = result.set || result.flashcard_set || result;
            cards = Array.isArray(result.cards) ? result.cards : [];
            cardIndex = 0;

            studyTitle.textContent = activeSet.title || "Study flashcards";
            studySection.hidden = false;
            studySection.scrollIntoView({ behavior: "smooth", block: "start" });

            if (!cards.length) {
                flashSideLabel.textContent = "Empty deck";
                flashCardText.textContent = "This deck has no cards yet.";
                reviewButtons.hidden = true;
                studyProgress.textContent = "0 cards";
                return;
            }

            showCurrentCard();
        } catch (error) {
            setStatus(`Could not open deck: ${error.message}`, true);
        }
    }

    function revealAnswer() {
        if (answerVisible || cardIndex >= cards.length || reviewBusy) return;

        answerVisible = true;
        const card = cards[cardIndex];
        flashSideLabel.textContent = "Answer";
        flashCardText.textContent = card.answer || "No answer available";
        flashDueLabel.textContent = "How well did you remember it?";
        reviewButtons.hidden = false;
        flashCard.setAttribute("aria-label", "Answer revealed");
    }

    async function reviewCard(rating) {
        if (reviewBusy || cardIndex >= cards.length || !answerVisible) return;

        const card = cards[cardIndex];
        reviewBusy = true;
        reviewButtons.querySelectorAll("button").forEach((button) => {
            button.disabled = true;
        });
        reviewStatus.textContent = "Saving review...";

        try {
            await api(`/flashcards/${encodeURIComponent(card.id)}/review`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ rating })
            });

            cardIndex += 1;
            showCurrentCard();
            await loadDecks();
        } catch (error) {
            reviewStatus.textContent = `Could not save review: ${error.message}`;
        } finally {
            reviewBusy = false;
            reviewButtons.querySelectorAll("button").forEach((button) => {
                button.disabled = false;
            });
        }
    }

    form?.addEventListener("click", generateDeck);
    $("refreshDecks")?.addEventListener("click", loadDecks);

    decksContainer?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-study-set]");
        if (button) studyDeck(button.dataset.studySet);
    });

    flashCard?.addEventListener("click", revealAnswer);

    $("closeStudy")?.addEventListener("click", () => {
        studySection.hidden = true;
    });

    reviewButtons?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-rating]");
        if (button) reviewCard(button.dataset.rating);
    });

    loadDocuments();
    loadDecks();
});
