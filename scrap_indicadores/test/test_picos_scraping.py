import asyncio
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal
from pysus.api.client import PySUS

from scrap_indicadores.extract_picos import fetch_dataset, fetch_sinan_dengue_picos
from scrap_indicadores.picos_indicators import (
    calculate_picos_indicators,
    calculate_sim_indicators,
    filter_picos,
)


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "picos"
SIM_API_SAMPLE_COLUMNS = ["CODMUNRES", "IDADE", "SEXO", "CAUSABAS"]


def load_fixture(name: str) -> pd.DataFrame:
    return pd.read_csv(FIXTURES_DIR / name, dtype=str).fillna("")


def assert_same_data(actual: pd.DataFrame, expected: pd.DataFrame) -> None:
    assert_frame_equal(
        actual.reset_index(drop=True).astype(str),
        expected.reset_index(drop=True).astype(str),
        check_dtype=False,
    )


class FakeRemoteFile:
    def __init__(self, name: str) -> None:
        self.path = Path(name)


class FakeLocalFile:
    def __init__(self, path: str) -> None:
        self.path = path


class FakeParquetReader:
    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df

    def df(self) -> pd.DataFrame:
        return self._df


class FakePysus:
    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df
        self.downloaded = []

    async def query(self, **kwargs):
        self.query_kwargs = kwargs
        return [
            FakeRemoteFile("DOPI2024.parquet"),
            FakeRemoteFile("DOSP2024.parquet"),
        ]

    async def download(self, remote_file: FakeRemoteFile):
        self.downloaded.append(remote_file.path.name)
        return FakeLocalFile(f"/tmp/{remote_file.path.name}")

    def read_parquet(self, paths):
        self.read_paths = paths
        return FakeParquetReader(self._df)


class FakePysusFiles:
    def __init__(self, files_by_name: dict[str, Path]) -> None:
        self.files_by_name = files_by_name
        self.downloaded = []

    async def query(self, **kwargs):
        self.query_kwargs = kwargs
        return [FakeRemoteFile(name) for name in self.files_by_name]

    async def download(self, remote_file: FakeRemoteFile):
        self.downloaded.append(remote_file.path.name)
        return FakeLocalFile(str(self.files_by_name[remote_file.path.name]))


def test_scraping_result_is_validated_only_for_picos_records():
    scraped_df = load_fixture("sim_raw.csv")
    expected_picos = load_fixture("sim_picos_expected.csv")
    fake_pysus = FakePysus(scraped_df)

    df = asyncio.run(fetch_dataset(fake_pysus, "sim", state="PI", year=2024))
    df_picos, municipality_column = filter_picos(df, ["CODMUNRES"])
    result = calculate_sim_indicators(df)

    assert fake_pysus.query_kwargs == {
        "dataset": "sim",
        "state": "PI",
        "year": 2024,
        "group": None,
    }
    assert fake_pysus.downloaded == ["DOPI2024.parquet", "DOSP2024.parquet"]
    assert municipality_column == "CODMUNRES"
    assert_same_data(df_picos, expected_picos)
    assert result["obitos_total"] == 3
    assert result["obitos_mulheres_idade_fertil"] == 1
    assert result["obitos_maternos"] == 2
    assert result["obitos_infantis"] == 1


def test_scraping_filter_keeps_only_related_remote_files_before_download():
    fake_pysus = FakePysus(pd.DataFrame({"CODMUNRES": ["220800"]}))

    asyncio.run(
        fetch_dataset(
            fake_pysus,
            "sim",
            state="PI",
            year=2024,
            filter_fn=lambda remote_file: remote_file.path.name.startswith(
                "DOPI"),
        )
    )

    assert fake_pysus.downloaded == ["DOPI2024.parquet"]
    assert fake_pysus.read_paths == ["/tmp/DOPI2024.parquet"]


def test_sinan_dengue_fetch_uses_national_file_and_filters_picos(tmp_path):
    dengue_path = tmp_path / "DENGBR24.parquet"
    other_path = tmp_path / "CHIKBR24.parquet"
    pd.DataFrame(
        {
            "ID_MN_RESI": ["220800", "221100", "220800"],
            "CLASSI_FIN": ["10", "10", "11"],
            "HOSPITALIZ": ["1", "2", "2"],
            "EVOLUCAO": ["1", "2", "1"],
        }
    ).to_parquet(dengue_path)
    pd.DataFrame({"ID_MN_RESI": ["220800"]}).to_parquet(other_path)
    fake_pysus = FakePysusFiles(
        {
            "DENGBR24.parquet": dengue_path,
            "CHIKBR24.parquet": other_path,
        }
    )

    df = asyncio.run(fetch_sinan_dengue_picos(fake_pysus, year=2024))

    assert fake_pysus.query_kwargs == {
        "dataset": "sinan",
        "group": "DENG",
        "year": 2024,
    }
    assert fake_pysus.downloaded == ["DENGBR24.parquet"]
    assert df["ID_MN_RESI"].tolist() == ["220800", "220800"]


def test_all_scraped_dataset_fixtures_match_expected_picos_csvs():
    datasets = [
        ("sim_raw.csv", "sim_picos_expected.csv", ["CODMUNRES"]),
        ("sih_raw.csv", "sih_picos_expected.csv", ["MUNIC_RES"]),
        ("sinan_raw.csv", "sinan_picos_expected.csv",
         ["ID_MN_RESI", "CO_MUN_RES"]),
        ("pni_raw.csv", "pni_picos_expected.csv", ["CODMUNRES", "CO_MUNICIP"]),
    ]

    for raw_csv, expected_csv, municipality_columns in datasets:
        df = load_fixture(raw_csv)
        expected = load_fixture(expected_csv)

        df_picos, municipality_column = filter_picos(df, municipality_columns)

        assert municipality_column in municipality_columns
        assert_same_data(df_picos, expected)


def test_indicators_match_expected_csv_from_picos_fixtures():
    indicators = calculate_picos_indicators(
        df_sim=load_fixture("sim_raw.csv"),
        df_sih=load_fixture("sih_raw.csv"),
        df_sinan=load_fixture("sinan_raw.csv"),
        df_pni=load_fixture("pni_raw.csv"),
    )
    expected = load_fixture("indicators_expected.csv")

    actual = pd.DataFrame(
        [
            {"base": base, "indicador": indicator, "valor": str(value)}
            for base, values in indicators.items()
            for indicator, value in values.items()
            if indicator != "coluna_municipio" and not isinstance(value, dict)
        ]
    )

    assert_same_data(actual, expected)


def test_real_pysus_api_sim_data_matches_picos_csv_snapshot():
    async def fetch_real_sim_pi_2024() -> pd.DataFrame:
        async with PySUS() as pysus:
            return await fetch_dataset(pysus, "sim", state="PI", year=2024)

    df = asyncio.run(fetch_real_sim_pi_2024())
    df_picos, municipality_column = filter_picos(df, ["CODMUNRES"])
    expected_sample = load_fixture("sim_api_picos_sample_expected.csv")
    expected_indicators = load_fixture("sim_api_indicators_expected.csv")

    actual_sample = df_picos[SIM_API_SAMPLE_COLUMNS].head(10)
    actual_indicators = pd.DataFrame(
        [
            {"indicador": indicator, "valor": str(value)}
            for indicator, value in calculate_sim_indicators(df).items()
        ]
    )

    assert municipality_column == "CODMUNRES"
    assert_same_data(actual_sample, expected_sample)
    assert_same_data(actual_indicators, expected_indicators)
