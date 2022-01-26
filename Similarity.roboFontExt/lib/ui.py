import importlib
import cosineSimilarity
importlib.reload(cosineSimilarity)

import vanilla
import math, time
import AppKit

from cosineSimilarity import cosineSimilarity, SimilarGlyphsKey

from mojo.UI import CurrentSpaceCenter, OpenSpaceCenter, setDefault, getDefault, OpenGlyphWindow
from mojo.subscriber import Subscriber, WindowController, registerGlyphEditorSubscriber
from glyphNameFormatter.reader import u2r, u2c

RED = (1, 0, 0, 0.4)
BLUE = (.5, 0, 1, 0.3)

roboFontItalicSlantLibKey = "com.typemytype.robofont.italicSlantOffset"

class RightAlignEditTextList2Cell(vanilla.EditTextList2Cell):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.editText.getNSTextField().setAlignment_(AppKit.NSTextAlignmentRight)


class SimilarityUI(Subscriber, WindowController):
    # simple window to show similarity ranking for the current glyph
    
    thresholdPrefKey = "com.letterror.similarity.threshold"
    unicodeCategoryPrefKey = "com.letterror.similarity.unicodeCategory"
    unicodeRangePrefKey = "com.letterror.similarity.unicodeRange"
    syncSpaceCenterPrefKey = "com.letterror.similarity.syncSpaceCenter"
    clipPrefKey = "com.letterror.similarity.clip"
    
    def build(self):
        
        glyphEditor = self.getGlyphEditor()
        self.clip = getDefault(self.clipPrefKey, 100)
        self.previousCurrentGlyph = None
        self.container = glyphEditor.extensionContainer(
            identifier="com.roboFont.NeighboursDemo.foreground",
            location="background",
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
        self.leftClipLayer = self.container.appendLineSublayer()
        self.rightClipLayer = self.container.appendLineSublayer()

        
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
                    'width': 150,
                },
                {   'title': "◀︎",
                    'key':'leftMargin',
                    'editable':False,
                    'width': 50,
                },
                {   'title': "Left",
                    'key':'scoreLeft',
                    'editable':False,
                    'width': 100,
                },
                {   'title': "Right",
                    'key':'scoreRight',
                    'editable':False,
                    'width': 100,
                },
                {   'title': "▶︎",
                    'key':'rightMargin',
                    'editable':False,
                    'width': 50,
                },
                {   'title': "Cat",
                    'key':'unicodeCategory',
                    'editable':False,
                    'width': 50,
                },
                {   'title': "Range",
                    'key':'unicodeRange',
                    'editable':False,
                    'width': 150,
                },
        ]
        col1 = 100
        col2 = 260
        colWidth = (col2-col1)
        col3 = col2+colWidth
        col4 = col3+colWidth
        line1 = 5
        line2 = 30
        line3 = 55
        line4 = 80
        self.w = vanilla.Window((730, 500), "LTR Similarity", minSize=(200,100))
        self.w.l = vanilla.List((5,100,-5, -40),[], 
            columnDescriptions=glyphDescriptions, 
            selectionCallback=self.selectItemsCallback,
            doubleClickCallback = self.listDoubleClickCallback
            )
        self.w.cb1 = vanilla.CheckBox((col1, line1, 150, 20), "Above xHeight", value=1, callback=self.zoneCallback)
        self.w.cb2 = vanilla.CheckBox((col1, line2, 150, 20), "Baseline to xHeight", value=1, callback=self.zoneCallback)
        self.w.cb3 = vanilla.CheckBox((col1, line3, 150, 20), "Below baseline", value=1, callback=self.zoneCallback)
        self.w.cbuniCat = vanilla.CheckBox((col2, line1, -5, 20), "Unicode category", value=getDefault(self.unicodeCategoryPrefKey, 1), callback=self.update)
        self.w.cbuniRange = vanilla.CheckBox((col2, line2, -5, 20), "Unicode range", value=getDefault(self.unicodeRangePrefKey, 1), callback=self.update)

        self.w.threshold = vanilla.EditText((col4,line1,50,20), self.threshold, sizeStyle="small", callback=self.editThreshold)
        self.w.thresholdSlider = vanilla.Slider((col3, line1, colWidth-10, 20), minValue=0, maxValue=1, value=self.threshold, callback=self.sliderCallback, continuous=True, sizeStyle="small")
        self.w.thresholdCaption = vanilla.TextBox((col4+55,line1+2,100,20), "Threshold", sizeStyle="small")
 
        self.w.clipSlider = vanilla.Slider((col3, line2, colWidth-10, 20), minValue=50, maxValue=300, value=self.clip, tickMarkCount=11, stopOnTickMarks=True, callback=self.clipSliderCallback, continuous=False, sizeStyle="small")
        self.w.clipCaption = vanilla.TextBox((col4, line2, 120, 20), f"Clip: {self.clip}", sizeStyle="small")
 
        self.w.toSpaceCenter = vanilla.Button((10,-30,150,20), "To SpaceCenter", callback=self.toSpaceCenter)
        self.w.selectInFont = vanilla.Button((170,-30,150,20), "Select", callback=self.selectInFont)
        self.w.calcTime = vanilla.TextBox((-140, -30+5, -10, 20), "", sizeStyle="small")
        self.w.bind("close", self.destroy)
        self.w.open()
        self.update()

    def listDoubleClickCallback(self, sender):
        # after double clicking, can we see the previous currentglyph
        # selected in the list?
        self.previousCurrentGlyph = self.currentGlyph.name
        selectedItems = [self.w.l[s] for s in self.w.l.getSelection()]
        name = selectedItems[0].get('glyphName')
        OpenGlyphWindow(CurrentFont()[name])
    
    def clipSliderCallback(self, sender):
        self.clip = int(sender.get())
        self.w.clipCaption.set(f'Clip: {self.clip}')
        self.update()
        self._updateNeighbours(self.currentGlyph)
        
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

    def glyphEditorWillClose(self, info):
        try:
            self.w.close()
        except:
            pass
    
    def glyphDidChangeMetrics(self, info):
        self.currentGlyph = info['glyph']
        if self.currentGlyph is not None:
            self.update()
            self._updateNeighbours(self.currentGlyph)
        
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
        hasDrawnLeft = False
        hasDrawnRight = False
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
                hasDrawnLeft = True
            elif len(item.get('scoreRight')) > 0:
                pp = self.rightPathLayer.appendPathSublayer(
                    strokeColor=BLUE,                    
                    fillColor=None,
                    strokeWidth=1,
                    name="rightNeighbour")
                pp.setPath(glyphPath)
                pp.setPosition((-simGlyph.width + glyph.width, 0))
                hasDrawnRight = True
        if hasDrawnLeft:
            self.leftClipLayer = self.leftPathLayer.appendLineSublayer(
                startPoint=(self.clip, font.info.descender),
                endPoint=(self.clip, font.info.ascender),
                strokeColor=RED,
                fillColor=None,
                strokeWidth=1,
                strokeDash=(10,10),
                name="leftClip")
        if hasDrawnRight:
            self.rightClipLayer = self.rightPathLayer.appendLineSublayer(
                startPoint=(glyph.width-self.clip, font.info.descender),
                endPoint=(glyph.width-self.clip, font.info.ascender),
                strokeColor=BLUE,
                fillColor=None,
                strokeWidth=1,
                strokeDash=(10,10),
                name="rightClip")

    
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
        text = f"/{self.currentName}/space/space{'/'+'/'.join(leftNames)} \\n/{self.currentName}/space{'/'+'/'.join(rightNames)}"
        if self.currentGlyph is not None:
            #sc = CurrentSpaceCenter(self.currentGlyph.font)
            #if sc is None:
            OpenSpaceCenter(self.currentGlyph.font)
            sc = CurrentSpaceCenter(self.currentGlyph.font)
            sc.setRaw(text)
        
    def update(self, sender=None):
        start = time.time_ns()
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
            self.w.setTitle("LTR Similarity")
            return
        self.currentName = this.name
        self.w.setTitle(f'LTR Similarity: {self.currentName}')
        
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
            clip=self.clip
            )
        rankRight = this.getRepresentation(SimilarGlyphsKey,
            threshold=self.threshold,
            sameUnicodeClass=limitUnicodeCategory,
            sameUnicodeRange=limitUnicodeRange,
            zones=z,
            side="right",
            clip=self.clip
            )
     
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
                lm = this.leftMargin-font[name].leftMargin
                if lm == 0.0:
                    lm = ""
                else:
                    lm = f'{lm:3.1f}'
                items.append(dict(glyphName=name, 
                    scoreLeft=f"{k:3.5f}", 
                    scoreRight="", 
                    leftMargin = lm,
                    rightMargin = '',
                    unicodeCategory=cat,
                    unicodeRange=rng,
                    ))
        rk = list(rankRight.keys())
        rk = sorted(rk, key = lambda x : float('-inf') if math.isnan(x) else x)
        rk = [v for v in rk if v > self.threshold]
        rk.sort()
        rk.reverse()
        itemIndex = 0
        for k in rk[:self.showSimilar]:
            for name in rankRight[k]:
                cat = u2c(font[name].unicode)
                if cat is None:
                    cat = ''
                rng = u2r(font[name].unicode)
                if rng is None:
                    rng = ''
                rm = this.rightMargin-font[name].rightMargin
                if rm == 0.0:
                    rm = ""
                else:
                    rm = f'{rm:3.1f}'
                items.append(dict(glyphName=name, 
                    scoreRight=f"{k:3.5f}", 
                    scoreLeft="",
                    leftMargin = '',
                    rightMargin = rm,
                    unicodeCategory=cat,
                    unicodeRange=rng,
                    ))
        self.w.l.set(items)
        end = time.time_ns()
        duration = (end-start) / (10 ** 9)
        self.w.calcTime.set(f'update: {duration:3.3f} seconds')
        if self.previousCurrentGlyph is not None:
            sel = []
            for index, item in enumerate(self.w.l):
                if item['glyphName'] == self.previousCurrentGlyph:
                    sel.append(index)
            if sel:
                self.w.l.setSelection(sel)
            self.previousCurrentGlyph = None


registerGlyphEditorSubscriber(SimilarityUI)

