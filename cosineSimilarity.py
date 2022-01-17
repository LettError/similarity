import statistics
import math
import numpy
from fontPens.marginPen import MarginPen
from defcon import addRepresentationFactory

from mojo.UI import OpenSpaceCenter
import vanilla


# principle: 
# https://www.delftstack.com/howto/python/cosine-similarity-between-lists-python/
from numpy import dot
from numpy.linalg import norm


from fontTools.pens.basePen import BasePen
from fontTools.misc.bezierTools import splitLine, splitCubic

def NormalizedGlyphProfileFactory(glyph):
    return makeNormalizedProfile(glyph)

normalizedProfileKey = "com.letterror.normalizedGlyphProfile4"
addRepresentationFactory(normalizedProfileKey, NormalizedGlyphProfileFactory)


class MultipleMarginPen(BasePen):

    def __init__(self, glyphSet, values, isHorizontal=True):
        BasePen.__init__(self, glyphSet)
        self.values = values
        self.hits = {}
        self.filterDoubles = True
        self.startPt = None
        self.currentPt = None
        self.isHorizontal = isHorizontal
    
    def _addHit(self, value, hit):
        if value not in self.hits:
            self.hits[value] = []
        x, y = hit
        self.hits[value].append(hit[not self.isHorizontal])

    def _moveTo(self, pt):
        self.currentPt = pt
        self.startPt = pt

    def _lineTo(self, pt):
        if self.filterDoubles:
            if pt == self.currentPt:
                return
        for value in self.values:
            hits = splitLine(self.currentPt, pt, value, self.isHorizontal)
            for hit in hits[:-1]:
                self._addHit(value, hit[-1])
        self.currentPt = pt

    def _curveToOne(self, pt1, pt2, pt3):
        for value in self.values:
            hits = splitCubic(self.currentPt, pt1, pt2, pt3, value, self.isHorizontal)
            for hit in hits[:-1]:
                self._addHit(value, hit[-1])                
        self.currentPt = pt3

    def _closePath(self):
        if self.currentPt != self.startPt:
            self._lineTo(self.startPt)
        self.currentPt = self.startPt = None

    def _endPath(self):
        self.currentPt = None

    def getMargins(self):
        return self.hits    
        
def stepRange(mn, mx, parts):
    # return a list of parts between mn, mx
    # stepRange(0,10,2)
    # [0.0, 5.0, 10.0]
    v = []
    for i in range(parts+1):
        v.append(mn+(i/(parts)*(mx-mn)))
    return v

def makeNormalizedProfile(glyph, clip=200):
    # make a normalized profile of left and right side of glyph
    # make samples from font.info.descender to font.info.ascender, in stepSize increments
    # ignore samples that are clip distance away from left or right margin
    # de-skew if there is an italic angle set.
    # 
    shift = 30    # test value to add to all sampled values to differentiate with 0, non-samples
    leftValues = []
    rightValues = []
    if glyph is None:
        return
    font = glyph.font
    a = font.info.italicAngle
    if a is None:
        a = 0
    profile = []
    sections = [
        (0, font.info.descender, 5),
        (0, font.info.xHeight, 50),
        (font.info.xHeight, font.info.unitsPerEm, 25)
    ]
    sampleHeights = []
    for mn,mx,step in sections:
        [sampleHeights.append(v) for v in stepRange(mn,mx,step) if v not in sampleHeights]
    sampleHeights.sort()
    mmp = MultipleMarginPen(glyph.font, sampleHeights)
    glyph.draw(mmp)
    hits = mmp.getMargins()
    for h in sampleHeights:
        ta = math.tan(math.radians(-a)) * h
        m = hits.get(h)
        if m is None:
            profile.append((h, None, None))
        else:
            mn = min(m)-ta
            if mn > clip:
                # replace sample with None if clipped
                mn = None
            mx = max(m)-ta
            if mx < (glyph.width-clip):
                # replace sample with None if clipped
                mx = None
            profile.append((h, mn, mx))
    leftValues = []
    rightValues = []
    # calculate the averages
    for i, v in enumerate(profile):
        y, mn, mx = v
        if mn is not None:
            leftValues.append(mn)
        if mx is not None:    
            rightValues.append(mx)
    if not leftValues:
        leftAverage = 0
    else:
        leftAverage = statistics.median_grouped(leftValues)
    if not rightValues:
        rightAverage = 0
    else:
        rightAverage = statistics.median_grouped(rightValues)
    normalized = []
    for i, v in enumerate(profile):
        y, mn, mx = v
        if mn is not None:
            mn -= leftAverage - shift
        else:
            mn = 0
        if mx is not None:            
            mx -= rightAverage - shift
        else:
            mx = 0
        normalized.append((y, mn, mx))      
    return normalized

