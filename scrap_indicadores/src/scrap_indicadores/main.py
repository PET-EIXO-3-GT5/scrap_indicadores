import sys
import uvicorn

def main():
    print("Iniciando a extração de dados")
    if "pytest" not in sys.modules:
        uvicorn.run("scrap_indicadores.api:app", host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
