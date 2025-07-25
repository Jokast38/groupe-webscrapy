from ebooklib import epub
import re

def generate_epub_from_data(book_data, chapters, output_path=None):
    title = book_data.get('title', 'Unknown')
    author = book_data.get('author', 'Unknown')

    book = epub.EpubBook()
    book.set_title(title)
    book.add_author(author)
    book.set_language('en')
    book.add_metadata('DC', 'title', title)
    book.add_metadata('DC', 'creator', author)

    epub_chapters = []
    for idx, chapter in enumerate(chapters):
        chap_title = chapter.get('chapter_title', f'Chapitre {idx+1}')
        content = chapter.get('content', '')

        # Nettoyage du contenu et format HTML
        paragraphs = re.split(r'\n{2,}', content.strip())
        html_paragraphs = ['<p>' + p.strip().replace('\n', '<br>') + '</p>' for p in paragraphs if p.strip()]
        html_content = '\n'.join(html_paragraphs)

        c = epub.EpubHtml(title=chap_title, file_name=f'chap_{idx+1}.xhtml', lang='en')
        c.content = f'<h2>{chap_title}</h2><div>{html_content}</div>'
        book.add_item(c)
        epub_chapters.append(c)

    book.toc = tuple(epub_chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav'] + epub_chapters

    if not output_path:
        safe_title = re.sub(r'[^\w\- ]', '', title).strip().replace(' ', '_') or 'resultat'
        output_path = f"{safe_title}.epub"

    epub.write_epub(output_path, book)
    print(f"✅ EPUB généré avec succès : {output_path}")
    return output_path
