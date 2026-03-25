/**
 * LITFLICK - CORE APPLICATION SCRIPT
 * ---------------------------------
 * This script handles data fetching, user authentication, 
 * UI rendering (Carousel & Grid), and profile management.
 */

// --- 1. CONFIGURATION & CONSTANTS ---
const API_URL = "http://localhost:5000/api";
const TMDB_BASE = "https://image.tmdb.org/t/p/w500";     // Standard poster size
const TMDB_HD = "https://image.tmdb.org/t/p/original";  // High-def backdrop/poster

// --- 2. GLOBAL STATE ---
let currentTab = "movies";    // Tracks if we are viewing 'movies', 'books', or 'recommendations'
let allData = [];             // Stores the list of items for the current active tab
let isLoginMode = true;       // Toggle for the Auth Modal (Login vs Register)
let currentSlide = 0;         // Tracks current position in the Hero Carousel
let slidesData = [];          // Stores the top 5 items currently shown in the Carousel
let currentUser = null;       // Stores the logged-in user object
let currentPage = 1; // Tracks the current page of results

// --- 3. INITIALIZATION ---
/**
 * Runs when the browser window finishes loading.
 * Initializes the Auth check and sets the default view to 'movies'.
 */
window.onload = () => {
    const searchInput = document.getElementById("searchInput");
    const clearBtn = document.getElementById("clearSearch");

    // Hide the "x" button and clear input on page refresh to ensure a clean UI
    if (searchInput) searchInput.value = "";
    if (clearBtn) clearBtn.style.display = "none";

    checkAuth();
    switchTab('movies');
};

// --- 4. AUTHENTICATION LOGIC ---

/**
 * Verifies if a JWT token exists in LocalStorage and validates it with the backend.
 */
