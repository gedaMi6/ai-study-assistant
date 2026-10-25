/*
 * KANIA.AI - Tab-specific authentication
 *
 * Each browser tab keeps its own authentication session in sessionStorage.
 * The session ID is sent to the backend through X-Study-Session.
 */

(function () {
    const AUTH_KEY = "study_assistant_auth_session";
    const originalFetch = window.fetch.bind(window);

    window.fetch = function (input, init = {}) {
        const sessionId = sessionStorage.getItem(AUTH_KEY);

        if (!sessionId) {
            return originalFetch(input, init);
        }

        const options = { ...init };
        const headers = new Headers(options.headers || {});

        headers.set("X-Study-Session", sessionId);

        options.headers = headers;

        return originalFetch(input, options);
    };
})();
