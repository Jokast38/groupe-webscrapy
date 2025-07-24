
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
    result = subprocess.run([
        'wuxia_search',
        '-a', f'search_query={query}',
        '-o', output_path,
        '-t', 'json',
        '-s', 'LOG_ENABLED=False'
    ], cwd='../scraper', capture_output=True, text=True)
    if result.returncode != 0:
        return jsonify({'error': 'Scrapy error', 'stdout': result.stdout, 'stderr': result.stderr}), 500
    # Recharge le fichier après le crawl
    with open(output_path, encoding='utf-8') as f:
        books = json.load(f)
    results = []
    for book in books:
        if query in book.get('title', '').lower():
            results.append({
                'title': book.get('title'),
                'author': book.get('author', ''),
                'image_url': book.get('image_url', ''),
                'url': book.get('url', ''),
                'slug': book.get('slug', '')
            })
        if len(results) >= 10:
            break
    return jsonify(results)

@app.route('/download', methods=['GET'])
def download():
    title = request.args.get('title')
    # TODO: Lancer le scraper pour ce titre, générer l'epub et retourner le fichier
    return send_file('path_to_epub', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
