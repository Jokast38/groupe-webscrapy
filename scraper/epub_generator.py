from ebooklib import epub
import os
import json

def generate_epub(json_path, output_path=None):
    with open(json_path, 'r', encoding='utf-8') as f:
        chapters = json.load(f)
    # Si le json contient un dict avec 'chapters', adapte
    if isinstance(chapters, dict) and 'chapters' in chapters:
        title = chapters.get('title', 'Unknown')
        author = chapters.get('author', 'Unknown')
        chapters = chapters['chapters']
    else:
        title = 'Unknown'
        author = 'Unknown'
    book = epub.EpubBook()
    book.set_title(title)
    book.add_author(author)
    book.set_language('en')
    book.add_metadata('DC', 'title', title)
    book.add_metadata('DC', 'creator', author)
    epub_chapters = []
    for idx, chapter in enumerate(chapters):
        chap_title = chapter.get('chapter_title', f'Chapitre {idx+1}')
        c = epub.EpubHtml(title=chap_title, file_name=f'chap_{idx+1}.xhtml', lang='en')
        # Amélioration de la gestion des sauts de ligne et paragraphes
        content = chapter.get('content', '')
        # Découpe en paragraphes sur double saut de ligne ou \n\n
        import re
        # On considère qu'un paragraphe est séparé par deux sauts de ligne ou plus
        paragraphs = re.split(r'\n{2,}', content.strip())
        # Nettoie chaque paragraphe et entoure de <p>
        html_paragraphs = ['<p>' + p.strip().replace('\n', '<br>') + '</p>' for p in paragraphs if p.strip()]
        html_content = '\n'.join(html_paragraphs)
        c.content = f'<h2>{chap_title}</h2><div>{html_content}</div>'
        book.add_item(c)
        epub_chapters.append(c)
    book.toc = tuple(epub_chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav'] + epub_chapters
    if not output_path:
        # Nettoie le titre pour un nom de fichier valide
        import re
        safe_title = re.sub(r'[^\w\- ]', '', title).strip().replace(' ', '_')
        if not safe_title:
            safe_title = 'resultat'
        output_path = f"{safe_title}.epub"
    epub.write_epub(output_path, book, {})
    return output_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python epub_generator.py <resultats.json> [output.epub]")
        sys.exit(1)
    json_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    try:
        epub_file = generate_epub(json_path, output_path)
        if os.path.exists(epub_file):
            print(f"✅ EPUB généré avec succès : {epub_file}")
        else:
            print("❌ Erreur : le fichier EPUB n'a pas été créé.")
    except Exception as e:
        print(f"❌ Erreur lors de la génération de l'EPUB : {e}")
