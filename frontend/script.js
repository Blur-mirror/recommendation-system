/**
 * LITFLICK - CORE APPLICATION SCRIPT
 * ---------------------------------
 * This script handles data fetching, user authentication,
 * UI rendering (Carousel & Grid), and profile management.
 */

// --- 1. CONFIGURATION & CONSTANTS ---
const API_URL = "/api"; //removed harcocded localhost to allow relative path for deployment flexibility
const TMDB_BASE = "https://image.tmdb.org/t/p/w500"; // Standard poster size
const TMDB_HD = "https://image.tmdb.org/t/p/original"; // High-def backdrop/poster

// --- 2. GLOBAL STATE ---
let currentTab = "movies"; // Tracks if we are viewing 'movies', 'books', or 'recommendations'
let allData = []; // Stores the list of items for the current active tab
let isLoginMode = true; // Toggle for the Auth Modal (Login vs Register)
let currentSlide = 0; // Tracks current position in the Hero Carousel
let slidesData = []; // Stores the top 5 items currently shown in the Carousel
let currentUser = null; // Stores the logged-in user object
let currentPage = 1; // Tracks the current page of results

// --- 4. AUTHENTICATION LOGIC ---

/**
 * Verifies if a JWT token exists in LocalStorage and validates it with the backend.
 */
