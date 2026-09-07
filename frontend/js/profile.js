async function loadCurrentUserProfile() {
    const avatar = document.getElementById("userAvatar");

    if (!avatar) {
        console.warn("userAvatar element not found");
        return;
    }

    try {
        const response = await fetch("/auth/me", {
            credentials: "include",
            cache: "no-store"
        });

        if (!response.ok) {
            console.error("Failed to load user:", response.status);
            return;
        }

        const data = await response.json();
        const user = data.user;

        console.log("Current user:", user);

        if (user.profile_image) {
            console.log("Loading profile image:", user.profile_image);

            avatar.classList.add("has-image");

            const img = document.createElement("img");
            img.src = user.profile_image + "?t=" + Date.now();
            img.alt = user.name || "Profile";
            img.style.width = "100%";
            img.style.height = "100%";
            img.style.objectFit = "cover";
            img.style.display = "block";

            img.onload = () => {
                console.log("Profile image loaded successfully");
            };

            img.onerror = () => {
                console.error("Profile image failed to load:", img.src);
            };

            avatar.innerHTML = "";
            avatar.appendChild(img);

        } else {
            console.log("No profile image, using initial");

            avatar.classList.remove("has-image");
            avatar.textContent = user.name
                ? user.name.trim().charAt(0).toUpperCase()
                : "U";
        }

    } catch (error) {
        console.error("Profile loading error:", error);
    }
}

document.addEventListener("DOMContentLoaded", loadCurrentUserProfile);

