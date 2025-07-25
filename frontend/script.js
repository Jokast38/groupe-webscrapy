
const searchInput = document.getElementById('search');
const searchBtn = document.getElementById('search-btn');
const suggestions = document.getElementById('suggestions');
const loadingSearch = document.getElementById('loading-search');
const loadingDownload = document.getElementById('loading-download');
let selectedBook = null;

async function doSearch() {
    const q = searchInput.value;
    selectedBook = null;
    suggestions.innerHTML = '';
    if (q.length < 2) return;
    loadingSearch.style.display = 'block';
    const errorDiv = document.getElementById('error-message');
    errorDiv.style.display = 'none';
    try {
        const res = await fetch(`http://127.0.0.1:5000/search?q=${encodeURIComponent(q)}`);
        if (!res.ok) throw new Error('Erreur lors de la recherche');
        const data = await res.json();
        if (Array.isArray(data) && data.length === 0) {
            errorDiv.textContent = 'Aucun résultat trouvé.';
            errorDiv.style.display = 'block';
        }
        data.slice(0, 10).forEach(book => {
            const li = document.createElement('li');
            // Affiche une image par défaut si image_url absent ou cassé
            const coverUrl = book.image_url && book.image_url.trim() ? book.image_url : 'https://i.pinimg.com/1200x/ac/81/f0/ac81f0d7df3564c0d8c229b09df743d8.jpg';
            li.innerHTML = `<img class="cover-thumb" src="${coverUrl}" alt="cover" onerror="this.onerror=null;this.src='https://via.placeholder.com/60x80?text=No+Cover';"> <span>${book.title}</span> <button class="download-btn">Télécharger</button>`;
            const btn = li.querySelector('.download-btn');
            btn.onclick = (e) => {
                e.stopPropagation();
                console.log('Téléchargement demandé pour :', book);
                handleDownload(book);
            };
            suggestions.appendChild(li);
        });
    } catch (e) {
        errorDiv.textContent = e.message || 'Erreur lors de la recherche.';
        errorDiv.style.display = 'block';
    } finally {
        loadingSearch.style.display = 'none';
    }

}

function handleDownload(book) {
    loadingDownload.style.display = 'block';
    const progressBar = document.getElementById('download-progress');
    const percentSpan = document.getElementById('progress-percent');
    progressBar.value = 0;
    percentSpan.textContent = '0%';
    progressBar.style.display = 'inline-block';
    const errorDiv = document.getElementById('error-message');
    errorDiv.style.display = 'none';
    if (!book.slug) {
        errorDiv.textContent = 'Téléchargement impossible : slug manquant.';
        errorDiv.style.display = 'block';
        loadingDownload.style.display = 'none';
        return;
    }
    // Utilise l'URL complète de l'API backend
    const url = `http://127.0.0.1:5000/download?slug=${encodeURIComponent(book.slug)}`;
    let animInterval = null;
    let animPercent = 0;
    let animDirection = 1;
    fetch(url)
        .then(async response => {
            if (!response.ok) {
                let msg = 'Erreur lors du téléchargement.';
                try {
                    const err = await response.json();
                    msg = err.error || msg;
                } catch {}
                throw new Error(msg);
            }
            const contentLength = response.headers.get('Content-Length');
            if (!contentLength) {
                // Mode indéterminé : anime la barre jusqu'à 90% pendant le chargement
                animPercent = 0;
                animDirection = 1;
                animInterval = setInterval(() => {
                    animPercent += animDirection * 2;
                    if (animPercent >= 90) animDirection = -1;
                    if (animPercent <= 10) animDirection = 1;
                    progressBar.value = animPercent;
                    percentSpan.textContent = animPercent + '%';
                }, 80);
                const blob = await response.blob();
                clearInterval(animInterval);
                progressBar.value = 100;
                percentSpan.textContent = '100%';
                triggerDownload(blob, book.title || book.slug || 'book.epub');
                loadingDownload.style.display = 'none';
                return;
            }
            const total = parseInt(contentLength, 10);
            let loaded = 0;
            const reader = response.body.getReader();
            let chunks = [];
            function updateProgress(val) {
                progressBar.value = val;
                percentSpan.textContent = val + '%';
                progressBar.dispatchEvent(new Event('change'));
            }
            // Anime la barre même si le backend est lent
            animPercent = 0;
            animInterval = setInterval(() => {
                if (animPercent < 90) {
                    animPercent += 1;
                    updateProgress(animPercent);
                }
            }, 80);
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                chunks.push(value);
                loaded += value.length;
                const percent = Math.min(99, Math.round((loaded / total) * 100));
                updateProgress(percent);
            }
            clearInterval(animInterval);
            updateProgress(100);
            const blob = new Blob(chunks);
            triggerDownload(blob, book.title || book.slug || 'book.epub');
            loadingDownload.style.display = 'none';
        })
        .catch((e) => {
            if (animInterval) clearInterval(animInterval);
            loadingDownload.style.display = 'none';
            errorDiv.textContent = e.message || 'Erreur lors du téléchargement.';
            errorDiv.style.display = 'block';
            progressBar.value = 0;
            percentSpan.textContent = '0%';
        });
}

function triggerDownload(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename.endsWith('.epub') ? filename : filename + '.epub';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
        window.URL.revokeObjectURL(url);
        a.remove();
    }, 1000);
};

searchBtn.addEventListener('click', doSearch);
searchInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') doSearch(); });
