import io
import json
import os
from pathlib import Path

import calibre
from calibre.db.legacy import LibraryDatabase
from calibre.ebooks.metadata.book.base import Metadata
from calibre.db import backend

root = Path(os.environ['CALIBRE_PATCH_TEST_DIR'])
root.mkdir(parents=True, exist_ok=True)
library = root / 'library'
legacy_db = LibraryDatabase(str(library))
db = legacy_db.new_api
def check(value, detail='check failed'):
    if not value:
        raise RuntimeError(str(detail))
mi = Metadata('三体：地球往事', ['刘慈欣'])
book = db.create_book_entry(mi)
check(db.add_format(book, 'TXT', io.BytesIO('这是中文书籍内容。\n保留中文作者和书名。'.encode('utf-8')), run_hooks=False))
first = Path(db.format_abspath(book, 'TXT'))
check(first.is_file(), first)
check(first.parent.parent.name == '刘慈欣', first)
check(first.name == '三体：地球往事 - 刘慈欣.txt', first)
db.set_field('title', {book: '中文书名测试'})
db.set_field('authors', {book: ['中文作者']})
renamed = Path(db.format_abspath(book, 'TXT'))
check(renamed.is_file(), renamed)
check(renamed.parent.parent.name == '中文作者', renamed)
check(renamed.name == '中文书名测试 - 中文作者.txt', renamed)
check(not first.exists())
check(renamed.read_text() == '这是中文书籍内容。\n保留中文作者和书名。')
print(json.dumps({'version': calibre.__version__, 'loaded_source': backend.__file__,
                  'imported_book': str(first.relative_to(library)),
                  'renamed_book': str(renamed.relative_to(library)),
                  'contents_unchanged': True}, ensure_ascii=False, indent=2))
db.backend.close()
