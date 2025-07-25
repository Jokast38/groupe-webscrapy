from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import os
from flask import Response
import json
import sys
import importlib.util
import re
import tempfile
from json import JSONDecoder
import pymongo
from dotenv import load_dotenv


app = Flask(__name__)
# Autorise toutes les origines et expose les headers nécessaires pour le téléchargement
CORS(app, resources={r"/*": {"origins": "*"}}, expose_headers=["Content-Disposition", "Content-Length"], supports_credentials=True)

# Ajoute les headers CORS sur toutes les réponses, même en cas d'erreur
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition,Content-Length'
    return response

# Log les erreurs 500 pour debug
@app.errorhandler(500)
def handle_500_error(e):
    import traceback
    print('[FLASK ERROR 500]', traceback.format_exc())
    response = jsonify({'error': 'Erreur interne du serveur', 'details': str(e)})
    response.status_code = 500
    return response

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
    # Met à jour le fichier search_result.json en lançant le spider Scrapy
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../scraper/search_result.json'))
    if os.path.exists(output_path):
        os.remove(output_path)
    result = subprocess.run([
        sys.executable, '-m', 'scrapy', 'crawl', 'wuxia_search', '-a', f'search_query={query}', '-s', 'LOG_ENABLED=False'
    ], cwd='../scraper', capture_output=True, text=True)
    if result.returncode != 0:
        return jsonify({'error': 'Scrapy error', 'stdout': result.stdout, 'stderr': result.stderr}), 500
    # Recherche d'abord dans la base MongoDB (collection novels)
    load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../scraper/.env')))
    mongo_uri = os.getenv('MONGODB_URI')
    db_name = os.getenv('DB_NAME')
    client = pymongo.MongoClient(mongo_uri)
    db = client[db_name]
    collection = db['novels']
    books = list(collection.find({'title': {'$regex': query, '$options': 'i'}}).limit(10))
    results = []
    for book in books:
        first_chap_url = book.get('first_chapter_url', '')
        slug = book.get('slug', '')
        if (not slug or not isinstance(slug, str) or not slug.strip()) and book.get('url'):
            match = re.search(r'/novel/([\w\-]+)$', book['url'])
            if match:
                slug = match.group(1)
        results.append({
            'title': book.get('title'),
            'author': book.get('author', ''),
            'image_url': book.get('image_url', ''),
            'url': book.get('url', ''),
            'slug': slug,
            'first_chapter_url': first_chap_url
        })
    # Si aucun résultat trouvé, lance le spider de recherche Scrapy pour compléter
    if not results:
        import json as pyjson
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmpf:
            search_json_path = tmpf.name
        result = subprocess.run([
            sys.executable, '-m', 'scrapy', 'crawl', 'wuxia_search', '-a', f'search_query={query}', '-o', search_json_path, '-s', 'LOG_ENABLED=False'
        ], cwd='../scraper', capture_output=True, text=True)
        if result.returncode == 0 and os.path.exists(search_json_path):
            try:
                with open(search_json_path, encoding='utf-8') as f:
                    spider_books = pyjson.load(f)
                for book in spider_books:
                    slug = book.get('slug', '')
                    if (not slug or not isinstance(slug, str) or not slug.strip()) and book.get('url'):
                        match = re.search(r'/novel/([\w\-]+)$', book['url'])
                        if match:
                            slug = match.group(1)
                    results.append({
                        'title': book.get('title'),
                        'author': book.get('author', ''),
                        'image_url': book.get('image_url', ''),
                        'url': book.get('url', ''),
                        'slug': slug,
                        'first_chapter_url': book.get('first_chapter_url', '')
                    })
            except Exception as e:
                print(f"[SEARCH] Erreur lecture JSON spider: {e}")
        # Nettoie le fichier temporaire
        try:
            os.remove(search_json_path)
        except Exception:
            pass
    client.close()
    return jsonify(results)

