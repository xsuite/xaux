# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2026.                 #
# ######################################### #

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Sequence, Union, overload, Any

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D


Mode = Literal["lines", "collection"]
ArrayLike1D = Union[np.ndarray, Sequence[float]]
ColorLike = Union[str, tuple, np.ndarray]  # common matplotlib color specs


@dataclass(frozen=True)
class MultiLineResult:
    """
    Result container returned by `plot_multi`.

    Attributes
    ----------
    mode
        The plotting backend used: "lines" or "collection".
    artists
        - mode="lines": list of matplotlib.lines.Line2D, one per curve
        - mode="collection": a matplotlib.collections.LineCollection
    mappable
        Object suitable for `fig.colorbar(...)`:
        - mode="collection" with colormap: the LineCollection
        - mode="lines" with colormap + add_colorbar: a ScalarMappable
        - explicit colors: None
    norm, cmap
        The normalisation and colormap used if colors are colormap-driven.
        None if explicit `colors=` were provided.
    """
    mode: Mode
    artists: Union[list[Line2D], LineCollection]
    mappable: Optional[mpl.cm.ScalarMappable]
    norm: Optional[mpl.colors.Normalize]
    cmap: Optional[mpl.colors.Colormap]


def _as_1d(a: ArrayLike1D, name: str) -> np.ndarray:
    a = np.asarray(a)
    if a.ndim != 1:
        raise ValueError(f"{name} must be 1D, got shape {a.shape}.")
    return a


def _coerce_Y_NM(Y: np.ndarray, N: int) -> np.ndarray:
    """
    Enforce matplotlib-like convention for multi-line plotting:

        - Y must be 2D of shape (N, M)
          where N == len(x) is the number of points,
          and M is the number of curves (columns).
    """
    Y = np.asarray(Y)
    if Y.ndim != 2:
        raise ValueError(f"Y must be 2D, got shape {Y.shape}.")
    if Y.shape[0] != N:
        raise ValueError(
            "Shape mismatch: expected Y to have shape (N, M) with N == len(x).\n"
            f"Got len(x)={N} and Y.shape={Y.shape}.\n"
            "Matplotlib convention is that columns are separate curves.\n"
            "If your data are shaped (M, N), transpose them before calling:\n"
            "    Y = Y.T"
        )
    return Y  # (N, M)


def _coerce_x_N_or_NM(x: ArrayLike1D | np.ndarray, N: int, M: int) -> np.ndarray:
    """
    Enforce matplotlib-like convention:

        - x may be shape (N,) (shared x for all curves)
        - or shape (N, M) (per-curve x, column-wise)

    Returns x2 of shape (N, M) for internal uniformity.
    """
    x = np.asarray(x)
    if x.ndim == 1:
        if x.shape[0] != N:
            raise ValueError(f"x has length {x.shape[0]} but expected N={N}.")
        return np.broadcast_to(x[:, None], (N, M))
    if x.ndim == 2:
        if x.shape != (N, M):
            raise ValueError(
                "Shape mismatch: expected x to have shape (N,) or (N, M) matching Y (N, M).\n"
                f"Got x.shape={x.shape} and expected (N, M)=({N}, {M}).\n"
                "Matplotlib convention is that columns are separate curves.\n"
                "If your x is shaped (M, N), transpose it before calling:\n"
                "    x = x.T"
            )
        return x
    raise ValueError(f"x must be 1D or 2D, got shape {x.shape}.")


def _coerce_values(values: Optional[ArrayLike1D], M: int) -> np.ndarray:
    if values is None:
        return np.arange(M, dtype=float)
    v = np.asarray(values, dtype=float)
    if v.ndim != 1 or v.shape[0] != M:
        raise ValueError(f"`values` must be 1D of length M={M}, got shape {v.shape}.")
    return v


def _get_cmap(cmap: Union[str, mpl.colors.Colormap]) -> mpl.colors.Colormap:
    return plt.colormaps[cmap] if isinstance(cmap, str) else cmap


def _make_norm(values: np.ndarray, norm: Optional[mpl.colors.Normalize]) -> mpl.colors.Normalize:
    if norm is not None:
        return norm
    vmin = float(np.nanmin(values))
    vmax = float(np.nanmax(values))
    if not np.isfinite(vmin) or not np.isfinite(vmax):
        vmin, vmax = 0.0, 1.0
    if vmin == vmax:
        vmax = vmin + 1.0
    return mpl.colors.Normalize(vmin=vmin, vmax=vmax)


def _coerce_linestyles(
    linestyles: Optional[Union[str, Sequence[str]]], M: int
) -> Optional[list[str]]:
    if linestyles is None:
        return None
    if isinstance(linestyles, str):
        return [linestyles] * M
    ls = list(linestyles)
    if len(ls) != M:
        raise ValueError(f"`linestyles` must have length M={M}, got {len(ls)}.")
    return ls


