from typing import Dict, List

from enum import IntEnum

class SegmentType(IntEnum):
    DEFAULT_TYPE = 1
    JUMP = 2
    DEFAULT = 5

class TrackSegment():
    def __init__(self):
        self.id: int = 0
        self.type: SegmentType = SegmentType.DEFAULT_TYPE

        self.parents: List[TrackSegment] = []
        self.parentIds: List[int] = []
        self.parentById: Dict[int, TrackSegment] = {}

        self.children: List[TrackSegment] = []
        self.childrenIds: List[int] = []
        self.childrenById: Dict[int, TrackSegment] = {}
