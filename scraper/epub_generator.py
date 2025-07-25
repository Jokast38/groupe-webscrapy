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
        # Encodage du contenu pour compatibilité
        content = chapter.get('content', '')
        c.content = f'<h2>{chap_title}</h2><div>{content}</div>'
        book.add_item(c)
        epub_chapters.append(c)
    book.toc = tuple(epub_chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav'] + epub_chapters
    if not output_path:
        output_path = os.path.splitext(json_path)[0] + '.epub'
    epub.write_epub(output_path, book, {})
    return output_path