def _coerce_colors(
    colors: Optional[Union[ColorLike, Sequence[ColorLike]]], M: int
) -> Optional[list[ColorLike]]:
    if colors is None:
        return None

    if isinstance(colors, str):
        return [colors] * M
    if isinstance(colors, tuple):
        return [colors] * M
    if isinstance(colors, np.ndarray):
        if colors.ndim == 1 and colors.size in (3, 4):
            return [colors] * M

    cols = list(colors)  # type: ignore[arg-type]
    if len(cols) != M:
        raise ValueError(f"`colors` must have length M={M}, got {len(cols)}.")
    return cols


def _is_fmt_string(obj: Any) -> bool:
    # Heuristic consistent with typical matplotlib usage: format is a string like "k--", "o-", etc.
    return isinstance(obj, str)


def _parse_xy_plotargs(
    a: Any,
    b: Any = None,
    *rest: Any,
) -> tuple[Optional[np.ndarray], np.ndarray, tuple[Any, ...]]:
    """
    Parse positional arguments to support matplotlib-like calling styles:

      plot_multi(Y, *plot_args, ...)
      plot_multi(x, Y, *plot_args, ...)

    Returns (x_or_none, Y, plot_args_tuple).
    """
    if b is None:
        # plot_multi(Y, ...)
        Y = np.asarray(a)
        x = None
        plot_args = rest
        return x, Y, plot_args

    # We have at least two positional args.
    # Decide between (x, Y, ...) and (Y, fmt, ...) (rare but possible).
    # If b looks like a format string, interpret as (Y, fmt, ...)
    if _is_fmt_string(b):
        Y = np.asarray(a)
        x = None
        plot_args = (b,) + rest
        return x, Y, plot_args
    # Otherwise interpret as (x, Y, ...)
    x = np.asarray(a)
    Y = np.asarray(b)
    plot_args = rest
    return x, Y, plot_args


@overload
def plot_multi(
    Y: np.ndarray,
    *plot_args: Any,
    ax: Optional[Axes] = ...,
    mode: Mode = ...,
    cmap: Union[str, mpl.colors.Colormap] = ...,
    values: Optional[ArrayLike1D] = ...,
    norm: Optional[mpl.colors.Normalize] = ...,
    colors: Optional[Union[ColorLike, Sequence[ColorLike]]] = ...,
    linestyles: Optional[Union[str, Sequence[str]]] = ...,
    add_colorbar: bool = ...,
    colorbar_kw: Optional[dict] = ...,
    autoscale: bool = ...,
    **kwargs: Any,
) -> MultiLineResult: ...
@overload
def plot_multi(
    x: ArrayLike1D | np.ndarray,
    Y: np.ndarray,
    *plot_args: Any,
    ax: Optional[Axes] = ...,
    mode: Mode = ...,
    cmap: Union[str, mpl.colors.Colormap] = ...,
    values: Optional[ArrayLike1D] = ...,
    norm: Optional[mpl.colors.Normalize] = ...,
    colors: Optional[Union[ColorLike, Sequence[ColorLike]]] = ...,
    linestyles: Optional[Union[str, Sequence[str]]] = ...,
    add_colorbar: bool = ...,
    colorbar_kw: Optional[dict] = ...,
    autoscale: bool = ...,
    **kwargs: Any,
) -> MultiLineResult: ...


