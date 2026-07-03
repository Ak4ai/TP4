# ==============================================================================
# TRABALHO PRÁTICO 4 - SISTEMA DE BIBLIOTECA CEFET (FRONTEND DATA APP)
# Disciplina: Programação em Python
# Aluno: Henrique de Freitas Araujo
# Instituição: CEFET-MG
# ==============================================================================
# Este módulo (app.py) representa a camada de VIEW / CONTROLLER da aplicação.
# Desenvolvido com Streamlit, constrói uma interface web (Data App) interativa.
# Integra carregamento de dados local, gráficos analíticos de acervo e comunicação
# assíncrona com APIs externas (Suwayomi via GraphQL, Jikan & OpenLibrary via REST).
# ==============================================================================

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import tempfile
import os
import html as html_mod
import importlib

# ------------------------------------------------------------------------------
# 1. IMPORTAÇÃO E RECARREGAMENTO DINÂMICO DO BACKEND
# ------------------------------------------------------------------------------
# Importamos o módulo de negócios biblioteca.py e usamos importlib.reload() para 
# garantir que alterações no backend sejam refletidas no Streamlit sem reiniciar o servidor.
import biblioteca
importlib.reload(biblioteca)
from biblioteca import (
    Biblioteca, Livro, Usuario, Emprestimo,
    CodigoDuplicadoError, MatriculaDuplicadaError,
    LivroNaoEncontradoError, UsuarioNaoEncontradoError,
    LivroIndisponivelError, UsuarioInativoError,
    EmprestimoNaoEncontradoError,
    ArquivoAusenteError, ArquivoVazioError, ArquivoInvalidoError
)

# ------------------------------------------------------------------------------
# 2. CONFIGURAÇÃO DA PÁGINA STREAMLIT
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Sistema de Biblioteca CEFET",
    layout="wide",                  # Ocupa toda a largura da tela do navegador
    page_icon="📚",
    initial_sidebar_state="expanded" # Barra lateral começa aberta
)

# ------------------------------------------------------------------------------
# 3. ESTILIZAÇÃO CSS CUSTOMIZADA (VISUAL PREMIUM MODO ESCURO)
# ------------------------------------------------------------------------------
# Injetamos o arquivo CSS externo para estilizar a interface geral do Streamlit,
# incluindo o banner superior de gradiente e os cartões de métricas padrões.
try:
    with open("style.css", "r", encoding="utf-8") as css_file:
        custom_css = css_file.read()
    st.markdown(f"<style>{custom_css}</style>", unsafe_allow_html=True)
except Exception as e:
    st.error(f"Erro ao carregar a folha de estilos style.css: {e}")

# ------------------------------------------------------------------------------
# 4. GESTÃO DE ESTADO DA SESSION STATE
# ------------------------------------------------------------------------------
# Inicializa a biblioteca em memória dentro do estado da sessão do Streamlit,
# garantindo que os dados persistam entre recarregamentos de página (reruns).
if 'biblioteca' not in st.session_state:
    st.session_state.biblioteca = Biblioteca("Biblioteca CEFET")
    # Cadastra usuários padrão de demonstração para facilitar a avaliação do trabalho
    st.session_state.biblioteca.cadastrar_usuario(Usuario("U001", "Ana Souza", "ana@email.com"))
    st.session_state.biblioteca.cadastrar_usuario(Usuario("U002", "Bruno Lima", "bruno@email.com"))
    st.session_state.biblioteca.cadastrar_usuario(Usuario("U003", "Carlos Oliveira", "carlos@email.com"))

biblioteca = st.session_state.biblioteca

# Compatibilidade de Estado: Reconstrói dinamicamente referências a classes de objetos 
# em cache para evitar desserialização incompleta e garantir consistência de atributos herdados.
for l in biblioteca.livros:
    l.__class__ = Livro
    if not hasattr(l, "lido"):
        l.lido = False
    if not hasattr(l, "nota_pessoal"):
        l.nota_pessoal = None
    if not hasattr(l, "resenha"):
        l.resenha = None

for u in biblioteca.usuarios:
    u.__class__ = Usuario


# ------------------------------------------------------------------------------
# 5. INTEGRACÕES COM APIS EXTERNAS
# ------------------------------------------------------------------------------

