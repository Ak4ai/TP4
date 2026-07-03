# ==============================================================================
# TRABALHO PRÁTICO 4 - SISTEMA DE GESTÃO DE BIBLIOTECA
# Disciplina: Programação em Python
# Aluno: Henrique de Freitas Araujo
# Instituição: CEFET-MG
# ==============================================================================
# Este módulo (biblioteca.py) representa a camada de MODELO / BACKEND do sistema.
# Ele encapsula toda a lógica de negócio, entidades de domínio (Livro, Usuario, 
# Emprestimo, Biblioteca), validações de consistência e o parser para arquivos CSV.
# ==============================================================================

import csv
import os

# ==============================================================================
# 1. EXCEÇÕES CUSTOMIZADAS (TRATAMENTO DE ERROS DE NEGÓCIO)
# ==============================================================================
# Em vez de utilizar exceções genéricas, criamos classes específicas herdando da
# classe base 'Exception'. Isso permite um controle granular do fluxo do sistema e 
# facilita a exibição de mensagens claras na interface gráfica do Streamlit.

class CodigoDuplicadoError(Exception):
    """Exceção lançada quando tenta-se adicionar um livro com código já cadastrado."""
    pass

class MatriculaDuplicadaError(Exception):
    """Exceção lançada quando tenta-se cadastrar um usuário com matrícula já existente."""
    pass

class LivroNaoEncontradoError(Exception):
    """Exceção lançada quando o livro não é encontrado no acervo."""
    pass

class UsuarioNaoEncontradoError(Exception):
    """Exceção lançada quando o usuário não é encontrado no cadastro."""
    pass

class LivroIndisponivelError(Exception):
    """Exceção lançada quando tenta-se emprestar um livro que já está emprestado."""
    pass

class UsuarioInativoError(Exception):
    """Exceção lançada quando tenta-se realizar um empréstimo para um usuário inativo."""
    pass

class EmprestimoNaoEncontradoError(Exception):
    """Exceção lançada quando tenta-se devolver um livro sem empréstimo ativo."""
    pass

class ArquivoAusenteError(Exception):
    """Exceção lançada quando o arquivo CSV não é encontrado no caminho especificado."""
    pass

class ArquivoVazioError(Exception):
    """Exceção lançada quando o arquivo CSV fornecido está vazio."""
    pass

class ArquivoInvalidoError(Exception):
    """Exceção lançada quando o arquivo CSV não contém colunas obrigatórias ou está corrompido."""
    pass


# ==============================================================================
# 2. CLASSES DE DOMÍNIO (ORIENTAÇÃO A OBJETOS)
# ==============================================================================

class Livro:
    """
    Representa uma obra literária no acervo da biblioteca.
    Contém os metadados do livro, seu estado de disponibilidade e controle de leitura.
    """
    
    # Construtor da classe Livro. Inicializa todos os dados básicos e de controle.
    def __init__(self, codigo, titulo, autor, ano, genero=None, disponivel=True, capa_url=None, lido=False, nota_pessoal=None, resenha=None):
        self.codigo = codigo          # Código identificador único (ex: L001, S15 para digitais)
        self.titulo = titulo          # Título da obra
        self.autor = autor            # Nome do autor
        self.ano = ano                # Ano de publicação (inteiro)
        self.genero = genero          # Gênero literário (pode conter múltiplos separados por vírgula)
        self.disponivel = disponivel  # Status de disponibilidade física (True/False)
        self.capa_url = capa_url      # URL externa para imagem de capa (usado na integração digital)
        self.lido = lido              # Indicador pessoal se o usuário já leu a obra (True/False)
        self.nota_pessoal = nota_pessoal  # Avaliação numérica pessoal de 0.0 a 10.0
        self.resenha = resenha        # Comentário de texto curto (resenha) sobre a obra

    # Altera o status para indisponível (livro foi emprestado)
    def marcar_como_emprestado(self):
        self.disponivel = False

    # Altera o status para disponível (livro foi devolvido)
    def marcar_como_disponivel(self):
        self.disponivel = True

    # Registra que a obra foi lida pelo usuário, aplicando nota e resenha opcional
    def marcar_como_lido(self, nota=None, resenha=None):
        self.lido = True
        if nota is not None:
            self.nota_pessoal = nota
        if resenha is not None:
            self.resenha = resenha

    # Remove os dados de leitura e marca o livro novamente como não lido
    def marcar_como_nao_lido(self):
        self.lido = False
        self.nota_pessoal = None
        self.resenha = None

    # Retorna uma representação em string formatada do status atual do livro
    def retornar_descricao(self):
        if getattr(self, "lido", False):
            status = "Lido"
        elif self.codigo.startswith("S"):
            status = "Digital"
        elif self.disponivel == True:
            status = "Disponivel"
        else:
            status = "Emprestado"
        genero_str = f" | Genero: {self.genero}" if self.genero else ""
        return f"[{self.codigo}] {self.titulo} - {self.autor} ({self.ano}){genero_str} | Status: {status}"

    # Método mágico do Python para representação em string (__str__)
    def __str__(self):
        return self.retornar_descricao()


