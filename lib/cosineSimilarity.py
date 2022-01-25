import statistics
import math
import numpy
from fontPens.marginPen import MarginPen
from defcon import addRepresentationFactory, registerRepresentationFactory
import defcon


# principle: 
# https://www.delftstack.com/howto/python/cosine-similarity-between-lists-python/
from numpy import dot
from numpy.linalg import norm

from glyphNameFormatter.reader import u2r, u2c

#registerRepresentationFactory(Glyph, "com.letterror.sim", myFactoryCallback) (edited) 


from multipleMarginPen import MultipleMarginPen

def NormalizedGlyphProfileFactory(glyph):
    la, ra, profile = makeNormalizedProfile(glyph)
    return profile

normalizedProfileKey = "com.letterror.similarity.normalizedGlyphProfile"
registerRepresentationFactory(defcon.Glyph, normalizedProfileKey, NormalizedGlyphProfileFactory)

def LeftAverageMarginFactory(glyph):
    leftAverage, ra, p = makeNormalizedProfile(glyph)
    return leftAverage

leftAverageMarginKey = "com.letterror.similarity.leftAverageMargin"
registerRepresentationFactory(defcon.Glyph, leftAverageMarginKey, LeftAverageMarginFactory)

def RightAverageMarginFactory(glyph):
    la, rightAverage, p = makeNormalizedProfile(glyph)
    return rightAverage

rightAverageMarginKey = "com.letterror.similarity.rightAverageMargin"
registerRepresentationFactory(defcon.Glyph, rightAverageMarginKey, RightAverageMarginFactory)



# experimental factory with parameters
SimilarGlyphsKey = "com.letterror.similarity.similarGlyphs"

def SimilarityRepresentationFactory(glyph, threshold=0.99, sameUnicodeClass=True, sameUnicodeRange=True, zones=None, side="left"):
    # return the glyphs that are similar on the left
    thisUnicodeRange = u2r(glyph.unicode)
    thisUnicodeClass = u2c(glyph.unicode)
    hits = {}
    # todo list
    font = glyph.font
    for other in font:
        #print("testing", threshold, other.name)
        otherUnicodeRange = u2r(other.unicode)
        if sameUnicodeRange and (otherUnicodeRange != thisUnicodeRange) and thisUnicodeRange is not None: continue
        otherUnicodeClass = u2c(other.unicode)
        if sameUnicodeClass and (otherUnicodeClass != thisUnicodeClass) and thisUnicodeClass is not None: continue
        # ok here we should only have the glyphs with same unicode range and class if we want to be selective
        score = cosineSimilarity(glyph, other, side=side, zones=zones)
        if threshold is not None:
            if score >= threshold:
                #print(f'{other.name}: {score}, {hits}')
                if not score in hits:
                    hits[score] = []
                hits[score].append(other.name)
        else:
            if not score in hits:
                hits[score] = []
            hits[score].append(other.name)
    return hits
    
# example of set up of representations + parameters
#        flat2 = other.getRepresentation("defcon.contour.flattened", approximateSegmentLength=segmentLength, segmentLines=True)
#    cls.representationFactories[name] = dict(factory=factory, destructiveNotifications=destructiveNotifications)

defcon.Glyph.representationFactories[SimilarGlyphsKey] = dict(factory=SimilarityRepresentationFactory, threshold=0.99, sameUnicodeClass=True, sameUnicodeRange=True, zones=None, side="left")
        
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
        return None, None, None
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
    return leftAverage, rightAverage, normalized

def getRange(values, zones):
    if zones is None: return values
    ok = []
    for v in values:
        for mn, mx in zones:
            if mn <= v <= mx:
                if v not in ok:
                    ok.append(v)
    ok.sort()
    return ok
        
def cosineSimilarity(first, second, side="left", zones=None):
    # compare normalized profiles of these glyphs according to cosine similarity
    # https://www.delftstack.com/howto/python/cosine-similarity-between-lists-python/
    sides = {}
    firstProfile = first.getRepresentation(normalizedProfileKey)
    secondProfile = second.getRepresentation(normalizedProfileKey)
    leftResult = rightResult = None            
    heights = [a for a,b,c in firstProfile] # the sample heights
    zoned = getRange(heights, zones)
    if side == "left":
        firstLeftProfile = [b for a,b,c in firstProfile if a in zoned]
        secondLeftProfile = [b for a,b,c in secondProfile if a in zoned]
        if firstLeftProfile and secondLeftProfile:
            leftResult = dot(firstLeftProfile, secondLeftProfile)/(norm(firstLeftProfile)*norm(secondLeftProfile))
            return float(leftResult)
    elif side=="right":
        firstRightProfile = [c for a,b,c in firstProfile if a in zoned]
        secondRightProfile = [c for a,b,c in secondProfile if a in zoned]
        if firstRightProfile and secondRightProfile:
            rightResult = dot(firstRightProfile, secondRightProfile)/(norm(firstRightProfile)*norm(secondRightProfile))
            return float(rightResult)
    return None

def compareGlyphs(font, members, side="left", zones=None):
    # see if the members of this group look like each other
    # returns a dict with comparisons between each of the members
    sideResult = {}
    done = []
    for first in members:
        for second in members:
            key = [first, second]
            key.sort()
            key = tuple(key)
            if first == second: continue
            if key in done: continue
            similarityValue = cosineSimilarity(font[key[0]], font[key[1]], side=side, zones=zones)
            sideResult[key] = similarityValue
            done.append(key)
    return sideResult

