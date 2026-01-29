
import numpy as np
import pytest

import matplotlib
matplotlib.use("Agg")  # headless / CI-safe

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D


from xaux import plot_multi, MultiLineResult


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


def _make_data(N=50, M=4, seed=0):
    rng = np.random.default_rng(seed)
    Y = rng.normal(size=(N, M))
    x = np.linspace(0.0, 1.0, N)
    x2 = np.tile(x[:, None], (1, M)) + 0.01 * rng.normal(size=(N, M))
    return x, x2, Y


def test_callstyle_Y_only_defaults_x_indices_lines():
    _, _, Y = _make_data()
    res = plot_multi(Y)
    assert isinstance(res, MultiLineResult)
    assert res.mode == "lines"
    assert isinstance(res.artists, list)
    assert all(isinstance(a, Line2D) for a in res.artists)
    assert len(res.artists) == Y.shape[1]


def test_callstyle_Y_and_fmt_string_detected():
    _, _, Y = _make_data()
    res = plot_multi(Y, "k--", lw=1.2)
    # We don't assert linestyle exactly (matplotlib parsing can be nuanced),
    # but we do check that it created the right number/type of artists.
    assert res.mode == "lines"
    assert len(res.artists) == Y.shape[1]


def test_callstyle_x_Y_lines():
    x, _, Y = _make_data()
    res = plot_multi(x, Y)
    assert res.mode == "lines"
    assert len(res.artists) == Y.shape[1]


def test_callstyle_x2_Y_lines_per_curve_x():
    _, x2, Y = _make_data()
    res = plot_multi(x2, Y, "o-", markersize=2)
    assert res.mode == "lines"
    assert len(res.artists) == Y.shape[1]


def test_collection_mode_returns_linecollection():
    _, _, Y = _make_data()
    res = plot_multi(Y, mode="collection", linewidths=1.0, alpha=0.8)
    assert res.mode == "collection"
    assert isinstance(res.artists, LineCollection)


def test_add_colorbar_lines_creates_mappable():
    _, _, Y = _make_data()
    fig, ax = plt.subplots()
    res = plot_multi(Y, ax=ax, add_colorbar=True)
    assert res.mode == "lines"
    assert res.mappable is not None
    # Colorbar should have been added: axes count increases (main + cbar)
    assert len(fig.axes) >= 2


def test_add_colorbar_collection_uses_collection_as_mappable():
    _, _, Y = _make_data()
    fig, ax = plt.subplots()
    res = plot_multi(Y, ax=ax, mode="collection", add_colorbar=True)
    assert res.mode == "collection"
    assert isinstance(res.mappable, LineCollection)
    assert len(fig.axes) >= 2


def test_explicit_colors_disables_colorbar():
    _, _, Y = _make_data()
    cols = ["tab:blue", "tab:orange", "tab:green", "tab:red"]
    with pytest.raises(ValueError, match="not compatible"):
        plot_multi(Y, colors=cols, add_colorbar=True)


def test_colors_length_mismatch_raises():
    _, _, Y = _make_data(M=4)
    cols = ["k", "r"]  # wrong length
    with pytest.raises(ValueError, match="must have length"):
        plot_multi(Y, colors=cols)


def test_linestyles_broadcast_lines():
    _, _, Y = _make_data()
    res = plot_multi(Y, linestyles="--")
    assert res.mode == "lines"
    assert all(ln.get_linestyle() == "--" for ln in res.artists)


def test_linestyles_list_length_mismatch_raises():
    _, _, Y = _make_data(M=4)
    with pytest.raises(ValueError, match="linestyles.*length"):
        plot_multi(Y, linestyles=["-", "--"])


def test_shape_strictness_Y_must_be_NM():
    x, _, Y = _make_data(N=20, M=3)
    # Provide Y as (M, N) instead of (N, M) -> should raise with advice to transpose
    with pytest.raises(ValueError, match=r"(?s)Y\.shape=.*transpose"):
        plot_multi(x, Y.T)


def test_shape_strictness_x_must_match_Y_columns():
    x, _, Y = _make_data(N=30, M=5)
    x_bad = np.linspace(0.0, 1.0, 29)  # wrong N
    with pytest.raises(ValueError, match=r"(?s)N == len\(x\).*Got len\(x\)=29"):
        plot_multi(x_bad, Y)


def test_shape_strictness_x2_must_be_NM():
    x, _, Y = _make_data(N=30, M=5)
    x2_bad = np.tile(x[:, None], (1, 6))  # wrong M
    with pytest.raises(ValueError, match=r"x\.shape=.*expected"):
        plot_multi(x2_bad, Y)


def test_values_length_mismatch_raises():
    _, _, Y = _make_data(N=10, M=4)
    with pytest.raises(ValueError, match="values.*length"):
        plot_multi(Y, values=np.arange(3))


def test_collection_mode_accepts_explicit_colors_and_linestyles():
    _, _, Y = _make_data(N=40, M=4)
    cols = ["k", "r", "g", "b"]
    lss = ["-", "--", ":", "-."]
    res = plot_multi(
        Y,
        mode="collection",
        colors=cols,
        linestyles=lss,
        linewidths=1.2,
    )
    assert res.mode == "collection"
    assert isinstance(res.artists, LineCollection)
    assert res.mappable is None  # explicit colors => no mappable


def test_fmt_string_second_arg_disambiguation_Y_fmt_not_x_Y():
    # Ensure plot_multi(Y, "k--") is treated as Y+fmt, not x+Y
    _, _, Y = _make_data()
    res = plot_multi(Y, "k--")
    assert res.mode == "lines"
    assert len(res.artists) == Y.shape[1]