class Usuario:
    """
    Representa um usuário cadastrado no sistema da biblioteca que pode
    realizar empréstimos de livros físicos.
    """
    
    # Construtor do Usuário. Todo usuário inicia por padrão com status ATIVO.
    def __init__(self, matricula, nome, email):
        self.matricula = matricula    # Matrícula identificadora única (ex: U001)
        self.nome = nome              # Nome completo do usuário
        self.email = email            # Endereço de e-mail
        self.ativo = True             # Usuário começa ativo para empréstimos

    # Permite a reativação de um usuário desativado
    def ativar_usuario(self):
        self.ativo = True

    # Desativa o usuário, impedindo-o de contrair novos empréstimos
    def desativar_usuario(self):
        self.ativo = False

    # Retorna descrição textual detalhada do usuário e seu status de atividade
    def retornar_descricao(self):
        if self.ativo == True:
            status = "Ativo"
        else:
            status = "Inativo"
        return f"Matricula: {self.matricula} | Nome: {self.nome} | E-mail: {self.email} | Status: {status}"

    # Método mágico __str__ para impressão em console do usuário
    def __str__(self):
        return self.retornar_descricao()


class Emprestimo:
    """
    Representa um registro de empréstimo físico na biblioteca, associando
    um livro a um usuário e registrando as datas de movimentação.
    """
    
    # Construtor do Empréstimo. Registra a associação e inicializa o empréstimo como ATIVO (em aberto).
    def __init__(self, livro, usuario, data_emprestimo):
        self.livro = livro                        # Referência direta ao objeto do Livro emprestado
        self.usuario = usuario                    # Referência direta ao objeto do Usuário retirante
        self.data_emprestimo = data_emprestimo    # Data de retirada do livro (DD/MM/AAAA)
        self.data_devolucao = None                # Data de devolução (inicialmente nula)
        self.ativo = True                         # Status do empréstimo (True = Em aberto, False = Finalizado)

    # Finaliza a transação gravando a data de devolução e desativando o registro
    def registrar_devolucao(self, data_devolucao):
        self.data_devolucao = data_devolucao
        self.ativo = False

    # Retorna um resumo legível com o andamento da transação
    def retornar_resumo(self):
        if self.ativo == True:
            status_str = "Ativo (Em aberto)"
        else:
            status_str = f"Devolvido em {self.data_devolucao}"
        return f"Livro: '{self.livro.titulo}' | Usuario: {self.usuario.nome} | Emprestimo: {self.data_emprestimo} | Status: {status_str}"

    # Método mágico __str__ para representação textual do empréstimo
    def __str__(self):
        return self.retornar_resumo()


# ==============================================================================
# 3. CLASSE DE CONTROLE CENTRAL (BIBLIOTECA)
# ==============================================================================

