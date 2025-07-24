from ebooklib import epub
import os
import json

def generate_epub(json_path, output_path=None):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    book = epub.EpubBook()
    book.set_title(data['title'])
    chapters = []
    for idx, chapter in enumerate(data['chapters']):
        c = epub.EpubHtml(title=chapter['chapter_title'], file_name=f'chap_{idx+1}.xhtml', lang='en')
        c.content = chapter['content']
        book.add_item(c)
        chapters.append(c)
    book.toc = chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav'] + chapters
    if not output_path:
        output_path = os.path.splitext(json_path)[0] + '.epub'
    epub.write_epub(output_path, book, {})
    return output_path
