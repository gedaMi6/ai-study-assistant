document.addEventListener("DOMContentLoaded", () => {

    const chatForm = document.getElementById("chatForm");
    const questionInput = document.getElementById("questionInput");
    const sendButton = document.getElementById("sendButton");
    const scrollToBottomButton =
        document.getElementById("scrollToBottomButton");
    const chatMessages = document.getElementById("chatMessages");

    const sidebarToggle =
         document.getElementById("sidebarToggle");
    const chatContainer =
         document.querySelector(".chat-container");
    const newChatButton =
        document.getElementById("newChatButton");

    const recentChatsList =
        document.getElementById("recentChatsList");

    // =========================================
    // Chat session
    // =========================================

    function getSessionId() {

        const userId =
            localStorage.getItem(
                "study_assistant_user_id"
            );

        const storedUserId =
            localStorage.getItem(
                "study_assistant_session_user_id"
            );

        let sessionId =
            localStorage.getItem(
                "study_assistant_session_id"
            );

        // A chat session belongs to one authenticated user.
        // If the account changed, never reuse the old user's session.
        if (
            !userId ||
            storedUserId !== userId ||
            !sessionId ||
            sessionId === "default"
        ) {
            sessionId =
                crypto.randomUUID();

            localStorage.setItem(
                "study_assistant_session_id",
                sessionId
            );

            if (userId) {
                localStorage.setItem(
                    "study_assistant_session_user_id",
                    userId
                );
            }
        }

        return sessionId;
    }


    function setSessionId(sessionId) {

        localStorage.setItem(
            "study_assistant_session_id",
            sessionId
        );

        const userId =
            localStorage.getItem(
                "study_assistant_user_id"
            );

        if (userId) {
            localStorage.setItem(
                "study_assistant_session_user_id",
                userId
            );
        }
    }


    // =========================================
    // Helpers
    // =========================================

    function escapeHtml(text) {

        const div =
            document.createElement("div");

        div.textContent =
            text ?? "";

        return div.innerHTML;
    }


    function renderMarkdown(text) {

        if (
            typeof marked === "undefined" ||
            typeof DOMPurify === "undefined"
        ) {
            return escapeHtml(text)
                .replace(/\n/g, "<br>");
        }

        const rawHtml =
            marked.parse(text);

        return DOMPurify.sanitize(
            rawHtml
        );
    }


    async function showWelcomeMessage() {

        chatMessages.innerHTML = `
            <div class="chat-message assistant-message">
                <div class="message-avatar">AI</div>

                <div class="message-content">
                    <strong>AI STUDY ASSISTANT</strong>

                    <div class="message-text">
                        <p>
                            Hi <span id="chatGreetingName">there</span>! Ask me a question about your
                            study materials and I'll answer using
                            your documents.
                        </p>
                    </div>
                </div>
            </div>
        `;

        try {
            const response = await fetch("/auth/me", {
                credentials: "include",
                cache: "no-store"
            });

            if (!response.ok) {
                return;
            }

            const data = await response.json();

            const greetingName =
                document.getElementById("chatGreetingName");

            if (
                greetingName &&
                data.user &&
                data.user.name
            ) {
                greetingName.textContent = data.user.name;
            }

        } catch (error) {
            console.error(
                "Could not load user name for greeting:",
                error
            );
        }
    }


    function clearChatMessages() {

        chatMessages.innerHTML = "";
    }


    // =========================================
    // Message rendering
    // =========================================

    function addMessage(
        message,
        type,
        sources = []
    ) {

        const messageDiv =
            document.createElement("div");

        messageDiv.className =
            `chat-message ${type}-message`;

        const avatar =
            type === "assistant"
                ? "AI"
                : "G";

        const name =
            type === "assistant"
                ? "AI STUDY ASSISTANT"
                : "You";

        let sourcesHtml = "";

        if (
            type === "assistant" &&
            sources.length > 0
        ) {

            const sourceItems =
                sources.map(source => {

                    const filename =
                        escapeHtml(
                            source.document ||
                            "Unknown document"
                        );

                    const chunk =
                        escapeHtml(
                            String(
                                source.chunk ?? ""
                            )
                        );

                    return `
                        <li>
                            <span class="source-document">
                                ${filename}
                            </span>

                            <span class="source-chunk">
                                Chunk ${chunk}
                            </span>
                        </li>
                    `;
                }).join("");

            sourcesHtml = `
                <div class="message-sources">
                    <strong>📚 Sources</strong>

                    <ul>
                        ${sourceItems}
                    </ul>
                </div>
            `;
        }

        const messageHtml =
            type === "assistant"
                ? renderMarkdown(message)
                : `<p>${escapeHtml(message)}</p>`;

        messageDiv.innerHTML = `
            <div class="message-avatar">
                ${avatar}
            </div>

            <div class="message-content">
                <strong>${name}</strong>

                <div class="message-text">
                    ${messageHtml}
                </div>

                ${sourcesHtml}
            </div>
        `;

        chatMessages.appendChild(
            messageDiv
        );

        chatMessages.scrollTop =
            chatMessages.scrollHeight;
    }


    // =========================================
    // Thinking indicator
    // =========================================

    function showThinkingIndicator() {

        hideThinkingIndicator();

        const thinkingDiv =
            document.createElement("div");

        thinkingDiv.id =
            "aiThinkingIndicator";

        thinkingDiv.className =
            "chat-message ai-thinking-message";

        thinkingDiv.innerHTML = `
            <div class="message-avatar">
                AI
            </div>

            <div class="message-content">
                <strong>AI STUDY ASSISTANT</strong>

                <div class="ai-thinking-content">
                    <div
                        class="ai-thinking-dots"
                        aria-label="AI is thinking"
                    >
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        `;

        chatMessages.appendChild(
            thinkingDiv
        );

        chatMessages.scrollTop =
            chatMessages.scrollHeight;
    }


    function hideThinkingIndicator() {

        const thinkingDiv =
            document.getElementById(
                "aiThinkingIndicator"
            );

        if (thinkingDiv) {
            thinkingDiv.remove();
        }
    }


    // =========================================
    // Recent chat helpers
    // =========================================

    function formatChatDate(dateString) {

        if (!dateString) {
            return "";
        }

        const date =
            new Date(
                dateString.replace(" ", "T")
            );

        if (Number.isNaN(date.getTime())) {
            return "";
        }

        const now =
            new Date();

        const diff =
            now.getTime() -
            date.getTime();

        const minute =
            60 * 1000;

        const hour =
            60 * minute;

        const day =
            24 * hour;

        if (diff < minute) {
            return "Just now";
        }

        if (diff < hour) {
            const minutes =
                Math.floor(
                    diff / minute
                );

            return `${minutes}m ago`;
        }

        if (diff < day) {
            const hours =
                Math.floor(
                    diff / hour
                );

            return `${hours}h ago`;
        }

        if (diff < 7 * day) {
            const days =
                Math.floor(
                    diff / day
                );

            return `${days}d ago`;
        }

        return date.toLocaleDateString(
            undefined,
            {
                month: "short",
                day: "numeric"
            }
        );
    }


    function createChatIcon() {

        return `
            <svg
                class="recent-chat-icon"
                viewBox="0 0 24 24"
                aria-hidden="true"
            >
                <path
                    d="M20 11.5a7.5 7.5 0 0 1-7.5 7.5H8l-4 2v-4.5A7.5 7.5 0 1 1 20 11.5Z"
                ></path>
            </svg>
        `;
    }


    function createMoreIcon() {

        return `
            <svg
                class="chat-more-icon"
                viewBox="0 0 24 24"
                aria-hidden="true"
            >
                <circle cx="5" cy="12" r="1.4"></circle>
                <circle cx="12" cy="12" r="1.4"></circle>
                <circle cx="19" cy="12" r="1.4"></circle>
            </svg>
        `;
    }


    function createPinIcon() {

        return `
            <svg
                class="chat-action-icon"
                viewBox="0 0 24 24"
                aria-hidden="true"
            >
                <path
                    d="M8 4h8l-1 6 3 3v2H6v-2l3-3-1-6Z"
                ></path>
                <path d="M12 15v5"></path>
            </svg>
        `;
    }


    function createRenameIcon() {

        return `
            <svg
                class="chat-action-icon"
                viewBox="0 0 24 24"
                aria-hidden="true"
            >
                <path
                    d="M4 20h4L19 9a2.1 2.1 0 0 0-4-4L4 16v4Z"
                ></path>
                <path d="m13.5 6.5 4 4"></path>
            </svg>
        `;
    }


    function createDeleteIcon() {

        return `
            <svg
                class="chat-action-icon"
                viewBox="0 0 24 24"
                aria-hidden="true"
            >
                <path d="M5 7h14"></path>
                <path d="M9 7V4h6v3"></path>
                <path d="M7 7l1 13h8l1-13"></path>
                <path d="M10 11v5"></path>
                <path d="M14 11v5"></path>
            </svg>
        `;
    }


    // =========================================
    // Chat action menu
    // =========================================

    function closeAllChatMenus() {

        document
            .querySelectorAll(".chat-actions-menu.open")
            .forEach(menu => {
                menu.classList.remove("open");
            });
    }


    function createChatActionsMenu(
        session
    ) {

        const menu =
            document.createElement("div");

        menu.className =
            "chat-actions-menu";

        const pinLabel =
            session.is_pinned
                ? "Unpin"
                : "Pin";

        menu.innerHTML = `
            <button
                type="button"
                class="chat-action-menu-item"
                data-action="pin"
            >
                ${createPinIcon()}
                <span>${pinLabel}</span>
            </button>

            <button
                type="button"
                class="chat-action-menu-item"
                data-action="rename"
            >
                ${createRenameIcon()}
                <span>Rename</span>
            </button>

            <button
                type="button"
                class="chat-action-menu-item danger"
                data-action="delete"
            >
                ${createDeleteIcon()}
                <span>Delete</span>
            </button>
        `;

        menu
            .querySelector('[data-action="pin"]')
            .addEventListener(
                "click",
                async event => {

                    event.stopPropagation();

                    closeAllChatMenus();

                    await togglePinChat(
                        session
                    );
                }
            );

        menu
            .querySelector('[data-action="rename"]')
            .addEventListener(
                "click",
                event => {

                    event.stopPropagation();

                    closeAllChatMenus();

                    openRenameModal(
                        session
                    );
                }
            );

        menu
            .querySelector('[data-action="delete"]')
            .addEventListener(
                "click",
                async event => {

                    event.stopPropagation();

                    closeAllChatMenus();

                    await deleteChat(
                        session
                    );
                }
            );

        return menu;
    }


    // =========================================
    // Render recent chats
    // =========================================

    function renderChatItem(session) {

        const currentSessionId =
            getSessionId();

        const wrapper =
            document.createElement("div");

        wrapper.className =
            "recent-chat-wrapper";

        const button =
            document.createElement("button");

        button.type =
            "button";

        button.className =
            "recent-chat-item";

        if (
            session.session_id ===
            currentSessionId
        ) {
            button.classList.add(
                "active"
            );
        }

        if (session.is_pinned) {
            button.classList.add(
                "pinned"
            );
        }

        button.dataset.sessionId =
            session.session_id;

        button.innerHTML = `
            ${createChatIcon()}

            <span class="recent-chat-info">
                <span class="recent-chat-title">
                    ${escapeHtml(
                        session.title ||
                        "New chat"
                    )}
                </span>

                <span class="recent-chat-date">
                    ${escapeHtml(
                        formatChatDate(
                            session.updated_at
                        )
                    )}
                </span>
            </span>
        `;

        const moreButton =
            document.createElement("button");

        moreButton.type =
            "button";

        moreButton.className =
            "chat-more-button";

        moreButton.setAttribute(
            "aria-label",
            "Chat options"
        );

        moreButton.title =
            "Chat options";

        moreButton.innerHTML =
            createMoreIcon();

        const menu =
            createChatActionsMenu(
                session
            );

        moreButton.addEventListener(
            "click",
            event => {

                event.stopPropagation();

                const wasOpen =
                    menu.classList.contains(
                        "open"
                    );

                closeAllChatMenus();

                if (!wasOpen) {
                    menu.classList.add(
                        "open"
                    );
                }
            }
        );

        button.addEventListener(
            "click",
            async () => {

                closeAllChatMenus();

                await switchChat(
                    session.session_id
                );
            }
        );

        wrapper.appendChild(
            button
        );

        wrapper.appendChild(
            moreButton
        );

        wrapper.appendChild(
            menu
        );

        return wrapper;
    }


    function renderRecentChats(
        sessions
    ) {

        recentChatsList.innerHTML = "";

        const pinnedChats =
            sessions.filter(
                session =>
                    Boolean(
                        session.is_pinned
                    )
            );

        const recentChats =
            sessions.filter(
                session =>
                    !session.is_pinned
            );

        if (!sessions.length) {

            recentChatsList.innerHTML = `
                <div class="recent-chats-empty">
                    No recent chats yet.
                </div>
            `;

            return;
        }

        if (pinnedChats.length) {

            const pinnedHeader =
                document.createElement("div");

            pinnedHeader.className =
                "chat-section-label";

            pinnedHeader.innerHTML = `
                <svg
                    class="chat-section-pin-icon"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                >
                    <path
                        d="M8 4h8l-1 6 3 3v2H6v-2l3-3-1-6Z"
                    ></path>
                    <path d="M12 15v5"></path>
                </svg>

                <span>Pinned</span>
            `;

            recentChatsList.appendChild(
                pinnedHeader
            );

            pinnedChats.forEach(
                session => {
                    recentChatsList.appendChild(
                        renderChatItem(
                            session
                        )
                    );
                }
            );
        }

        if (recentChats.length) {

            const recentHeader =
                document.createElement("div");

            recentHeader.className =
                "chat-section-label";

            recentHeader.innerHTML = `
                <span>Recent chats</span>
            `;

            recentChatsList.appendChild(
                recentHeader
            );

            recentChats.forEach(
                session => {
                    recentChatsList.appendChild(
                        renderChatItem(
                            session
                        )
                    );
                }
            );
        }

        if (
            !recentChats.length &&
            pinnedChats.length
        ) {
            const allPinnedMessage =
                document.createElement("div");

            allPinnedMessage.className =
                "recent-chats-empty chat-all-pinned";

            allPinnedMessage.textContent =
                "All your chats are pinned.";

            recentChatsList.appendChild(
                allPinnedMessage
            );
        }
    }


    // Close menus when clicking elsewhere.
    document.addEventListener(
        "click",
        () => {
            closeAllChatMenus();
        }
    );


    // =========================================
    // Load recent chats
    // =========================================

    async function loadRecentChats() {

        if (!recentChatsList) {
            return;
        }

        try {

            const response =
                await fetch(
                    "/chat/sessions",
                    {
                        credentials:
                            "include",

                        cache:
                            "no-store"
                    }
                );

            if (!response.ok) {

                if (
                    response.status === 401
                ) {
                    console.warn(
                        "User is not authenticated."
                    );
                }

                throw new Error(
                    "Failed to load recent chats."
                );
            }

            const data =
                await response.json();

            renderRecentChats(
                data.sessions || []
            );

        } catch (error) {

            console.error(
                "Recent chats error:",
                error
            );

            recentChatsList.innerHTML = `
                <div class="recent-chats-empty">
                    Unable to load chats.
                </div>
            `;
        }
    }


    // =========================================
    // Register current session
    // =========================================

    async function registerCurrentSession() {

        const sessionId =
            getSessionId();

        try {

            const response =
                await fetch(
                    "/chat/sessions",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        credentials:
                            "include",

                        body:
                            JSON.stringify({
                                session_id:
                                    sessionId
                            })
                    }
                );

            if (!response.ok) {
                throw new Error(
                    "Failed to register chat session."
                );
            }

            return true;

        } catch (error) {

            console.error(
                "Session registration error:",
                error
            );

            return false;
        }
    }


    // =========================================
    // Load conversation
    // =========================================

    async function loadConversationHistory(
        sessionId
    ) {

        clearChatMessages();

        try {

            const response =
                await fetch(
                    `/ask/history/${encodeURIComponent(
                        sessionId
                    )}`,
                    {
                        credentials:
                            "include",

                        cache:
                            "no-store"
                    }
                );

            if (!response.ok) {
                throw new Error(
                    "Failed to load conversation history."
                );
            }

            const data =
                await response.json();

            const messages =
                data.messages || [];

            if (!messages.length) {

                showWelcomeMessage();

                return;
            }

            for (
                const message of messages
            ) {

                addMessage(
                    message.content,
                    message.role === "user"
                        ? "user"
                        : "assistant"
                );
            }

        } catch (error) {

            console.error(
                "History loading error:",
                error
            );

            showWelcomeMessage();
        }
    }


    // =========================================
    // Switch chat
    // =========================================

    async function switchChat(
        sessionId
    ) {

        if (!sessionId) {
            return;
        }

        if (
            recognition &&
            isListening
        ) {
            recognition.stop();
        }

        setSessionId(
            sessionId
        );

        questionInput.value =
            "";

        hideThinkingIndicator();

        await loadConversationHistory(
            sessionId
        );

        await loadRecentChats();

        questionInput.focus();
    }


    // =========================================
    // Create new chat
    // =========================================

    async function createNewChat() {

        if (
            newChatButton &&
            newChatButton.disabled
        ) {
            return;
        }

        if (
            recognition &&
            isListening
        ) {
            recognition.stop();
        }

        if (newChatButton) {
            newChatButton.disabled =
                true;
        }

        try {

            const response =
                await fetch(
                    "/chat/sessions",
                    {
                        method:
                            "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        credentials:
                            "include",

                        body:
                            JSON.stringify({})
                    }
                );

            const data =
                await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                    "Failed to create a new chat."
                );
            }

            const sessionId =
                data.session.session_id;

            setSessionId(
                sessionId
            );

            questionInput.value =
                "";

            hideThinkingIndicator();

            clearChatMessages();

            showWelcomeMessage();

            await loadRecentChats();

            questionInput.focus();

        } catch (error) {

            console.error(
                "New chat error:",
                error
            );

            addMessage(
                `I couldn't create a new chat. ${error.message}`,
                "assistant"
            );

        } finally {

            if (newChatButton) {
                newChatButton.disabled =
                    false;
            }
        }
    }


    if (newChatButton) {

        newChatButton.addEventListener(
            "click",
            createNewChat
        );
    }


    // =========================================
    // Pin / Unpin
    // =========================================

    async function togglePinChat(
        session
    ) {

        try {

            const response =
                await fetch(
                    `/chat/sessions/${encodeURIComponent(
                        session.session_id
                    )}/pin`,
                    {
                        method:
                            "PATCH",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        credentials:
                            "include",

                        body:
                            JSON.stringify({
                                is_pinned:
                                    !Boolean(
                                        session.is_pinned
                                    )
                            })
                    }
                );

            const data =
                await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                    "Failed to update chat pin."
                );
            }

            await loadRecentChats();

        } catch (error) {

            console.error(
                "Pin chat error:",
                error
            );

            alert(
                `Couldn't update the chat pin. ${error.message}`
            );
        }
    }


    // =========================================
    // Rename modal
    // =========================================

    let renameTargetSession = null;


    function getRenameModal() {

        return document.getElementById(
            "renameChatModal"
        );
    }


    function openRenameModal(
        session
    ) {

        const modal =
            getRenameModal();

        const input =
            document.getElementById(
                "renameChatInput"
            );

        if (!modal || !input) {

            const fallback =
                window.prompt(
                    "Rename chat:",
                    session.title ||
                    "New chat"
                );

            if (
                fallback !== null
            ) {
                renameChat(
                    session,
                    fallback
                );
            }

            return;
        }

        renameTargetSession =
            session;

        input.value =
            session.title ||
            "New chat";

        modal.classList.add(
            "open"
        );

        modal.setAttribute(
            "aria-hidden",
            "false"
        );

        setTimeout(
            () => {
                input.focus();
                input.select();
            },
            50
        );
    }


    function closeRenameModal() {

        const modal =
            getRenameModal();

        if (!modal) {
            return;
        }

        modal.classList.remove(
            "open"
        );

        modal.setAttribute(
            "aria-hidden",
            "true"
        );

        renameTargetSession =
            null;
    }


    async function renameChat(
        session,
        title
    ) {

        const cleanTitle =
            String(
                title || ""
            ).trim();

        if (!cleanTitle) {
            return;
        }

        try {

            const response =
                await fetch(
                    `/chat/sessions/${encodeURIComponent(
                        session.session_id
                    )}`,
                    {
                        method:
                            "PATCH",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        credentials:
                            "include",

                        body:
                            JSON.stringify({
                                title:
                                    cleanTitle
                            })
                    }
                );

            const data =
                await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                    "Failed to rename chat."
                );
            }

            await loadRecentChats();

        } catch (error) {

            console.error(
                "Rename chat error:",
                error
            );

            alert(
                `Couldn't rename the chat. ${error.message}`
            );
        }
    }


    const renameForm =
        document.getElementById(
            "renameChatForm"
        );

    const renameCancelButton =
        document.getElementById(
            "renameChatCancel"
        );

    const renameCloseButton =
        document.getElementById(
            "renameChatClose"
        );


    if (renameForm) {

        renameForm.addEventListener(
            "submit",
            async event => {

                event.preventDefault();

                if (!renameTargetSession) {
                    return;
                }

                const input =
                    document.getElementById(
                        "renameChatInput"
                    );

                const title =
                    input
                        ? input.value
                        : "";

                const session =
                    renameTargetSession;

                closeRenameModal();

                await renameChat(
                    session,
                    title
                );
            }
        );
    }


    if (renameCancelButton) {

        renameCancelButton.addEventListener(
            "click",
            closeRenameModal
        );
    }


    if (renameCloseButton) {

        renameCloseButton.addEventListener(
            "click",
            closeRenameModal
        );
    }


    const renameModal =
        getRenameModal();

    if (renameModal) {

        renameModal.addEventListener(
            "click",
            event => {

                if (
                    event.target ===
                    renameModal
                ) {
                    closeRenameModal();
                }
            }
        );
    }


    document.addEventListener(
        "keydown",
        event => {

            if (
                event.key === "Escape"
            ) {
                closeRenameModal();
                closeAllChatMenus();
            }
        }
    );


    // =========================================
    // Delete chat
    // =========================================

    async function deleteChat(
        session
    ) {

        const confirmed =
            window.confirm(
                `Delete "${session.title || "New chat"}"?\n\nThis will permanently remove the conversation.`
            );

        if (!confirmed) {
            return;
        }

        try {

            const response =
                await fetch(
                    `/chat/sessions/${encodeURIComponent(
                        session.session_id
                    )}`,
                    {
                        method:
                            "DELETE",

                        credentials:
                            "include"
                    }
                );

            const data =
                await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                    "Failed to delete chat."
                );
            }

            const deletedCurrent =
                getSessionId() ===
                session.session_id;

            if (deletedCurrent) {

                const listResponse =
                    await fetch(
                        "/chat/sessions",
                        {
                            credentials:
                                "include",

                            cache:
                                "no-store"
                        }
                    );

                if (
                    listResponse.ok
                ) {

                    const listData =
                        await listResponse.json();

                    const remaining =
                        listData.sessions ||
                        [];

                    if (remaining.length) {

                        setSessionId(
                            remaining[0]
                                .session_id
                        );

                    } else {

                        const newResponse =
                            await fetch(
                                "/chat/sessions",
                                {
                                    method:
                                        "POST",

                                    headers: {
                                        "Content-Type":
                                            "application/json"
                                    },

                                    credentials:
                                        "include",

                                    body:
                                        JSON.stringify({})
                                }
                            );

                        const newData =
                            await newResponse.json();

                        if (
                            !newResponse.ok
                        ) {
                            throw new Error(
                                newData.detail ||
                                "Failed to create replacement chat."
                            );
                        }

                        setSessionId(
                            newData.session
                                .session_id
                        );
                    }

                    await loadConversationHistory(
                        getSessionId()
                    );
                }
            }

            await loadRecentChats();

            questionInput.focus();

        } catch (error) {

            console.error(
                "Delete chat error:",
                error
            );

            alert(
                `Couldn't delete the chat. ${error.message}`
            );
        }
    }


    // =========================================
    // Send question
    // =========================================

    chatForm.addEventListener(
        "submit",
        async event => {

            event.preventDefault();

            const question =
                questionInput.value.trim();

            if (!question) {
                return;
            }

            const sessionId =
                getSessionId();

            addMessage(
                question,
                "user"
            );

            questionInput.value =
                "";

            sendButton.disabled =
                true;

            sendButton.setAttribute(
                "aria-label",
                "Thinking..."
            );

            sendButton.title =
                "Thinking...";

            showThinkingIndicator();

            try {

                const response =
                    await fetch(
                        "/ask",
                        {
                            method:
                                "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            credentials:
                                "include",

                            body:
                                JSON.stringify({
                                    question:
                                        question,

                                    session_id:
                                        sessionId
                                })
                        }
                    );

                const data =
                    await response.json();

                if (!response.ok) {

                    throw new Error(
                        data.detail ||
                        "Failed to get an answer."
                    );
                }

                hideThinkingIndicator();

                addMessage(
                    data.answer,
                    "assistant",
                    data.sources || []
                );

                await loadRecentChats();

            } catch (error) {

                hideThinkingIndicator();

                console.error(
                    "Chat error:",
                    error
                );

                addMessage(
                    `Sorry, I couldn't answer that question. ${error.message}`,
                    "assistant"
                );

            } finally {

                sendButton.disabled =
                    false;

                sendButton.setAttribute(
                    "aria-label",
                    "Send message"
                );

                sendButton.title =
                    "Send message";

                questionInput.focus();
            }
        }
    );


    // =========================================
    // Voice interaction
    // =========================================

    const voiceButton =
        document.getElementById(
            "voiceButton"
        );

    const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;

    let recognition = null;
    let isListening = false;


    if (
        SpeechRecognition &&
        voiceButton
    ) {

        recognition =
            new SpeechRecognition();

        recognition.continuous =
            false;

        recognition.interimResults =
            true;

        recognition.lang =
            "en-US";


        recognition.onstart = () => {

            isListening =
                true;

            voiceButton.classList.add(
                "listening"
            );

            voiceButton.classList.add(
                "recording"
            );

            voiceButton.title =
                "Stop listening";

            questionInput.placeholder =
                "Listening... speak your question";
        };


        recognition.onresult =
            event => {

                let transcript =
                    "";

                for (
                    let i =
                        event.resultIndex;
                    i <
                        event.results.length;
                    i++
                ) {

                    transcript +=
                        event.results[i][0]
                            .transcript;
                }

                questionInput.value =
                    transcript;
            };


        recognition.onerror =
            event => {

                console.error(
                    "Speech recognition error:",
                    event.error
                );

                if (
                    event.error ===
                    "not-allowed"
                ) {

                    addMessage(
                        "Microphone access was blocked. Please allow microphone access in your browser and try again.",
                        "assistant"
                    );

                } else if (
                    event.error !==
                    "aborted"
                ) {

                    addMessage(
                        "I couldn't hear that clearly. Please try again.",
                        "assistant"
                    );
                }
            };


        recognition.onend = () => {

            isListening =
                false;

            voiceButton.classList.remove(
                "listening"
            );

            voiceButton.classList.remove(
                "recording"
            );

            voiceButton.title =
                "Speak your question";

            questionInput.placeholder =
                "Ask a question about your study material...";

            questionInput.focus();

            if (
                questionInput.value.trim()
            ) {
                chatForm.requestSubmit();
            }
        };


        voiceButton.addEventListener(
            "click",
            () => {

                if (isListening) {

                    recognition.stop();

                    return;
                }

                questionInput.value =
                    "";

                try {

                    recognition.start();

                } catch (error) {

                    console.error(
                        "Could not start speech recognition:",
                        error
                    );
                }
            }
        );

    } else if (voiceButton) {

        voiceButton.disabled =
            true;

        voiceButton.title =
            "Voice recognition is not supported by this browser";

        console.warn(
            "Speech Recognition API is not supported by this browser."
        );
    }


    // =========================================
    // Initialisation
    // =========================================

    async function initializeChat() {

        const registered =
            await registerCurrentSession();

        if (!registered) {
            return;
        }

        const sessionId =
            getSessionId();

        await loadConversationHistory(
            sessionId
        );

        await loadRecentChats();

        questionInput.focus();
    }

    initializeChat();
