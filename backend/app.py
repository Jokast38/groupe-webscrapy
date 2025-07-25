from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import os
from flask import Response

app = Flask(__name__)
# Autorise toutes les origines et expose les headers nécessaires pour le téléchargement
CORS(app, resources={r"/*": {"origins": "*"}}, expose_headers=["Content-Disposition", "Content-Length"], supports_credentials=True)

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
    import re
    for book in books:
        # Ajoute le lien du premier chapitre si dispo
        first_chap_url = book.get('first_chapter_url', '')
        slug = book.get('slug', '')
        # Si slug vide, tente de l'extraire depuis la fin de l'URL
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
        # On ne bloque plus sur le code retour, mais on vérifie la présence et le contenu du JSON
        chapters = None
        title = 'Unknown'
        chapter_list = []
        # Si le JSON n'existe pas, tente d'extraire les chapitres depuis le stdout
        if not os.path.exists(output_json):
            print(f"[EPUB] Erreur Scrapy: output JSON manquant, tentative extraction depuis stdout...")
            import re, ast
            # Cherche une ligne dans stdout qui ressemble à un dump JSON de chapitres
            # On suppose que le spider affiche une ligne spéciale: [EPUB_JSON] <json>
            match = re.search(r'\[EPUB_JSON\](.*)', result.stdout)
            if match:
                try:
                    chapters = json.loads(match.group(1).strip())
                    if isinstance(chapters, dict) and 'chapters' in chapters:
                        title = chapters.get('title', 'Unknown')
                        chapter_list = chapters['chapters']
                    else:
                        title = 'Unknown'
                        chapter_list = chapters if isinstance(chapters, list) else []
                    print(f"[EPUB] Extraction chapitres depuis stdout: {len(chapter_list)} chapitres")
                    # On écrit ce JSON dans output_json pour la suite
                    with open(output_json, 'w', encoding='utf-8') as fjson:
                        json.dump(chapters, fjson, ensure_ascii=False)
                except Exception as e:
                    print(f"[EPUB] Erreur extraction JSON depuis stdout: {e}")
                    return jsonify({'error': f'Erreur extraction JSON depuis stdout: {e}', 'stdout': result.stdout, 'stderr': result.stderr}), 500
            else:
                print(f"[EPUB] Aucun dump JSON trouvé dans stdout.")
                return jsonify({'error': 'Erreur Scrapy: aucun chapitre récupéré', 'stdout': result.stdout, 'stderr': result.stderr}), 500
        else:
            # Lecture du JSON pour extraire le titre et vérifier qu'il y a des chapitres
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
        # Charger le générateur d'epub dynamiquement
        epub_gen_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../scraper/epub_generator.py'))
        spec = importlib.util.spec_from_file_location('epub_generator', epub_gen_path)
        epub_generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(epub_generator)
        print(f"[EPUB] Génération de l'epub...")
        # Nettoie le titre pour un nom de fichier valide
        import re
        safe_title = re.sub(r'[^\w\- ]', '', title).strip().replace(' ', '_')
        if not safe_title:
            safe_title = 'resultat'
        epub_filename = f"{safe_title}.epub"
        epub_path = os.path.join(tmpdir, epub_filename)
        try:
            epub_generator.generate_epub(output_json, epub_path)
            print(f"[EPUB] EPUB généré: {epub_path}")
            # Lis tout le fichier en mémoire avant de sortir du contexte temporaire
            with open(epub_path, 'rb') as f:
                epub_data = f.read()
            file_size = len(epub_data)
            response = Response(epub_data, mimetype='application/epub+zip')
            response.headers['Content-Disposition'] = f'attachment; filename="{epub_filename}"'
            response.headers['Content-Length'] = str(file_size)
            return response
        except Exception as e:
            print(f"[EPUB] Erreur technique lors de la génération de l'EPUB: {e}")
            return jsonify({'error': "Une erreur technique est survenue lors de la génération du livre. Merci de réessayer ou de contacter le support."}), 500

if __name__ == '__main__':
    app.run(debug=True)
