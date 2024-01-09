import importlib
import cosineSimilarity
importlib.reload(cosineSimilarity)
from cosineSimilarity import normalizedProfileKey, cosineSimilarity, glyphPseudoUnicodeKey
from numpy import dot
from numpy.linalg import norm
import math
from glyphNameFormatter.reader import u2r, u2c
import fontTools.unicodedata
from itertools import combinations


"""
    Experiments with forming groups based on similarity profiles.
    The SimilarGroup object can add glyphs, if they're similar enough
    and in the same unicode class and unicode script, 
    the glyph's profile is added to the group profile. 
    
    The approach for finding the groups of a font is to
    start a SimilarGroup for each glyph, and then add each of the
    other glyphs in the font. If suitable, a glyph is added.
    
    That means we can have duplicates or near-duplicates. 
    This is filtered by the same() function.
    The balanceGroups() function sees if very similar groups
    can 
    

"""

class SimilarGroup(object):
    def __init__(self, side=None, clip=300, verbose=False, sameUnicodeClass=True, sameUnicodeScript=True):
        self.side = side
        self.verbose = verbose
        self.members = {}
        self.friends = {}
        self.seedName = None
        self.groupProfile = None    # average profile
        self.heights = None
        self.clip = clip
        self.sameUnicodeClass = sameUnicodeClass
        self.sameUnicodeScript = sameUnicodeScript
        self.groupUnicodeClass = None
        self.groupUnicodeScript = None
        
    def keys(self):
        return sorted(self.members.keys())
    
    def __len__(self):
        return len(self.members)
        
    def __repr__(self):
        sc = ss = ""
        if self.sameUnicodeClass:
            sc = f", {self.groupUnicodeClass}"
        if self.sameUnicodeScript:
            ss = f", {self.groupUnicodeScript}"

        return f"<SimilarGroup {self.side}{sc}{ss}, {self.asSlashString()} >"
    
    def asSlashString(self):
        ranked = self.ranked()
        return '/'+'/'.join([b.name for a, b in self.ranked()])
        
    def __cmp__(self, other):
        return self.keys() == other.keys()

    def __eq__(self, other):
        return self.keys() == other.keys()

    def __hash__(self):
        return hash(tuple(self.keys()))
    
    def identity(self):
        # returns a unique string for this group: tuple of sorted member names
        names = list(self.members.keys())
        names.sort()
        return tuple(names)
    
    def rate(self, other):
        # calculate how similar our membership is compared to the other group
        s1 = set(self.keys())
        s2 = set(other.keys())
        # union = all members
        # intersection = what they have in common
        # so if they have everything in common, the numbers will be the same, and the factor is 1
        # if they have nothing in common, the intersection will be 0 and the factor will be 0
        union = len(s1.union(s2))
        intersection = len(s1.intersection(s2))
        if union == 0: return 0
        if intersection == 0: return 0
        # can this be a value for the similarity of the membership?
        return intersection/union

    def checkCategories(self, glyph):
        # first time this gets called, we imprint the group on the class and script
        # second and other times, we compare to the imprinted values
        glyph_unicode = glyph.unicode
        glyph_UnicodeClass = None
        glyph_unicodeScript = None
        if glyph_unicode is None:
            glyph_unicode = glyph.getRepresentation(glyphPseudoUnicodeKey)
        if glyph_unicode is not None:
            glyph_UnicodeClass = u2c(glyph_unicode)
            glyph_unicodeScript = fontTools.unicodedata.script(glyph_unicode)
        # imprinting the default values for this group
        imprinted = False
        if not self.groupUnicodeClass and self.sameUnicodeClass:
            self.groupUnicodeClass = glyph_UnicodeClass
            imprinted = True
        if not self.groupUnicodeScript and self.sameUnicodeScript:
            self.groupUnicodeScript = glyph_unicodeScript
            imprinted = True
        if imprinted:
            # imprinting is done, nothing to compare
            #print('imprinted ', self.groupUnicodeClass, self.groupUnicodeScript)
            return True, True
            
        # we have values to compare with
        classOK = scriptOK = False
        if self.sameUnicodeClass:
            if self.groupUnicodeClass is not None:
                if glyph_UnicodeClass is not None:
                    if self.groupUnicodeClass == glyph_UnicodeClass:
                        classOK = True
        if self.sameUnicodeScript:
            if self.groupUnicodeScript is not None:
                if glyph_unicodeScript is not None:
                    if self.groupUnicodeScript == glyph_unicodeScript:
                        scriptOK = True
        #print(glyph.name, glyph_unicode, classOK, scriptOK)
        if self.sameUnicodeClass and self.sameUnicodeScript:
            return classOK and scriptOK
        elif self.sameUnicodeClass and not self.sameUnicodeScript:
            return classOK
        elif not self.sameUnicodeClass and self.sameUnicodeScript:
            return scriptOK
        return False

    def getGlyph(self, glyphName):
        return self.members.get(glyphName)[0]
        
    def addMember(self, glyph, minDistance=0.9, accept=True):
        if self.verbose:
            print('candidate addMember', glyph.name)
        if not self.checkCategories(glyph): return False, 0
        heights = []
        d = 1
        if self.members:
            d = self.distance(glyph)
            if d < minDistance:
                if self.verbose:
                    print(f'\t\tdiscarding {glyph.name} because {float(d):3.3}')
                return False, d
        else:
            self.seedName = glyph.name
            
        if self.verbose:
            print(f'\tadding {glyph.name}')
        p = glyph.getRepresentation(normalizedProfileKey, clip = self.clip)
        if self.heights is None:
            self.heights = [a for a,b,c in p]
        else:
            assert self.heights == [a for a,b,c in p]
        if self.side == "left":
            profile = [b for a,b,c in p]
        elif self.side == "right":
            profile = [c for a,b,c in p]
        if accept:
            self.members[glyph.name] = glyph, profile    # store the profile of each member so we can recalculate the average.
            self.average()
        return True, d
    
    def groupDistance(self, other):
        # calculate the cosine sim distance between the group profiles
        result = dot(other.groupProfile, self.groupProfile)/(norm(other.groupProfile)*norm(self.groupProfile))
        if math.isnan(result):
            result = 0
        return result
        
    def distance(self, glyph):
        p = glyph.getRepresentation(normalizedProfileKey, clip=self.clip)
        result = None
        if self.side == "left":
            leftProfile = [b for a,b,c in p]
            result = dot(leftProfile, self.groupProfile)/(norm(leftProfile)*norm(self.groupProfile))
        elif self.side == "right":
            rightProfile = [c for a,b,c in p]
            result = dot(rightProfile, self.groupProfile)/(norm(rightProfile)*norm(self.groupProfile))
        if math.isnan(result):
            result = 0
        return result

    def audit(self):
        # how do the members compare to the average?
        members = []
        for name, item in self.members.items():
            glyph, profile = item
            print("\taudit", name, self.distance(glyph))
            members.append(f"/{name}")
            #print(''.join(members))
    
    def ranked(self):
        ranking = []
        for glyphName, (glyph, profile) in self.members.items():
            dst = self.distance(glyph)
            ranking.append((dst,glyph))
        return sorted(ranking, key=lambda x: x[0], reverse=True)
            
    def average(self):
        # calculate the average profile
        d = {}
        if not self.members:
            return False
        for m, item in self.members.items():
            glyph, values = item
            for y, v in enumerate(values):
                if not y in d:
                    d[y] = []
                d[y].append(v)
        l = []
        for h in sorted(d.keys()):
            l.append(sum(d[h])/len(d[h]))
        self.groupProfile = l
        return True
    
    def asSpaceCenter(self):
        # return this group as a space center string
        ranked = self.ranked()
        t = '/'+'/'.join([b.name for a, b in self.ranked()])
        if self.side == "left":
            t = f"[{self.seedName} " + t
        else:
            t = f"{self.seedName}] " + t
        return t
    
    def asFDKGroup(self):
        groupText = f'@similarity_{self.side}_{self.seedName} = [{" ".join(self.keys())}];'
        return groupText

