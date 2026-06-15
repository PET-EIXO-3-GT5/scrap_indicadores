from scrap_indicadores.main import main

def test_main(capsys):
    main()
    captured = capsys.readouterr()
    assert "Iniciando a extração de dados" in captured.out
