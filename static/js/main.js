// Toggle the user dropdown menu
function toggleDropdown() {
    const menu = document.getElementById("userDropdown");
    menu.classList.toggle("show");
}

// Close dropdown when clicking outside of it
window.addEventListener("click", function (event) {
    const dropdown = document.querySelector(".dropdown");
    const menu = document.getElementById("userDropdown");
    if (dropdown && menu && !dropdown.contains(event.target)) {
        menu.classList.remove("show");
    }
});

// Dark mode toggle (persists via localStorage)
function toggleDarkMode() {
    document.body.classList.toggle("dark-mode");
    const isDark = document.body.classList.contains("dark-mode");
    localStorage.setItem("sahabat-dark-mode", isDark ? "1" : "0");
}

// Apply saved dark mode preference on page load
(function () {
    const saved = localStorage.getItem("sahabat-dark-mode");
    if (saved === "1") {
        document.body.classList.add("dark-mode");
    }
})();
