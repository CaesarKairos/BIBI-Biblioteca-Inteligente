# Referencia anterior a refatoracao

`app_monolitico.py` e uma copia exata do app.py original, mantida para comparacao e testes. Nao execute diretamente: seus caminhos dependiam de estar na raiz do projeto. Os testes carregam essa copia com caminhos e LOCALAPPDATA isolados.

Use `python app.py` na raiz para executar a versao modular. O monolito nao e importado pela aplicacao modular e nao deve ser incluido no pacote de distribuicao.
