"""Catálogo fictício com capas tipográficas próprias, somente para testes/capturas.

Não utiliza a instalação da escola nem imagens de editoras.
"""
from pathlib import Path
import sqlite3
import tempfile
import textwrap
import zipfile
from PIL import Image, ImageDraw, ImageFont


def create_archive(destination):
    with tempfile.TemporaryDirectory(prefix='bibi-catalogo-sintetico-') as work:
        root = Path(work)
        conn = sqlite3.connect(root/'Biblioteca.db')
        conn.executescript((Path(__file__).resolve().parents[1]/'database/schema.sql').read_text(encoding='utf-8'))
        titles = ['A biblioteca das janelas', 'Caminhos de papel', 'O jardim das palavras', 'Cartas para amanhã', 'Entre rios e estrelas', 'A menina e o farol', 'Memórias de uma praça', 'O mapa dos encontros', 'Ciência no quintal', 'Histórias da nossa escola', 'Pequenas descobertas', 'O mundo das sementes', 'Mulheres e conhecimento', 'O céu que observamos', 'Perguntas sobre o tempo', 'Retratos da comunidade', 'Versos da manhã', 'O silêncio das árvores', 'Palavras ao vento', 'Caderno de horizontes', 'Rimas para um domingo', 'A cor dos encontros', 'Poemas do caminho', 'Vozes do nosso lugar', 'Clube dos exploradores', 'Uma aventura na escola', 'O mistério do caderno', 'A cidade dos desenhos', 'Viagem ao planeta azul', 'Amigos da biblioteca', 'O segredo da estação', 'Uma história em quadros']
        colors = ['#734f42', '#386d67', '#af7045', '#575077', '#53754d', '#9c5e6b', '#32617d', '#87734a']
        font_path = Path('C:/Windows/Fonts/georgia.ttf')
        font = ImageFont.truetype(str(font_path), 31)
        small = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
        folder = root/'static/images/uploadedcovers'
        folder.mkdir(parents=True)
        for i, title in enumerate(titles):
            image = Image.new('RGB', (320, 460), colors[i%len(colors)])
            draw = ImageDraw.Draw(image)
            draw.rectangle((20, 20, 299, 439), outline='#e5d8bd', width=2)
            draw.text((36, 45), 'BIBI / ACERVO DEMONSTRATIVO', font=small, fill='#f5ecdb')
            draw.line((36, 105, 284, 105), fill='#dac8a7', width=2)
            draw.multiline_text((36, 142), '\n'.join(textwrap.wrap(title, 17)), font=font, spacing=10, fill='#fff7e8')
            author = ['Ana Exemplo', 'Lia Demonstração', 'Caio Exemplo', 'Rita Demonstração'][i%4]
            draw.text((36, 363), author, font=small, fill='#fff7e8')
            draw.text((36, 403), 'OBRA FICTÍCIA · EDIÇÃO DE TESTE', font=small, fill='#e5d8bd')
            image.save(folder/f'demo-{i+1}.png')
            conn.execute('INSERT INTO Livros(nome,autor,capa_url,descricao,temas,categoria,estoque,quantidade_disponivel,localizacao) VALUES (?,?,?,?,?,?,?,?,?)', (title,author,f'/static/images/uploadedcovers/demo-{i+1}.png','Obra fictícia do catálogo demonstrativo da BIBI. Dados criados exclusivamente para apresentar os recursos da biblioteca.','leitura, descoberta, comunidade',['Ficção','Não-ficção','Poesia','Quadrinhos'][i//8],3,3,f'{chr(65+i//8)}-{i%8+1:02}'))
        conn.commit()
        conn.close()
        with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in root.rglob('*'):
                if path.is_file():
                    archive.write(path,path.relative_to(root).as_posix())


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('destination',type=Path)
    create_archive(parser.parse_args().destination)
