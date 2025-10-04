import pandas as pd
import numpy as np
import pandas as pd
from typing import Tuple
import numpy as np
import pandas as pd
import datetime
from ProjectQCDashboard.helper.processDataForFig import preprocess_data, filter_df, Create_DFs


def make_sample_df(n: int = 12, include_standards: bool = True, include_placeholderdate: bool = True) -> pd.DataFrame:
    """Create a sample DataFrame compatible with processDataForFig functions.

    Columns created: DateTime (ISO strings), Date (string), FileType, Intensity.100.
    include_standards: if True, some rows will have FileType as 'HSstd' or 'OtherStandard'
    include_placeholderdate: if True, one row will have Date as '1900.01.01'
    
    :param n: number of rows to create
    :param include_standards: whether to include some standard file types
    :param include_placeholderdate: whether to include a placeholder date '1900.01.01'
    :return: DataFrame with sample data
    :rtype: pd.DataFrame

    """
    rows = []
    base = datetime.datetime(2025, 8, 1, 12, 0, 0)
    for i in range(n):
        dt = base + datetime.timedelta(days=i)
        # Alternate file types and insert some standards if requested
        if include_standards and i % 5 == 0:
            ftype = "HSstd"
        elif include_standards and i % 7 == 0:
            ftype = "OtherStandard"
        else:
            ftype = "Sample"

        # insert a placeholder date for one row
        if include_placeholderdate:
            if i == 1:
                date_val = "1900.01.01"
            else:
                date_val = dt.strftime("%Y.%m.%d")
        else:
            date_val = dt.strftime("%Y.%m.%d")        

        # make intensity numeric strings and one NaN
        if i % 6 == 0:
            intensity = None
        else:
            intensity = float(10 + i * 2)

        rows.append({
            "Name": f"sample_{i}",
            "DateTime": dt.isoformat(),
            "Date": date_val,
            "FileType": ftype,
            "Intensity.100.": intensity,
        })

    return pd.DataFrame(rows)


def test_preprocess_data_removes_placeholder_and_sorts():
    """ Test that preprocess_data removes placeholder dates and sorts by DateTime"""
    
    df = make_sample_df(6)
    # shuffle rows to ensure sorting works
    df = df.sample(frac=1).reset_index(drop=True)

    out = preprocess_data(df)
    # placeholder '1900.01.01' should be removed
    assert not (out["Date"] == "1900.01.01").any()

    # DateTime should be converted to datetime and sorted ascending
    assert pd.api.types.is_datetime64_any_dtype(out["DateTime"]) is True
    assert out["DateTime"].is_monotonic_increasing


def test_filter_df_removes_standards_and_coerces():
    
    """Test that filter_df removes standard samples and coerces y-label to numeric"""
    

    df = make_sample_df(10, include_standards=True, include_placeholderdate=False)
    # ensure there are standards
    assert (df["FileType"].isin(["HSstd", "OtherStandard"]).sum()) >= 1

    filtered = filter_df(df.copy(), "Intensity.100.")
    # no standard file types remain
    assert not filtered["FileType"].isin(["HSstd", "OtherStandard"]).any()

    # no NaN in the y-label column and dtype numeric
    assert filtered["Intensity.100."].isna().sum() == 0
    assert pd.api.types.is_float_dtype(filtered["Intensity.100."])


def test_rolling_mean_and_median_df_calculations():
    """ Test rolling mean and median DF calculations"""

    # create a filtered DF with numeric values and no standards
    base = make_sample_df(15, include_standards=False, include_placeholderdate=False)
    # ensure no NaNs for this test
    base = base.dropna(subset=["Intensity.100."])

    df_filtered = base.reset_index(drop=True)
    y_label = "Intensity.100."

    creator = Create_DFs(df_filtered.copy(), y_label)

    # Test RollingMean_DF with width 3
    df_roll, mean_print, median_print, std_print = creator.RollingMean_DF(width=3)
    # rolling DF should have same number of rows as non-NaN original
    assert df_roll.shape[0] == df_filtered.shape[0]

    # mean_print should be close to numpy mean (pandas uses ddof=1 for std)
    expected_mean = float(np.mean(df_filtered[y_label].values))
    expected_median = float(np.median(df_filtered[y_label].values))
    expected_std = float(np.std(df_filtered[y_label].values, ddof=1))

    assert np.isclose(mean_print, expected_mean, rtol=1e-6)
    assert np.isclose(mean_print, 24.5, rtol=1e-6)
    assert np.isclose(median_print, expected_median, rtol=1e-6)
    assert np.isclose(std_print, expected_std, rtol=1e-6)

    # Test Median_DF
    creator2 = Create_DFs(df_filtered.copy(), y_label)
    df_med, mean_val, median_val, std_val = creator2.Median_DF()
    assert "Median" in df_med.columns and "Upper" in df_med.columns and "Lower" in df_med.columns
    assert np.isclose(median_val, expected_median, rtol=1e-6)
    assert np.isclose(mean_val, expected_mean, rtol=1e-6)
    assert np.isclose(std_val, expected_std, rtol=1e-6)
    assert df_med.shape[0] == df_filtered.shape[0]