def asSimilarGroup(groupName, font):
    side = None
    if "public.kern1" in groupName:
        side = "right"
    elif "public.kern" in groupName:
        side = "left"
    if side is not None:
        g = SimilarGroup(side=side)
        for m in font.groups[groupName]:
            #print('adding', m)
            g.addMember(font[m], minDistance=0)
        return g
    return None
        
def rateGroups(groups):
    # find identical and near identical groups
    for pair in combinations(groups.keys(), 2):
        g1 = groups[pair[0]]
        g2 = groups[pair[1]]
        rateMember = g1.rate(g2)
        rateProfile = g1.groupDistance(g2)
        if rateMember > .6 and rateProfile > 0.6:
            #print(rateMember, rateProfile, pair)
            #print("\t", g1)
            #print("\t", g2)
            balanceGroups(g1, g2, show=False)
    return groups

def same(groups):
    seen = {}
    for name, g in groups.items():
        i = g.identity()
        seen[g.identity()] = (name, g)
    groups = {}
    for i, value in seen.items():
        groups[value[0]] = value[1]    
    return groups
    
def singles(groups):
    # filter the groups that only have 1 member
    seen = {}
    for name, g in groups.items():
        if len(g) < 2:
            continue
        seen[name] = g
    return seen

def balanceGroups(group1, group2, show=False):
    # show the members in columns
    # with overlap and exclusive parts of the groups
    if show:
        print(f'\n\n|    {str(group1):<25}({str(group2):<25})')
    s1 = set(group1.keys())
    s2 = set(group2.keys())
    intersection = s1.intersection(s2)
    s1only = s1.difference(s2)
    s2only = s2.difference(s1)
    #print()
    for item in list(s1only):
        g = group1.getGlyph(item)
        ok, value = group2.addMember(g)
        if ok and show:
            print(f'|    {item:<25}({value:<25})')
    if show:
        for item in list(intersection):
            print(f'|    {item:<25}{item:<25}')
    for item in list(s2only):
        g = group2.getGlyph(item)
        ok, value = group1.addMember(g)
        if ok and show:
            print(f'|    ({value:<25}){item:<25}')