def carregar_detalhes_suwayomi():
    """
    Integração de Backend via GraphQL com o servidor de mangás Suwayomi.
    Busca metadados estendidos (descrições e tracks de notas) e os enriquece
    fazendo chamadas HTTP em paralelo à API Jikan (MyAnimeList) para compor a nota global.
    """
    # Inicializa caches na sessão para economizar banda e evitar gargalos de requisições repetidas
    if 'suwayomi_cache_v2' not in st.session_state:
        st.session_state.suwayomi_cache_v2 = {}
    if 'jikan_cache_v2' not in st.session_state:
        st.session_state.jikan_cache_v2 = {}
        
    # Filtra identificadores numéricos de mangás digitais cadastrados no acervo
    mangas_ids = [l.codigo[1:] for l in biblioteca.livros if l.codigo.startswith("S")]
    if not mangas_ids:
        return
        
    # Determina quais mangás ainda não possuem metadados em cache
    ids_faltando = [mid for mid in mangas_ids if mid not in st.session_state.suwayomi_cache_v2]
    if not ids_faltando:
        return
        
    def fetch_jikan_score(mal_title):
        """Busca nota média de uma obra diretamente na REST API Jikan (MyAnimeList)."""
        if not mal_title:
            return None
        if mal_title in st.session_state.jikan_cache_v2:
            return st.session_state.jikan_cache_v2[mal_title]
        try:
            import urllib.request
            import urllib.parse
            import json
            # Codifica título para URL e solicita busca limitada a 1 resultado
            url = f"https://api.jikan.moe/v4/manga?q={urllib.parse.quote(mal_title)}&limit=1"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                res = json.loads(response.read().decode('utf-8'))
                if res.get('data'):
                    score = res['data'][0].get('score')
                    st.session_state.jikan_cache_v2[mal_title] = score
                    return score
        except Exception as ex:
            st.error(f"Erro no Jikan para '{mal_title}': {ex}")
        return None
        
    try:
        import urllib.request
        import json
        
        # Query GraphQL para obter detalhes estruturados dos mangás da biblioteca virtual
        query = """
        query {
          mangas(filter: { inLibrary: { equalTo: true } }) {
            nodes {
              id
              description
              trackRecords {
                nodes {
                  score
                  title
                  tracker {
                    name
                  }
                }
              }
            }
          }
        }
        """
        
        req = urllib.request.Request(
            suwayomi_url,
            data=json.dumps({'query': query}).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            res = json.loads(response.read().decode('utf-8'))
            
        if 'data' in res and 'mangas' in res['data']:
            nodes = res['data']['mangas']['nodes']
            for node in nodes:
                mid = str(node['id'])
                desc = node.get('description') or "Sem descrição disponível."
                
                # Procura registros de track com MyAnimeList para obter título exato de busca
                rating = "Sem nota (MAL)"
                tracks = node.get('trackRecords', {}).get('nodes', [])
                for t in tracks:
                    if t.get('tracker', {}).get('name') == 'MyAnimeList':
                        score = t.get('score')
                        mal_title = t.get('title')
                        
                        # Realiza a consulta na API Jikan
                        global_score = fetch_jikan_score(mal_title)
                        
                        parts = []
                        if global_score:
                            parts.append(f"⭐ {global_score:.2f} (MAL)")
                        if score and score > 0:
                            # Nota pessoal cadastrada no tracker local do Suwayomi
                            parts.append(f"👤 ⭐ {score:.1f} (Pessoal)")
                            
                        if parts:
                            rating = " | ".join(parts)
                        else:
                            rating = "⭐ Sem nota (MAL)"
                        break
                
                # Grava no cache de sessão para evitar carregamento repetido
                st.session_state.suwayomi_cache_v2[mid] = {
                    'description': desc,
                    'rating': rating
                }
    except Exception as e:
        st.error(f"Erro em carregar_detalhes_suwayomi: {e}")


def processar_upload_csv(uploaded_file):
    """
    Auxiliar para salvar o buffer temporário enviado via FileUploader 
    em um arquivo real em disco, permitindo o carregamento pelo backend.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as temp_file:
        temp_file.write(uploaded_file.read())
        temp_path = temp_file.name
    try:
        adicionados, duplicados = biblioteca.carregar_livros_de_csv(temp_path)
        return adicionados, duplicados
    finally:
        # Garante a destruição do arquivo temporário mesmo em caso de exceções no parser
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ==============================================================================
# 6. CONFIGURAÇÃO DA BARRA LATERAL (SIDEBAR)
# ==============================================================================

# Seção 1: Upload Manual de planilhas CSV de Acervos
st.sidebar.markdown("### 📥 Importação de Acervo")
uploaded_file = st.sidebar.file_uploader(
    "Fazer upload de arquivo de acervo (.csv)",
    type=['csv'],
    help="O arquivo deve conter as colunas: codigo,titulo,autor,ano,genero,disponivel"
)

if uploaded_file is not None:
    try:
        add, dup = processar_upload_csv(uploaded_file)
        if add > 0:
            st.sidebar.success(f"Sucesso! {add} livros importados. ({dup} duplicados ignorados)")
        else:
            st.sidebar.warning(f"Nenhum livro novo importado. ({dup} duplicados ignorados)")
    except Exception as e:
        st.sidebar.error(f"Erro ao carregar arquivo: {e}")

# Seção 2: Carga Rápida (Carregadores integrados de bases preexistentes de teste)
st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ Carga Rápida de Exemplo")
col_b1, col_b2 = st.sidebar.columns(2)
with col_b1:
    if st.button("Exemplo Padrão", width='stretch', help="Carrega a base livros_exemplo.csv"):
        try:
            add, dup = biblioteca.carregar_livros_de_csv("livros_exemplo.csv")
            st.sidebar.success(f"Carregados {add} livros do exemplo padrão ({dup} duplicados).")
        except Exception as e:
            st.sidebar.error(f"Erro: {e}")
with col_b2:
    if st.button("Exemplo Grande", width='stretch', help="Carrega a base livros_exemplo_grande.csv"):
        try:
            add, dup = biblioteca.carregar_livros_de_csv("livros_exemplo_grande.csv")
            st.sidebar.success(f"Carregados {add} livros do exemplo grande ({dup} duplicados).")
        except Exception as e:
            st.sidebar.error(f"Erro: {e}")

# Seção 3: Conexão direta com Servidor GraphQL Suwayomi (Funcionalidade Livre)
st.sidebar.markdown("---")
st.sidebar.markdown("### 🌐 Integração Suwayomi")
suwayomi_url = st.sidebar.text_input(
    "URL do Servidor Suwayomi", 
    value="https://suwayomi-server-ak4ai.fly.dev/api/graphql",
    help="URL do endpoint GraphQL do seu servidor Suwayomi"
)

if st.sidebar.button("Importar Biblioteca Suwayomi", width='stretch'):
    try:
        import urllib.request
        import json
        import re
        
        # Query GraphQL para mapear catálogo do servidor
        query = """
        query {
          mangas(filter: { inLibrary: { equalTo: true } }) {
            nodes {
              id
              title
              author
              genre
              thumbnailUrl
            }
          }
        }
        """
        
        req = urllib.request.Request(
            suwayomi_url,
            data=json.dumps({'query': query}).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=15) as response:
            res = json.loads(response.read().decode('utf-8'))
            
        if 'errors' in res:
            st.sidebar.error(f"Erro no GraphQL: {res['errors'][0]['message']}")
        else:
            nodes = res['data']['mangas']['nodes']
            adicionados = 0
            duplicados = 0
            
            for node in nodes:
                manga_id = node['id']
                codigo = f"S{manga_id}"  # Prefixo 'S' indica obra digital
                titulo = node['title']
                autor = node.get('author') or "Autor Desconhecido"
                
                genres = node.get('genre', [])
                genero = ", ".join(genres) if genres else "Mangá"
                
                # Tenta extrair ano de parênteses no título, ex: "Batman (1940)" -> 1940
                ano = 2026
                match = re.search(r'\((\d{4})\)', titulo)
                if match:
                    ano = int(match.group(1))
                
                # Resolve caminhos relativos de imagens de capa providos pelo Suwayomi
                thumbnail_rel = node.get('thumbnailUrl')
                capa_url = None
                if thumbnail_rel:
                    from urllib.parse import urlparse
                    parsed = urlparse(suwayomi_url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    capa_url = f"{base_url}{thumbnail_rel}"
                
                # Adiciona livro no acervo da biblioteca local
                livro = Livro(codigo, titulo, autor, ano, genero, disponivel=True, capa_url=capa_url)
                
                try:
                    biblioteca.adicionar_livro(livro)
                    adicionados += 1
                except CodigoDuplicadoError:
                    duplicados += 1
            
            if adicionados > 0:
                if 'suwayomi_cache_v2' in st.session_state:
                    st.session_state.suwayomi_cache_v2.clear()
                st.sidebar.success(f"Sucesso! {adicionados} mangás importados do Suwayomi. ({duplicados} já existentes)")
                st.rerun()
            else:
                st.sidebar.warning(f"Nenhum mangá novo importado. ({duplicados} já existentes)")
                
    except Exception as e:
        st.sidebar.error(f"Erro ao conectar ao Suwayomi: {e}")

# Seção 4: Filtros Interativos de Acervo (Disponíveis caso existam livros no acervo)
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔍 Filtros de Pesquisa")

has_books = len(biblioteca.livros) > 0

if has_books:
    # Busca textual reativa
    filtro_busca = st.sidebar.text_input("Buscar Título ou Autor", placeholder="Ex: Machado, Asimov...")

    # Extrai gêneros únicos mapeados nas obras do acervo para alimentar filtro multiselect
    generos_individuais = set()
    for l in biblioteca.livros:
        if l.genero:
            for g in l.genero.split(','):
                g_clean = g.strip()
                if g_clean:
                    generos_individuais.add(g_clean)
    generos_disponiveis = sorted(list(generos_individuais))
    filtro_generos = st.sidebar.multiselect("Filtrar por Gênero", options=generos_disponiveis, default=[])

    # Filtro por categorias lógicas
    filtro_status = st.sidebar.selectbox("Status de Disponibilidade", ["Todos", "Disponível", "Emprestado", "Digital", "Lido"])

    # Intervalo de anos com Slider
    anos = [l.ano for l in biblioteca.livros]
    ano_min, ano_max = min(anos), max(anos)
    if ano_min == ano_max:
        ano_max += 1
    filtro_ano_range = st.sidebar.slider("Intervalo de Ano", int(ano_min), int(ano_max), (int(ano_min), int(ano_max)))
else:
    st.sidebar.info("Aguardando carregamento de acervo para habilitar filtros.")

# ------------------------------------------------------------------------------
# 7. CONSTRUÇÃO DO PAINEL PRINCIPAL (ABAS / TABS)
# ------------------------------------------------------------------------------
tab_acervo, tab_emprestimos, tab_usuarios, tab_avaliacoes = st.tabs([
    "📚 Acervo e Estatísticas",
    "👥 Empréstimos & Devoluções",
    "🛠️ Cadastros & Administração",
    "⭐ Avaliações & Leitura"
])

# ==============================================================================
# ABA 1: ACERVO E ESTATÍSTICAS
# ==============================================================================
with tab_acervo:
    if not has_books:
        st.info("💡 **Dica de início rápido**: Use os botões na barra lateral para carregar a base de livros de exemplo ('Exemplo Padrão' ou 'Exemplo Grande') ou faça upload do seu próprio arquivo CSV.")
        st.subheader("Configurações iniciais do sistema:")
        st.markdown("""
        O sistema já está inicializado com **3 usuários de teste** cadastrados prontos para uso:
        - `U001` - Ana Souza
        - `U002` - Bruno Lima
        - `U003` - Carlos Oliveira
        
        Carregue os livros para poder realizar empréstimos e visualizar estatísticas completas!
        """)
    else:
        # APLICAÇÃO DOS FILTROS DA BARRA LATERAL À LISTA DE LIVROS
        livros_filtrados = biblioteca.livros
        
        # Filtro 1: Texto
        if filtro_busca:
            busca_lower = filtro_busca.lower()
            livros_filtrados = [
                l for l in livros_filtrados 
                if busca_lower in l.titulo.lower() or busca_lower in l.autor.lower()
            ]
            
        # Filtro 2: Gêneros Literários
        if filtro_generos:
            livros_filtrados_temp = []
            for l in livros_filtrados:
                if l.genero:
                    livro_genres = [g.strip() for g in l.genero.split(',')]
                    if any(g in filtro_generos for g in livro_genres):
                        livros_filtrados_temp.append(l)
            livros_filtrados = livros_filtrados_temp
            
        # Filtro 3: Status lógico de disponibilidade e leitura
        if filtro_status == "Disponível":
            livros_filtrados = [l for l in livros_filtrados if l.disponivel and not l.codigo.startswith("S")]
        elif filtro_status == "Emprestado":
            livros_filtrados = [l for l in livros_filtrados if not l.disponivel and not l.codigo.startswith("S")]
        elif filtro_status == "Digital":
            livros_filtrados = [l for l in livros_filtrados if l.codigo.startswith("S")]
        elif filtro_status == "Lido":
            livros_filtrados = [l for l in livros_filtrados if getattr(l, "lido", False)]
            
        # Filtro 4: Escopo Temporal de Anos
        livros_filtrados = [
            l for l in livros_filtrados 
            if filtro_ano_range[0] <= l.ano <= filtro_ano_range[1]
        ]
        
        # PAINEL DE INDICADORES (MÉTRIQUES OPERACIONAIS)
        col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
        
        total_livros = len(biblioteca.livros)
        total_filtrados = len(livros_filtrados)
        livros_disponiveis = sum(1 for l in biblioteca.livros if l.disponivel and not l.codigo.startswith("S"))
        livros_emprestados = sum(1 for l in biblioteca.livros if not l.disponivel and not l.codigo.startswith("S"))
        livros_digitais = sum(1 for l in biblioteca.livros if l.codigo.startswith("S"))
        total_fisicos = livros_disponiveis + livros_emprestados
        taxa_disponibilidade = (livros_disponiveis / total_fisicos * 100) if total_fisicos > 0 else 0
        
        with col_m1:
            st.metric("Total no Acervo", f"{total_livros}", help="Total de livros cadastrados (Físicos + Digitais)")
        with col_m2:
            st.metric("Físicos Livres", f"{livros_disponiveis}", delta=f"{livros_disponiveis} livres", delta_color="normal")
        with col_m3:
            st.metric("Físicos Emprestados", f"{livros_emprestados}", delta=f"{livros_emprestados} ocupados", delta_color="inverse")
        with col_m4:
            st.metric("Digitais (Suwayomi)", f"{livros_digitais}", help="Livros digitais importados")
        with col_m5:
            st.metric("Disp. Física", f"{taxa_disponibilidade:.1f}%")
            
        st.markdown("---")
        
        # Transforma os objetos filtrados em um DataFrame do Pandas para alimentar visualizações e tabelas
        df_livros_data = []
        for l in livros_filtrados:
            df_livros_data.append({
                "Código": l.codigo,
                "Título": l.titulo,
                "Autor": l.autor,
                "Ano": l.ano,
                "Gênero": l.genero if l.genero else "Não especificado",
                "Status": "Digital" if l.codigo.startswith("S") else ("Disponível" if l.disponivel else "Emprestado")
            })
            
        df_livros = pd.DataFrame(df_livros_data)
        
        # PAINEL DE ANÁLISE GRÁFICA DO ACERVO (MÍNIMO 2 GRÁFICOS)
        st.subheader("📊 Análise Visual do Acervo")
        
        if total_filtrados > 0:
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.markdown("##### Distribuição de Livros por Gênero")
                tipo_g1 = st.selectbox(
                    "Estilo de Visualização (Gênero)", 
                    ["Gráfico de Barras", "Gráfico de Linhas", "Gráfico de Área"], 
                    key="tipo_g1",
                    label_visibility="collapsed"
                )
                # Explode os gêneros mapeados (quando separados por vírgula em um livro) e conta suas frequências
                generos_expandidos = df_livros["Gênero"].astype(str).str.split(r",\s*").explode().str.strip()
                genero_series = generos_expandidos.value_counts()
                
                if tipo_g1 == "Gráfico de Barras":
                    st.bar_chart(genero_series, color="#3b82f6")
                elif tipo_g1 == "Gráfico de Linhas":
                    st.line_chart(genero_series, color="#3b82f6")
                else:
                    st.area_chart(genero_series, color="#3b82f6")
                
            with col_g2:
                st.markdown("##### Linha do Tempo de Publicação")
                tipo_g2 = st.selectbox(
                    "Tipo de Visualização Temporal", 
                    ["Anos Individuais (Sem Lacunas)", "Cronologia Real (Com Lacunas)", "Crescimento Acumulado"], 
                    key="tipo_g2",
                    label_visibility="collapsed"
                )
                # Agrupa e ordena obras de acordo com seu ano de publicação
                ano_series = df_livros["Ano"].value_counts().sort_index()
                
                if tipo_g2 == "Anos Individuais (Sem Lacunas)":
                    ano_series.index = ano_series.index.astype(str)
                    st.bar_chart(ano_series, color="#1e3a8a")
                elif tipo_g2 == "Cronologia Real (Com Lacunas)":
                    st.area_chart(ano_series, color="#1e3a8a")
                else:
                    # Gráfico de crescimento acumulado do acervo ao longo do tempo (soma cumulativa)
                    acumulado_series = ano_series.cumsum()
                    st.line_chart(acumulado_series, color="#10b981")
        else:
            st.info("Carregue dados ou relaxe os filtros para gerar gráficos de análise.")
            
        st.markdown("---")
        
        # TABELA DE DADOS PREMIUM CUSTOMIZADA (HTML + JAVASCRIPT EM IFRAME)
        st.subheader(f"Livros no Acervo ({total_filtrados} exibidos)")
        
        if total_filtrados > 0:
            import json
            
            rows_html_list = []
            
            # Executa cacheamento de detalhes do Suwayomi/MyAnimeList antes de construir a tabela
            carregar_detalhes_suwayomi()
            
            for l in livros_filtrados:
                # Determina status e classes de cores da célula
                if getattr(l, "lido", False):
                    status_label = "Lido"
                    status_color = "#a855f7"
                elif l.codigo.startswith("S"):
                    status_label = "Digital"
                    status_color = "#3b82f6"
                elif l.disponivel:
                    status_label = "Disponível"
                    status_color = "#10b981"
                else:
                    status_label = "Emprestado"
                    status_color = "#f59e0b"
                
                # Monta a estrutura da Tooltip interativa da linha
                if l.codigo.startswith("S"):
                    manga_id = l.codigo[1:]
                    cache_info = st.session_state.suwayomi_cache_v2.get(manga_id, {})
                    desc_val = cache_info.get('description') or "Descrição indisponível."
                    
                    suwa_rating = cache_info.get('rating') or "⭐ Sem nota (MAL)"
                    nota_pessoal = getattr(l, "nota_pessoal", None)
                    if nota_pessoal is not None:
                        rating_val = f"{suwa_rating} | 👤 ⭐ {nota_pessoal:.1f} (Pessoal)"
                    else:
                        rating_val = suwa_rating
                    
                    resenha_val = getattr(l, "resenha", None)
                    resenha_html = f'<p style="font-style: italic; margin-bottom: 8px; color: #cbd5e1; font-size: 0.8rem; background-color: rgba(168,85,247,0.15); padding: 6px; border-left: 3px solid #a855f7; border-radius: 4px;">"{resenha_val}"</p>' if resenha_val else ''
                    
                    capa_img_tag = f'<img class="tooltip-img" src="{l.capa_url}" alt="Capa">' if getattr(l, "capa_url", None) else ''
                    tooltip_html = f"""
                    <div class="book-tooltip">
                        {capa_img_tag}
                        <strong class="tooltip-title">{l.titulo}</strong>
                        <span class="tooltip-rating">{rating_val}</span>
                        {resenha_html}
                        <p class="tooltip-desc">{desc_val}</p>
                    </div>
                    """
                else:
                    # Livros físicos obtêm nota e comentários cadastrados no diário de leitura
                    nota_pessoal = getattr(l, "nota_pessoal", None)
                    if nota_pessoal is not None:
                        rating_val = f"⭐ {nota_pessoal:.1f} (Sua Nota)"
                    else:
                        rating_val = "Físico"
                        
                    resenha_val = getattr(l, "resenha", None)
                    resenha_html = f'<p style="font-style: italic; margin-bottom: 8px; color: #cbd5e1; font-size: 0.8rem; background-color: rgba(168,85,247,0.15); padding: 6px; border-left: 3px solid #a855f7; border-radius: 4px;">"{resenha_val}"</p>' if resenha_val else ''
                    
                    safe_title = html_mod.escape(l.titulo)
                    safe_author = html_mod.escape(l.autor)
                    
                    # Placeholder para carregamento da capa e descrição assíncrona (OpenLibrary API)
                    tooltip_html = f"""
                    <div class="book-tooltip" data-book-title="{safe_title}" data-book-author="{safe_author}" data-loaded="false">
                        <div class="tooltip-cover-placeholder"></div>
                        <strong class="tooltip-title">{l.titulo}</strong>
                        <span class="tooltip-rating">{rating_val}</span>
                        {resenha_html}
                        <p class="tooltip-desc">Passe o mouse para carregar detalhes...</p>
                    </div>
                    """
                
                # Monta a estrutura da linha da tabela (TDs)
                row_html = f"""
                    <td style="font-family: monospace; font-weight: 600; color: #64748b;">{l.codigo}</td>
                    <td class="tooltip-trigger">
                        {l.titulo}
                        {tooltip_html}
                    </td>
                    <td>{l.autor}</td>
                    <td>{l.ano}</td>
                    <td>{l.genero if l.genero else "Não especificado"}</td>
                    <td>
                        <span style="background-color: {status_color}15; color: {status_color}; padding: 4px 8px; border-radius: 4px; font-size: 0.85rem; font-weight: 600; display: inline-block;">
                            {status_label}
                        </span>
                    </td>
                """
                # Normaliza quebras de linha para inserção segura no script Javascript
                rows_html_list.append(row_html.replace("\n", " ").replace("\r", " ").replace("</script>", "<\/script>"))

            # Serializa linhas processadas em formato JSON
            rows_json = json.dumps(rows_html_list)
            
            # Lemos o template HTML separado que contém o design e o comportamento lógico
            # (HTML, CSS e JavaScript de Tooltips e Rolagem Infinita)
            try:
                with open("acervo_template.html", "r", encoding="utf-8") as template_file:
                    template_content = template_file.read()
                # Injeta a string JSON das linhas geradas pelo Python no marcador {{ROWS_JSON}}
                html_content = template_content.replace("{{ROWS_JSON}}", rows_json)
            except Exception as e:
                st.error(f"Erro ao carregar o template do acervo: {e}")
                html_content = ""
            
            iframe_height = 650
            st.iframe(html_content, height=iframe_height)
            
            # Exportação de Dados em CSV (Requisito Mínimo)
            csv_export = df_livros.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Exportar Tabela Filtrada para CSV",
                data=csv_export,
                file_name="acervo_biblioteca_filtrado.csv",
                mime="text/csv",
                width='content'
            )
        else:
            st.warning("Nenhum livro atende aos critérios dos filtros selecionados.")

# ==============================================================================
# ABA 2: EMPRÉSTIMOS E DEVOLUÇÕES
# ==============================================================================
with tab_emprestimos:
    st.subheader("🔄 Controle Operacional de Empréstimos")
    
    col_e1, col_e2 = st.columns([1, 1.3])
    
    with col_e1:
        st.markdown("### 📤 Novo Empréstimo")
        
        # Filtra apenas livros físicos que estão de fato livres para retirada
        livros_disponiveis_list = [l for l in biblioteca.livros if l.disponivel and not l.codigo.startswith("S")]
        usuarios_ativos_list = [u for u in biblioteca.usuarios if u.ativo]
        
        if not livros_disponiveis_list:
            st.warning("⚠️ Não há livros disponíveis para empréstimo no momento.")
        elif not usuarios_ativos_list:
            st.warning("⚠️ Não há usuários ativos cadastrados no sistema.")
        else:
            # Dicionários elegantes para mapear strings de exibição aos IDs de negócio das entidades
            livro_options = {f"[{l.codigo}] {l.titulo} - {l.autor}": l.codigo for l in livros_disponiveis_list}
            user_options = {f"[{u.matricula}] {u.nome} ({u.email})": u.matricula for u in usuarios_ativos_list}
            
            selected_livro_str = st.selectbox("Selecione o Livro", list(livro_options.keys()))
            selected_user_str = st.selectbox("Selecione o Usuário", list(user_options.keys()))
            
            if st.button("Confirmar Empréstimo", type="primary", width='stretch'):
                cod_l = livro_options[selected_livro_str]
                mat_u = user_options[selected_user_str]
                try:
                    # Executa chamada de empréstimo no engine de negócio
                    biblioteca.emprestar_livro(cod_l, mat_u)
                    st.success("Empréstimo registrado com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao processar empréstimo: {e}")
                    
        st.markdown("---")
        
        st.markdown("### 📥 Registrar Devolução")
        # Filtra livros atualmente indisponíveis (emprestados)
        livros_emprestados = [l for l in biblioteca.livros if not l.disponivel]
        
        if not livros_emprestados:
            st.info("Nenhum livro pendente de devolução.")
        else:
            devolucao_options = {}
            for l in livros_emprestados:
                # Procura a transação de empréstimo em aberto daquele livro
                emp_ativo = None
                for emp in biblioteca.emprestimos:
                    if emp.livro.codigo == l.codigo and emp.ativo:
                        emp_ativo = emp
                        break
                
                if emp_ativo:
                    label = f"[{l.codigo}] {l.titulo} (Usuário: {emp_ativo.usuario.nome})"
                else:
                    label = f"[{l.codigo}] {l.titulo} (Sem empréstimo registrado)"
                
                devolucao_options[label] = l.codigo

            selected_devolucao_str = st.selectbox("Selecione o Livro para Devolução", list(devolucao_options.keys()))
            
            if st.button("Registrar Devolução", width='stretch'):
                cod_l = devolucao_options[selected_devolucao_str]
                try:
                    # Dá baixa do empréstimo no backend
                    biblioteca.devolver_livro(cod_l)
                    st.success("Devolução concluída com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao processar devolução: {e}")
                    
    with col_e2:
        st.markdown("### 📋 Empréstimos Registrados")
        
        if not biblioteca.emprestimos:
            st.info("Nenhum empréstimo foi registrado no sistema ainda.")
        else:
            # Constrói tabela contendo histórico consolidado das transações ocorridas na sessão
            emp_records = []
            for emp in biblioteca.emprestimos:
                emp_records.append({
                    "Livro": f"[{emp.livro.codigo}] {emp.livro.titulo}",
                    "Usuário": f"[{emp.usuario.matricula}] {emp.usuario.nome}",
                    "Data Empréstimo": emp.data_emprestimo,
                    "Data Devolução": emp.data_devolucao if emp.data_devolucao else "Pendente",
                    "Status": "Ativo" if emp.ativo else "Devolvido"
                })
            
            df_emp = pd.DataFrame(emp_records)
            st.dataframe(
                df_emp,
                width='stretch',
                hide_index=True
            )

# ==============================================================================
# ABA 3: CADASTROS E ADMINISTRAÇÃO
# ==============================================================================
with tab_usuarios:
    st.subheader("🛠️ Painel Administrativo de Cadastros")
    
    col_cad1, col_cad2 = st.columns(2)
    
    # Formulário 1: Cadastro Manual de Livros
    with col_cad1:
        st.markdown("### 📖 Cadastrar Livro Manual")
        with st.form("form_cadastro_livro", clear_on_submit=True):
            novo_codigo = st.text_input("Código do Livro", placeholder="Ex: L105").strip()
            novo_titulo = st.text_input("Título", placeholder="Ex: Grande Sertão: Veredas")
            novo_autor = st.text_input("Autor", placeholder="Ex: João Guimarães Rosa")
            novo_ano = st.number_input("Ano de Publicação", min_value=0, max_value=2100, value=2026)
            novo_genero = st.text_input("Gênero Literário", placeholder="Ex: Literatura, Ficção...")
            
            submit_livro = st.form_submit_button("Cadastrar Livro", width='stretch')
            
            if submit_livro:
                if not novo_codigo or not novo_titulo or not novo_autor or not novo_genero:
                    st.error("Todos os campos do formulário de livro são obrigatórios!")
                else:
                    livro_novo = Livro(novo_codigo, novo_titulo, novo_autor, int(novo_ano), novo_genero)
                    try:
                        biblioteca.adicionar_livro(livro_novo)
                        st.success(f"Livro '{novo_titulo}' adicionado ao acervo com sucesso!")
                        st.rerun()
                    except CodigoDuplicadoError as e:
                        st.error(f"Erro: {e}")
                    except Exception as e:
                        st.error(f"Erro inesperado: {e}")
                        
    # Formulário 2: Cadastro Manual de Usuários
    with col_cad2:
        st.markdown("### 👤 Cadastrar Novo Usuário")
        with st.form("form_cadastro_usuario", clear_on_submit=True):
            nova_matricula = st.text_input("Matrícula", placeholder="Ex: U004").strip()
            novo_nome = st.text_input("Nome Completo", placeholder="Ex: Marina Silva")
            novo_email = st.text_input("E-mail", placeholder="Ex: marina@email.com")
            
            submit_usuario = st.form_submit_button("Cadastrar Usuário", width='stretch')
            
            if submit_usuario:
                if not nova_matricula or not novo_nome or not novo_email:
                    st.error("Todos os campos do formulário de usuário são obrigatórios!")
                else:
                    usuario_novo = Usuario(nova_matricula, novo_nome, novo_email)
                    try:
                        biblioteca.cadastrar_usuario(usuario_novo)
                        st.success(f"Usuário '{novo_nome}' cadastrado com sucesso!")
                        st.rerun()
                    except MatriculaDuplicadaError as e:
                        st.error(f"Erro: {e}")
                    except Exception as e:
                        st.error(f"Erro inesperado: {e}")
                        
    st.markdown("---")
    
    # Seção 3: Controle e Gestão de Contas de Usuários (Ativar / Desativar)
    st.subheader("👥 Gestão de Usuários Cadastrados")
    if not biblioteca.usuarios:
        st.info("Nenhum usuário cadastrado.")
    else:
        col_list, col_act = st.columns([1.5, 1])
        
        # Lista em tabela o status atual dos usuários
        with col_list:
            user_records = []
            for u in biblioteca.usuarios:
                user_records.append({
                    "Matrícula": u.matricula,
                    "Nome": u.nome,
                    "E-mail": u.email,
                    "Status": "Ativo" if u.ativo else "Inativo"
                })
            df_users = pd.DataFrame(user_records)
            st.dataframe(df_users, width='stretch', hide_index=True)
            
        # Botões operacionais para alternar atividade (Ativar / Desativar)
        with col_act:
            st.markdown("##### Ativar/Desativar Usuário")
            user_dict = {f"[{u.matricula}] {u.nome} ({'Ativo' if u.ativo else 'Inativo'})": u for u in biblioteca.usuarios}
            selected_user_label = st.selectbox("Selecione o Usuário para Alterar Status", list(user_dict.keys()))
            u_obj = user_dict[selected_user_label]
            
            col_act1, col_act2 = st.columns(2)
            with col_act1:
                st.button("Ativar Usuário", disabled=u_obj.ativo, width='stretch', on_click=u_obj.ativar_usuario)
            with col_act2:
                st.button("Desativar Usuário", disabled=not u_obj.ativo, width='stretch', on_click=u_obj.desativar_usuario)
                    
    st.markdown("---")
    # Zona de Perigo: Botão administrativo para redefinir e zerar o estado da biblioteca na sessão
    st.markdown("### ⚠️ Zona de Perigo")
    if st.button("Reiniciar Biblioteca (Limpar Sessão)", type="secondary", width='stretch', help="Use esta opção para recarregar o sistema e aplicar atualizações no código"):
        if "biblioteca" in st.session_state:
            del st.session_state.biblioteca
        st.rerun()

# ==============================================================================
# ABA 4: AVALIAÇÕES & LEITURA
# ==============================================================================
with tab_avaliacoes:
    st.subheader("⭐ Avaliações & Histórico de Leitura")
    st.markdown("Gerencie seu progresso de leitura, marque obras como lidas e defina suas notas pessoais.")
    
    if not has_books:
        st.info("Cadastre livros ou importe mangás para poder avaliá-los.")
    else:
        col_av1, col_av2 = st.columns([1, 1.2])
        
        # Painel de Avaliação (Esquerda)
        with col_av1:
            st.markdown("### 📝 Avaliar / Marcar Leitura")
            
            livros_map = {f"[{l.codigo}] {l.titulo}": l for l in biblioteca.livros}
            selected_livro_lbl = st.selectbox("Escolha um Livro/Mangá", list(livros_map.keys()))
            l_selecionado = livros_map[selected_livro_lbl]
            
            # Caixa de seleção lógico "Marcar como Lido"
            is_lido = st.checkbox("Marcar como Lido", value=getattr(l_selecionado, "lido", False))
            
            # Atribuição de Nota e Comentário desbloqueada apenas se marcado como Lido
            rating_pessoal = st.slider(
                "Sua Nota Pessoal",
                min_value=0.0,
                max_value=10.0,
                value=float(getattr(l_selecionado, "nota_pessoal", 5.0) if getattr(l_selecionado, "nota_pessoal", None) is not None else 5.0),
                step=0.5,
                disabled=not is_lido,
                help="A nota só pode ser atribuída a livros marcados como lidos."
            )
            
            resenha_curta = st.text_area(
                "Resenha Curta",
                value=getattr(l_selecionado, "resenha", "") or "",
                max_chars=200,
                disabled=not is_lido,
                placeholder="Escreva seus comentários curtos sobre o livro (máx. 200 caracteres)..."
            )
            
            if st.button("Confirmar Status, Nota e Resenha", type="primary", width='stretch'):
                try:
                    if is_lido:
                        # Grava dados de leitura no objeto do livro
                        l_selecionado.marcar_como_lido(rating_pessoal, resenha_curta)
                        st.success(f"Sucesso! '{l_selecionado.titulo}' marcado como Lido com nota {rating_pessoal:.1f}.")
                    else:
                        # Limpa informações de leitura do objeto
                        l_selecionado.marcar_como_nao_lido()
                        st.success(f"Sucesso! Status de leitura de '{l_selecionado.titulo}' removido.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar avaliação: {e}")
                    
        # Diário de Leitura: Lista apenas obras lidas com notas e resenhas (Direita)
        with col_av2:
            st.markdown("### 🏆 Livros que Você Já Leu")
            
            livros_lidos = [l for l in biblioteca.livros if getattr(l, "lido", False)]
            
            if not livros_lidos:
                st.info("Nenhum livro marcado como lido no momento. Vá na coluna ao lado para marcar seu primeiro livro!")
            else:
                lidos_records = []
                for l in livros_lidos:
                    lidos_records.append({
                        "Código": l.codigo,
                        "Título": l.titulo,
                        "Autor": l.autor,
                        "Minha Nota": f"⭐ {l.nota_pessoal:.1f}" if getattr(l, "nota_pessoal", None) is not None else "Sem nota",
                        "Resenha": getattr(l, "resenha", "") or "Sem comentários"
                    })
                df_lidos = pd.DataFrame(lidos_records)
                st.dataframe(df_lidos, width='stretch', hide_index=True)
