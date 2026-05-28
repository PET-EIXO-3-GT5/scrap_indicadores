from importlib.metadata import version


def main():
    pysus_version = version("pysus")
    print(f"PySUS instalado. Versao: {pysus_version}")

if __name__ == "__main__":
    main()
