const API_URL = "http://localhost:5000/api";
const TMDB_BASE = "https://image.tmdb.org/t/p/w500";
const TMDB_HD = "https://image.tmdb.org/t/p/original";

let currentTab = "movies";
let allData = [];
let isLoginMode = true;
let currentSlide = 0;
let slidesData = [];
let currentUser = null;

window.onload = () => {
    checkAuth();
    switchTab('movies');
};

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
        } catch (e) { localStorage.removeItem("token"); }
    }
}

async function loadData(type) {
    const contentDiv = document.getElementById("content");
    try {
        const res = await fetch(`${API_URL}/${type}/`);
        const data = await res.json();
        allData = data[type] || [];

        
        const validData = allData.filter(item => type === 'movies' ? item.poster_path : item.thumbnail);

        setupCarousel(validData, type);
        renderGrid(validData, type);
    } catch (e) {
        contentDiv.innerHTML = "Error connecting to server.";
    }
}

async function loadRecommendations() {
    const contentDiv = document.getElementById("content");
    const token = localStorage.getItem("token");

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
        // We launch both requests at the same time for better performance
        const [resMovies, resBooks] = await Promise.all([
            fetch(`${API_URL}/recommendations/movies`, { headers: { Authorization: `Bearer ${token}` } }),
            fetch(`${API_URL}/recommendations/books`, { headers: { Authorization: `Bearer ${token}` } })
        ]);

        const dataMovies = await resMovies.json();
        const dataBooks = await resBooks.json();

        let combinedRecs = [];

        if (resMovies.ok && dataMovies.recommendations) {
            combinedRecs = [...combinedRecs, ...dataMovies.recommendations];
        }

        if (resBooks.ok && dataBooks.recommendations) {
            combinedRecs = [...combinedRecs, ...dataBooks.recommendations];
        }

        if (combinedRecs.length > 0) {
            // Optional: Shuffle the array so movies and books are mixed
            combinedRecs.sort(() => Math.random() - 0.5);

            renderGrid(combinedRecs, 'recommendations');
            document.getElementById("stats").innerHTML = `Here the <span>${combinedRecs.length}</span> best Movies and Books recommendation for you!`;
        } else {
            contentDiv.innerHTML = `
                <div style="text-align:center; padding:50px; opacity:0.7;">
                <h3>Your feed is empty</h3>
                <p style="margin-top:10px;">Rate a few more movies and books so we can find what you love!</p>
                </div>`;
        }
    } catch (e) {
        console.error("Error combined recommendations:", e);
        contentDiv.innerHTML = "<div class='loading'>Error connecting to the recommendation engine.</div>";
    }
}

