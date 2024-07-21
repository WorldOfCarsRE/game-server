from direct.directnotify.DirectNotifyGlobal import directNotify

from .TrackSegment import TrackSegment
from typing import Dict, List
import xml.etree.ElementTree as ET

class Track():
    notify = directNotify.newCategory("Track")

    def __init__(self, physicsFile):
        self.segments: List[TrackSegment] = []
        self.segmentById: Dict[int, TrackSegment] = {}
        self.startingTrackSegment: int = 1

        # Parse physics file.
        self.notify.info(f"Parsing physics file: {physicsFile}")
        tree = ET.parse(f"physics/{physicsFile}") # Assuming a symbolic link was placed to the physics xml files there.
        segments = tree.getroot()[0]

        for segment in segments:
            data = segment.attrib
            segment = TrackSegment()
            segment.id = int(data['id'])
            segment.type = int(data['type'])
            for parentId in data['parents'].split(','):
                segment.parentIds.append(int(parentId))
            for childrenId in data['children'].split(','):
                segment.childrenIds.append(int(childrenId))
            self.segments.append(segment)
            self.segmentById[segment.id] = segment

        # Iterate and populate parents and children.
        for segment in self.segments:
            for parentId in segment.parentIds:
                parent = self.segmentById.get(parentId)
                if not parent:
                    self.notify.warning(f'Parent {parentId} for segment {segment.id} missing!')
                    continue
                segment.parents.append(parent)
                segment.parentById[parentId] = parent

            for childrenId in segment.childrenIds:
                children = self.segmentById.get(childrenId)
                if not children:
                    self.notify.warning(f'Children {childrenId} for segment {segment.id} missing!')
                    continue
                segment.children.append(children)
                segment.childrenById[childrenId] = children
