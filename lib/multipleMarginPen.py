
from fontTools.pens.basePen import BasePen
from fontTools.misc.bezierTools import splitLine, splitCubic

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
            self.hits[value] = set()
        x, y = hit        
        self.hits[value].add(hit[not self.isHorizontal])

    def _moveTo(self, pt):
        self.currentPt = pt
        self.startPt = pt
        
        for value in self.values:
            if pt[self.isHorizontal] == value:
                self._addHit(value, pt)

    def _lineTo(self, pt):
        if self.filterDoubles:
            if pt == self.currentPt:
                return
        
        for value in self.values:
            if pt[self.isHorizontal] == value:
                self._addHit(value, pt)
                
        for value in self.values:
            hits = splitLine(self.currentPt, pt, value, self.isHorizontal)
            for hit in hits[:-1]:
                self._addHit(value, hit[-1])
        self.currentPt = pt

    def _curveToOne(self, pt1, pt2, pt3):
        for value in self.values:
            if pt3[self.isHorizontal] == value:
                self._addHit(value, pt3)
                
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