async function checkAuth() {
    const token = localStorage.getItem("token");
    if (token) {
        try {
            const res = await fetch(`${API_URL}/auth/verify`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            const data = await res.json();
            if (data.valid) {
                currentUser = data.user;
                updateUIForLoggedInUser(data.user);
            }
        } catch (e) {
            // If verification fails, clear the invalid token
            localStorage.removeItem("token");
        }
    }
}

/**
 * Updates the Navbar and UI elements once a user is authenticated.
 */
function updateUIForLoggedInUser(user) {
    const userInfo = document.getElementById("userInfo");
    const usernameSpan = document.getElementById("username");

    // Display user avatar and name with a link to the profile
    usernameSpan.innerHTML = `
        <div class="user-profile-link" onclick="showProfile()" style="cursor:pointer; display:flex; align-items:center; gap:8px;">
            <img src="${user.avatar_url || 'https://cdn-icons-png.flaticon.com/512/1144/1144760.png'}" 
                alt="avatar" class="nav-avatar" id="navAvatar">
            ${user.username}
        </div>
    `;

    // Toggle button visibility
    userInfo.style.display = "flex";
    document.getElementById("loginBtn").style.display = "none";
    document.getElementById("registerBtn").style.display = "none";
    document.getElementById("logoutBtn").style.display = "block";
}

/**
 * Handles form submission for both Login and Register actions.
 */
async function handleAuth(e) {
    e.preventDefault(); // Stop page reload
    const endpoint = isLoginMode ? "login" : "register";

    const payload = {
        username: document.getElementById("authUsername").value,
        password: document.getElementById("authPassword").value
    };

    // Add email to payload if we are in Register mode
    if (!isLoginMode) payload.email = document.getElementById("email").value;

    const res = await fetch(`${API_URL}/auth/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (res.ok) {
        localStorage.setItem("token", data.token);
        location.reload(); // Refresh to apply changes
    } else {
        alert(data.error);
    }
}

// --- 5. DATA LOADING & RECOMMENDATIONS ---

/**
 * Fetches data from the API with pagination support.
 * @param {string} type - 'movies' or 'books'
 * @param {boolean} append - If true, adds new results to the existing ones
 */
async function loadData(type, append = false) {
    const contentDiv = document.getElementById("content");
    const statsDiv = document.getElementById("stats");

    try {
        // We add the 'page' parameter to get different results from the API
        const res = await fetch(`${API_URL}/${type}/?page=${currentPage}`);
        const data = await res.json();
        const newData = data[type] || [];

        // If 'append' is true, we combine lists; otherwise, we replace it
        if (append) {
            allData = [...allData, ...newData];
        } else {
            allData = newData;
        }

        // Shuffle the results so they don't always appear in the same order
        allData.sort(() => Math.random() - 0.5);

        if (!append) setupCarousel(allData, type);
        renderGrid(allData, type);

        if (statsDiv) statsDiv.innerHTML = `Explored <span>${allData.length}</span> ${type}`;
    } catch (error) {
        console.error("Connection error:", error);
    }
}

/**
 * Fetches personalized recommendations using the user's token.
 */
async function loadRecommendations() {
    const contentDiv = document.getElementById("content");
    const token = localStorage.getItem("token");

    // Redirect or show message if not logged in
    if (!currentUser || !token) {
        contentDiv.innerHTML = `
        <div class="auth-cta-container">
            <div class="auth-cta-icon">✨</div>
            <h2>Unlock Your <br><span>Recommendations</span></h2>
            <p>Login to see a curated list of movies and books based on your personal taste.</p>
            
            <button class="btn-cta-login" onclick="showLoginModal()">Login Now</button>
        </div>`;
        return;
    }

    contentDiv.innerHTML = "<div class='loading'>Curating your personal library and cinema...</div>";

    try {
        // Fetch movies and books recommendations in parallel
        const [resMovies, resBooks] = await Promise.all([
            fetch(`${API_URL}/recommendations/movies`, { headers: { Authorization: `Bearer ${token}` } }),
            fetch(`${API_URL}/recommendations/books`, { headers: { Authorization: `Bearer ${token}` } })
        ]);

        const dataMovies = await resMovies.json();
        const dataBooks = await resBooks.json();

        let combinedRecs = [];
        if (resMovies.ok && dataMovies.recommendations) combinedRecs = [...combinedRecs, ...dataMovies.recommendations];
        if (resBooks.ok && dataBooks.recommendations) combinedRecs = [...combinedRecs, ...dataBooks.recommendations];

        if (combinedRecs.length > 0) {
            // Shuffle mix for variety
            combinedRecs.sort(() => Math.random() - 0.5);
            renderGrid(combinedRecs, 'recommendations');
            document.getElementById("stats").innerHTML = `Here are the <span>${combinedRecs.length}</span> best Movies and Books recommendations for you!`;
        } else {
            contentDiv.innerHTML = `
                <div style="text-align:center; padding:50px; opacity:0.7;">
                <h3>Your feed is empty</h3>
                <p style="margin-top:10px;">Rate a few more movies and books so we can find what you love!</p>
                </div>`;
        }
    } catch (e) {
        console.error("Recommendation fetch failed:", e);
        contentDiv.innerHTML = "<div class='loading'>Error connecting to the recommendation engine.</div>";
    }
}

// --- 6. RENDERING LOGIC (GRID & CAROUSEL) ---

/**
 * Generates the HTML grid of cards for movies and books.
 */
/**
 * Renders the main content grid.
 * Uses a Progressive Loading strategy: shows low-res first, then upgrades to HD
 * only if it's a real image (not Google's 128px "No Image" placeholder).
 */
function renderGrid(data, type) {
    const contentDiv = document.getElementById("content");

    if (!data || data.length === 0) {
        contentDiv.innerHTML = "<p style='text-align:center; padding:20px; opacity:0.5;'>No results found.</p>";
        return;
    }

    // 1. Generate the HTML structure
    contentDiv.innerHTML = data.map(item => {
        const isBook = !!item.authors;
        const itemType = isBook ? 'books' : 'movies';

        // Define original thumbnail (safe) and potential HD version
        const originalThumb = (item.thumbnail || item.image_url || "").replace('http://', 'https://');
        let hdImg = isBook ? originalThumb.replace('zoom=1', 'zoom=0') : `${TMDB_BASE}${item.poster_path}`;

        const placeholder = 'https://placehold.jp/24/1b2432/ffffff/500x750.png?text=No+Cover';

        // Determine the starting image (Always start with the reliable original thumb for books)
        let startingImg = originalThumb || placeholder;
        if (!isBook && item.poster_path) startingImg = `${TMDB_BASE}${item.poster_path}`;

        return `
        <div class="card">
            <div class="card-image-container">
                <span class="rating-badge">★ ${item.rating ? Number(item.rating).toFixed(1) : '0.0'}</span>
                <img src="${startingImg}" 
                    id="img-${itemType}-${item.id}" 
                    alt="${item.title}" 
                    onerror="this.onerror=null; this.src='${placeholder}';">
            </div>
            <div class="card-content">
                <h3>${item.title}</h3>
                <p style="font-size:0.75rem; opacity:0.5; margin-bottom: 10px;">
                    ${item.release_year || item.authors || item.year || ''}
                </p>
                <div id="rating-${itemType}-${item.id}" class="rating-section">
                    <span class="loading-stars" style="font-size: 0.7rem; opacity: 0.5;">Loading rating...</span>
                </div>
            </div>
        </div>
        `;
    }).join('');

    // 2. Post-rendering logic: Ratings and HD Upgrade
    data.forEach(item => {
        const isBook = !!item.authors;
        const itemType = isBook ? 'books' : 'movies';

        // --- PROGRESIVE HD UPGRADE (The Gatekeeper) ---
        if (isBook && item.thumbnail) {
            const originalThumb = item.thumbnail.replace('http://', 'https://');
            const hdImg = originalThumb.replace('zoom=1', 'zoom=0');

            // Create a background probe to check HD dimensions
            const probe = new Image();
            probe.src = hdImg;
            probe.onload = function () {
                // If width > 130px, it's a real cover. If it's 128px, it's Google's error box.
                if (this.naturalWidth > 130) {
                    const imgInDOM = document.getElementById(`img-${itemType}-${item.id}`);
                    if (imgInDOM) imgInDOM.src = hdImg; // Silent swap to high resolution
                }
            };
        }

        // Load star ratings
        loadRatingForItem(itemType, item.id);
    });
}

/**
 * Configures the Hero Carousel.
 * This version is cleaned of all "comment" text and uses smart truncation.
 */
function setupCarousel(data, type) {
    const container = document.getElementById("carouselContainer");
    const dotsContainer = document.getElementById("carouselDots");
    if (!container || !dotsContainer) return;

    // Use the top 5 items for the spotlight
    slidesData = data.slice(0, 5);
    container.innerHTML = "";
    dotsContainer.innerHTML = "";
    currentSlide = 0;

    slidesData.forEach((item, index) => {
        // --- SMART TRUNCATION ---
        // We cut the text at 160 characters but ensure we don't break a word.
        const maxLength = 160;
        const description = item.description || "No description available.";



        // 1. Force lowercase first, then handle truncation
        // This bypasses any "All-Caps" data coming from the backend
        let cleanDescription = description.toLowerCase();

        if (cleanDescription.length > maxLength) {
            cleanDescription = cleanDescription.substring(0, maxLength).split(" ").slice(0, -1).join(" ") + "...";
        }

        // 2. Capitalize ONLY the first letter for a professional look
        cleanDescription = cleanDescription.charAt(0).toUpperCase() + cleanDescription.slice(1);

        // --- IMAGE LOGIC ---
        const rawThumb = (item.thumbnail || item.image_url || '').replace('http://', 'https://');
        let hdBgUrl = type === 'movies' ? `${TMDB_HD}${item.poster_path}` : rawThumb.replace('zoom=1', 'zoom=2');

        const slide = document.createElement("div");
        slide.className = "slide";
        slide.style.backgroundImage = `url('${rawThumb}')`;

        // Progressive background upgrade (Gatekeeper logic)
        const imgLoader = new Image();
        imgLoader.src = hdBgUrl;
        imgLoader.onload = function () {
            if (this.naturalWidth > 130) slide.style.backgroundImage = `url('${hdBgUrl}')`;
        };

        // --- CLEAN HTML TEMPLATE ---
        // Ensure no extra text or comments are inside the template string.
        // --- Inside your setupCarousel loop ---
        slide.innerHTML = `
            <div class="slide-content">
                <span class="slide-tag">${type.toUpperCase()} SPOTLIGHT | ★ ${item.rating ? item.rating.toFixed(1) : '0.0'}</span>
                <h2>${item.title}</h2>
                <p class="slide-desc" style="text-transform: none !important; font-variant: normal !important; text-transform: lowercase; display: block;">
                    ${cleanDescription}
                </p>
                <button class="btn-purple" style="margin-top: 20px; padding: 10px 25px;">Watch Now</button>
            </div>
        `;
        container.appendChild(slide);

        // --- DOTS GENERATION ---
        const dot = document.createElement("div");
        dot.className = `dot ${index === 0 ? 'active' : ''}`;
        dot.onclick = () => goToSlide(index);
        dotsContainer.appendChild(dot);
    });

    updateCarouselUI();
}

/**
 * Updates the visual position of the carousel.
 */
function updateCarouselUI() {
    const container = document.getElementById("carouselContainer");
    if (container) {
        container.style.transform = `translateX(-${currentSlide * 100}%)`;
    }
    document.querySelectorAll(".dot").forEach((dot, idx) => {
        dot.classList.toggle("active", idx === currentSlide);
    });
}

function goToSlide(index) {
    currentSlide = index;
    updateCarouselUI();
}

function moveCarousel(dir) {
    if (slidesData.length === 0) return;
    currentSlide = (currentSlide + dir + slidesData.length) % slidesData.length;
    updateCarouselUI();
}

/**
 * Navigates between Movies, Books, and Recommendations tabs.
 */
function switchTab(tab) {
    currentTab = tab;

    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Cambia esto de "Loading..." a "" para que no se vea el texto
    document.getElementById("stats").innerHTML = "";

    document.getElementById("heroCarousel").style.display = (tab === 'recommendations') ? 'none' : 'block';

    if (tab === 'recommendations') {
        loadRecommendations();
    } else {
        loadData(tab);
    }
}

// --- 7. INTERACTIVE FEATURES (RATINGS & SEARCH) ---

/**
 * Fetches and renders the star rating (average + user's specific rating).
 */
async function loadRatingForItem(type, id) {
    const token = localStorage.getItem("token");
    const container = document.getElementById(`rating-${type}-${id}`);
    if (!container) return;

    try {
        const res = await fetch(`${API_URL}/ratings/${type}/${id}`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {}
        });

        if (res.ok) {
            const data = await res.json();
            let starsHtml = `<div class="star-rating">`;

            for (let i = 1; i <= 5; i++) {
                const isFilled = data.your_rating && i <= data.your_rating;
                const color = isFilled ? '#ffd700' : '#444';

                starsHtml += `
            <span class="star ${isFilled ? 'filled' : ''}" 
                style="color: ${color}; cursor: pointer; font-size: 1.2rem;"
                onclick="rateItem('${type}', ${id}, ${i})">★</span>`;
            }
            starsHtml += `</div>`;

            if (data.your_rating) {
                starsHtml += `<span class="your-rating-badge" style="font-size: 0.7rem; color: #c3f73a; display: block; margin-top: 5px;">
                        Your rating: ${data.your_rating}/5
                    </span>`;
            }
            container.innerHTML = starsHtml;
        }
    } catch (e) {
        console.error("Star loading failed:", e);
    }
}

/**
 * Submits a new star rating to the backend.
 */
async function rateItem(type, id, val) {
    const token = localStorage.getItem("token");
    if (!token) return showLoginModal();

    try {
        const res = await fetch(`${API_URL}/ratings/${type}/${id}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`
            },
            body: JSON.stringify({ rating: val })
        });

        if (res.ok) {
            await loadRatingForItem(type, id);
        } else {
            const errorData = await res.json();
            alert("Rating failed: " + errorData.error);
        }
    } catch (e) {
        console.error("Rating submission error:", e);
    }

    // Refresh recommendations if the user rates something in that tab
    if (currentTab === 'recommendations') {
        setTimeout(() => loadRecommendations(), 500);
    }
}

/**
 * Unified search function for Desktop and Mobile.
 * @param {boolean} isMobile - Set to true when calling from the hamburger menu.
 */
function handleSearch(isMobile = false) {
    // 1. Identify which input to read from
    const inputId = isMobile ? "searchInputMobile" : "searchInput";
    const input = document.getElementById(inputId);
    
    // 2. Safety check: if input doesn't exist, stop
    if (!input) return;

    const q = input.value.toLowerCase();

    // 3. Handle the "X" (clear) button visibility
    const clearBtnId = isMobile ? "clearSearchMobile" : "clearSearch";
    const clearBtn = document.getElementById(clearBtnId);
    if (clearBtn) {
        clearBtn.style.display = q.length > 0 ? "block" : "none";
    }

    /** * 4. FILTERING LOGIC
     * We removed "isValidURL(d)" because it was causing a ReferenceError.
     * We only filter by title.
     */
    const filtered = allData.filter(item => {
        const titleMatch = item.title && item.title.toLowerCase().includes(q);
        return titleMatch;
    });

    // 5. Update the UI with filtered results
    renderGrid(filtered, currentTab);
}

/**
 * Unified clear search function.
 */
function clearSearchInput(isMobile = false) {
    const inputId = isMobile ? "searchInputMobile" : "searchInput";
    const input = document.getElementById(inputId);
    
    if (input) {
        input.value = "";
        
        // Hide clear button
        const clearBtnId = isMobile ? "clearSearchMobile" : "clearSearch";
        const clearBtn = document.getElementById(clearBtnId);
        if (clearBtn) clearBtn.style.display = "none";
    }

    // Reset grid to show all data
    renderGrid(allData, currentTab);
    if (input) input.focus();
}

// --- 8. UI HELPERS & MODALS ---

function showLoginModal() { isLoginMode = true; updateModalUI(); document.getElementById("loginModal").classList.add("active"); }
function showRegisterModal() { isLoginMode = false; updateModalUI(); document.getElementById("loginModal").classList.add("active"); }
function toggleAuthMode() { isLoginMode = !isLoginMode; updateModalUI(); }

function updateModalUI() {
    document.getElementById("modalTitle").textContent = isLoginMode ? "Login" : "Register";
    document.getElementById("emailGroup").classList.toggle("hidden", isLoginMode);
}

function logout() { document.getElementById("logoutModal").classList.add("active"); }
function closeLogoutModal() { document.getElementById("logoutModal").classList.remove("active"); }

function confirmLogout() {
    localStorage.removeItem("token");
    currentUser = null;
    location.reload();
}

function closeModal() { document.getElementById("loginModal").classList.remove("active"); }

// Close modal if user clicks outside of it
window.onclick = function (event) {
    const modal = document.getElementById("loginModal");
    if (event.target == modal) closeModal();
}

// --- 9. PROFILE MANAGEMENT ---

/**
 * Renders the Profile Settings view inside the main content area.
 */
function showProfile() {
    if (!currentUser) return;

    document.getElementById("heroCarousel").style.display = 'none';
    document.getElementById("stats").innerHTML = "User Settings";

    const contentDiv = document.getElementById("content");
    contentDiv.innerHTML = `
        <div class="profile-container" style="max-width: 600px; margin: 0 auto; padding: 40px; background: #1b2432; border-radius: 20px; grid-column: 1 / -1;">
            <div style="text-align:center; margin-bottom: 30px;">
                <div style="position: relative; display: inline-block;">
                    <img src="${currentUser.avatar_url || 'https://cdn-icons-png.flaticon.com/512/1144/1144760.png'}" 
                        id="profilePageAvatar" 
                        style="width:150px; height:150px; border-radius:50%; object-fit:cover; border: 3px solid #a855f7;">
                    <label for="avatarInput" style="position:absolute; bottom:5px; right:5px; background:#a855f7; padding:8px; border-radius:50%; cursor:pointer;">📸</label>
                    <input type="file" id="avatarInput" accept="image/*" style="display:none;" onchange="uploadAvatar(event)">
                </div>
            </div>

            <form id="editProfileForm" onsubmit="updateUserData(event)" style="display: flex; flex-direction: column; gap: 15px;">
                <div class="input-group">
                    <label style="display:block; font-size: 0.8rem; opacity: 0.6; margin-bottom: 5px;">Username</label>
                    <input type="text" id="editUsername" value="${currentUser.username}" class="profile-input">
                </div>
                <div class="input-group">
                    <label style="display:block; font-size: 0.8rem; opacity: 0.6; margin-bottom: 5px;">Email</label>
                    <input type="email" id="editEmail" value="${currentUser.email || ''}" class="profile-input">
                </div>
                <div class="input-group">
                    <label style="display:block; font-size: 0.8rem; opacity: 0.6; margin-bottom: 5px;">New Password (leave blank to keep current)</label>
                    <input type="password" id="editPassword" placeholder="********" class="profile-input">
                </div>
                
                <div style="display: flex; gap: 10px; margin-top: 20px;">
                    <button type="submit" class="btn-purple" style="flex: 1;">Save Changes</button>
                    <button type="button" class="btn-outline" onclick="switchTab('movies')" style="flex: 1;">Cancel</button>
                </div>
            </form>
        </div>
    `;
}

/**
 * Handles avatar image upload to the server.
 */
async function uploadAvatar(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Preview image locally immediately
    const reader = new FileReader();
    reader.onload = function (e) {
        document.getElementById("profilePageAvatar").src = e.target.result;
        document.getElementById("navAvatar").src = e.target.result;
    }
    reader.readAsDataURL(file);

    // Prepare multipart form data
    const formData = new FormData();
    formData.append("avatar", file);

    const token = localStorage.getItem("token");
    try {
        const res = await fetch(`${API_URL}/auth/upload-avatar`, {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` },
            body: formData
        });

        if (res.ok) {
            const data = await res.json();
            currentUser.avatar_url = data.avatar_url;
            alert("Avatar updated successfully!");
        }
    } catch (e) {
        console.error("Upload failed", e);
    }
}