// =========================================
// Scroll to bottom
// =========================================

function isChatAtBottom() {
    if (!chatMessages) {
        return true;
    }

    const distanceFromBottom =
        chatMessages.scrollHeight -
        chatMessages.scrollTop -
        chatMessages.clientHeight;

    return distanceFromBottom < 80;
}

function updateScrollToBottomButton() {
    if (!scrollToBottomButton || !chatMessages) {
        return;
    }

    if (isChatAtBottom()) {
        scrollToBottomButton.classList.remove("visible");
    } else {
        scrollToBottomButton.classList.add("visible");
    }
}

function scrollChatToBottom(smooth = true) {
    if (!chatMessages) {
        return;
    }

    chatMessages.scrollTo({
        top: chatMessages.scrollHeight,
        behavior: smooth ? "smooth" : "auto"
    });

    updateScrollToBottomButton();
}

if (chatMessages) {
    chatMessages.addEventListener(
        "scroll",
        updateScrollToBottomButton,
        { passive: true }
    );
}

if (scrollToBottomButton) {
    scrollToBottomButton.addEventListener(
        "click",
        () => {
            scrollChatToBottom(true);
        }
    );
}
// =========================================
// Account-based collapsible sidebar
// =========================================

async function loadSidebarPreference() {
    if (!chatContainer) {
        return;
    }

    try {
        const response = await fetch("/auth/me");

        if (!response.ok) {
            return;
        }

        const data = await response.json();

        const collapsed =
            Boolean(data.user?.sidebar_collapsed);

        applySidebarState(collapsed);
    } catch (error) {
        console.error(
            "Failed to load sidebar preference:",
            error
        );
    }
}

function applySidebarState(collapsed) {
    if (!chatContainer) {
        return;
    }

    chatContainer.classList.toggle(
        "sidebar-collapsed",
        collapsed
    );

    if (sidebarToggle) {
        sidebarToggle.setAttribute(
            "aria-label",
            collapsed
                ? "Expand sidebar"
                : "Collapse sidebar"
        );

        sidebarToggle.setAttribute(
            "title",
            collapsed
                ? "Expand sidebar"
                : "Collapse sidebar"
        );
    }
}

async function saveSidebarPreference(collapsed) {
    try {
        const response = await fetch(
            "/auth/sidebar",
            {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    collapsed: collapsed
                })
            }
        );

        if (!response.ok) {
            throw new Error(
                `Sidebar preference failed: ${response.status}`
            );
        }
    } catch (error) {
        console.error(
            "Failed to save sidebar preference:",
            error
        );
    }
}

if (sidebarToggle) {
    sidebarToggle.addEventListener(
        "click",
        async () => {

            const collapsed =
                !chatContainer.classList.contains(
                    "sidebar-collapsed"
                );

            applySidebarState(collapsed);

            await saveSidebarPreference(
                collapsed
            );
        }
    );
}

loadSidebarPreference();

});
