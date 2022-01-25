import importlib
import cosineSimilarity
importlib.reload(cosineSimilarity)
import itertools
import math
from cosineSimilarity import cosineSimilarity, leftAverageMarginKey, rightAverageMarginKey
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
        self.similarPairs = {}
        self.similarLeft = {}
        self.similarRight = {}
        self.currentCategory = None
        self.currentRange = None
        
    def analyse(self, pair):
        combs = findGroup(pair, self.font)
        print('combs', combs)

        rankRight = {}
        items = []
        rangeLookup = {}
        categoryLookup = {}
        for g in font:
            if g.name == this.name:
                continue
            if limitUnicodeCategory:
                if self.currentCategory != u2c(g.unicode):
                    continue
            if limitUnicodeRange:
                if self.currentRange != u2r(g.unicode):
                    continue
            thisUniCat = u2c(g.unicode)
            if thisUniCat is not None:
                categoryLookup[g.name] = thisUniCat
            thisUniRange = u2r(g.unicode)
            if thisUniRange is not None:
                rangeLookup[g.name] = thisUniRange
            ls = cosineSimilarity(this, g, side="left", zones=self.zones)
            rs = cosineSimilarity(this, g, side="right", zones=self.zones)
            if not ls in rankLeft:
                rankLeft[ls] = []
            rankLeft[ls].append(g.name)
            if not rs in rankRight:
                rankRight[rs] = []
            rankRight[rs].append(g.name)        
        rk = list(rankLeft.keys())
        rk = sorted(rk, key = lambda x : float('-inf') if math.isnan(x) else x)
        rk = [v for v in rk if v > self.threshold]
        rk.sort()
        rk.reverse()
        for k in rk[:self.showSimilar]:
            for name in rankLeft[k]:
                items.append(())
        rk = list(rankRight.keys())
        rk = sorted(rk, key = lambda x : float('-inf') if math.isnan(x) else x)
        rk = [v for v in rk if v > self.threshold]
        rk.sort()
        rk.reverse()
        for k in rk[:self.showSimilar]:
            for name in rankRight[k]:
                items.append(dict(glyphName=name, 
                    scoreRight=f"{k:3.3f}", 
                    scoreLeft="", 
                    unicodeCategory=categoryLookup.get(name, ''),
                    unicodeRange=rangeLookup.get(name, ''),
                    ))
        self.w.l.set(items)

f = CurrentFont()
sk = SimilarKerning(f)
r1 = sk.analyse(("A", "O"))


r2 = sk.analyse(("public.kern1.A", "public.kern2.O"))
r3 = sk.analyse(("public.kern1.A", "O"))

print(r1 == r2 == r3)

print(getValue(("A", "O"), f))
print(getValue(("public.kern1.A", "public.kern2.O"), f))