function renderGrid(data, type) {
    const contentDiv = document.getElementById("content");

    if (!data || data.length === 0) {
        contentDiv.innerHTML = "<p style='text-align:center; padding:20px; opacity:0.5;'>No results found.</p>";
        return;
    }

    contentDiv.innerHTML = data.map(item => {
        const rawPath = item.poster_path || item.thumbnail || item.image_url
        const placeholder = 'https://placehold.jp/24/1b2432/ffffff/500x750.png?text=No+Cover';

        let finalImg = placeholder;
        if (rawPath) {
            finalImg = rawPath.startsWith('http') ? rawPath : `https://image.tmdb.org/t/p/w500${rawPath}`;
        }


        const itemType = item.authors ? 'books' : 'movies';

        return `
        <div class="card">
            <div class="card-image-container">
            <span class="rating-badge">★ ${item.rating ? Number(item.rating).toFixed(1) : '0.0'}</span>
            <img src="${finalImg}" alt="${item.title}" onerror="this.onerror=null; this.src='${placeholder}';">
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


    data.forEach(item => {
        const itemType = item.authors ? 'books' : 'movies';
        loadRatingForItem(itemType, item.id);
    });
}

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
        console.error("Error loading the stars:", e);
    }
}

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
            console.log(`Rating de ${val} guardado para ${type} ID: ${id}`);

            await loadRatingForItem(type, id);
        } else {
            const errorData = await res.json();
            alert("Error al guardar rating: " + errorData.error);
        }
    } catch (e) {
        console.error("Error in requesting the rating:", e);
    }

    if (currentTab === 'recommendations') {
        loadRecommendations();
        setTimeout(() => {
            loadRecommendations();
        }, 500);
    }
}


function setupCarousel(data, type) {
    const container = document.getElementById("carouselContainer");
    const dotsContainer = document.getElementById("carouselDots");

    if (!container || !dotsContainer) return; 

    slidesData = data.slice(0, 5);
    container.innerHTML = "";
    dotsContainer.innerHTML = "";
    currentSlide = 0;

    slidesData.forEach((item, index) => {
        const bgImg = type === 'movies' ? `${TMDB_HD}${item.poster_path}` : (item.thumbnail || 'https://via.placeholder.com/500x750?text=No+Cover');
        const slide = document.createElement("div");
        slide.className = "slide";
        slide.style.backgroundImage = `url('${bgImg}')`;

        const shortDescription = item.description
            ? (item.description.length > 180 ? item.description.substring(0, 180) + "..." : item.description)
            : "No description available for this title.";

        slide.innerHTML = `
            <div class="slide-content">
                <span class="slide-tag">${type.toUpperCase()} SPOTLIGHT | ★ ${item.rating.toFixed(1)}</span>
                <h2>${item.title}</h2>
                <p class="slide-desc">${shortDescription}</p>
                <button class="btn-purple" style="margin-top: 20px; padding: 10px 25px;">Watch Now</button>
            </div>
            `;
        container.appendChild(slide);


        const dot = document.createElement("div");
        dot.className = `dot ${index === 0 ? 'active' : ''}`;
        dot.onclick = () => goToSlide(index);
        dotsContainer.appendChild(dot);
    });

    updateCarouselUI();
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

function updateCarouselUI() {
    const container = document.getElementById("carouselContainer");
    if (container) {
        container.style.transform = `translateX(-${currentSlide * 100}%)`;
    }


    document.querySelectorAll(".dot").forEach((dot, idx) => {
        dot.classList.toggle("active", idx === currentSlide);
    });
}


/**
 * Handles tab switching and ensures the UI is cleared before loading new content.
 */
function switchTab(tab) {
    currentTab = tab;

    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Clear stats and content IMMEDIATELY to avoid "stuck" text
    document.getElementById("stats").innerHTML = "";
    document.getElementById("content").innerHTML = ""; // This removes the "Loading..."


    document.getElementById("heroCarousel").style.display = (tab === 'recommendations') ? 'none' : 'block';

    if (tab === 'recommendations') {
        loadRecommendations();
    } else {
        loadData(tab);
    }
}

function handleSearch() {
    const input = document.getElementById("searchInput");
    const clearBtn = document.getElementById("clearSearch");
    const q = input.value.toLowerCase();

    
    clearBtn.style.display = q.length > 0 ? "block" : "none";

    
    const filtered = allData.filter(d => d.title.toLowerCase().includes(q));
    renderGrid(filtered, currentTab);
}

function clearSearchInput() {
    const input = document.getElementById("searchInput");
    input.value = "";
    document.getElementById("clearSearch").style.display = "none";
    
    
    renderGrid(allData, currentTab);
    input.focus(); 
}

// Auth Utils
function showLoginModal() { isLoginMode = true; updateModalUI(); document.getElementById("loginModal").classList.add("active"); }
function showRegisterModal() { isLoginMode = false; updateModalUI(); document.getElementById("loginModal").classList.add("active"); }
function toggleAuthMode() { isLoginMode = !isLoginMode; updateModalUI(); }
function updateModalUI() {
    document.getElementById("modalTitle").textContent = isLoginMode ? "Login" : "Register";
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

async function handleAuth(e) {
    e.preventDefault();
    const endpoint = isLoginMode ? "login" : "register";
    const payload = {
        username: document.getElementById("authUsername").value,
        password: document.getElementById("authPassword").value
    };
    if (!isLoginMode) payload.email = document.getElementById("email").value;

    const res = await fetch(`${API_URL}/auth/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok) { localStorage.setItem("token", data.token); location.reload(); }
    else { alert(data.error); }
}

function updateUIForLoggedInUser(user) {
    const userInfo = document.getElementById("userInfo");
    const usernameSpan = document.getElementById("username");

    
    usernameSpan.innerHTML = `
        <div class="user-profile-link" onclick="showProfile()" style="cursor:pointer; display:flex; align-items:center; gap:8px;">
            <img src="${user.avatar_url || 'https://cdn-icons-png.flaticon.com/512/1144/1144760.png'}" 
                alt="avatar" class="nav-avatar" id="navAvatar">
            ${user.username}
        </div>
    `;

    userInfo.style.display = "flex"; 
    document.getElementById("loginBtn").style.display = "none";
    document.getElementById("registerBtn").style.display = "none";
    document.getElementById("logoutBtn").style.display = "block";
}

function closeModal() {
    document.getElementById("loginModal").classList.remove("active");
}

window.onclick = function (event) {
    const modal = document.getElementById("loginModal");
    if (event.target == modal) {
        closeModal();
    }
}


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
                    <input type="file" id="avatarInput" accept="image/*" onchange="uploadAvatar(event)">
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


async function uploadAvatar(event) {
    const file = event.target.files[0];
    if (!file) return;

    
    const reader = new FileReader();
    reader.onload = function(e) {
        document.getElementById("profilePageAvatar").src = e.target.result;
        document.getElementById("navAvatar").src = e.target.result;
    }
    reader.readAsDataURL(file);

    
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

        const data = await res.json();

        if (res.ok) {
            alert("Profile updated!");
            // IMPORTANTE: Recargar para limpiar el overlay y actualizar el navbar
            location.reload(); 
        } else {
            alert("Error: " + data.error);
        }
    } catch (error) {
        console.error("Connection error:", error);
        // Si falla la conexión, igual cerramos la vista de perfil para que no se trabe
        switchTab('movies'); 
    }
}

