from ebooklib import epub
import os
import json

def generate_epub(json_path, output_path=None):
    with open(json_path, 'r', encoding='utf-8') as f:
        chapters = json.load(f)
    # Si le json contient un dict avec 'chapters', adapte
    if isinstance(chapters, dict) and 'chapters' in chapters:
        title = chapters.get('title', 'Unknown')
        chapters = chapters['chapters']
    else:
        title = 'Unknown'
    book = epub.EpubBook()
    book.set_title(title)
    epub_chapters = []
    for idx, chapter in enumerate(chapters):
        c = epub.EpubHtml(title=chapter.get('chapter_title', f'Chapitre {idx+1}'), file_name=f'chap_{idx+1}.xhtml', lang='en')
        c.content = chapter.get('content', '')
        book.add_item(c)
        epub_chapters.append(c)
    book.toc = epub_chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav'] + epub_chapters
    if not output_path:
        output_path = os.path.splitext(json_path)[0] + '.epub'
    epub.write_epub(output_path, book, {})
    return output_path
