
import statistics
import math
import numpy
from defcon import addRepresentationFactory, registerRepresentationFactory
import defcon


from numpy import dot
from numpy.linalg import norm
from glyphNameFormatter.reader import u2r, u2c
from multipleMarginPen import MultipleMarginPen
import fontTools.unicodedata


# make the defcon pseudo unicodes available in a factory
# destruct on changed glyphname. (can't find changed unicode in defcon)
glyphPseudoUnicodeKey = "com.letterror.similarity.glyphPseudoUnicode"

def PseudoUnicodeFactory(glyph):
    return glyph.font.asDefcon().unicodeData.pseudoUnicodeForGlyphName(glyph.name)
    
defcon.Glyph.representationFactories[glyphPseudoUnicodeKey] = dict(
    factory=PseudoUnicodeFactory, 
    destructiveNotifications=("Glyph.NameChanged", "Glyph.UnicodesChanged"),
    )

#g = CurrentGlyph()
#uni = g.getRepresentation(glyphPseudoUnicodeKey)
#print(g.name, uni)



def NormalizedGlyphProfileFactory(glyph, clip=200):
    la, ra, profile = makeNormalizedProfile(glyph, clip=clip)
    return profile

normalizedProfileKey = "com.letterror.similarity.normalizedGlyphProfile"

defcon.Glyph.representationFactories[normalizedProfileKey] = dict(
    factory=NormalizedGlyphProfileFactory, 
    destructiveNotifications=("Contour.PointsChanged",),
    clip=200,
    )

SimilarGlyphsKey = "com.letterror.similarity.similarGlyphs"


def SimilarityRepresentationFactory(glyph, threshold=0.99, 
                sameUnicodeClass=True, 
                sameUnicodeRange=False, 
                sameUnicodeScript=True,
                zones=None, 
                side="left", 
                clip=200, 
                ):
    glyph_unicode = glyph.unicode
    font = glyph.font
    if glyph_unicode is None:
        glyph_unicode = glyph.getRepresentation(glyphPseudoUnicodeKey)
        #glyph_unicode = font.asDefcon().unicodeData.pseudoUnicodeForGlyphName(glyph.name)
    # return the glyphs that are similar on the left
    thisUnicodeClass = u2c(glyph_unicode)
    if glyph_unicode is not None:
        thisUnicodeScript = fontTools.unicodedata.script(glyph_unicode)
    else:
        thisUnicodeScript = None
    hits = {}
    for other in font:
        other_unicode = other.unicode
        if other_unicode is None:
            other_unicode = other.getRepresentation(glyphPseudoUnicodeKey)
            #other_unicode = font.asDefcon().unicodeData.pseudoUnicodeForGlyphName(other.name)
        if other_unicode is not None:
            otherUnicodeClass = u2c(other_unicode)
            otherUnicodeScript = fontTools.unicodedata.script(other_unicode)
            if sameUnicodeClass and (otherUnicodeClass != thisUnicodeClass) and thisUnicodeClass is not None:
                #print(f"A ----- {glyph.name}: {otherUnicodeScript} {thisUnicodeScript}")                
                continue
            if sameUnicodeScript and (otherUnicodeScript != thisUnicodeScript) and thisUnicodeScript is not None:
                #print(f"B ----- {glyph.name}: {otherUnicodeScript} {thisUnicodeScript}")
                continue
        # the other.unicode is None
        # skip comparisons between a glyph that has a unicode and the other that does not.
        # this may skip some alternates.
        # this may need to be addressed with pseudo-unicodes
        if glyph_unicode is not None and other_unicode is None:
            #print(f"\tD ----- {glyph.name}: {glyph.unicode} / {other.name} {other.unicode}")
            continue
        if glyph_unicode is None:
            continue
                
        #print(f"C ----- {glyph.name}: {glyph.unicode} / {other.name} {other.unicode}")                
        # ok here we should only have the glyphs with same unicode script and class if we want to be selective
        score = cosineSimilarity(glyph, other, side=side, zones=zones, clip=clip)
        if score is not None:
            if threshold is not None:
                if score >= threshold:
                    if not score in hits:
                        hits[score] = []
                    hits[score].append(other.name)
            else:
                if not score in hits:
                    hits[score] = []
                hits[score].append(other.name)
    return hits
    
defcon.Glyph.representationFactories[SimilarGlyphsKey] = dict(
    factory=SimilarityRepresentationFactory, 
    destructiveNotifications=("Contour.PointsChanged",),
    threshold=0.99, 
    sameUnicodeClass=True, 
    sameUnicodeScript=True, 
    zones=None, 
    side="left"
    )
        
def stepRange(mn, mx, parts):
    # return a list of *parts or sections* between mn, mx
    # so not the length of the output list.
    # stepRange(0,10,2)
    # [0.0, 5.0, 10.0]
    if parts < 1:
        return [mn, mx]
    d = mx-mn
    return [mn+(i/(parts)*d) for i in range(parts+1)]

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
    padding = 100
    sections = [
        (0, font.info.descender - padding, 20),
        (0, font.info.xHeight, 40),
        (font.info.xHeight, font.info.unitsPerEm+font.info.descender + padding, 20)
    ]
    sampleHeights = []
    for mn,mx,step in sections:
        [sampleHeights.append(v) for v in stepRange(mn,mx,step) if v not in sampleHeights]
    sampleHeights.sort()
    mmp = MultipleMarginPen(glyph.font, sampleHeights)
    glyph.draw(mmp)
    hits = mmp.getMargins()
    _tana = math.tan(math.radians(-a))
    for h in sampleHeights:
        if a is not 0:
            ta = _tana * h
        else:
            ta = 0
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
        
def cosineSimilarity(first, second, side="left", zones=None, clip=300):
    sides = {}
    firstProfile = first.getRepresentation(normalizedProfileKey, clip=clip)
    secondProfile = second.getRepresentation(normalizedProfileKey, clip=clip)
    leftResult = rightResult = None            
    heights = [a for a,b,c in firstProfile] # the sample heights
    zoned = getRange(heights, zones)
    # we need to manage the numpy error levels for this operation
    # in some cases it will raise a lot of RuntimeWarning: invalid value encountered in double_scalars
    # https://numpy.org/doc/stable/reference/generated/numpy.seterr.html
    # we will store the original settings
    old_settings = numpy.seterr(all='ignore')  #seterr to known value
    result = None
    if side == "left":
        firstLeftProfile = [b for a,b,c in firstProfile if a in zoned]
        secondLeftProfile = [b for a,b,c in secondProfile if a in zoned]
        if firstLeftProfile and secondLeftProfile:
            result = float(dot(firstLeftProfile, secondLeftProfile)/(norm(firstLeftProfile)*norm(secondLeftProfile)))
    elif side=="right":
        firstRightProfile = [c for a,b,c in firstProfile if a in zoned]
        secondRightProfile = [c for a,b,c in secondProfile if a in zoned]
        if firstRightProfile and secondRightProfile:
            result = float(dot(firstRightProfile, secondRightProfile)/(norm(firstRightProfile)*norm(secondRightProfile)))
    numpy.seterr(**old_settings)  # reset to default
    return result

def compareGlyphs(font, members, side="left", zones=None):
    # see if the members of this group look like each other
    # returns a dict with comparisons between each of the members
    sideResult = {}
    done = []
    for first in members:
        for second in members:
            if first == second: continue
            key = [first, second]
            key.sort()
            key = tuple(key)
            if key in done: continue
            similarityValue = cosineSimilarity(font[key[0]], font[key[1]], side=side, zones=zones)
            sideResult[key] = similarityValue
            done.append(key)
    return sideResult

