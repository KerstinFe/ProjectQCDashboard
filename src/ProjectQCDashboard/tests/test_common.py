

from ProjectQCDashboard.helper.common import (
    MakePathNice,
    SplitProjectName,
    convert_timestamps,
    removeLastNumber_fromFileName,
    CreateOutputFilePath,
    IsStandardSample
)


def test_split_project_name():
    name = "Astral_20250716_XYZ_HSdia_01"
    ProjectID, ProjectID_regex, ProjectID_regex_sql, ProjectID_Date = SplitProjectName(name)
    assert ProjectID == "Astral_20250716_XYZ"
    assert ProjectID_regex == "Astral_202507[0-9]{2}_XYZ"
    assert ProjectID_regex_sql == "Astral_202507___XYZ%"
    assert ProjectID_Date == "20250716" 

def test_make_path_nice():
    raw = '"C:\\some\\path\\file.csv"'
    nice = MakePathNice(raw)
    assert '"' not in nice and "'" not in nice
    assert "C:" in nice or "/" in nice


def test_convert_timestamps():
    date_in = "2025-08-01 12:34:56"
    date_str, time_str, datetime_str = convert_timestamps(date_in)
    assert date_str == "2025.08.01"
    assert time_str == "12:34:56"
    assert datetime_str == "2025-08-01T12:34:56"
    

def test_remove_last_number_from_filename():    
    assert removeLastNumber_fromFileName("Astral_20250716_XYZ_HSdia_01") == "Astral_20250716_XYZ_HSdia"


def test_create_output_file_path(tmp_path, monkeypatch):
    # Patch the CSVFolder used by CreateOutputFilePath by patching the helper module
    monkeypatch.setattr("ProjectQCDashboard.helper.common.CSVFolder", tmp_path.as_posix())
    path = CreateOutputFilePath("Astral_20250716_XYZ")
    assert path.endswith("_ProjectData.csv")
    assert str(path) == str(tmp_path /"Astral_20250716_XYZ_ProjectData.csv")
    # assert tmp_path.as_posix() in path


def test_is_standard_sample():
    assert IsStandardSample("QExactive_20250728_XYZ_HSstd_116")
    assert IsStandardSample("QExactive_20250728_XYZ_HS_standard_1")
    assert not IsStandardSample("QExactive_20250728_XYZ_HS_01")