import importlib
import cosineSimilarity
importlib.reload(cosineSimilarity)

from cosineSimilarity import cosineSimilarity
import math
from mojo.UI import CurrentSpaceCenter, OpenSpaceCenter
import vanilla
from pprint import pprint
from random import choice
from mojo.subscriber import Subscriber, WindowController, registerCurrentFontSubscriber

from glyphNameFormatter.reader import u2r
from mojo.UI import setDefault, getDefault

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
        ls = cosineSimilarity(this, g, side="left")
        rs = cosineSimilarity(this, g, side="right")
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


class SimilarityUI(Subscriber, WindowController):
    # simple window to show similarity ranking for the current glyph
    
    thresholdPrefKey = "com.letterror.similarity,threshold"
    
    def build(self):
        self.zones = None
        self.showSimilar = 10
        self.threshold = getDefault(self.thresholdPrefKey, 0.9)
        self.currentName = None
        self.currentGlyph = None
        self.currentRange = None
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
                {   'title': "Range",
                    'key':'unicodeRange',
                    'editable':False,
                },
        ]
        self.w = vanilla.Window((300, 500), "Similarity", minSize=(200,100))
        self.w.l = vanilla.List((5,100,-5, -40),[], columnDescriptions=glyphDescriptions)
        self.w.cb1 = vanilla.CheckBox((100, 5, -5, 20), "Above xHeight", value=1, callback=self.zoneCallback)
        self.w.cb2 = vanilla.CheckBox((100, 25, -5, 20), "Baseline to xHeight", value=1, callback=self.zoneCallback)
        self.w.cb3 = vanilla.CheckBox((100, 45, -5, 20), "Below baseline", value=1, callback=self.zoneCallback)
        self.w.cbur = vanilla.CheckBox((100, 65, -5, 20), "Only same Unicode range", value=1, callback=self.update)
        self.w.threshold = vanilla.EditText((5,-35,50,20), self.threshold, sizeStyle="small", callback=self.editThreshold)
        self.w.thresholdCaption = vanilla.TextBox((60,-32,100,20), "Threshold", sizeStyle="small")
        #self.w.update = vanilla.Button((-100, 5, -5, 20), "Update", callback=self.update)
        self.w.current = vanilla.TextBox((10,5, 90,20), "Nothing")
        self.w.toSpaceCenter = vanilla.CheckBox((-100,-35,-5,20), "SpaceCenter", self.toSpaceCenter, sizeStyle="small")
        self.w.open()
        self.update()

    def zoneCallback(self, sender):
        font = CurrentFont()
        zones = []
        if self.w.cb1.get():
            zones.append((font.info.xHeight, font.info.unitsPerEm+font.info.descender))
        if self.w.cb2.get():
            zones.append((0, font.info.xHeight))
        if self.w.cb3.get():
            zones.append((font.info.descender, 0))
        if not zones:
            self.zones = None
        else:
            self.zones = zones
        self.update()
        
    def started(self):
        self.w.open()

    def glyphEditorDidSetGlyph(self, info):
        self.currentGlyph = info['glyph']
        self.update()
    
    def editThreshold(self, sender=None):
        v = None
        try:
            v = float(sender.get())
        except ValueError:
            return
        if v:
            self.threshold = v
            setDefault(self.thresholdPrefKey, self.threshold)
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
        if self.currentGlyph is not None:
            sc = CurrentSpaceCenter(self.currentGlyph.font)
            if sc is None:
                OpenSpaceCenter(self.currentGlyph.font)
            sc.setRaw(text)
        
    def update(self, sender=None):
        this = self.currentGlyph
        if this is None:
            self.currentRange = None
            self.w.l.set([])
            return
        limitUnicodeRange = self.w.cbur.get()
        self.currentRange = u2r(this.unicode)
        font = CurrentFont()
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
        rangeLookup = {}
        for g in font:
            if g.name == this.name:
                continue
            if limitUnicodeRange:
                if self.currentRange != u2r(g.unicode):
                    continue
            v = u2r(g.unicode)
            if v is not None:
                rangeLookup[g.name] = v
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
                items.append(dict(glyphName=name, scoreLeft=f"{k:3.3f}", scoreRight="", unicodeRange=rangeLookup.get(name, '')))
        rk = list(rankRight.keys())
        rk = sorted(rk, key = lambda x : float('-inf') if math.isnan(x) else x)
        rk = [v for v in rk if v > self.threshold]
        rk.sort()
        rk.reverse()
        for k in rk[:self.showSimilar]:
            for name in rankRight[k]:
                items.append(dict(glyphName=name, scoreRight=f"{k:3.3f}", scoreLeft="", unicodeRange=rangeLookup.get(name, '')))
        self.w.l.set(items)
        if self.w.toSpaceCenter.get():
            self.toSpaceCenter()


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
        ls = cosineSimilarity(this, g, side="left")
        rs = cosineSimilarity(this, g, side="right")
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

