import importlib
import cosineSimilarity
importlib.reload(cosineSimilarity)
import itertools
import vanilla
import math
from cosineSimilarity import cosineSimilarity
from glyphNameFormatter.reader import u2r, u2c



def getValue(pair, font):
    left, right = pair
    for name, mems in font.groups.items():
        if "public.kern1" in name:
            if left in mems:
                left = name
        elif "public.kern2" in name:
            if right in mems:
                right = name
    return font.kerning[(left,right)]
    
def findGroup(pair, font):
    left, right = pair
    #print(left, right)
    leftGroup = None
    rightGroup = None
    also = []
    if "public.kern1" in left:
        leftGroup = left
    if "public.kern2" in right:
        rightGroup = right
    if not leftGroup and not rightGroup:
        for name, mems in font.groups.items():
            if "public.kern1" in name:
                if left in mems:
                    leftGroup = name
            elif "public.kern2" in name:
                if right in mems:
                    rightGroup = name
    print('groups', leftGroup, rightGroup)
    allCombinations = []
    if leftGroup and rightGroup:
        allCombinations = list(itertools.product(font.groups[rightGroup], font.groups[rightGroup]))
    elif leftGroup and not rightGroup:
        allCombinations = [(a, right) for a in font.groups[leftGroup]]        
    elif rightGroup and not leftGroup:
        allCombinations = [(left, a) for a in font.groups[rightGroup]]
    else:
        allCombinations = [(left, right)]
    # possible pairs

    print('allCombinations', allCombinations)
    return allCombinations


class SimilarKerning(object):
    def __init__(self, font):
        self.font = font
        
        self.w = vanilla.Window((700, 600), "LTR Similarity Kern", minSize=(700, 600))
        h = 200
        self.w.groups = vanilla.List((0, 30, 200, h), [])
        self.w.members = vanilla.List((200, 30, 200, h), [])
        self.w.candidates = vanilla.List((400, 30, -0, h), [])
        
        self.w.open()
    
    def update(self):
        pass

f = CurrentFont()
sk = SimilarKerning(f)