
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
            self.hits[value] = []
        x, y = hit
        v = hit[not self.isHorizontal]
        if v not in self.hits[value]:
            self.hits[value].append(v)

    def _moveTo(self, pt):
        self.currentPt = pt
        self.startPt = pt

    def _lineTo(self, pt):
        if self.filterDoubles:
            if pt == self.currentPt:
                return
        for value in self.values:
            hits = splitLine(self.currentPt, pt, value, self.isHorizontal)
            if len(hits) == 1:
                # splitLine returns the original line segment
                # if there is no split (see fontTools/bezierTools.
                # This means we are responsible
                # for handling intersections through start / end points
                checkEnd = hits[0][1]
                if self.isHorizontal:
                    if checkEnd[1] == value:
                        self._addHit(value, checkEnd)
                else:
                    if checkEnd[0] == value:
                        self._addHit(value, checkEnd)
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
        s = {}
        for k, v in self.hits.items():
            v.sort()
            s[k]=v
        return s

