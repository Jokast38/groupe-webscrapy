from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import os

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
        results.append({
            'title': book.get('title'),
            'author': book.get('author', ''),
            'image_url': book.get('image_url', ''),
            'url': book.get('url', ''),
            'slug': book.get('slug', '')
        })
    client.close()
    return jsonify(results)

@app.route('/download', methods=['GET'])
def download():
    title = request.args.get('title')
    # TODO: Lancer le scraper pour ce titre, générer l'epub et retourner le fichier
    return send_file('path_to_epub', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
