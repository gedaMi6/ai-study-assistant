/*
 * AI Study Assistant - Mobile Navigation
 * Handles the shared sidebar on phones.
 */

(function () {
    const sidebar = document.querySelector(".sidebar");

    // Admin has its own navigation system.
    if (!sidebar) return;

    // Create overlay.
    const overlay = document.createElement("div");
    overlay.className = "mobile-sidebar-overlay";
    overlay.setAttribute("aria-hidden", "true");

    // Create menu button.
    const menuButton = document.createElement("button");
    menuButton.className = "mobile-menu-button";
    menuButton.type = "button";
    menuButton.setAttribute("aria-label", "Open navigation");
    menuButton.setAttribute("aria-expanded", "false");

    menuButton.innerHTML = `
        <span></span>
        <span></span>
        <span></span>
    `;

    document.body.appendChild(overlay);
    document.body.appendChild(menuButton);

    function openMenu() {
        sidebar.classList.add("mobile-open");
        overlay.classList.add("show");

        menuButton.classList.add("active");
        menuButton.setAttribute("aria-expanded", "true");
        menuButton.setAttribute("aria-label", "Close navigation");

        document.body.classList.add("mobile-menu-open");
    }

    function closeMenu() {
        sidebar.classList.remove("mobile-open");
        overlay.classList.remove("show");

        menuButton.classList.remove("active");
        menuButton.setAttribute("aria-expanded", "false");
        menuButton.setAttribute("aria-label", "Open navigation");

        document.body.classList.remove("mobile-menu-open");
    }

    menuButton.addEventListener("click", function () {
        if (sidebar.classList.contains("mobile-open")) {
            closeMenu();
        } else {
            openMenu();
        }
    });

    overlay.addEventListener("click", closeMenu);

    // Close after selecting a navigation item.
    sidebar.querySelectorAll("a.nav-item").forEach(function (link) {
        link.addEventListener("click", closeMenu);
    });

    // Escape closes the menu.
    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeMenu();
        }
    });

    // Reset when returning to desktop.
    window.addEventListener("resize", function () {
        if (window.innerWidth > 650) {
            closeMenu();
        }
    });
})();