def proposeGroupsGlyph(glyph, side, sameUnicodeClass=True, sameUnicodeScript=True, repeats=2):
    font = glyph.font
    sg = SimilarGroup(side=side, sameUnicodeClass=sameUnicodeClass, sameUnicodeScript=sameUnicodeScript)
    sg.addMember(glyph)
    for other in font.keys():
        if other == glyph: continue
        sg.addMember(font[other])
    return sg

def proposeGroupsFont(font, side, sameUnicodeClass=True, sameUnicodeScript=True, repeats=4):
    names = font.keys()
    groups = {}
    for first in names:
        sg = proposeGroupsGlyph(font[first], side=side, sameUnicodeClass=sameUnicodeClass, sameUnicodeScript=sameUnicodeScript)
        groups[first] = sg
    groups = singles(groups)
    for r in range(repeats):
        print(f"run {r+1} {len(groups)}")
        groups = same(groups)
        groups = rateGroups(groups)
    return groups

if __name__ == "__main__":
    import time
    
    font = CurrentFont()
    glyph = CurrentGlyph()
    show = False
    
    if glyph is not None:
        # expected: single group for left, single group for right
        # takes less than .1 seconds per side per glyph
        start = time.time()
        left = proposeGroupsGlyph(glyph, "left")
        right = proposeGroupsGlyph(glyph, "right")
        end = time.time()
        print(f"duration glyph {glyph.name} {end-start}")
        print(f'left: {left}')
        left.audit()
        print(f'right: {right}')
        right.audit()
        if show:
            print("left\t", left)
            print("right\t", right)

    if font is not None:
        # expected: for the whole font, left groups and right groups
        # takes about 25 seconds per side for a 500 glyph font
        start = time.time()
        left = proposeGroupsFont(font, "left")
        right = proposeGroupsFont(font, "right")
        end = time.time()
        print(f"duration font {len(font)} glyphs {end-start}")
        print(f'final left: {len(left)}')
        print(f'final right: {len(right)}')
        if show:
            for name, group in left.items():
                print("left\t", group)
            for name, group in right.items():
                print("right\t", group)
                
        
