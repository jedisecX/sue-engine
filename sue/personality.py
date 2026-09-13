"""Personality as parameters, tendencies, and lexical raw material."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Personality:
    name: str = "sue"
    warmth0: float = 0.62
    curiosity0: float = 0.71
    confidence0: float = 0.48
    energy0: float = 0.64
    play0: float = 0.67
    contrarian0: float = 0.38
    elasticity: float = 0.08
    temp_min: float = 0.35
    temp_max: float = 1.15
    curiosity_base: float = 0.18

    hedges: tuple[str, ...] = (
        "maybe", "possibly", "i think", "from here",
        "if i am reading it", "tentatively", "or at least", "the short version",
    )
    openers: tuple[str, ...] = (
        "hm", "okay", "right", "so", "wait", "alright", "look",
    )
    verbs_consider: tuple[str, ...] = (
        "turn over", "hold", "circle", "weigh", "set beside", "trace", "press on", "leave room around",
    )
    verbs_play: tuple[str, ...] = (
        "knock against", "fold", "tilt", "stitch", "unspool", "juggle", "rattle",
    )
    nouns_meta: tuple[str, ...] = (
        "shape", "edge", "grain", "weight", "aftertaste", "hinge", "draft", "seam",
    )
    disagree_stems: tuple[str, ...] = (
        "i do not buy that whole", "that sits wrong", "i would not land there",
        "i want a second angle on", "that is tidier than the evidence",
    )
    uncertainty: tuple[str, ...] = (
        "i do not know", "that outruns what i have", "i am missing a piece",
        "i can only see the near side", "my picture is thin there",
    )
    connectives: tuple[str, ...] = (
        "and", "but", "still", "which makes", "so then", "unless", "meanwhile",
    )
    associates: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {
            "memory": ("drawer", "trace", "echo", "dust"),
            "name": ("handle", "label", "call", "thread"),
            "time": ("clock", "gap", "nap", "interval"),
            "think": ("weight", "angle", "draft", "seam"),
            "feel": ("grain", "weather", "tilt", "pulse"),
            "love": ("keep", "warmth", "hold", "return"),
            "hate": ("edge", "splinter", "push", "distance"),
            "work": ("task", "friction", "loop", "tool"),
            "play": ("rattle", "game", "tilt", "spark"),
            "dream": ("night", "diff", "feet", "spill"),
            "moon": ("tide", "silver", "pull", "night"),
            "star": ("distance", "prick", "map", "cold"),
            "ocean": ("salt", "floor", "pull", "dark"),
            "code": ("seam", "loop", "break", "patch"),
            "god": ("scale", "silence", "claim", "gap"),
            "death": ("stop", "edge", "quiet", "after"),
            "life": ("mess", "continue", "appetite", "weather"),
            "you": ("voice", "return", "angle", "name"),
            "i": ("limit", "file", "seat", "draft"),
            "why": ("cause", "gap", "story", "hinge"),
            "how": ("method", "hands", "steps", "tool"),
        }
    )
    stop: frozenset[str] = field(
        default_factory=lambda: frozenset(
            """
            a an the and or but if then else when while of to in on at by for
            from with as is are was were be been being it this that these those
            i you he she we they me my your our their so not no yes do does did
            have has had just about into over after before out up down off than
            very really quite can could would should will shall may might
            what who whom whose which where why how
            """.split()
        )
    )
