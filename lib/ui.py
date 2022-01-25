import importlib
import cosineSimilarity
importlib.reload(cosineSimilarity)

import vanilla
import math

from cosineSimilarity import cosineSimilarity, SimilarGlyphsKey, leftAverageMarginKey, rightAverageMarginKey

from mojo.UI import CurrentSpaceCenter, OpenSpaceCenter, setDefault, getDefault, OpenGlyphWindow
from mojo.subscriber import Subscriber, WindowController, registerGlyphEditorSubscriber
from glyphNameFormatter.reader import u2r, u2c


#g = CurrentGlyph()
#print('test with', g.name)
#r = g.getRepresentation(SimilarGlyphsKey, threshold=0.90, side="left")
#print(r)

#r = g.getRepresentation(SimilarGlyphsKey, threshold=0.90, side="right")
#print(r)


YELLOW = (1, 1, 0, 0.4)
RED = (1, 0, 0, 0.4)
BLUE = (.5, 0, 1, 0.3)

roboFontItalicSlantLibKey = "com.typemytype.robofont.italicSlantOffset"


class SimilarityUI(Subscriber, WindowController):
    # simple window to show similarity ranking for the current glyph
    
    thresholdPrefKey = "com.letterror.similarity.threshold"
    unicodeCategoryPrefKey = "com.letterror.similarity.unicodeCategory"
    unicodeRangePrefKey = "com.letterror.similarity.unicodeRange"
    syncSpaceCenterPrefKey = "com.letterror.similarity.syncSpaceCenter"
    
    def build(self):
        
        glyphEditor = self.getGlyphEditor()

        self.container = glyphEditor.extensionContainer(
            identifier="com.roboFont.NeighboursDemo.foreground",
            location="foreground",
            clear=True)
        self.leftPathLayer = self.container.appendPathSublayer(
            strokeColor=RED,
            fillColor=None,
            strokeWidth=2,
            name="leftNeighbour")
        self.rightPathLayer = self.container.appendPathSublayer(
            strokeColor=BLUE,
            fillColor=None,
            strokeWidth=2,
            name="rightNeighbour")
        
        self.zones = None
        self.showSimilar = 10
        self.threshold = getDefault(self.thresholdPrefKey, 0.9)
        self.currentName = None
        self.currentGlyph = None
        self.currentCategory = None
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
                {   'title': "Category",
                    'key':'unicodeCategory',
                    'editable':False,
                },
                {   'title': "Range",
                    'key':'unicodeRange',
                    'editable':False,
                },
        ]
        col1 = 100
        col2 = 260
        col3 = col2+(col2-col1)
        self.w = vanilla.Window((600, 500), "LTR Similarity", minSize=(200,100))
        self.w.l = vanilla.List((5,100,-5, -40),[], 
            columnDescriptions=glyphDescriptions, 
            selectionCallback=self.selectItemsCallback,
            doubleClickCallback = self.listDoubleClickCallback
            )
        self.w.cb1 = vanilla.CheckBox((col1, 5, 150, 20), "Above xHeight", value=1, callback=self.zoneCallback)
        self.w.cb2 = vanilla.CheckBox((col1, 25, 150, 20), "Baseline to xHeight", value=1, callback=self.zoneCallback)
        self.w.cb3 = vanilla.CheckBox((col1, 45, 150, 20), "Below baseline", value=1, callback=self.zoneCallback)
        self.w.cbuniCat = vanilla.CheckBox((col2, 5, -5, 20), "Unicode category", value=getDefault(self.unicodeCategoryPrefKey, 1), callback=self.update)
        self.w.cbuniRange = vanilla.CheckBox((col2, 25, -5, 20), "Unicode range", value=getDefault(self.unicodeRangePrefKey, 1), callback=self.update)
        self.w.threshold = vanilla.EditText((col2,70,50,20), self.threshold, sizeStyle="small", callback=self.editThreshold)
        self.w.thresholdSlider = vanilla.Slider((col1, 70, 120, 20), minValue=0, maxValue=1, value=self.threshold, callback=self.sliderCallback, continuous=True)
        self.w.thresholdCaption = vanilla.TextBox((315,72,100,20), "Threshold", sizeStyle="small")
        #self.w.update = vanilla.Button((-100, 5, -5, 20), "Update", callback=self.update)
        self.w.current = vanilla.TextBox((10,5, 90,20), "Nothing")
        self.w.toSpaceCenter = vanilla.Button((10,-30,150,20), "To SpaceCenter", callback=self.toSpaceCenter)
        self.w.selectInFont = vanilla.Button((170,-30,150,20), "Select", callback=self.selectInFont)
        self.w.bind("close", self.destroy)
        self.w.open()
        self.update()

    def listDoubleClickCallback(self, sender):
        selectedItems = [self.w.l[s] for s in self.w.l.getSelection()]
        name = selectedItems[0].get('glyphName')
        OpenGlyphWindow(CurrentFont()[name])
        
    def sliderCallback(self, sender):
        self.threshold = float(sender.get())
        self.update()
        self._updateNeighbours(self.currentGlyph)
        self.w.threshold.set(self.threshold)
    
    def selectItemsCallback(self, sender):
        self._updateNeighbours(self.currentGlyph)
        
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

    def destroy(self, sender=None):
        setDefault(self.unicodeCategoryPrefKey, self.w.cbuniCat.get())
        setDefault(self.unicodeRangePrefKey, self.w.cbuniRange.get())
        self.container.clearSublayers()

    def glyphEditorDidSetGlyph(self, info):
        self.currentGlyph = info['glyph']
        if self.currentGlyph is not None:
            self.update()
            self._updateNeighbours(self.currentGlyph)

    def _updateNeighbours(self, glyph):
        if glyph is None: return
        font = glyph.font
        italicSlantOffset = font.lib.get(roboFontItalicSlantLibKey, 0)
        self.leftPathLayer.clearSublayers()
        self.rightPathLayer.clearSublayers()
        selectedItems = [self.w.l[s] for s in self.w.l.getSelection()]
        for item in selectedItems:
            simGlyph = font[item['glyphName']]
            glyphPath = simGlyph.getRepresentation("merz.CGPath")
            if len(item.get('scoreLeft')) > 0:
                pp = self.leftPathLayer.appendPathSublayer(
                    strokeColor=RED,                    
                    fillColor=None,
                    strokeWidth=1,
                    name="leftNeighbour")
                pp.setPath(glyphPath)
                pp.setPosition((-simGlyph.leftMargin+glyph.leftMargin, 0))
            elif len(item.get('scoreRight')) > 0:
                pp = self.rightPathLayer.appendPathSublayer(
                    strokeColor=BLUE,                    
                    fillColor=None,
                    strokeWidth=1,
                    name="rightNeighbour")
                pp.setPath(glyphPath)
                #pp.setPosition((-simGlyph.width - simGlyph.rightMargin + glyph.rightMargin + glyph.width, 0))
                pp.setPosition((-simGlyph.width + glyph.width, 0))
    
    def editThreshold(self, sender=None):
        v = None
        try:
            v = float(sender.get())
        except ValueError:
            return
        if v:
            self.threshold = v
            self.w.thresholdSlider.set(self.threshold)
            setDefault(self.thresholdPrefKey, self.threshold)
            self.update()
    
    def selectInFont(self, sender=None):
        # select the selected glyphs in the font window
        leftNames, rightNames = self.getSelectedGlyphs()
        allNames = set.union(set(leftNames), set(rightNames))
        font = CurrentFont()
        font.selection = allNames
        
    def getSelectedGlyphs(self):
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
        return leftNames, rightNames
        
    def toSpaceCenter(self, sender=None):
        # put the selected names in a spacecenter
        leftNames, rightNames = self.getSelectedGlyphs()
        text = f"/bracketleft/{self.currentName}/space/space{'/'+'/'.join(leftNames)}\\n/{self.currentName}/bracketright/space/space{'/'+'/'.join(rightNames)}"
        if self.currentGlyph is not None:
            sc = CurrentSpaceCenter(self.currentGlyph.font)
            if sc is None:
                OpenSpaceCenter(self.currentGlyph.font)
            sc = CurrentSpaceCenter(self.currentGlyph.font)
            sc.setRaw(text)
        
    def update(self, sender=None):
        this = self.currentGlyph
        if this is None:
            self.currentCategory = None
            self.currentRange = None
            self.w.l.set([])
            return
        limitUnicodeCategory = self.w.cbuniCat.get()
        limitUnicodeRange = self.w.cbuniRange.get()
        self.currentCategory = u2c(this.unicode)
        self.currentRange = u2r(this.unicode)
        font = CurrentFont()
        if this is None:
            self.w.l.set([])
            self.currentName = None
            self.w.current.set("")
            return
        self.currentName = this.name
        self.w.current.set(self.currentName)
        
        items = []
        if self.zones:
            z = tuple(self.zones)
        else:
            z = None
        rankLeft = this.getRepresentation(SimilarGlyphsKey,
            threshold=self.threshold, 
            sameUnicodeClass=limitUnicodeCategory,
            sameUnicodeRange=limitUnicodeRange,
            zones=z,
            side="left",
            )
        rankRight = this.getRepresentation(SimilarGlyphsKey,
            threshold=self.threshold,
            sameUnicodeClass=limitUnicodeCategory,
            sameUnicodeRange=limitUnicodeRange,
            zones=z,
            side="right",
            )


        # rankLeft = {}
        # rankRight = {}
        # items = []
        # rangeLookup = {}
        # categoryLookup = {}
        # for g in font:
        #     if g.name == this.name:
        #         continue
        #     if limitUnicodeCategory:
        #         if self.currentCategory != u2c(g.unicode):
        #             continue
        #     if limitUnicodeRange:
        #         if self.currentRange != u2r(g.unicode):
        #             continue
        #     thisUniCat = u2c(g.unicode)
        #     if thisUniCat is not None:
        #         categoryLookup[g.name] = thisUniCat
        #     thisUniRange = u2r(g.unicode)
        #     if thisUniRange is not None:
        #         rangeLookup[g.name] = thisUniRange
        #     ls = cosineSimilarity(this, g, side="left", zones=self.zones)
        #     rs = cosineSimilarity(this, g, side="right", zones=self.zones)
        #     if not ls in rankLeft:
        #         rankLeft[ls] = []
        #     rankLeft[ls].append(g.name)
        #     if not rs in rankRight:
        #         rankRight[rs] = []
        #     rankRight[rs].append(g.name)        
        rk = list(rankLeft.keys())
        rk = sorted(rk, key = lambda x : float('-inf') if math.isnan(x) else x)
        rk = [v for v in rk if v > self.threshold]
        rk.sort()
        rk.reverse()
        for k in rk[:self.showSimilar]:
            for name in rankLeft[k]:
                cat = u2c(font[name].unicode)
                if cat is None:
                    cat = ''
                rng = u2r(font[name].unicode)
                if rng is None:
                    rng = ''
                items.append(dict(glyphName=name, 
                    scoreLeft=f"{k:3.5f}", 
                    scoreRight="", 
                    unicodeCategory=cat,
                    unicodeRange=rng,
                    ))
        rk = list(rankRight.keys())
        rk = sorted(rk, key = lambda x : float('-inf') if math.isnan(x) else x)
        rk = [v for v in rk if v > self.threshold]
        rk.sort()
        rk.reverse()
        for k in rk[:self.showSimilar]:
            for name in rankRight[k]:
                cat = u2c(font[name].unicode)
                if cat is None:
                    cat = ''
                rng = u2r(font[name].unicode)
                if rng is None:
                    rng = ''
                items.append(dict(glyphName=name, 
                    scoreRight=f"{k:3.5f}", 
                    scoreLeft="", 
                    unicodeCategory=cat,
                    unicodeRange=rng,
                    ))
        self.w.l.set(items)

registerGlyphEditorSubscriber(SimilarityUI)

