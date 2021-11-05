ZONE_BITS = 16

def locationAsChannel(parentId, zone):
    return (parentId << ZONE_BITS) | zone

def parentToChildren(parentId):
    return (1 << ZONE_BITS) | parentId