/**
 * Updates user credentials (username, email, password).
 */
async function updateUserData(e) {
    e.preventDefault();
    const token = localStorage.getItem("token");

    const updatedData = {
        username: document.getElementById("editUsername").value,
        email: document.getElementById("editEmail").value,
        password: document.getElementById("editPassword").value
    };

    try {
        const res = await fetch(`${API_URL}/auth/update`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`
            },
            body: JSON.stringify(updatedData)
        });

        if (res.ok) {
            alert("Profile updated!");
            location.reload(); // Refresh to show new name in Navbar
        } else {
            const data = await res.json();
            alert("Update Error: " + data.error);
        }
    } catch (error) {
        console.error("Connection failed during update:", error);
        switchTab('movies');
    }
}


/**
 * Toggles the mobile navigation menu.
 */
function toggleMobileMenu() {
    const nav = document.querySelector(".header-right");
    const hamburger = document.getElementById("hamburger");
    
    nav.classList.toggle("active");
    hamburger.classList.toggle("open");
}

/**
 * Enhanced switchTab to also close the mobile menu
 */
const originalSwitchTab = switchTab; // Save original
switchTab = function(tab) {
    originalSwitchTab(tab);
    
    // Close mobile menu if open
    const nav = document.querySelector(".header-right");
    const hamburger = document.getElementById("hamburger");
    if (nav.classList.contains("active")) {
        toggleMobileMenu();
    }
}

/**
 * Close menu when clicking outside
 */
document.addEventListener('click', (e) => {
    const nav = document.querySelector(".header-right");
    const hamburger = document.getElementById("hamburger");
    
    if (nav.classList.contains("active") && 
        !nav.contains(e.target) && 
        !hamburger.contains(e.target)) {
        toggleMobileMenu();
    }
});