# --- ROUTE EPUB DOWNLOAD ROBUSTE ---
@app.route('/download', methods=['GET'])
def download():
    slug = request.args.get('slug')
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
        chapters = None
        title = 'Unknown'
        chapter_list = []
        partiel = False
        # Extraction JSON depuis fichier ou stdout/stderr
        if not os.path.exists(output_json):
            print(f"[EPUB] Erreur Scrapy: output JSON manquant, tentative extraction depuis stdout/stderr...")
            dump_json = None
            for output in [result.stdout, result.stderr]:
                if not output:
                    continue
                for line in output.splitlines():
                    if line.strip().startswith('[EPUB_JSON]'):
                        dump_json = line.strip()[len('[EPUB_JSON]'):].strip()
                        break
                if dump_json:
                    break
            print(f"[EPUB] Dump JSON récupéré: {dump_json}")
            if not dump_json or not dump_json.strip() or dump_json.strip()[0] not in '{[':
                print(f"[EPUB] Dump JSON vide ou mal formé: {dump_json}")
                return jsonify({'error': 'Erreur Scrapy: aucun chapitre récupéré (dump vide ou mal formé)', 'dump': dump_json, 'stdout': result.stdout, 'stderr': result.stderr}), 500
            try:
                chapters = json.loads(dump_json)
            except Exception as e:
                print(f"[EPUB] Erreur extraction JSON depuis dump: {e}\nContenu dump: {dump_json}")
                try:
                    decoder = JSONDecoder()
                    chapters = None
                    idx = 0
                    while idx < len(dump_json):
                        try:
                            obj, end = decoder.raw_decode(dump_json[idx:])
                            chapters = obj
                            print(f"[EPUB] Extraction partielle JSON réussie à l'index {idx}")
                            partiel = True
                            break
                        except Exception:
                            idx += 1
                    if chapters is None:
                        raise ValueError("Aucun JSON partiel valide trouvé")
                except Exception as e2:
                    print(f"[EPUB] Extraction partielle échouée: {e2}")
                    return jsonify({'error': f'Erreur extraction JSON depuis dump: {e}', 'dump': dump_json, 'stdout': result.stdout, 'stderr': result.stderr}), 500
            if isinstance(chapters, dict) and 'chapters' in chapters:
                title = chapters.get('title', 'Unknown')
                chapter_list = chapters['chapters']
            else:
                title = 'Unknown'
                chapter_list = chapters if isinstance(chapters, list) else []
            print(f"[EPUB] Extraction chapitres depuis dump: {len(chapter_list)} chapitres (partiel possible)")
            with open(output_json, 'w', encoding='utf-8') as fjson:
                json.dump(chapters, fjson, ensure_ascii=False)
        else:
            with open(output_json, encoding='utf-8') as f:
                try:
                    chapters = json.load(f)
                    if isinstance(chapters, dict) and 'chapters' in chapters:
                        title = chapters.get('title', 'Unknown')
                        chapter_list = chapters['chapters']
                    else:
                        title = 'Unknown'
                        chapter_list = chapters if isinstance(chapters, list) else []
                    print(f"[EPUB] Nombre de chapitres récupérés: {len(chapter_list)}")
                except Exception as e:
                    print(f"[EPUB] Erreur lecture JSON: {e}")
                    return jsonify({'error': f'Erreur lecture JSON: {e}'}), 500
        if not chapter_list or len(chapter_list) == 0:
            print(f"[EPUB] Aucun chapitre récupéré, abandon.")
            return jsonify({'error': "Aucun chapitre n’a pu être récupéré pour ce roman. Veuillez réessayer plus tard ou choisir un autre livre."}), 500
        # Nettoie le titre pour un nom de fichier valide
        safe_title = re.sub(r'[^\w\- ]', '', title).strip().replace(' ', '_').lower()
        if not safe_title:
            safe_title = 'resultat'
        epub_filename = f"{safe_title}{'_partiel' if partiel else ''}.epub"
        epub_path = os.path.join(tmpdir, epub_filename)
        try:
            epub_gen_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../scraper/epub_generator.py'))
            spec = importlib.util.spec_from_file_location('epub_generator', epub_gen_path)
            epub_generator = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(epub_generator)
            print(f"[EPUB] Génération de l'epub...")
            # output_json is a file path (str), not a dict! Use title and chapter_list already extracted
            book_data = {'title': title}
            epub_generator.generate_epub_from_data(book_data, chapter_list, epub_path)
            print(f"[EPUB] EPUB généré: {epub_path}")
            with open(epub_path, 'rb') as f:
                epub_data = f.read()
            file_size = len(epub_data)
            response = Response(epub_data, mimetype='application/epub+zip')
            response.headers['Content-Disposition'] = f'attachment; filename="{epub_filename}"'
            response.headers['Content-Length'] = str(file_size)
            if partiel:
                response.headers['X-EPUB-Partial'] = 'true'
            return response
        except Exception as e:
            print(f"[EPUB] Erreur technique lors de la génération de l'EPUB: {e}")
            return jsonify({'error': "Une erreur technique est survenue lors de la génération du livre. Merci de réessayer ou de contacter le support."}), 500

if __name__ == '__main__':
    app.run(debug=True)