class Biblioteca:
    """
    Classe de controle que gerencia coleções de livros, usuários e empréstimos.
    Implementa as regras de validação lógica de negócios e persistência em memória.
    """
    
    # Construtor da Biblioteca. Inicializa coleções vazias em memória.
    def __init__(self, nome):
        self.nome = nome            # Nome da unidade de biblioteca (ex: Biblioteca CEFET)
        self.livros = []            # Coleção (lista) de instâncias da classe Livro
        self.usuarios = []          # Coleção (lista) de instâncias da classe Usuario
        self.emprestimos = []        # Coleção (lista) de instâncias da classe Emprestimo

    # Insere um novo livro no acervo, validando contra chaves duplicadas
    def adicionar_livro(self, livro):
        # Validação: Garante que não haja dois livros com o mesmo código
        for l in self.livros:
            if l.codigo == livro.codigo:
                raise CodigoDuplicadoError(f"O livro '{livro.titulo}' nao pode ser adicionado. Codigo '{livro.codigo}' ja cadastrado!")
        
        self.livros.append(livro)
        print(f"Sucesso: Livro '{livro.titulo}' adicionado com sucesso.")
        return True

    # Cadastra um novo usuário no sistema, validando a matrícula única
    def cadastrar_usuario(self, usuario):
        # Validação: Garante que a matrícula seja única no sistema
        for u in self.usuarios:
            if u.matricula == usuario.matricula:
                raise MatriculaDuplicadaError(f"O usuario '{usuario.nome}' nao pode ser cadastrado. Matricula '{usuario.matricula}' ja existe!")
        
        self.usuarios.append(usuario)
        print(f"Sucesso: Usuario '{usuario.nome}' cadastrado com sucesso.")
        return True

    # Realiza busca flexível (por parte do título da obra) - Case Insensitive
    def buscar_livros_por_titulo(self, titulo):
        resultado = []
        for l in self.livros:
            # Normaliza para letras minúsculas para ignorar diferenças de caixa alta/baixa
            if titulo.lower() in l.titulo.lower():
                resultado.append(l)
        return resultado

    # Realiza busca flexível (por parte do nome do autor) - Case Insensitive
    def buscar_livros_por_autor(self, autor):
        resultado = []
        for l in self.livros:
            if autor.lower() in l.autor.lower():
                resultado.append(l)
        return resultado

    # Imprime no console todos os livros cadastrados na biblioteca
    def listar_livros(self):
        print(f"\n--- Livros da Biblioteca {self.nome} ---")
        if len(self.livros) == 0:
            print("Nenhum livro cadastrado.")
        else:
            for l in self.livros:
                print(l.retornar_descricao())

    # Imprime no console apenas os livros físicos que estão disponíveis (não emprestados)
    def listar_livros_disponiveis(self):
        print(f"\n--- Livros Disponiveis: {self.nome} ---")
        achou_algum = False
        for l in self.livros:
            if l.disponivel == True:
                print(l.retornar_descricao())
                achou_algum = True
        
        if achou_algum == False:
            print("Todos os livros estao emprestados.")

    # Registra o empréstimo de um livro para um usuário, após testar todas as validações
    def emprestar_livro(self, codigo_livro, matricula):
        # 1. Localização do livro pelo código fornecido
        livro_temp = None
        for l in self.livros:
            if l.codigo == codigo_livro:
                livro_temp = l
                break
        
        if livro_temp == None:
            raise LivroNaoEncontradoError(f"Codigo '{codigo_livro}' nao existe no acervo.")

        # 2. Localização do usuário pela matrícula fornecida
        usuario_temp = None
        for u in self.usuarios:
            if u.matricula == matricula:
                usuario_temp = u
                break
        
        if usuario_temp == None:
            raise UsuarioNaoEncontradoError(f"Matricula '{matricula}' nao cadastrada.")

        # 3. Validação de Regras de Negócio:
        # A. Livros digitais (prefixo 'S') não sofrem bloqueio de empréstimo físico
        if livro_temp.codigo.startswith("S"):
            raise Exception("Livros digitais (Suwayomi) nao precisam ser emprestados, pois estao sempre acessiveis!")

        # B. O livro físico deve estar disponível (livre)
        if livro_temp.disponivel == False:
            raise LivroIndisponivelError(f"O livro '{livro_temp.titulo}' ja esta emprestado.")

        # C. O usuário deve estar ativo
        if usuario_temp.ativo == False:
            raise UsuarioInativoError(f"O usuario '{usuario_temp.nome}' esta desativado.")

        # 4. Processamento da Transação:
        data = "19/06/2026"  # Data fixa de controle definida pelas especificações do trabalho
        novo_emp = Emprestimo(livro_temp, usuario_temp, data)
        
        # Altera o estado de disponibilidade do livro físico
        livro_temp.marcar_como_emprestado()
        
        # Guarda o empréstimo no histórico geral
        self.emprestimos.append(novo_emp)
        print(f"Sucesso: Livro '{livro_temp.titulo}' emprestado para '{usuario_temp.nome}'.")
        return True

    # Registra a devolução de um livro de volta ao acervo
    def devolver_livro(self, codigo_livro):
        # 1. Localização do livro no acervo
        livro_temp = None
        for l in self.livros:
            if l.codigo == codigo_livro:
                livro_temp = l
                break
        if not livro_temp:
            raise LivroNaoEncontradoError(f"Codigo '{codigo_livro}' nao existe no acervo.")

        # 2. Busca pelo empréstimo correspondente que está atualmente ativo (em aberto)
        emprestimo_temp = None
        for emp in self.emprestimos:
            if emp.livro.codigo == codigo_livro and emp.ativo == True:
                emprestimo_temp = emp
                break

        # 3. Tratamento de exceções e caminhos especiais:
        if emprestimo_temp == None:
            # Caso especial: Se o livro começou como indisponível direto do acervo e não tem registro
            # de empréstimo gerado, permitimos devolvê-lo para torná-lo livre sem erro de histórico.
            if livro_temp.disponivel == False:
                livro_temp.marcar_como_disponivel()
                print(f"Sucesso: Livro '{livro_temp.titulo}' que iniciou como indisponivel foi marcado como disponivel.")
                return True
            else:
                raise EmprestimoNaoEncontradoError(f"Nao achei nenhum emprestimo ativo para o livro '{codigo_livro}'.")

        # 4. Processamento da Devolução
        data_hj = "20/06/2026"  # Data fixa de devolução para controle de fluxos do trabalho
        emprestimo_temp.registrar_devolucao(data_hj)
        emprestimo_temp.livro.marcar_como_disponivel()
        print(f"Sucesso: Livro '{emprestimo_temp.livro.titulo}' devolvido por '{emprestimo_temp.usuario.nome}'.")
        return True

    # Imprime todos os registros de empréstimos atualmente em aberto
    def listar_emprestimos_ativos(self):
        print(f"\n--- Emprestimos Ativos: {self.nome} ---")
        contador = 0
        for emp in self.emprestimos:
            if emp.ativo == True:
                print(emp.retornar_resumo())
                contador = contador + 1
        
        if contador == 0:
            print("Nenhum emprestimo ativo.")

    # Carrega livros a partir de um arquivo CSV, implementando validação de arquivo e cabeçalhos
    def carregar_livros_de_csv(self, caminho_arquivo):
        # Validação 1: O arquivo físico existe no caminho especificado?
        if not os.path.exists(caminho_arquivo):
            raise ArquivoAusenteError(f"Arquivo nao encontrado: '{caminho_arquivo}'")
        
        # Validação 2: O arquivo está com tamanho 0 (vazio)?
        if os.path.getsize(caminho_arquivo) == 0:
            raise ArquivoVazioError(f"O arquivo '{caminho_arquivo}' esta vazio.")
        
        livros_carregados = []  # Lista temporária de instâncias lidas com sucesso no parsing
        
        try:
            with open(caminho_arquivo, mode='r', encoding='utf-8') as f:
                # Validação 3: Lê a primeira linha (cabeçalho) e confere se há dados
                header_line = f.readline()
                if not header_line or header_line.strip() == "":
                    raise ArquivoVazioError(f"O arquivo '{caminho_arquivo}' esta vazio.")
                
                # Reseta o cursor do arquivo para ler desde o início com o DictReader
                f.seek(0)
                reader = csv.DictReader(f)
                
                # Validação 4: Garante que os nomes de colunas no cabeçalho do CSV foram identificados
                if not reader.fieldnames:
                    raise ArquivoInvalidoError("Arquivo CSV invalido: cabecalho vazio ou ausente.")
                
                # Validação 5: Confere se TODAS as colunas obrigatórias estão declaradas no CSV
                colunas_obrigatorias = ['codigo', 'titulo', 'autor', 'ano', 'genero', 'disponivel']
                for col in colunas_obrigatorias:
                    if col not in reader.fieldnames:
                        raise ArquivoInvalidoError(f"Arquivo CSV invalido: coluna obrigatoria '{col}' nao encontrada no cabecalho.")
                
                # Loop de leitura das linhas do CSV (indexado a partir de 2 para reportar a linha do erro correta)
                for linha_num, row in enumerate(reader, start=2):
                    # Validação 6: Garante que nenhum campo obrigatório esteja em branco
                    for col in colunas_obrigatorias:
                        val = row.get(col)
                        if val is None or val.strip() == "":
                            raise ArquivoInvalidoError(f"Erro na linha {linha_num}: o campo '{col}' nao pode ser vazio.")
                    
                    codigo = row['codigo'].strip()
                    titulo = row['titulo'].strip()
                    autor = row['autor'].strip()
                    genero = row['genero'].strip()
                    
                    # Validação 7: Garante que o ano seja um número inteiro
                    try:
                        ano = int(row['ano'].strip())
                    except ValueError:
                        raise ArquivoInvalidoError(f"Erro na linha {linha_num}: ano '{row['ano']}' invalido. Deve ser um numero inteiro.")
                    
                    # Validação 8: Converte representação textual de disponibilidade em booleano
                    disp_str = row['disponivel'].strip().lower()
                    if disp_str in ['sim', 'true', '1']:
                        disponivel = True
                    elif disp_str in ['nao', 'não', 'false', '0']:
                        disponivel = False
                    else:
                        raise ArquivoInvalidoError(f"Erro na linha {linha_num}: status de disponibilidade '{row['disponivel']}' invalido. Deve ser 'sim' ou 'nao'.")
                    
                    # Se passou em todas as checagens, cria o objeto Livro e adiciona na lista de buffers
                    livro = Livro(codigo, titulo, autor, ano, genero, disponivel)
                    livros_carregados.append(livro)
                    
        except Exception as e:
            # Repassa as exceções de arquivo customizadas diretamente
            if isinstance(e, (ArquivoVazioError, ArquivoInvalidoError, ArquivoAusenteError)):
                raise e
            # Encapsula quaisquer outros problemas de parsing no formatador geral
            raise ArquivoInvalidoError(f"Erro inesperado ao processar o CSV: {e}")
            
        # Pós-processamento de carga: Adiciona os livros lidos ao acervo da biblioteca
        adicionados = 0
        duplicados = 0
        for livro in livros_carregados:
            try:
                # Tenta adicionar. Se houver código repetido em relação ao acervo atual,
                # a biblioteca lançará CodigoDuplicadoError, o qual capturamos para apenas pular a linha
                self.adicionar_livro(livro)
                adicionados += 1
            except CodigoDuplicadoError:
                duplicados += 1
                
        # Retorna o relatório final da importação para a interface gráfica exibir
        return adicionados, duplicados


