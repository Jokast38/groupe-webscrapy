from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import os
from flask import Response

app = Flask(__name__)
CORS(app)

config = {
    'DEBUG': True,
    'CORS_HEADERS': 'Content-Type'
}   
app.config.update(config)
@app.route('/')
def index():
    return "Welcome to the WuxiaWorld EPUB Downloader API!"
@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '').lower()
    import json
    # Met à jour le fichier search_result.json en lançant le spider Scrapy
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../scraper/search_result.json'))
    if os.path.exists(output_path):
        os.remove(output_path)
    import sys
    result = subprocess.run([
        sys.executable, '-m', 'scrapy', 'crawl', 'wuxia_search', '-a', f'search_query={query}', '-s', 'LOG_ENABLED=False'
    ], cwd='../scraper', capture_output=True, text=True)
    if result.returncode != 0:
        return jsonify({'error': 'Scrapy error', 'stdout': result.stdout, 'stderr': result.stderr}), 500
    # Recherche les résultats dans la base MongoDB (collection novels)
    import pymongo
    from dotenv import load_dotenv
    load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../scraper/.env')))
    mongo_uri = os.getenv('MONGODB_URI')
    db_name = os.getenv('DB_NAME')
    client = pymongo.MongoClient(mongo_uri)
    db = client[db_name]
    collection = db['novels']
    # Recherche insensible à la casse sur le titre
    books = list(collection.find({'title': {'$regex': query, '$options': 'i'}}).limit(10))
    results = []
    for book in books:
        # Ajoute le lien du premier chapitre si dispo
        first_chap_url = book.get('first_chapter_url', '')
        results.append({
            'title': book.get('title'),
            'author': book.get('author', ''),
            'image_url': book.get('image_url', ''),
            'url': book.get('url', ''),
            'slug': book.get('slug', ''),
            'first_chapter_url': first_chap_url
        })
    client.close()
    return jsonify(results)

@app.route('/download', methods=['GET'])
def download():
    slug = request.args.get('slug')
    import tempfile
    import json
    import sys
    import importlib.util
    import os
    if not slug:
        return jsonify({'error': 'Slug obligatoire pour le téléchargement'}), 400
    print(f"[EPUB] Lancement du scraping pour le slug: {slug}")
    with tempfile.TemporaryDirectory() as tmpdir:
        output_json = os.path.join(tmpdir, 'book_data.json')
        result = subprocess.run([
            sys.executable, '-m', 'scrapy', 'crawl', 'wuxia_epub', '-a', f'slug={slug}'
        ], cwd='../scraper', capture_output=True, text=True)
        print(f"[EPUB] Scrapy stdout:\n{result.stdout}")
        print(f"[EPUB] Scrapy stderr:\n{result.stderr}")
        if result.returncode != 0 or not os.path.exists(output_json):
            print(f"[EPUB] Erreur Scrapy: code={result.returncode}, output={output_json}")
            return jsonify({'error': 'Erreur Scrapy', 'stdout': result.stdout, 'stderr': result.stderr}), 500
        # Affiche le contenu JSON pour debug
        with open(output_json, encoding='utf-8') as f:
            try:
                chapters = json.load(f)
                print(f"[EPUB] Nombre de chapitres récupérés: {len(chapters)}")
                for i, chap in enumerate(chapters[:3]):
                    print(f"[EPUB] Chapitre {i+1}: {chap.get('chapter_title')} (longueur: {len(chap.get('content',''))})")
                if len(chapters) > 3:
                    print(f"[EPUB] ... {len(chapters)-3} chapitres supplémentaires ...")
            except Exception as e:
                print(f"[EPUB] Erreur lecture JSON: {e}")
        # Charger le générateur d'epub dynamiquement
        epub_gen_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../scraper/epub_generator.py'))
        spec = importlib.util.spec_from_file_location('epub_generator', epub_gen_path)
        epub_generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(epub_generator)
        print(f"[EPUB] Génération de l'epub...")
        epub_path = epub_generator.generate_epub(output_json)
        print(f"[EPUB] EPUB généré: {epub_path}")
        # Envoyer le fichier avec Content-Length pour la barre de progression
        file_size = os.path.getsize(epub_path)
        def generate():
            with open(epub_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    yield chunk
        response = Response(generate(), mimetype='application/epub+zip')
        filename = f"{slug}.epub"
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.headers['Content-Length'] = str(file_size)
        return response

if __name__ == '__main__':
    app.run(debug=True)
