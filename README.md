# 📚 Sistema de Gestão de Biblioteca — CEFET-MG

Este é o **Trabalho Prático 4 (TP4)** desenvolvido para a disciplina de **Programação em Python** do **CEFET-MG** pelo aluno **Henrique de Freitas Araujo**.

Trata-se de um sistema completo de gestão de biblioteca virtual e física com uma interface web interativa de alto padrão (Data App) construída com **Streamlit**, integrada a APIs de terceiros (REST e GraphQL) e com renderizações dinâmicas otimizadas em HTML/JS.

🔗 **Apresentação Online (GitHub Pages):** [Clique aqui para visualizar a apresentação](https://ak4ai.github.io/TP4/apresentacao/apresentacao.html)

---

## 🚀 Principais Funcionalidades

### 💻 Frontend & Experiência Visual
- **Interface Premium Dark Mode**: Estilização rica e moderna por meio de folha de estilos CSS personalizada ([style.css](file:///c:/Users/hfrei/CEFET/Python/TP4/style.css)).
- **Tabela de Acervo Otimizada**: Exibição dos livros em um IFrame com carregamento sob demanda (*Lazy Loading* / Rolagem Infinita) via JavaScript para suportar acervos massivos sem perda de performance.
- **Detalhamento Interativo (Tooltips)**: Hover dinâmico nas células exibindo sinopse e capa dos livros em tempo real.

### 🔌 Integrações com APIs Externas
- **Servidor GraphQL Suwayomi**: Conexão e sincronização direta com catálogo de mangás/livros digitais.
- **API Jikan (MyAnimeList - REST)**: Consulta automática de notas globais médias para mangás integrados.
- **API OpenLibrary (REST)**: Busca sob demanda e assíncrona (via AJAX/Fetch no frontend) das capas e descrições para os livros físicos cadastrados.

### 📊 Painéis de Negócio & Estatísticas
- **Indicadores Operacionais**: Métricas reativas (Total no Acervo, Físicos Livres, Emprestados, Digitais e Taxa de Disponibilidade).
- **Gráficos Dinâmicos**: Análise visual por gênero (Barras, Linhas, Área) e linha do tempo cronológica/acumulada de publicações.
- **Controle de Empréstimos**: Interface interativa de cadastro de novos empréstimos com validação de status e controle de devoluções.
- **Diário & Avaliações**: Espaço dedicado para o usuário marcar livros como lidos, dar notas pessoais e escrever pequenas resenhas.
- **Carga de Dados & Exportação**: Importador de planilhas CSV com tratamento automático de duplicados e exportador do acervo filtrado para CSV.

---

## 📂 Estrutura do Projeto

O projeto é dividido em camadas bem delimitadas:

- 🐍 [biblioteca.py](file:///c:/Users/hfrei/CEFET/Python/TP4/biblioteca.py): Contém a camada de **Model / Backend**, encapsulando toda a lógica orientada a objetos (classes `Biblioteca`, `Livro`, `Usuario`, `Emprestimo`), exceções customizadas de negócio e parsers de arquivos.
- 🎨 [app.py](file:///c:/Users/hfrei/CEFET/Python/TP4/app.py): Representa a camada de **View / Controller**, gerindo a interface do Streamlit, estado da sessão, requisições de API no backend e os filtros do painel.
- 📄 [acervo_template.html](file:///c:/Users/hfrei/CEFET/Python/TP4/acervo_template.html): Template estruturado com estilização interna, renderizador da tabela com *Lazy Loading*, manipulação do DOM e requisição dinâmica assíncrona (Fetch) da OpenLibrary API.
- 💅 [style.css](file:///c:/Users/hfrei/CEFET/Python/TP4/style.css): Customização CSS global injetada no Streamlit (cabeçalhos, gradientes, métricas e ajustes responsivos).
- 🧪 [test_biblioteca.py](file:///c:/Users/hfrei/CEFET/Python/TP4/test_biblioteca.py): Suíte de testes unitários automatizados cobrindo a lógica de negócio do backend.
- 📁 Bases de Exemplo:
  - `livros_exemplo.csv`: Base inicial resumida com livros de teste.
  - `livros_exemplo_grande.csv`: Base robusta com centenas de livros para demonstração de paginação e rolagem infinita.

---

## ⚙️ Instalação e Execução

### Pré-requisitos
Certifique-se de ter o Python 3.10+ instalado no seu sistema.

1. **Clonar/Acessar o diretório do projeto**:
   ```bash
   cd c:\Users\hfrei\CEFET\Python\TP4
   ```

2. **Criar e ativar o ambiente virtual (opcional, mas recomendado)**:
   ```bash
   python -m venv .venv
   # No Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   # No Linux/macOS:
   source .venv/bin/activate
   ```

3. **Instalar as dependências**:
   ```bash
   pip install streamlit pandas matplotlib pytest
   ```

4. **Executar a aplicação**:
   ```bash
   streamlit run app.py
   ```
   A aplicação será aberta automaticamente no seu navegador padrão (geralmente em `http://localhost:8501`).

---

## 🧪 Executando os Testes Unitários

Para validar a integridade lógica do sistema de negócio, execute os testes utilizando o `pytest`:

```bash
pytest test_biblioteca.py
```