# ==============================================================================
# 4. EXECUÇÃO DEMONSTRATIVA EM CONSOLE (MAIN)
# ==============================================================================
if __name__ == '__main__':
    print("------------------------------------------------------------")
    print("INICIO DA DEMONSTRACAO - SISTEMA DE BIBLIOTECA")
    print("------------------------------------------------------------")
    
    # Cria a biblioteca de demonstração
    biblioteca = Biblioteca("Biblioteca CEFET")

    # 1. Testes de cadastro de livros
    print("\n1) Cadastrando livros no sistema...")
    livro1 = Livro("L001", "Dom Casmurro", "Machado de Assis", 1899)
    livro2 = Livro("L002", "1984", "George Orwell", 1949)
    livro3 = Livro("L003", "Python Fluente", "Luciano Ramalho", 2015)
    
    try:
        biblioteca.adicionar_livro(livro1)
        biblioteca.adicionar_livro(livro2)
        biblioteca.adicionar_livro(livro3)
    except Exception as e:
        print(f"Erro inesperado no cadastro de livros: {e}")

    # Testando captura de erro de código repetido
    print("\nTentando adicionar livro com codigo repetido:")
    livro_duplicado = Livro("L001", "Memoria de Elefante", "Lobo Antunes", 1979)
    try:
        biblioteca.adicionar_livro(livro_duplicado)
    except CodigoDuplicadoError as e:
        print(f"Capturado erro esperado: {e}")

    # 2. Testes de cadastro de usuários
    print("\n2) Cadastrando usuarios no sistema...")
    usuario1 = Usuario("U001", "Ana Souza", "ana@email.com")
    usuario2 = Usuario("U002", "Bruno Lima", "bruno@email.com")
    
    try:
        biblioteca.cadastrar_usuario(usuario1)
        biblioteca.cadastrar_usuario(usuario2)
    except Exception as e:
        print(f"Erro inesperado no cadastro de usuarios: {e}")

    # Testando captura de erro de matrícula repetida
    print("\nTentando cadastrar usuario com matricula repetida:")
    usuario_duplicado = Usuario("U001", "Carlos Oliveira", "carlos@email.com")
    try:
        biblioteca.cadastrar_usuario(usuario_duplicado)
    except MatriculaDuplicadaError as e:
        print(f"Capturado erro esperado: {e}")

    # 3. Teste de listagem
    print("\n3) Listando todos os livros:")
    biblioteca.listar_livros()

    # 4. Testes de busca textual
    print("\n4) Testando buscas de livros:")
    print("Buscando por titulo '1984':")
    resultado_titulo = biblioteca.buscar_livros_por_titulo("1984")
    for l in resultado_titulo:
        print("->", l)

    print("Buscando por autor 'Ramalho':")
    resultado_autor = biblioteca.buscar_livros_por_autor("Ramalho")
    for l in resultado_autor:
        print("->", l)

    # Listando as obras que iniciam como disponíveis
    biblioteca.listar_livros_disponiveis()

    # 5. Registro de empréstimo válido
    print("\n5) Emprestando L001 para U001:")
    try:
        biblioteca.emprestar_livro("L001", "U001")
    except Exception as e:
        print(f"Erro ao realizar emprestimo: {e}")

    # 6. Testando bloqueio de livro indisponível (já emprestado)
    print("\n6) Tentando emprestar o L001 de novo (deve dar erro):")
    try:
        biblioteca.emprestar_livro("L001", "U002")
    except LivroIndisponivelError as e:
        print(f"Capturado erro esperado: {e}")

    # Testando bloqueio de empréstimo para usuário inativo
    print("\nDesativando usuario U002 e tentando fazer emprestimo:")
    usuario2.desativar_usuario()
    try:
        biblioteca.emprestar_livro("L002", "U002")
    except UsuarioInativoError as e:
        print(f"Capturado erro esperado: {e}")
    usuario2.ativar_usuario()  # Reativa o usuário para os próximos testes

    # 8. Listagem de empréstimos ativos
    print("\n8) Listando emprestimos ativos:")
    biblioteca.listar_emprestimos_ativos()

    # 7. Operação de devolução válida
    print("\n7) Devolvendo o livro L001:")
    try:
        biblioteca.devolver_livro("L001")
    except Exception as e:
        print(f"Erro ao devolver livro: {e}")

    # Listando os disponíveis após a devolução ocorrer
    biblioteca.listar_livros_disponiveis()

    # Listando os ativos pós devolução
    biblioteca.listar_emprestimos_ativos()
    
    print("\n------------------------------------------------------------")
    print("FIM DA DEMONSTRACAO")
    print("------------------------------------------------------------")