async function checkAuth() {
  const token = localStorage.getItem("token");
  if (token) {
    try {
      const res = await fetch(`${API_URL}/auth/verify`, {
        headers: { Authorization: `Bearer ${token}` },
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
        <div class="user-profile-link" onclick="goToProfile()"" style="cursor:pointer; display:flex; align-items:center; gap:8px;">
            <img src="${user.avatar_url || "https://cdn-icons-png.flaticon.com/512/1144/1144760.png"}"
                alt="avatar" class="nav-avatar" id="navAvatar">
            ${user.username}
        </div>
    `;

  // Toggle button visibility
  userInfo.style.display = "flex";
  document.getElementById("loginBtn").style.display = "none";
  document.getElementById("registerBtn").style.display = "none";
  document.getElementById("logoutBtn").style.display = "block";

  // Show admin nav link only for admins
  const adminLink = document.getElementById("adminNavLink");
  if (adminLink) adminLink.style.display = user.is_admin ? "inline" : "none";
}

/**
 * Handles form submission for both Login and Register actions.
 */
async function handleAuth(e) {
  e.preventDefault(); // Stop page reload
  const endpoint = isLoginMode ? "login" : "register";

  const payload = {
    username: document.getElementById("authUsername").value,
    password: document.getElementById("authPassword").value,
  };

  // Add email to payload if we are in Register mode
  if (!isLoginMode) payload.email = document.getElementById("email").value;

  const res = await fetch(`${API_URL}/auth/${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
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

    if (statsDiv)
      statsDiv.innerHTML = `Explored <span>${allData.length}</span> ${type}`;
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

  contentDiv.innerHTML =
    "<div class='loading'>Curating your personal library and cinema...</div>";

  try {
    // Fetch movies and books recommendations in parallel
    const [resMovies, resBooks] = await Promise.all([
      fetch(`${API_URL}/recommendations/movies`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
      fetch(`${API_URL}/recommendations/books`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
    ]);

    const dataMovies = await resMovies.json();
    const dataBooks = await resBooks.json();

    let combinedRecs = [];
    if (resMovies.ok && dataMovies.recommendations)
      combinedRecs = [...combinedRecs, ...dataMovies.recommendations];
    if (resBooks.ok && dataBooks.recommendations)
      combinedRecs = [...combinedRecs, ...dataBooks.recommendations];

    if (combinedRecs.length > 0) {
      // Shuffle mix for variety
      combinedRecs.sort(() => Math.random() - 0.5);
      renderGrid(combinedRecs, "recommendations");
      document.getElementById("stats").innerHTML =
        `Here are the <span>${combinedRecs.length}</span> best Movies and Books recommendations for you!`;
    } else {
      contentDiv.innerHTML = `
                <div style="text-align:center; padding:50px; opacity:0.7;">
                <h3>Your feed is empty</h3>
                <p style="margin-top:10px;">Rate a few more movies and books so we can find what you love!</p>
                </div>`;
    }
  } catch (e) {
    console.error("Recommendation fetch failed:", e);
    contentDiv.innerHTML =
      "<div class='loading'>Error connecting to the recommendation engine.</div>";
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
    contentDiv.innerHTML =
      "<p style='text-align:center; padding:20px; opacity:0.5;'>No results found.</p>";
    return;
  }

  // 1. Generate the HTML structure
  contentDiv.innerHTML = data
    .map((item) => {
      const isBook = !!item.authors;
      const itemType = isBook ? "books" : "movies";

      // Define original thumbnail (safe) and potential HD version
      const originalThumb = (item.thumbnail || item.image_url || "").replace(
        "http://",
        "https://",
      );
      let hdImg = isBook
        ? originalThumb.replace("zoom=1", "zoom=0")
        : `${TMDB_BASE}${item.poster_path}`;

      const placeholder =
        "https://placehold.jp/24/1b2432/ffffff/500x750.png?text=No+Cover";

      // Determine the starting image (Always start with the reliable original thumb for books)
      let startingImg = originalThumb || placeholder;
      if (!isBook && item.poster_path)
        startingImg = `${TMDB_BASE}${item.poster_path}`;

      return `
      <div class="card" onclick="showItemDetail(${JSON.stringify(item).replace(/"/g, "&quot;")}, '${itemType}')" style="cursor:pointer;">
            <div class="card-image-container">
                <span class="rating-badge">★ ${item.rating ? Number(item.rating).toFixed(1) : "0.0"}</span>
                <img src="${startingImg}"
                    id="img-${itemType}-${item.id}"
                    alt="${item.title}"
                    onerror="this.onerror=null; this.src='${placeholder}';">
            </div>
            <div class="card-content">
                <h3>${item.title}</h3>
                <p style="font-size:0.75rem; opacity:0.5; margin-bottom: 10px;">
                    ${item.release_year || item.authors || item.year || ""}
                </p>
                <div id="rating-${itemType}-${item.id}" class="rating-section">
                    <span class="loading-stars" style="font-size: 0.7rem; opacity: 0.5;">Loading rating...</span>
                </div>
            </div>
        </div>
        `;
    })
    .join("");

  // 2. Post-rendering logic: Ratings and HD Upgrade
  data.forEach((item) => {
    const isBook = !!item.authors;
    const itemType = isBook ? "books" : "movies";

    // --- PROGRESIVE HD UPGRADE (The Gatekeeper) ---
    if (isBook && item.thumbnail) {
      const originalThumb = item.thumbnail.replace("http://", "https://");
      const hdImg = originalThumb.replace("zoom=1", "zoom=0");

      // Create a background probe to check HD dimensions
      const probe = new Image();
      probe.src = hdImg;
      probe.onload = function () {
        // If width > 130px, it's a real cover. If it's 128px, it's Google's error box.
        if (this.naturalWidth > 130) {
          const imgInDOM = document.getElementById(
            `img-${itemType}-${item.id}`,
          );
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
      cleanDescription =
        cleanDescription
          .substring(0, maxLength)
          .split(" ")
          .slice(0, -1)
          .join(" ") + "...";
    }

    // 2. Capitalize ONLY the first letter for a professional look
    cleanDescription =
      cleanDescription.charAt(0).toUpperCase() + cleanDescription.slice(1);

    // --- IMAGE LOGIC ---
    const rawThumb = (item.thumbnail || item.image_url || "").replace(
      "http://",
      "https://",
    );
    let hdBgUrl =
      type === "movies"
        ? `${TMDB_HD}${item.poster_path}`
        : rawThumb.replace("zoom=1", "zoom=2");

    const slide = document.createElement("div");
    slide.className = "slide";
    slide.style.backgroundImage = `url('${rawThumb}')`;

    // Progressive background upgrade (Gatekeeper logic)
    const imgLoader = new Image();
    imgLoader.src = hdBgUrl;
    imgLoader.onload = function () {
      if (this.naturalWidth > 130)
        slide.style.backgroundImage = `url('${hdBgUrl}')`;
    };

    // --- CLEAN HTML TEMPLATE ---
    // Ensure no extra text or comments are inside the template string.
    // --- Inside your setupCarousel loop ---
    slide.innerHTML = `
            <div class="slide-content">
                <span class="slide-tag">${type.toUpperCase()} SPOTLIGHT | ★ ${item.rating ? item.rating.toFixed(1) : "0.0"}</span>
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
    dot.className = `dot ${index === 0 ? "active" : ""}`;
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
  const pages = {
    movies: "index.html",
    books: "books.html",
    recommendations: "recommendations.html",
  };
  if (pages[tab]) window.location.href = pages[tab];
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
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });

    if (res.ok) {
      const data = await res.json();
      let starsHtml = `<div class="star-rating">`;

      for (let i = 1; i <= 5; i++) {
        const isFilled = data.your_rating && i <= data.your_rating;
        const color = isFilled ? "#ffd700" : "#444";

        starsHtml += `
            <span class="star ${isFilled ? "filled" : ""}"
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
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ rating: val }),
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
  if (currentTab === "recommendations") {
    setTimeout(() => loadRecommendations(), 500);
  }
}

/**
 * Filters the current grid data based on search input.
 */
function handleSearch() {
  const input = document.getElementById("searchInput");
  const clearBtn = document.getElementById("clearSearch");
  const q = input.value.toLowerCase();

  // Show button only if there is text
  if (clearBtn) {
    clearBtn.style.display = q.length > 0 ? "block" : "none";
  }

  const filtered = allData.filter(
    (d) => d.title.toLowerCase().includes(q) && isValidURL(d),
  );
  renderGrid(filtered, currentTab);
}

function clearSearchInput() {
  const input = document.getElementById("searchInput");
  const clearBtn = document.getElementById("clearSearch");

  input.value = "";
  if (clearBtn) clearBtn.style.display = "none"; // Hide button after clear

  renderGrid(allData, currentTab);
  input.focus();
}

// --- 8. UI HELPERS & MODALS ---

function showLoginModal() {
  isLoginMode = true;
  updateModalUI();
  document.getElementById("loginModal").classList.add("active");
}
function showRegisterModal() {
  isLoginMode = false;
  updateModalUI();
  document.getElementById("loginModal").classList.add("active");
}
function toggleAuthMode() {
  isLoginMode = !isLoginMode;
  updateModalUI();
}

function updateModalUI() {
  document.getElementById("modalTitle").textContent = isLoginMode
    ? "Login"
    : "Register";
  document.getElementById("emailGroup").classList.toggle("hidden", isLoginMode);
}

function logout() {
  document.getElementById("logoutModal").classList.add("active");
}
function closeLogoutModal() {
  document.getElementById("logoutModal").classList.remove("active");
}

function confirmLogout() {
  localStorage.removeItem("token");
  currentUser = null;
  location.reload();
}

function closeModal() {
  document.getElementById("loginModal").classList.remove("active");
}

// Close modal if user clicks outside of it
window.onclick = function (event) {
  const modal = document.getElementById("loginModal");
  if (event.target == modal) closeModal();
};

// --- 9. PROFILE MANAGEMENT ---

/**
 * Handles avatar image upload to the server.
 */
async function uploadAvatar(event) {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = async function (e) {
    const base64 = e.target.result; // already a data URL

    // Preview immediately
    document.getElementById("profilePageAvatar").src = base64;
    const navAvatar = document.getElementById("navAvatar");
    if (navAvatar) navAvatar.src = base64;

    // Save to backend
    const token = localStorage.getItem("token");
    try {
      const res = await fetch(`${API_URL}/auth/upload-avatar`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ avatar: base64 }),
      });

      if (res.ok) {
        const data = await res.json();
        currentUser.avatar_url = data.avatar_url;
      } else {
        const err = await res.json();
        alert("Upload failed: " + err.error);
      }
    } catch (err) {
      console.error("Upload error:", err);
    }
  };
  reader.readAsDataURL(file);
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
    password: document.getElementById("editPassword").value,
  };

  try {
    const res = await fetch(`${API_URL}/auth/update`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(updatedData),
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
    switchTab("movies");
  }
}
// ============================================================
// LITFLICK — PROFILE & ADMIN ADDITIONS
// Paste this block at the end of script.js
// ============================================================

// --- PROFILE PAGE ---

/**
 * Renders the full user profile: stats + rated items history.
 * Replaces the old showProfile() stub. Calls:
 *   GET /api/profile/       → user info + aggregate stats
 *   GET /api/profile/ratings → every item the user has rated
 */
function goToProfile() {
  window.location.href = "profile.html";
}
async function showProfile() {
  if (!currentUser) return;

  // Hide carousel, clear stats label
  const carousel = document.getElementById("heroCarousel");
  if (carousel) carousel.style.display = "none";
  const contentDiv = document.getElementById("content");

  // Show a loading state immediately so the click feels responsive
  contentDiv.innerHTML = `
    <div class="profile-container" style="grid-column: 1 / -1;">
      <div class="loading">Loading your profile...</div>
    </div>`;

  const token = localStorage.getItem("token");

  try {
    // Fire both requests in parallel — no reason to wait on one before the other
    const [profileRes, ratingsRes] = await Promise.all([
      fetch(`${API_URL}/profile/`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
      fetch(`${API_URL}/profile/ratings`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
    ]);

    const profileData = await profileRes.json();
    const ratingsData = await ratingsRes.json();

    if (!profileRes.ok) {
      contentDiv.innerHTML = `<p style="color:red; grid-column:1/-1;">Error loading profile: ${profileData.error}</p>`;
      return;
    }

    const { user, statistics } = profileData;

    // Build the rated-items HTML. Movies and books come back separately — merge and label them.
    const allRated = [
      ...(ratingsData.movie_ratings || []).map((r) => ({
        ...r,
        kind: "movie",
      })),
      ...(ratingsData.book_ratings || []).map((r) => ({ ...r, kind: "book" })),
    ].sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at)); // newest first

    const ratedHTML =
      allRated.length === 0
        ? `<p style="opacity:0.5; text-align:center; padding: 20px;">
           You haven't rated anything yet. Start exploring!
         </p>`
        : allRated
            .map((r) => {
              // Each entry has either .movie or .book depending on kind
              const item = r.movie || r.book;
              const sub =
                r.kind === "movie"
                  ? item.release_year || ""
                  : item.authors || "";
              const stars =
                "★".repeat(r.user_rating) + "☆".repeat(5 - r.user_rating);
              const date = new Date(r.updated_at).toLocaleDateString("en-IE", {
                day: "numeric",
                month: "short",
                year: "numeric",
              });
              return `
  <div class="rated-item" style="
    display: flex; justify-content: space-between; align-items: center;
    padding: 12px 0; border-bottom: 1px solid #222;
    cursor: pointer; transition: opacity 0.15s;"
    onclick="openRatedItem(${JSON.stringify(r).replace(/"/g, "&quot;")})"
    onmouseover="this.style.opacity='0.7'"
    onmouseout="this.style.opacity='1'">
    <div>
      <span style="font-size:0.65rem; text-transform:uppercase; opacity:0.4;
        letter-spacing:1px; margin-right:8px;">${r.kind}</span>
      <span style="font-weight:600;">${item.title}</span>
      ${sub ? `<span style="font-size:0.75rem; opacity:0.5; margin-left:8px;">${sub}</span>` : ""}
      <span style="font-size:0.65rem; opacity:0.3; margin-left:8px;">→ view</span>
    </div>
    <div style="text-align:right; flex-shrink:0; margin-left:16px;">
      <div style="color:#ffd700; font-size:0.9rem;">${stars}</div>
      <div style="font-size:0.65rem; opacity:0.4; margin-top:2px;">${date}</div>
    </div>
  </div>`;
            })
            .join("");

    // Format member-since date nicely
    const memberSince = new Date(user.member_since).toLocaleDateString(
      "en-IE",
      {
        day: "numeric",
        month: "long",
        year: "numeric",
      },
    );

    contentDiv.innerHTML = `
      <div class="profile-container" style="
        max-width: 700px; margin: 0 auto; padding: 40px;
        background: #1b2432; border-radius: 20px; grid-column: 1 / -1;">

        <!-- Avatar + name -->
        <div style="text-align:center; margin-bottom: 32px;">
          <div style="position:relative; display:inline-block;">
            <img src="${currentUser.avatar_url || "https://cdn-icons-png.flaticon.com/512/1144/1144760.png"}"
              id="profilePageAvatar"
              style="width:110px; height:110px; border-radius:50%; object-fit:cover;
                border: 3px solid #a855f7;">
            <label for="avatarInput" style="
              position:absolute; bottom:4px; right:4px;
              background:#a855f7; padding:6px; border-radius:50%; cursor:pointer;
              font-size:0.8rem;"></label>
            <input type="file" id="avatarInput" accept="image/*"
              style="display:none;" onchange="uploadAvatar(event)">
          </div>
          <h2 style="margin-top:14px; margin-bottom:4px;">${user.username}</h2>
          <p style="font-size:0.75rem; opacity:0.4;">Member since ${memberSince}</p>
        </div>

        <!-- Stats row -->
        <div style="
          display: grid; grid-template-columns: repeat(4, 1fr);
          gap: 12px; margin-bottom: 32px; text-align:center;">
          ${[
            ["Total Ratings", statistics.total_ratings],
            ["Avg Rating", statistics.average_rating.toFixed(1) + " / 5"],
            ["Movies", statistics.movie_ratings],
            ["Books", statistics.book_ratings],
          ]
            .map(
              ([label, value]) => `
            <div style="background:#0f1014; border-radius:12px; padding:16px;">
              <div style="font-size:1.4rem; font-weight:700; color:#a855f7;">${value}</div>
              <div style="font-size:0.65rem; opacity:0.5; margin-top:4px; text-transform:uppercase;
                letter-spacing:1px;">${label}</div>
            </div>`,
            )
            .join("")}
        </div>

        <!-- Edit form -->
        <details style="margin-bottom: 28px;">
          <summary style="cursor:pointer; font-size:0.85rem; opacity:0.6;
            padding: 8px 0; user-select:none;">Edit account details ▸</summary>
          <form id="editProfileForm" onsubmit="updateUserData(event)"
            style="display:flex; flex-direction:column; gap:12px; margin-top:16px;">
            <input type="text" id="editUsername" value="${user.username}"
              placeholder="Username" class="profile-input">
            <input type="email" id="editEmail" value="${user.email || ""}"
              placeholder="Email" class="profile-input">
            <input type="password" id="editPassword" placeholder="New password (leave blank to keep)"
              class="profile-input">
            <div style="display:flex; gap:10px;">
              <button type="submit" class="btn-purple" style="flex:1;">Save Changes</button>
              <button type="button" class="btn-outline" onclick="switchTab('movies')"
                style="flex:1;">Cancel</button>
            </div>
          </form>
        </details>

        <!-- Rated items history -->
        <div>
          <h3 style="font-size:0.85rem; text-transform:uppercase; letter-spacing:1px;
            opacity:0.5; margin-bottom:16px;">
            Rating History (${allRated.length})
          </h3>
          ${ratedHTML}
        </div>

      </div>`;
  } catch (err) {
    console.error("Profile load error:", err);
    contentDiv.innerHTML = `
      <p style="color:red; grid-column:1/-1; text-align:center;">
        Could not load profile. Check your connection.
      </p>`;
  }
}

// --- ADMIN DASHBOARD ---

/**
 * Renders the admin dashboard. Only call this if currentUser.is_admin is true.
 * Calls:
 *   GET /api/admin/stats      → aggregate numbers
 *   GET /api/admin/users      → paginated user list
 *   GET /api/admin/activity   → recent rating activity
 */
async function showAdminDashboard() {
  window.location.hash = "admin";
  if (!currentUser || !currentUser.is_admin) {
    alert("Admin access required.");
    return;
  }

  const carousel = document.getElementById("heroCarousel");
  if (carousel) carousel.style.display = "none";
  const stats = document.getElementById("stats");
  if (stats) stats.innerHTML = "";

  const contentDiv = document.getElementById("content");
  contentDiv.innerHTML = `
    <div style="grid-column:1/-1; text-align:center; padding:40px;">
      <div class="loading">Loading admin dashboard...</div>
    </div>`;

  const token = localStorage.getItem("token");

  try {
    const [statsRes, usersRes, activityRes] = await Promise.all([
      fetch(`${API_URL}/admin/stats`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
      fetch(`${API_URL}/admin/users?per_page=20`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
      fetch(`${API_URL}/admin/activity?limit=20`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
    ]);

    const stats = await statsRes.json();
    const usersData = await usersRes.json();
    const activity = await activityRes.json();

    if (!statsRes.ok) {
      contentDiv.innerHTML = `<p style="color:red; grid-column:1/-1;">Error: ${stats.error}</p>`;
      return;
    }

    // ---- Stats cards ----
    const statCards = [
      ["Total Users", stats.users.total],
      ["New This Week", stats.users.new_this_week],
      ["Banned", stats.users.banned],
      ["Movies", stats.content.total_movies],
      ["Books", stats.content.total_books],
      ["Total Ratings", stats.ratings.total],
      ["Avg Rating", Number(stats.ratings.average).toFixed(2)],
      ["Ratings/Week", stats.ratings.new_this_week],
    ]
      .map(
        ([label, value]) => `
      <div style="background:#1b2432; border-radius:14px; padding:18px; text-align:center;">
        <div style="font-size:1.5rem; font-weight:700; color:#a855f7;">${value}</div>
        <div style="font-size:0.65rem; opacity:0.5; margin-top:4px;
          text-transform:uppercase; letter-spacing:1px;">${label}</div>
      </div>`,
      )
      .join("");

    // ---- User rows ----
    const userRows = (usersData.users || [])
      .map(
        (u) => `
      <tr id="user-row-${u.id}" style="border-bottom:1px solid #222;">
        <td style="padding:10px 8px;">${u.username}</td>
        <td style="padding:10px 8px; font-size:0.75rem; opacity:0.6;">${u.email || "—"}</td>
        <td style="padding:10px 8px; text-align:center;">${u.rating_count}</td>
        <td style="padding:10px 8px; text-align:center;">
          ${
            u.is_admin
              ? `<span style="color:#a855f7; font-size:0.7rem;">ADMIN</span>`
              : `<span style="font-size:0.7rem; opacity:0.4;">user</span>`
          }
        </td>
        <td style="padding:10px 8px; text-align:center;">
          ${
            u.is_banned
              ? `<span style="color:#ef4444; font-size:0.7rem;">BANNED</span>`
              : `<span style="color:#22c55e; font-size:0.7rem;">active</span>`
          }
        </td>
        <td style="padding:10px 8px; text-align:right;">
  ${
    !u.is_banned
      ? `
    <button onclick="adminBanUser(${u.id}, true)"
      style="font-size:0.7rem; padding:4px 10px; border-radius:6px; cursor:pointer;
        background:#ef444422; color:#ef4444; border:1px solid #ef4444;">
      Ban
    </button>`
      : `
    <button onclick="adminBanUser(${u.id}, false)"
      style="font-size:0.7rem; padding:4px 10px; border-radius:6px; cursor:pointer;
        background:#22c55e22; color:#22c55e; border:1px solid #22c55e;">
      Unban
    </button>`
  }
  ${
    !u.is_admin
      ? `
    <button onclick="adminPromoteUser(${u.id}, true)"
      style="font-size:0.7rem; padding:4px 10px; border-radius:6px; cursor:pointer;
        background:#a855f722; color:#a855f7; border:1px solid #a855f7; margin-left:6px;">
      Promote
    </button>`
      : `
    <button onclick="adminPromoteUser(${u.id}, false)"
      style="font-size:0.7rem; padding:4px 10px; border-radius:6px; cursor:pointer;
        background:#f9731622; color:#f97316; border:1px solid #f97316; margin-left:6px;">
      Demote
    </button>`
  }
</td>
      </tr>`,
      )
      .join("");

    // ---- Activity rows ----
    const activityRows =
      (activity.activities || [])
        .map((a) => {
          const time = new Date(a.timestamp).toLocaleString("en-IE", {
            day: "numeric",
            month: "short",
            hour: "2-digit",
            minute: "2-digit",
          });
          return `
        <div style="display:flex; justify-content:space-between; align-items:center;
          padding:10px 0; border-bottom:1px solid #1b2432; font-size:0.8rem;">
          <div>
            <span style="color:#a855f7; font-weight:600;">${a.username}</span>
            <span style="opacity:0.5; margin: 0 6px;">·</span>
            <span>${a.details}</span>
          </div>
          <div style="opacity:0.4; font-size:0.7rem; flex-shrink:0; margin-left:12px;">${time}</div>
        </div>`;
        })
        .join("") ||
      `<p style="opacity:0.4; text-align:center; padding:20px;">No activity yet.</p>`;

    // ---- Top movies ----
    const topMoviesHTML = (stats.top_movies || [])
      .map(
        (m, i) => `
      <div style="display:flex; align-items:center; gap:12px; padding:8px 0;
        border-bottom:1px solid #222; font-size:0.8rem;">
        <span style="color:#a855f7; font-weight:700; width:20px;">${i + 1}</span>
        <span style="flex:1;">${m.title}</span>
        <span style="opacity:0.5;">${m.rating_count} ratings</span>
        <span style="color:#ffd700;">★ ${Number(m.average_rating).toFixed(1)}</span>
      </div>`,
      )
      .join("");

    contentDiv.innerHTML = `
      <div style="grid-column:1/-1; max-width:1100px; margin:0 auto; width:100%;">

        <h2 style="margin-bottom:24px; font-size:1.1rem; opacity:0.7;
          text-transform:uppercase; letter-spacing:2px;">Admin Dashboard</h2>

        <!-- Stat cards -->
        <div style="display:grid; grid-template-columns:repeat(auto-fill,minmax(140px,1fr));
          gap:12px; margin-bottom:32px;">
          ${statCards}
        </div>

        <!-- Two-column: users + activity -->
        <div style="display:grid; grid-template-columns:1fr 340px; gap:24px;
          margin-bottom:32px; align-items:start;">

          <!-- User management table -->
          <div style="background:#1b2432; border-radius:16px; padding:24px; overflow-x:auto;">
            <div style="display:flex; justify-content:space-between; align-items:center;
              margin-bottom:16px;">
              <h3 style="font-size:0.85rem; text-transform:uppercase; letter-spacing:1px;
                opacity:0.5;">Users (${usersData.total})</h3>
              <input type="text" placeholder="Search users…"
                oninput="adminSearchUsers(this.value)"
                style="background:#0f1014; border:1px solid #333; color:white;
                  border-radius:8px; padding:6px 12px; font-size:0.8rem; width:160px;">
            </div>
            <table id="adminUserTable" style="width:100%; border-collapse:collapse;
              font-size:0.82rem;">
              <thead>
                <tr style="opacity:0.4; font-size:0.65rem; text-transform:uppercase;
                  letter-spacing:1px;">
                  <th style="text-align:left; padding:8px;">Username</th>
                  <th style="text-align:left; padding:8px;">Email</th>
                  <th style="text-align:center; padding:8px;">Ratings</th>
                  <th style="text-align:center; padding:8px;">Role</th>
                  <th style="text-align:center; padding:8px;">Status</th>
                  <th style="text-align:right; padding:8px;">Actions</th>
                </tr>
              </thead>
              <tbody id="adminUserBody">
                ${userRows}
              </tbody>
            </table>
          </div>

          <!-- Activity feed -->
          <div style="background:#1b2432; border-radius:16px; padding:24px;">
            <h3 style="font-size:0.85rem; text-transform:uppercase; letter-spacing:1px;
              opacity:0.5; margin-bottom:16px;">Recent Activity</h3>
            <div style="max-height:420px; overflow-y:auto;">
              ${activityRows}
            </div>
          </div>

        </div>

        <!-- Top movies -->
        <div style="background:#1b2432; border-radius:16px; padding:24px; margin-bottom:32px;">
          <h3 style="font-size:0.85rem; text-transform:uppercase; letter-spacing:1px;
            opacity:0.5; margin-bottom:16px;">Top Rated Movies</h3>
          ${topMoviesHTML || `<p style="opacity:0.4; text-align:center;">No data yet.</p>`}
        </div>

      </div>`;
  } catch (err) {
    console.error("Admin dashboard error:", err);
    contentDiv.innerHTML = `
      <p style="color:red; grid-column:1/-1; text-align:center;">
        Could not load dashboard. Check your connection.
      </p>`;
  }
}

// --- ADMIN ACTION HELPERS ---

/**
 * Ban or unban a user. Updates the row in place without a full reload.
 */
async function adminBanUser(userId, shouldBan) {
  const token = localStorage.getItem("token");
  try {
    const res = await fetch(`${API_URL}/admin/users/${userId}/ban`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ banned: shouldBan }),
    });
    const data = await res.json();
    if (res.ok) {
      // Reload dashboard to reflect changes
      showAdminDashboard();
    } else {
      alert("Error: " + data.error);
    }
  } catch (err) {
    console.error("Ban error:", err);
  }
}

/**
 * Promote or demote a user to/from admin.
 */
async function adminPromoteUser(userId, makeAdmin) {
  if (!confirm(`${makeAdmin ? "Promote" : "Demote"} this user?`)) return;
  const token = localStorage.getItem("token");
  try {
    const res = await fetch(`${API_URL}/admin/users/${userId}/promote`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ is_admin: makeAdmin }),
    });
    const data = await res.json();
    if (res.ok) {
      showAdminDashboard();
    } else {
      alert("Error: " + data.error);
    }
  } catch (err) {
    console.error("Promote error:", err);
  }
}

/**
 * Live search within the user table (client-side filter on already-loaded rows).
 * For a full server-side search, replace with a fetch to /api/admin/users?search=...
 */
function adminSearchUsers(query) {
  const rows = document.querySelectorAll("#adminUserBody tr");
  const q = query.toLowerCase();
  rows.forEach((row) => {
    const text = row.textContent.toLowerCase();
    row.style.display = text.includes(q) ? "" : "none";
  });
}

// ============================================================
// ITEM DETAIL — showItemDetail(item, type)
// Renders a full-screen overlay with poster, description,
// community rating, user's own rating, and similar items.
// ============================================================

async function showItemDetail(item, type) {
  // Update URL hash so reload restores this view
  history.replaceState(null, "", `#item-${type}-${item.id}`);

  const isBook = type === "books";
  const token = localStorage.getItem("token");

  // Poster / cover image
  const poster = isBook
    ? (item.thumbnail || "")
        .replace("http://", "https://")
        .replace("zoom=1", "zoom=0")
    : `https://image.tmdb.org/t/p/w500${item.poster_path}`;
  const backdrop = isBook
    ? poster
    : `https://image.tmdb.org/t/p/original${item.poster_path}`;
  const placeholder =
    "https://placehold.jp/24/1b2432/ffffff/500x750.png?text=No+Cover";

  // Fetch the user's existing rating if logged in
  let userRating = 0;
  let ratingCount = 0;
  if (token) {
    try {
      const rRes = await fetch(`${API_URL}/ratings/${type}/${item.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (rRes.ok) {
        const rData = await rRes.json();
        userRating = rData.your_rating || 0;
        ratingCount = rData.count || 0;
      }
    } catch (e) {
      /* non-fatal */
    }
  }

  // Build star HTML for the detail view
  function detailStars(current) {
    return Array.from({ length: 5 }, (_, i) => {
      const n = i + 1;
      return `<span
        class="detail-star"
        data-val="${n}"
        onclick="rateFromDetail('${type}', ${item.id}, ${n})"
        style="font-size:1.8rem; cursor:pointer; color:${n <= current ? "#ffd700" : "#444"};
          transition: color 0.15s;"
        onmouseover="highlightStars(${n})"
        onmouseout="resetStars(${userRating})"
      >★</span>`;
    }).join("");
  }

  const subline = isBook ? item.authors || "" : item.release_year || "";

  // Description — some entries are ALL CAPS from the API, normalise them
  const rawDesc = item.description || "No description available.";
  const cleanDesc =
    rawDesc.length > 0 && rawDesc === rawDesc.toUpperCase()
      ? rawDesc.charAt(0) + rawDesc.slice(1).toLowerCase()
      : rawDesc;

  // Inject the overlay into the DOM
  // We inject into body so it sits above everything
  const existing = document.getElementById("itemDetailOverlay");
  if (existing) existing.remove();

  const overlay = document.createElement("div");
  overlay.id = "itemDetailOverlay";
  overlay.style.cssText = `
    position: fixed; inset: 0; z-index: 1000;
    background: rgba(0,0,0,0.92);
    overflow-y: auto;
    animation: fadeIn 0.2s ease;
  `;

  overlay.innerHTML = `
    <style>
      @keyframes fadeIn { from { opacity:0 } to { opacity:1 } }
      @keyframes slideUp { from { transform:translateY(30px); opacity:0 }
                           to   { transform:translateY(0);    opacity:1 } }
      #itemDetailOverlay .detail-star:hover { transform: scale(1.2); }
    </style>

    <!-- Blurred backdrop -->
    <div style="
      position:fixed; inset:0; z-index:-1;
      background-image: url('${backdrop}');
      background-size: cover; background-position: center;
      filter: blur(40px) brightness(0.3);
      transform: scale(1.1);
    "></div>

    <!-- Close button -->
    <button onclick="closeItemDetail()"
      style="position:fixed; top:20px; right:24px; z-index:10;
        background:rgba(255,255,255,0.08); border:none; color:white;
        font-size:1.4rem; width:44px; height:44px; border-radius:50%;
        cursor:pointer; display:flex; align-items:center; justify-content:center;">
      ✕
    </button>

    <!-- Main content -->
    <div style="
      max-width: 900px; margin: 0 auto; padding: 60px 24px 80px;
      animation: slideUp 0.3s ease;
    ">
      <div style="display:flex; gap:40px; align-items:flex-start;
        flex-wrap:wrap;">

        <!-- Poster -->
        <div style="flex-shrink:0;">
          <img src="${poster}" alt="${item.title}"
            onerror="this.src='${placeholder}'"
            style="width:220px; border-radius:16px;
              box-shadow: 0 20px 60px rgba(0,0,0,0.6);">
        </div>

        <!-- Info -->
        <div style="flex:1; min-width:260px;">
          <div style="font-size:0.7rem; text-transform:uppercase; letter-spacing:2px;
            opacity:0.4; margin-bottom:8px;">${type.slice(0, -1)}</div>

          <h1 style="font-size:2rem; font-weight:800; margin:0 0 8px; line-height:1.2;">
            ${item.title}
          </h1>

          ${subline ? `<p style="opacity:0.5; margin:0 0 20px; font-size:0.9rem;">${subline}</p>` : ""}

          <!-- Community rating -->
          <div style="display:flex; align-items:center; gap:12px; margin-bottom:28px;">
            <div style="font-size:2.5rem; font-weight:800; color:#ffd700; line-height:1;">
              ${item.rating ? Number(item.rating).toFixed(1) : "—"}
            </div>
            <div>
              <div style="color:#ffd700; font-size:1rem;">★★★★★</div>
              <div style="font-size:0.7rem; opacity:0.4; margin-top:2px;">
                Community rating
              </div>
            </div>
          </div>

          <!-- User rating -->
          <div style="margin-bottom:28px;">
            <div style="font-size:0.7rem; text-transform:uppercase; letter-spacing:1px;
              opacity:0.5; margin-bottom:8px;">Your Rating</div>
            ${
              token
                ? `<div id="detailStarsContainer">${detailStars(userRating)}</div>
                 <div id="detailRatingLabel" style="font-size:0.75rem; opacity:0.5;
                   margin-top:6px; height:18px;">
                   ${userRating ? `You rated this ${userRating}/5` : "Click to rate"}
                 </div>`
                : `<p style="opacity:0.4; font-size:0.85rem;">
                   <a onclick="showLoginModal()"
                     style="color:#a855f7; cursor:pointer;">Login</a> to rate this
                 </p>`
            }
          </div>

          <!-- Description -->
          <div style="font-size:0.9rem; line-height:1.7; opacity:0.75; max-width:520px;">
            ${cleanDesc}
          </div>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);

  // Close on backdrop click (but not on content click)
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closeItemDetail();
  });

  // Close on Escape key
  const escHandler = (e) => {
    if (e.key === "Escape") {
      closeItemDetail();
      document.removeEventListener("keydown", escHandler);
    }
  };
  document.addEventListener("keydown", escHandler);
}

function closeItemDetail() {
  const overlay = document.getElementById("itemDetailOverlay");
  if (overlay) overlay.remove();
  // Restore the tab hash
  history.replaceState(null, "", "#" + currentTab);
}

// Star hover helpers (called from inline onmouseover/onmouseout)
function highlightStars(n) {
  document.querySelectorAll(".detail-star").forEach((s, i) => {
    s.style.color = i < n ? "#ffd700" : "#444";
  });
}

function resetStars(current) {
  document.querySelectorAll(".detail-star").forEach((s, i) => {
    s.style.color = i < current ? "#ffd700" : "#444";
  });
}

// Rating from inside the detail overlay
async function rateFromDetail(type, id, val) {
  await rateItem(type, id, val); // reuse existing rateItem function

  // Update the stars and label in place
  const container = document.getElementById("detailStarsContainer");
  const label = document.getElementById("detailRatingLabel");

  if (container) {
    // Re-render stars with new value
    container.querySelectorAll(".detail-star").forEach((s, i) => {
      s.style.color = i < val ? "#ffd700" : "#444";
      // Update onclick to reflect new current value for hover reset
      s.setAttribute("onmouseout", `resetStars(${val})`);
    });
  }
  if (label) label.textContent = `You rated this ${val}/5`;
}

async function openRatedItem(r) {
  const item = r.movie || r.book;
  const type = r.kind === "movie" ? "movies" : "books";

  // Try to find the full item in allData first (already loaded, free)
  let fullItem = allData.find((i) => i.id === item.id);

  // If not in allData (different tab was active), fetch it
  if (!fullItem) {
    try {
      const res = await fetch(`${API_URL}/${type}/?page=1`);
      const data = await res.json();
      fullItem = (data[type] || []).find((i) => i.id === item.id);
    } catch (e) {
      /* fall through to minimal */
    }
  }

  // Fall back to minimal object if fetch failed
  if (!fullItem) {
    fullItem = {
      id: item.id,
      title: item.title,
      rating: item.average_rating || 0,
      description: null,
      release_year: item.release_year || null,
      poster_path: null,
      authors: item.authors || null,
      thumbnail: null,
    };
  }

  showItemDetail(fullItem, type);
}

function toggleMenu() {
    const nav = document.getElementById('headerRight');
    const burger = document.getElementById('hamburger');
    
    nav.classList.toggle('active');
    burger.classList.toggle('open');
}


document.querySelectorAll('.nav-item').forEach(link => {
    link.addEventListener('click', () => {
        document.getElementById('headerRight').classList.remove('active');
        document.getElementById('hamburger').classList.remove('open');
    });
});
