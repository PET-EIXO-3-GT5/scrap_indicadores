import pytest

import os
import shutil

@pytest.fixture(scope="session")
def shared_data_dir():
    """
    Diretório compartilhado para toda a sessão de testes E2E.
    Salva os arquivos dentro do repositório em 'test/e2e/test_output' para inspeção do usuário.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "test_output")
    
    # Limpa o diretório de testes anteriores para evitar sujeira
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    return output_dir
