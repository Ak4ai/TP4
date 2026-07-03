# Trabalho Pratico 3 - Testes Unitarios
# Aluno: Henrique de Freitas Araujo
# Materia: Programacao em Python

import unittest
from biblioteca import (
    Biblioteca,
    Livro,
    Usuario,
    CodigoDuplicadoError,
    MatriculaDuplicadaError,
    LivroNaoEncontradoError,
    UsuarioNaoEncontradoError,
    LivroIndisponivelError,
    UsuarioInativoError,
    EmprestimoNaoEncontradoError,
    ArquivoAusenteError,
    ArquivoVazioError,
    ArquivoInvalidoError
)

class TestBiblioteca(unittest.TestCase):
    
    def setUp(self):
        # Cria uma biblioteca zerada para cada teste
        self.biblioteca = Biblioteca("Biblioteca CEFET Testes")
        
        # Cria e adiciona dados iniciais de teste
        self.livro1 = Livro("L001", "Dom Casmurro", "Machado de Assis", 1899)
        self.livro2 = Livro("L002", "1984", "George Orwell", 1949)
        self.usuario1 = Usuario("U001", "Ana Souza", "ana@email.com")
        self.usuario2 = Usuario("U002", "Bruno Lima", "bruno@email.com")
        
        self.biblioteca.adicionar_livro(self.livro1)
        self.biblioteca.adicionar_livro(self.livro2)
        self.biblioteca.cadastrar_usuario(self.usuario1)
        self.biblioteca.cadastrar_usuario(self.usuario2)

    # =========================================================================
    # CASOS VALIDOS (Caminho Feliz)
    # =========================================================================

    def test_adicionar_livro_com_sucesso(self):
        """Teste de caso valido: adiciona um livro novo e verifica se ele esta na biblioteca."""
        novo_livro = Livro("L003", "Python Fluente", "Luciano Ramalho", 2015)
        resultado = self.biblioteca.adicionar_livro(novo_livro)
        
        self.assertTrue(resultado) # Assercao 1: assertTrue
        self.assertIn(novo_livro, self.biblioteca.livros) # Assercao 2: assertIn

    def test_cadastrar_usuario_com_sucesso(self):
        """Teste de caso valido: cadastra um usuario novo e verifica se os dados conferem."""
        novo_usuario = Usuario("U003", "Carlos Oliveira", "carlos@email.com")
        resultado = self.biblioteca.cadastrar_usuario(novo_usuario)
        
        self.assertTrue(resultado)
        self.assertIn(novo_usuario, self.biblioteca.usuarios)
        self.assertEqual(novo_usuario.nome, "Carlos Oliveira") # Assercao 3: assertEqual

    def test_emprestimo_valido(self):
        """Teste de caso valido: realiza um emprestimo e verifica a mudanca de disponibilidade."""
        resultado = self.biblioteca.emprestar_livro("L001", "U001")
        
        self.assertTrue(resultado)
        self.assertFalse(self.livro1.disponivel) # Assercao 4: assertFalse
        self.assertEqual(len(self.biblioteca.emprestimos), 1)

    def test_devolucao_valida(self):
        """Teste de caso valido: faz a devolucao de um livro emprestado e verifica o retorno."""
        self.biblioteca.emprestar_livro("L001", "U001")
        resultado = self.biblioteca.devolver_livro("L001")
        
        self.assertTrue(resultado)
        self.assertTrue(self.livro1.disponivel)
        self.assertEqual(self.biblioteca.emprestimos[0].ativo, False)

    # =========================================================================
    # CASOS DE ERRO (Excecoes)
    # =========================================================================

    def test_adicionar_livro_duplicado_lanca_excecao(self):
        """Teste de erro: tenta adicionar um livro com codigo ja existente e lanca CodigoDuplicadoError."""
        livro_duplicado = Livro("L001", "Outro Livro", "Autor Desconhecido", 2020)
        
        # Assercao 5: assertRaises
        with self.assertRaises(CodigoDuplicadoError):
            self.biblioteca.adicionar_livro(livro_duplicado)

    def test_cadastrar_usuario_duplicado_lanca_excecao(self):
        """Teste de erro: tenta cadastrar usuario com matricula duplicada."""
        usuario_duplicado = Usuario("U001", "Duplicado", "dup@email.com")
        
        with self.assertRaises(MatriculaDuplicadaError):
            self.biblioteca.cadastrar_usuario(usuario_duplicado)

    def test_emprestar_livro_inexistente_lanca_excecao(self):
        """Teste de erro: tenta emprestar um livro inexistente."""
        with self.assertRaises(LivroNaoEncontradoError):
            self.biblioteca.emprestar_livro("L999", "U001")

    def test_emprestar_usuario_inexistente_lanca_excecao(self):
        """Teste de erro: tenta emprestar livro para um usuario nao cadastrado."""
        with self.assertRaises(UsuarioNaoEncontradoError):
            self.biblioteca.emprestar_livro("L001", "U999")

    def test_emprestar_livro_indisponivel_lanca_excecao(self):
        """Teste de erro: tenta emprestar livro ja emprestado."""
        self.biblioteca.emprestar_livro("L001", "U001")
        
        with self.assertRaises(LivroIndisponivelError):
            self.biblioteca.emprestar_livro("L001", "U002")

    def test_emprestar_usuario_inativo_lanca_excecao(self):
        """Teste de erro: tenta emprestar livro para usuario inativo."""
        self.usuario2.desativar_usuario()
        
        with self.assertRaises(UsuarioInativoError):
            self.biblioteca.emprestar_livro("L001", "U002")

    def test_devolver_livro_sem_emprestimo_lanca_excecao(self):
        """Teste de erro: tenta devolver um livro que nao esta emprestado."""
        with self.assertRaises(EmprestimoNaoEncontradoError):
            self.biblioteca.devolver_livro("L002")

    def test_devolver_livro_inexistente_lanca_excecao(self):
        """Teste de erro: tenta devolver um livro que nao existe no acervo."""
        with self.assertRaises(LivroNaoEncontradoError):
            self.biblioteca.devolver_livro("L999")

    # =========================================================================
    # TESTES DE MANIPULACAO DE ARQUIVOS (CSV)
    # =========================================================================

    def test_carregar_livros_csv_com_sucesso(self):
        """Teste de caso valido: carrega um CSV de livros com sucesso e valida atributos."""
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("codigo,titulo,autor,ano,genero,disponivel\n")
            f.write("L100,The Lord of the Rings,J.R.R. Tolkien,1954,Fantasia,sim\n")
            f.write("L101,The Hobbit,J.R.R. Tolkien,1937,Fantasia,nao\n")
            temp_path = f.name
            
        try:
            adicionados, duplicados = self.biblioteca.carregar_livros_de_csv(temp_path)
            self.assertEqual(adicionados, 2)
            self.assertEqual(duplicados, 0)
            self.assertEqual(len(self.biblioteca.livros), 4) # 2 iniciais + 2 novos
            
            l100 = next(l for l in self.biblioteca.livros if l.codigo == "L100")
            self.assertEqual(l100.titulo, "The Lord of the Rings")
            self.assertEqual(l100.genero, "Fantasia")
            self.assertTrue(l100.disponivel)
            
            l101 = next(l for l in self.biblioteca.livros if l.codigo == "L101")
            self.assertFalse(l101.disponivel)
        finally:
            os.remove(temp_path)

    def test_carregar_livros_csv_arquivo_ausente_lanca_excecao(self):
        """Teste de erro: tenta carregar um arquivo inexistente e lanca ArquivoAusenteError."""
        with self.assertRaises(ArquivoAusenteError):
            self.biblioteca.carregar_livros_de_csv("caminho_inexistente_12345.csv")

    def test_carregar_livros_csv_arquivo_vazio_lanca_excecao(self):
        """Teste de erro: tenta carregar um arquivo vazio e lanca ArquivoVazioError."""
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            temp_path = f.name
            
        try:
            with self.assertRaises(ArquivoVazioError):
                self.biblioteca.carregar_livros_de_csv(temp_path)
        finally:
            os.remove(temp_path)

    def test_carregar_livros_csv_colunas_faltantes_lanca_excecao(self):
        """Teste de erro: tenta carregar CSV sem colunas obrigatorias no cabecalho."""
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("codigo,titulo,autor,ano\n") # faltam genero e disponivel
            f.write("L100,Sem Genero,Autor,2020\n")
            temp_path = f.name
            
        try:
            with self.assertRaises(ArquivoInvalidoError):
                self.biblioteca.carregar_livros_de_csv(temp_path)
        finally:
            os.remove(temp_path)

    def test_carregar_livros_csv_campo_vazio_lanca_excecao(self):
        """Teste de erro: tenta carregar CSV com campos obrigatorios vazios."""
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("codigo,titulo,autor,ano,genero,disponivel\n")
            f.write("L100,,Autor,2020,Fantasia,sim\n") # titulo vazio
            temp_path = f.name
            
        try:
            with self.assertRaises(ArquivoInvalidoError):
                self.biblioteca.carregar_livros_de_csv(temp_path)
        finally:
            os.remove(temp_path)

    def test_carregar_livros_csv_ano_invalido_lanca_excecao(self):
        """Teste de erro: tenta carregar CSV com ano que nao e inteiro."""
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("codigo,titulo,autor,ano,genero,disponivel\n")
            f.write("L100,Titulo,Autor,ano_invalido,Fantasia,sim\n")
            temp_path = f.name
            
        try:
            with self.assertRaises(ArquivoInvalidoError):
                self.biblioteca.carregar_livros_de_csv(temp_path)
        finally:
            os.remove(temp_path)

    def test_carregar_livros_csv_disponivel_invalido_lanca_excecao(self):
        """Teste de erro: tenta carregar CSV com valor de disponivel invalido."""
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("codigo,titulo,autor,ano,genero,disponivel\n")
            f.write("L100,Titulo,Autor,2020,Fantasia,talvez\n") # 'talvez' nao e valido
            temp_path = f.name
            
        try:
            with self.assertRaises(ArquivoInvalidoError):
                self.biblioteca.carregar_livros_de_csv(temp_path)
        finally:
            os.remove(temp_path)

    def test_carregar_livros_csv_com_duplicados_ignora(self):
        """Teste de comportamento: se o CSV tiver livro com codigo ja existente no acervo, pula ele."""
        import tempfile
        import os
        
        # 'L001' ja foi inserido no setUp
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("codigo,titulo,autor,ano,genero,disponivel\n")
            f.write("L001,Dom Casmurro Duplicado,Machado de Assis,1899,Literatura,sim\n")
            f.write("L102,Livro Novo,Autor Novo,2026,Literatura,sim\n")
            temp_path = f.name
            
        try:
            adicionados, duplicados = self.biblioteca.carregar_livros_de_csv(temp_path)
            self.assertEqual(adicionados, 1) # apenas L102
            self.assertEqual(duplicados, 1)   # L001 foi pulado
            # Verifica que L001 original nao foi sobrescrito
            l001 = next(l for l in self.biblioteca.livros if l.codigo == "L001")
            self.assertEqual(l001.titulo, "Dom Casmurro")
        finally:
            os.remove(temp_path)

    def test_devolucao_livro_inicialmente_indisponivel_sem_emprestimo(self):
        """Teste de caso especial: devolve um livro que comeca como indisponivel, mesmo sem registro de emprestimo ativo."""
        livro_indisp = Livro("L999", "Livro Indisponivel", "Autor Especial", 2026, "Ficcao", disponivel=False)
        self.biblioteca.adicionar_livro(livro_indisp)
        
        self.assertFalse(livro_indisp.disponivel)
        
        resultado = self.biblioteca.devolver_livro("L999")
        
        self.assertTrue(resultado)
        self.assertTrue(livro_indisp.disponivel)


if __name__ == '__main__':
    unittest.main()
