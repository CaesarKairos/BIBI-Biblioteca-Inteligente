import io
from contextlib import closing
from pathlib import Path
import sqlite3
import zipfile
from PIL import Image
from tests.support import AppTest
from services.importacao_acervo import import_catalog,inspect,digest


class CatalogImportTests(AppTest):
    def source(self,cover='/static/images/uploadedcovers/capa.png',two=False):
        old=self.directory/'origem.db'
        with closing(sqlite3.connect(old)) as conn,conn:
            conn.execute('CREATE TABLE Livros(id INTEGER PRIMARY KEY,isbn TEXT,nome TEXT,autor TEXT,estoque INTEGER,quantidade_disponivel INTEGER,capa_url TEXT,descricao TEXT,temas TEXT,categoria TEXT,ano_publicacao INTEGER)')
            conn.execute('INSERT INTO Livros VALUES (1,?,?,?,?,?,?,?,?,?,?)',('9780000000001','Obra da origem','Autora',3,1,cover,'Descrição','Temas','Poesia',2001))
            if two:conn.execute("INSERT INTO Livros VALUES (2,'9780000000002','Falhar','Autora',1,1,?,'','','Poesia',2001)",(cover,))
        image=io.BytesIO();Image.new('RGB',(20,30),'green').save(image,format='PNG')
        archive=self.directory/'origem.zip'
        with zipfile.ZipFile(archive,'w') as z:z.write(old,'Biblioteca.db');z.writestr('static/images/uploadedcovers/capa.png',image.getvalue())
        return archive,image.getvalue()

    def test_catalog_only_preserves_account_reconciles_stock_and_is_idempotent(self):
        archive,image=self.source();accounts=self.sql('SELECT * FROM Contas')
        result=import_catalog(archive,self.directory,True)
        self.assertEqual(result['importados'],1)
        self.assertTrue(Path(result['backup']).is_file())
        self.assertEqual(self.sql('SELECT nome,autor,estoque,quantidade_disponivel,capa_url FROM Livros'),[('Obra da origem','Autora',3,3,'/uploadedcovers/capa.png')])
        self.assertEqual(self.sql('SELECT * FROM Contas'),accounts)
        self.assertEqual((self.directory/'uploadedcovers/capa.png').read_bytes(),image)
        self.assertEqual(import_catalog(archive,self.directory,True)['existentes'],1)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM Livros'),[(1,)])

    def test_filename_collision_does_not_overwrite_a_different_cover(self):
        archive,image=self.source();cover=self.directory/'uploadedcovers/capa.png';cover.write_bytes(b'existing-content')
        import_catalog(archive,self.directory,True)
        self.assertEqual(cover.read_bytes(),b'existing-content')
        url=self.sql('SELECT capa_url FROM Livros')[0][0]
        self.assertIn(digest(image),url)
        self.assertEqual((self.directory/url.lstrip('/')).read_bytes(),image)

    def test_conflicting_isbn_is_reported_without_overwriting(self):
        archive,_=self.source();book=self.book();self.sql("UPDATE Livros SET isbn='9780000000001' WHERE id=?",(book,))
        result=import_catalog(archive,self.directory,True)
        self.assertEqual(len(result['conflitos']),1)
        self.assertEqual(result['importados'],0)
        self.assertEqual(self.sql('SELECT nome FROM Livros'),[('Livro',)])

    def test_insert_failure_rolls_back_books_and_new_files(self):
        archive,_=self.source(two=True)
        self.sql("CREATE TRIGGER reject_book BEFORE INSERT ON Livros WHEN NEW.nome='Falhar' BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):import_catalog(archive,self.directory,True)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM Livros'),[(0,)])
        self.assertEqual(list((self.directory/'uploadedcovers').glob('*')),[])
        self.assertTrue(list((self.directory/'backups').glob('antes-acervo-*.zip')))

    def test_unsafe_cover_reference_is_rejected_before_any_mutation(self):
        archive,_=self.source(cover='/static/images/uploadedcovers/../other.png')
        with self.assertRaises(ValueError):inspect(archive)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM Livros'),[(0,)])
