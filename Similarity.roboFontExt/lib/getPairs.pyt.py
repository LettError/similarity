
def findGroup(pair, font):
    left, right = pair
    leftItems = [left]
    rightItems = [right]
    for name, mems in font.groups.items():
        if "kern1" in name:
            if left in mems:
                leftItems.append(name)
        if "kern2" in name:
            if right in mems:
                rightItems.append(name)
    # possible pairs
    pairs = zip(leftItems, rightItems)
    actual = [p for p in pairs if p in font.kerning]
    return actual

