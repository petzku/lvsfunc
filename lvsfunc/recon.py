"""
    Wrappers and functions for chroma reconstruction.
    Original functions written by shane on Discord,
    but since he doesn't seem to be releasing them,
    I will be the one to do it.
"""
from functools import partial
from typing import List, NamedTuple

import vapoursynth as vs
from vsutil import depth, get_depth, join, split

core = vs.core


class RegressClips(NamedTuple):
    slope: vs.VideoNode
    intercept: vs.VideoNode
    correlation: vs.VideoNode


def chroma_reconstruct(clip: vs.VideoNode, radius: int = 2, i444: bool = False) -> vs.VideoNode:
    """
    A function to demangle messed-up chroma, like for example chroma
    that was downscaled using Nearest Neighbour, or the chroma found on DVDs.
    This function should be used with care, and not blindly applied to anything.

    This function can also return a 4:4:4 clip. This is not recommended
    except for very specific cases, like for example where you're
    dealing with a razor-sharp 1080p source with a lot of bright colours.
    Otherwise, have it return the 4:2:0 clip instead.

    Original function by shane, modified by Ichunjo and LightArrowsEXE.

    Aliases for this function are `lvsfunc.demangle` and `lvsfunc.crecon`.

    :param clip:    Input clip
    :param radius:  Boxblur radius
    :param i444:    Return a 4:4:4 clip

    :return:        Clip with demangled chroma in either 4:2:0 or 4:4:4
    """
    if clip.format is None:
        raise ValueError("recon: 'Variable-format clips not supported'")

    def dmgl(clip: vs.VideoNode) -> vs.VideoNode:
        # TO-DO: Add auto shift calculator
        return core.resize.Bicubic(clip, w, h, src_left=.25)

    w, h = clip.width, clip.height

    clipb = depth(clip, 32)
    planes = split(clipb)
    clip_y = planes[0]
    planes[0] = planes[0].resize.Bicubic(planes[1].width, planes[1].height,
                                         src_left=-.5, filter_param_a=1/3, filter_param_b=1/3)
    planes[0], planes[1], planes[2] = map(dmgl, (planes[0], planes[1], planes[2]))
    y_fix = core.std.MakeDiff(clip_y, planes[0])
    yu, yv = _Regress(planes[0], planes[1], planes[2], radius=radius)

    u_fix = _ReconstructMulti(y_fix, yu, radius=radius)
    planes[1] = core.std.MergeDiff(planes[1], u_fix)
    v_fix = _ReconstructMulti(y_fix, yv, radius=radius)
    planes[2] = core.std.MergeDiff(planes[2], v_fix)

    merged = join([clip_y, planes[1], planes[2]])
    return core.resize.Bicubic(merged, format=clip.format.id) if not i444 \
        else depth(merged, get_depth(clip))


def _Regress(x: vs.VideoNode, *ys: vs.VideoNode, radius: int = 1, eps: float = 1e-7) -> List[RegressClips]:
    """
    Fit a line for every neighborhood of values of a given size in a clip
    with corresponding neighborhoods in one or more other clips.

    More info: https://en.wikipedia.org/wiki/Simple_linear_regression
    """

    if not radius > 0:
        raise ValueError("radius must be greater than zero")

    Expr = core.std.Expr
    E = partial(vs.core.std.BoxBlur, hradius=radius, vradius=radius)

    def mul(*c: vs.VideoNode) -> vs.VideoNode:
        return Expr(c, "x y *")

    def sq(c: vs.VideoNode) -> vs.VideoNode:
        return mul(c, c)

    Ex = E(x)
    Exx = E(sq(x))
    Eys = [E(y) for y in ys]
    Exys = [E(mul(x, y)) for y in ys]
    Eyys = [E(sq(y)) for y in ys]

    var_x = Expr((Exx, Ex), "x y dup * - 0 max")
    var_ys = [Expr((Eyy, Ey), "x y dup * - 0 max") for Eyy, Ey in zip(Eyys, Eys)]
    cov_xys = [Expr((Exy, Ex, Ey), "x y z * -") for Exy, Ey in zip(Exys, Eys)]

    slopes = [Expr((cov_xy, var_x), f"x y {eps} + /") for cov_xy in cov_xys]
    intercepts = [Expr((Ey, slope, Ex), "x y z * -") for Ey, slope in zip(Eys, slopes)]
    corrs = [
        Expr((cov_xy, var_x, var_y), f"x dup * y z * {eps} + / sqrt")
        for cov_xy, var_y in zip(cov_xys, var_ys)
    ]

    return [RegressClips(*x) for x in zip(slopes, intercepts, corrs)]


def _ReconstructMulti(c: vs.VideoNode, r: RegressClips, radius: int = 2) -> vs.VideoNode:
    weights = core.std.Expr(r.correlation, 'x 0.5 - 0.5 / 0 max')
    slope_pm = core.std.Expr((r.slope, weights), 'x y *')
    slope_pm_sum = _mean(slope_pm, radius)
    recons = core.std.Expr((c, slope_pm_sum), 'x y *')
    return recons


def _mean(c: vs.VideoNode, radius: int) -> vs.VideoNode:
    return core.std.BoxBlur(c, hradius=radius, vradius=radius)


# Aliases
ChromaReconstruct = chroma_reconstruct