def cosineSimilarity(first, second):
    # compare normalized profiles of these glyphs according to cosine similarity
    # https://www.delftstack.com/howto/python/cosine-similarity-between-lists-python/
    sides = {}
    firstProfile = first.getRepresentation(normalizedProfileKey)
    firstLeftProfile = [b for a,b,c in firstProfile]
    firstRightProfile = [c for a,b,c in firstProfile]
    secondProfile = second.getRepresentation(normalizedProfileKey)
    secondLeftProfile = [b for a,b,c in secondProfile]
    secondRightProfile = [c for a,b,c in secondProfile]
    if firstLeftProfile and secondLeftProfile and firstRightProfile and secondRightProfile:
        leftResult = dot(firstLeftProfile, secondLeftProfile)/(norm(firstLeftProfile)*norm(secondLeftProfile))
        rightResult = dot(firstRightProfile, secondRightProfile)/(norm(firstRightProfile)*norm(secondRightProfile))
        return float(leftResult), float(rightResult)
    return None, None

def compareGlyphs(font, members):
    # see if the members of this group look like each other
    # returns a dict with comparisons between each of the members
    leftResult = {}
    rightResult = {}
    done = []
    for first in members:
        for second in members:
            key = [first, second]
            key.sort()
            key = tuple(key)
            if first == second: continue
            if key in done: continue
            leftSim, rightSim = cosineSimilarity(font[key[0]], font[key[1]], )
            leftResult[key] = leftSim
            rightResult[key] = rightSim
            done.append(key)
    return leftResult, rightResult    

def showSimilarGlyphsInSpaceCenter(this, showSimilar=10):
    # find similars to current glyph
    # line 1: similar on right
    # line 2: current glyph
    # line 3: similar on left
    # showSimilar: maximum number of similar glyphs to show
    rankLeft = {}
    rankRight = {}
    for g in CurrentFont():
        if g.name == this.name:
            continue
        ls, rs = cosineSimilarity(this, g)
        if not ls in rankLeft:
            rankLeft[ls] = []
        rankLeft[ls].append(g.name)
        if not rs in rankRight:
            rankRight[rs] = []
        rankRight[rs].append(g.name)        
    rk = list(rankLeft.keys())
    rk = sorted(rk, key = lambda x : float('-inf') if math.isnan(x) else x)
    rk = [v for v in rk if v > 0.8]
    rk.sort()
    rk.reverse()
    similarLeftNames = []
    for k in rk[:showSimilar]:
        similarLeftNames += rankLeft[k]
    similarLeftNames.sort()
    rk = list(rankRight.keys())
    rk = sorted(rk, key = lambda x : float('-inf') if math.isnan(x) else x)
    rk = [v for v in rk if v > 0.85]
    rk.sort()
    rk.reverse()
    similarRightNames = []
    for k in rk[:showSimilar]:
        similarRightNames += rankRight[k]
    similarRightNames.sort()

    # well, lets' put these in a spacecenter and see
    from mojo.UI import CurrentSpaceCenter
    sp = CurrentSpaceCenter()
    if sp is not None:
        t = f'{"/"+"/".join(similarRightNames)} \\n{"/"+this.name}{"/"+this.name}{"/"+this.name} H{"/"+this.name} H{"/"+this.name} O{"/"+this.name} O \\n{"/"+"/".join(similarLeftNames)}'
        sp.setRaw(t)


