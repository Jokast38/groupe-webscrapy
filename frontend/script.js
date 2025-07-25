
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
            li.innerHTML = `<img class="cover-thumb" src="${book.image_url || ''}" alt="cover"> <span>${book.title}</span> <button class="download-btn">Télécharger</button>`;
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
                // Fallback si pas de taille connue
                const blob = await response.blob();
                triggerDownload(blob, book.title || book.slug || 'book.epub');
                loadingDownload.style.display = 'none';
                return;
            }
            const total = parseInt(contentLength, 10);
            let loaded = 0;
            const reader = response.body.getReader();
            let chunks = [];
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                chunks.push(value);
                loaded += value.length;
                const percent = Math.round((loaded / total) * 100);
                progressBar.value = percent;
                percentSpan.textContent = percent + '%';
            }
            const blob = new Blob(chunks);
            triggerDownload(blob, book.title || book.slug || 'book.epub');
            loadingDownload.style.display = 'none';
            percentSpan.textContent = '100%';
        })
        .catch((e) => {
            loadingDownload.style.display = 'none';
            errorDiv.textContent = e.message || 'Erreur lors du téléchargement.';
            errorDiv.style.display = 'block';
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