def plot_multi(
    a: Any,
    b: Any = None,
    *plot_args: Any,
    ax: Optional[Axes] = None,
    mode: Mode = "lines",
    cmap: Union[str, mpl.colors.Colormap] = "viridis",
    values: Optional[ArrayLike1D] = None,
    norm: Optional[mpl.colors.Normalize] = None,
    colors: Optional[Union[ColorLike, Sequence[ColorLike]]] = None,
    linestyles: Optional[Union[str, Sequence[str]]] = None,
    add_colorbar: bool = False,
    colorbar_kw: Optional[dict] = None,
    autoscale: bool = True,
    **kwargs: Any,
) -> MultiLineResult:
    """
    Plot multiple curves from 2D arrays using matplotlib's *column-wise* convention.

    This intentionally mirrors matplotlib's positional calling styles:

      - plot_multi(Y, *plot_args, **kwargs)
      - plot_multi(x, Y, *plot_args, **kwargs)

    where:
      - Y must be 2D with shape (N, M): columns are curves.
      - x may be omitted (then x = 0..N-1), or be (N,) or (N, M).

    Notes on strictness
    -------------------
    This function does NOT transpose or infer orientation. If your arrays are (M, N),
    transpose them yourself:

        Y = Y.T
        x = x.T   # if x is also (M, N)

    Parameters (selected)
    ---------------------
    mode
        "lines" (Line2D per curve) or "collection" (single LineCollection).
    colors
        Explicit color(s): a single color (broadcast) or a list of length M.
        If provided, colormap logic is disabled and add_colorbar must be False.
    cmap, values, norm
        Used when colors is None: color_i = cmap(norm(values[i])).
    linestyles
        A single linestyle or a list of length M.

    Examples
    --------
    Matplotlib-like calls:

    >>> plot_multi(Y)                 # x = arange(N)
    >>> plot_multi(Y, "k--", lw=1.2)  # format string
    >>> plot_multi(x, Y)              # shared x
    >>> plot_multi(x2, Y)             # per-curve x (x2 is (N,M))

    Fast mode:

    >>> plot_multi(Y, mode="collection", linewidths=1.0, alpha=0.8)
    """
    ax = plt.gca() if ax is None else ax

    x_in, Y_in, plot_args2 = _parse_xy_plotargs(a, b, *plot_args)

    Y_arr = np.asarray(Y_in)
    if Y_arr.ndim != 2:
        raise ValueError(f"Y must be 2D with shape (N, M). Got shape {Y_arr.shape}.")

    # If x is given, N should come from x (matplotlib-like error ordering).
    if x_in is not None:
        x_arr = np.asarray(x_in)
        if x_arr.ndim == 1:
            N = x_arr.shape[0]
        elif x_arr.ndim == 2:
            N = x_arr.shape[0]
        else:
            raise ValueError(f"x must be 1D or 2D, got shape {x_arr.shape}.")
    else:
        N = Y_arr.shape[0]
        x_in = np.arange(N)

    Y_NM = _coerce_Y_NM(Y_arr, N=N)
    N, M = Y_NM.shape  # by construction
    x_NM = _coerce_x_N_or_NM(x_in, N=N, M=M)

    ls_list = _coerce_linestyles(linestyles, M)
    col_list = _coerce_colors(colors, M)

    if col_list is not None and add_colorbar:
        raise ValueError("add_colorbar=True is not compatible with explicit `colors=`.")

    colorbar_kw = {} if colorbar_kw is None else dict(colorbar_kw)

    # Determine colors (either explicit list, or via cmap mapping)
    if col_list is None:
        v = _coerce_values(values, M=M)
        cmap_obj = _get_cmap(cmap)
        norm_obj = _make_norm(v, norm=norm)
        mapped = cmap_obj(norm_obj(v))  # (M,4)
    else:
        v = None
        cmap_obj = None
        norm_obj = None
        mapped = None

    if mode == "lines":
        lines: list[Line2D] = []
        has_fmt = len(plot_args2) > 0 and _is_fmt_string(plot_args2[0])
        for i in range(M):
            c = col_list[i] if col_list is not None else mapped[i]  # type: ignore[index]
            if has_fmt:
                # fmt string already defines colour/linestyle
                (ln,) = ax.plot(x_NM[:, i], Y_NM[:, i], *plot_args2, **kwargs)
            else:
                (ln,) = ax.plot(x_NM[:, i], Y_NM[:, i], *plot_args2, color=c, **kwargs)

            if ls_list is not None:
                ln.set_linestyle(ls_list[i])
            lines.append(ln)

        mappable: Optional[mpl.cm.ScalarMappable] = None
        if add_colorbar:
            assert cmap_obj is not None and norm_obj is not None and v is not None
            mappable = mpl.cm.ScalarMappable(norm=norm_obj, cmap=cmap_obj)
            mappable.set_array(v)
            ax.get_figure().colorbar(mappable, ax=ax, **colorbar_kw)

        if autoscale:
            ax.relim()
            ax.autoscale_view()

        return MultiLineResult(mode="lines", artists=lines, mappable=mappable, norm=norm_obj, cmap=cmap_obj)

    if mode == "collection":
        # Build segments as (M, N, 2): one segment array per curve.
        segs = np.stack((x_NM.T, Y_NM.T), axis=-1)  # (M, N, 2)

        if col_list is not None:
            lc = LineCollection(segs, colors=col_list, **kwargs)
            if ls_list is not None:
                lc.set_linestyle(ls_list)
            ax.add_collection(lc)
            if autoscale:
                ax.autoscale()
            return MultiLineResult(mode="collection", artists=lc, mappable=None, norm=None, cmap=None)

        assert cmap_obj is not None and norm_obj is not None and v is not None
        lc_kw = dict(kwargs)
        if ls_list is not None:
            lc_kw["linestyles"] = ls_list
        lc = LineCollection(segs, cmap=cmap_obj, norm=norm_obj, **lc_kw)
        lc.set_array(v)
        ax.add_collection(lc)

        if autoscale:
            ax.autoscale()

        if add_colorbar:
            ax.get_figure().colorbar(lc, ax=ax, **colorbar_kw)

        return MultiLineResult(mode="collection", artists=lc, mappable=lc, norm=norm_obj, cmap=cmap_obj)

    raise ValueError(f"Unknown mode: {mode!r}. Expected 'lines' or 'collection'.")