class SimilarityUI(object):
    # simple window to show similarity ranking for the current glyph
    
    def __init__(self):
        self.showSimilar = 10
        self.threshold = 0.98
        self.currentName = None
        glyphDescriptions = [
                {   'title': "Name",
                    'key':'glyphName',
                    'editable':False,
                },
                {   'title': "Left",
                    'key':'scoreLeft',
                    'editable':False,
                },
                {   'title': "Right",
                    'key':'scoreRight',
                    'editable':False,
                },
        ]
        self.w = vanilla.Window((300, 500), "Similarity", minSize=(200,100))
        self.w.l = vanilla.List((5,35,-5, -40),[], columnDescriptions=glyphDescriptions)
        self.w.threshold = vanilla.EditText((5,-35,50,20), self.threshold, sizeStyle="small", callback=self.editThreshold)
        self.w.thresholdCaption = vanilla.TextBox((60,-32,100,20), "Threshold", sizeStyle="small")
        self.w.update = vanilla.Button((-100, 5, -5, 20), "Update", callback=self.update)
        self.w.current = vanilla.TextBox((10,5, -110,20), "Nothing")
        self.w.toSpaceCenter = vanilla.Button((-100,-35,-5,20), "SpaceCenter", self.toSpaceCenter)
        self.w.open()
        self.update()
    
    def editThreshold(self, sender=None):
        v = None
        try:
            v = float(sender.get())
        except ValueError:
            return
        if v:
            self.threshold = v
            self.update()
        
    def toSpaceCenter(self, sender=None):
        # put the selected names in a spacecenter
        s = self.w.l.getSelection()
        leftNames = []
        rightNames = []
        if not s:
            for item in self.w.l:
                if item['scoreLeft']!="":
                    leftNames.append(item['glyphName'])
                else:
                    rightNames.append(item['glyphName'])
        else:
            for index in s:
                if self.w.l[index]['scoreLeft']!="":
                    leftNames.append(self.w.l[index]['glyphName'])
                else:
                    rightNames.append(self.w.l[index]['glyphName'])
        text = f"/bracketleft/{self.currentName}/space/space{'/'+'/'.join(leftNames)}\\n/{self.currentName}/bracketright/space/space{'/'+'/'.join(rightNames)}"
        sc = OpenSpaceCenter(CurrentFont())
        sc.setRaw(text)
        
    def update(self, sender=None):
        this = CurrentGlyph()
        if this is None:
            self.w.l.set([])
            self.currentName = None
            self.w.current.set("")
            return
        self.currentName = this.name
        self.w.current.set(self.currentName)
        rankLeft = {}
        rankRight = {}
        items = []
        for g in CurrentFont():
            if g.name == this.name:
                continue
            ls, rs = cosineSimilarity(this, g)
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
                items.append(dict(glyphName=name, scoreLeft=f"{k:3.3f}", scoreRight=""))
        rk = list(rankRight.keys())
        rk = sorted(rk, key = lambda x : float('-inf') if math.isnan(x) else x)
        rk = [v for v in rk if v > self.threshold]
        rk.sort()
        rk.reverse()
        for k in rk[:self.showSimilar]:
            for name in rankRight[k]:
                items.append(dict(glyphName=name, scoreRight=f"{k:3.3f}", scoreLeft=""))
        self.w.l.set(items)
    

if "__main__" in __name__:
    from pprint import pprint
    from random import choice
    
    OpenWindow(SimilarityUI)    

    
    if False:

        f = CurrentFont()
        g = CurrentGlyph()

        makeNormalizedProfile(g)

        # some other applications that could be useful
        # how long does this take?
        import timeit
        start = timeit.default_timer()
        for g in CurrentFont():
            p = g.getRepresentation(normalizedProfileKey)
        end = timeit.default_timer()
        print(f"profiling {len(f)} glyphs: {end-start}")
    
        # example: calculate the similarity between the members of a group
        if f.groups.keys():
            testGroup = choice(f.groups.keys())
            print(f'random testgroup \"{testGroup}\"\n\tfrom {f.path}')
            threshold = None
            print(f"\nshowing similarity")
            left, right = compareGlyphs(f, f.groups[testGroup])
            if "kern2" in testGroup:
                print('[ kern2')
                pprint(left)
            if 'kern1' in testGroup:
                print('kern1 ]')
                pprint(right)
            if not "kern" in testGroup:
                print("non-kerning group left")
                pprint(left)
                print("non-kerning group right")
                pprint(right)

        # example: compare two glyphs
        print("\nthis compares individual glyphs:")
        compare = [("V", "W"), ("E", 'F'), ("O", "C")]
        for left, right in compare:
            ls, rs = cosineSimilarity(f[left], f[right])
            print(f'\t[{left} [{right} {ls}]\n\t{left}] {right}] {rs}]')
    
        # example: compare selected glyphs in the current font
        sel = f.selection
        left, right = compareGlyphs(f, sel)
        print("\n\nselected left")
        pprint(left)
        print("\n\nselected right")
        pprint(right)

        g = CurrentGlyph()
        if g is not None:
            showSimilarGlyphsInSpaceCenter(g)
    
    