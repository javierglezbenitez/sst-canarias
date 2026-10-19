from sstcanarias.cli import parse_scene_name, scene_title

NAME = "S3B_SL_2_WST____20261018T232112_20261018T232412_20261019T000421_0180_126_016_0360_MAR_O_NR_004"


def test_parse_scene_name():
    assert parse_scene_name(NAME) == ("S3B", "2026-10-18T23:21:12Z")
    assert parse_scene_name(NAME + ".SEN3") == ("S3B", "2026-10-18T23:21:12Z")


def test_parse_scene_name_unknown_returns_none():
    assert parse_scene_name("otra_cosa.nc") is None


def test_scene_title_is_short_and_readable():
    assert scene_title(NAME) == "SST Canarias · Sentinel-3B · 18/10/2026 23:21 UTC"
    assert scene_title("raro") == "SST Canarias · raro"
