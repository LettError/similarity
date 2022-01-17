import importlib
import cosineSimilarity
importlib.reload(cosineSimilarity)
from cosineSimilarity import normalizedProfileKey, cosineSimilarity
from numpy import dot
from numpy.linalg import norm
import math

# some experiments with similarity objects?

class SimilarGroup(object):
    def __init__(self, side=None, verbose=False):
        self.side = side
        self.verbose = verbose
        self.members = {}
        self.seedName = None
        self.profile = None    # average profile
        self.heights = None
        
    def keys(self):
        return sorted(self.members.keys())
    
    def __len__(self):
        return len(self.members)
        
    def __repr__(self):
        return f"<SimilarGroup {self.side} with {' '.join(self.keys())}>"
        
    def __cmp__(self, other):
        return self.keys() == other.keys()

    def __eq__(self, other):
        return self.keys() == other.keys()

    def __hash__(self):
        return hash(tuple(self.keys()))
    
    def addMember(self, glyph, minDistance=0.9):
        if self.verbose:
            print('candidate addMember', glyph.name)
        heights = []
        if self.members:
            d = self.distance(glyph)
            if d < minDistance:
                if self.verbose:
                    print(f'\t\tdiscarding {glyph.name} because {float(d):3.3}')
                return
        else:
            self.seedName = glyph.name
            
        if self.verbose:
            print(f'\tadding {glyph.name}')
        p = glyph.getRepresentation(normalizedProfileKey)
        if self.heights is None:
            self.heights = [a for a,b,c in p]
        else:
            assert self.heights == [a for a,b,c in p]

        if self.side == "left":
            profile = [b for a,b,c in p]
        elif self.side == "right":
            profile = [c for a,b,c in p]
        self.members[glyph.name] = glyph, profile    # store the profile of each member so we can recalculate the average.
        self.average()
    
    def distance(self, glyph):
        p = glyph.getRepresentation(normalizedProfileKey)
        result = None
        if self.side == "left":
            leftProfile = [b for a,b,c in p]
            result = dot(leftProfile, self.profile)/(norm(leftProfile)*norm(self.profile))
        elif self.side == "right":
            rightProfile = [c for a,b,c in p]
            result = dot(rightProfile, self.profile)/(norm(rightProfile)*norm(self.profile))
        if math.isnan(result):
            result = 0
        return result

    def audit(self):
        # how do the members compare to the average?
        members = []
        for name, item in self.members.items():
            glyph, profile = item
            print("audit", name, self.distance(glyph))
            members.append(f"/{name}")
            #print(''.join(members))
        
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
        self.profile = l
        return True
    
    def asSpaceCenter(self):
        # return this group as a space center string
        t = '/'+'/'.join(self.keys())
        if self.side == "left":
            t = f"[{self.seedName} " + t
        else:
            t = f"{self.seedName}] " + t
        return t
    
    def asFDKGroup(self):
        groupText = f'@similarity_{self.side}_{self.seedName} = [{" ".join(self.keys())}];'
        return groupText

    
def uniqueGroups(groups, smallest=2):
    # filter all the duplicate lists
    s = set()
    for name, group in groups.items():
        if len(group) <= smallest:
            continue
        s.add(group)
    return list(s)
    

