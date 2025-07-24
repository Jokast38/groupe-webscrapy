const searchInput = document.getElementById('search');
const searchBtn = document.getElementById('search-btn');
const suggestions = document.getElementById('suggestions');
let selectedBook = null;

async function doSearch() {
    const q = searchInput.value;
    selectedBook = null;
    suggestions.innerHTML = '';
    if (q.length < 2) return;
    const res = await fetch(`http://127.0.0.1:5000/search?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    data.slice(0, 10).forEach(book => {
        const li = document.createElement('li');
        li.innerHTML = `<img class="cover-thumb" src="${book.image_url || ''}" alt="cover"> <span>${book.title}</span> <button class="download-btn">Télécharger</button>`;
        const btn = li.querySelector('.download-btn');
        btn.onclick = (e) => {
            e.stopPropagation();
            window.location = `/download?title=${encodeURIComponent(book.title)}`;
        };
        suggestions.appendChild(li);
    });
}

searchBtn.addEventListener('click', doSearch);
searchInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') doSearch(); });
