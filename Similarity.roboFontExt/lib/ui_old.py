import importlib
import cosineSimilarity
importlib.reload(cosineSimilarity)

import vanilla
import math, time, datetime
import AppKit
import fontTools.unicodedata

from cosineSimilarity import cosineSimilarity, SimilarGlyphsKey

from mojo.UI import CurrentSpaceCenter, OpenSpaceCenter, setDefault, getDefault, OpenGlyphWindow
from mojo.subscriber import Subscriber, WindowController, registerGlyphEditorSubscriber
from glyphNameFormatter.reader import u2r, u2c

RED = (1, 0, 0, 0.3)
BLUE = (.5, 0, 1, 0.3)
REDZone = (1, 0, 0, 0.05)
BLUEZone = (.5, 0, 1, 0.05)

roboFontItalicSlantLibKey = "com.typemytype.robofont.italicSlantOffset"

class RightAlignEditTextList2Cell(vanilla.EditTextList2Cell):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.editText.getNSTextField().setAlignment_(AppKit.NSTextAlignmentRight)

def findKernGroups(glyph):
    left = {}
    right = {}
    font = glyph.font
    for groupName, members in font.groups.items():
        if "public.kern1" in groupName:
            if g in members:
                for m in members:
                    if not m in left:
                        left[m] = groupName
        if "public.kern2" in groupName:
            if g in members:
                for m in members:
                    if not m in right:
                        right[m] = groupName
    return left, right

class SimilarityUI(Subscriber, WindowController):
    # simple window to show similarity ranking for the current glyph
    
    thresholdPrefKey = "com.letterror.similarity.threshold"
    unicodeCategoryPrefKey = "com.letterror.similarity.unicodeCategory"
    unicodeScriptPrefKey = "com.letterror.similarity.unicodeScript"
    selectInterestingPrefKey = "com.letterror.similarity.selectInteresting"
    syncSpaceCenterPrefKey = "com.letterror.similarity.syncSpaceCenter"
    zonesPrefKey = "com.letterror.similarity.zones"
    clipPrefKey = "com.letterror.similarity.clip"
    
    def build(self):
        
        glyphEditor = self.getGlyphEditor()
        self.clip = getDefault(self.clipPrefKey, 200)
        self.interestingMarginThreshold = 5
        self.previousCurrentGlyph = None
        self.previewStrokeWidth = 1.4
        self.container = glyphEditor.extensionContainer(
            identifier="com.lettError.similarity.foreground",
            location="background",
            clear=True)
        self.leftZonesLayer = self.container.appendPathSublayer(
            strokeColor=None,
            fillColor=REDZone,
            name="leftZones")
        self.leftPathLayer = self.container.appendPathSublayer(
            strokeColor=RED,
            fillColor=None,
            strokeWidth=2,
            name="leftNeighbour")
        self.rightZonesLayer = self.container.appendPathSublayer(
            strokeColor=None,
            fillColor=BLUEZone,
            name="rightZones")
        self.rightPathLayer = self.container.appendPathSublayer(
            strokeColor=BLUE,
            fillColor=None,
            strokeWidth=2,
            name="rightNeighbour")
        self.leftClipLayer = self.container.appendLineSublayer()
        self.rightClipLayer = self.container.appendLineSublayer()

        
        self.zones = None
        self.zoneLayerNames = []
        self.showSimilar = 10
        self.threshold = getDefault(self.thresholdPrefKey, 0.9)
        zonePrefs = getDefault(self.zonesPrefKey, (1, 1, 1))
        self.currentName = None
        self.currentGlyph = None
        glyphDescriptions = [
                {   'title': "Name",
                    'key':'glyphName',
                    'editable':False,
                    'width': 250,
                },
                {   'title': "◀︎",
                    'key':'leftMargin',
                    'editable':False,
                    'width': 50,
                },
                {"title": "Score Left",
                    'key': 'confidenceLeft',
                    'width': 70,
                     "cell": vanilla.LevelIndicatorListCell(style="continuous",
                         minValue=0,
                         maxValue=100,
                         warningValue=95,
                         criticalValue=75,
                         )
                 },
                {"title": "Score Right",
                    'key': 'confidenceRight',
                    'width': 70,
                     "cell": vanilla.LevelIndicatorListCell(style="continuous",
                         minValue=0,
                         maxValue=100,
                         warningValue=95,
                         criticalValue=75,
                         )
                 },
                {   'title': "▶︎",
                    'key':'rightMargin',
                    'editable':False,
                    'width': 50,
                },
                {   'title': "U-Cat",
                    'key':'unicodeCategory',
                    'editable':False,
                    'width': 50,
                },
                {   'title': "U-Script",
                    'key':'unicodeScript',
                    'editable':False,
                    'width': 150,
                },
        ]
        col1 = 20
        col2 = 180
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
        self.w.cb1 = vanilla.CheckBox((col4, line1, 150, 20), "Above xHeight", value=zonePrefs[0], callback=self.zoneCallback)
        self.w.cb2 = vanilla.CheckBox((col4, line2, 150, 20), "Baseline to xHeight", value=zonePrefs[1], callback=self.zoneCallback)
        self.w.cb3 = vanilla.CheckBox((col4, line3, 150, 20), "Below baseline", value=zonePrefs[2], callback=self.zoneCallback)
        self.w.cbuniCat = vanilla.CheckBox((col3, line1, -5, 20), "Unicode category", value=getDefault(self.unicodeCategoryPrefKey, 1), callback=self.update)
        self.w.cbuniScript = vanilla.CheckBox((col3, line2, -5, 20), "Unicode script", value=getDefault(self.unicodeScriptPrefKey, 1), callback=self.update)
        self.w.cbSelectInteresting = vanilla.CheckBox((col1, line3, -5, 20), f"Select margin outliers (>{self.interestingMarginThreshold})", value=getDefault(self.selectInterestingPrefKey, 0), callback=self.update)
        self.w.threshold = vanilla.EditText((col2,line1,50,20), self.threshold, sizeStyle="small", callback=self.editThreshold)
        self.w.thresholdSlider = vanilla.Slider((col1, line1, colWidth-10, 20), minValue=0, maxValue=1, value=self.threshold, callback=self.sliderCallback, continuous=True, sizeStyle="small")
        self.w.thresholdCaption = vanilla.TextBox((col2+55,line1+2,100,20), "Threshold", sizeStyle="small")
 
        self.w.clipSlider = vanilla.Slider((col1, line2, colWidth-10, 20), minValue=50, maxValue=300, value=self.clip, tickMarkCount=11, stopOnTickMarks=True, callback=self.clipSliderCallback, continuous=False, sizeStyle="small")
        self.w.clipCaption = vanilla.TextBox((col2, line2, 120, 20), f"Clip: {self.clip}", sizeStyle="small")
 
        self.w.toSpaceCenter = vanilla.Button((10,-30,150,20), "To SpaceCenter", callback=self.toSpaceCenter)
        self.w.selectInFont = vanilla.Button((170,-30,150,20), "Select", callback=self.selectInFont)
        self.w.calcTime = vanilla.TextBox((-140, -30+5, -10, 20), "", sizeStyle="small")
        self.w.bind("close", self.destroy)
        self.w.setDefaultButton(self.w.toSpaceCenter)
        self.w.open()
        self.zoneCallback()

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
        self.zoneCallback()
        self._updateNeighbours(self.currentGlyph)
        
    def sliderCallback(self, sender):
        self.threshold = float(sender.get())
        self.update()
        self._updateNeighbours(self.currentGlyph)
        self.w.threshold.set(self.threshold)
    
    def selectItemsCallback(self, sender):
        self._updateNeighbours(self.currentGlyph)
        
    def zoneCallback(self, sender=None):
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

        self.leftZonesLayer.clearSublayers()
        self.rightZonesLayer.clearSublayers()
        
        self.zoneLayerNames = []
        if self.zones is not None:
            a = font.info.italicAngle
            if a is None:
                a = 0
            for mn, mx in self.zones:
                zoneName = f'leftZone_{mn}_{mx}'
                self.zoneLayerNames.append(zoneName)
                leftZoneLayer = self.leftZonesLayer.appendPathSublayer(
                    fillColor=REDZone,
                    name=zoneName
                    )
                zonePen = leftZoneLayer.getPen()
                mnOff = math.tan(math.radians(-a)) * mn
                mxOff = math.tan(math.radians(-a)) * mx
                zonePen.moveTo((0+mnOff, mn))
                zonePen.lineTo((self.clip+mnOff, mn))
                zonePen.lineTo((self.clip+mxOff, mx))
                zonePen.lineTo((0+mxOff, mx))
                zonePen.closePath()
                leftZoneLayer.setVisible(False)

                zoneName = f'rightZone_{mn}_{mx}'
                self.zoneLayerNames.append(zoneName)
                rightZoneLayer = self.rightZonesLayer.appendPathSublayer(
                    fillColor=BLUEZone,
                    name=zoneName
                    )
                zonePen = rightZoneLayer.getPen()
                zonePen.moveTo((0-self.clip+mnOff, mn))
                zonePen.lineTo((+mnOff, mn))
                zonePen.lineTo((+mxOff, mx))
                zonePen.lineTo((0-self.clip+mxOff, mx))
                zonePen.closePath()
                if self.currentGlyph is not None:
                    rightZoneLayer.setPosition((self.currentGlyph.width, 0))
                rightZoneLayer.setVisible(False)

        self.update()
        
    def started(self):
        self.w.open()

    def destroy(self, sender=None):
        setDefault(self.unicodeCategoryPrefKey, self.w.cbuniCat.get())
        setDefault(self.unicodeScriptPrefKey, self.w.cbuniScript.get())
        setDefault(self.selectInterestingPrefKey, self.w.cbSelectInteresting.get())        
        setDefault(self.thresholdPrefKey, self.threshold)
        setDefault(self.clipPrefKey, self.clip)
        zonePrefs = (self.w.cb1.get(), self.w.cb2.get(), self.w.cb3.get())
        setDefault(self.zonesPrefKey, zonePrefs)
        self.container.clearSublayers()

    def glyphEditorWillClose(self, info):
        try:
            self.w.close()
        except:
            pass
    
    def glyphEditorDidSetGlyph(self, info):
        self.currentGlyph = info['glyph']
        if self.currentGlyph is not None:
            self.zoneCallback()
            self.update()
            self._updateNeighbours(self.currentGlyph)
        
    def _updateNeighbours(self, glyph):
        if glyph is None: return
        font = glyph.font
        #italicSlantOffset = font.lib.get(roboFontItalicSlantLibKey, 0)
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
                    strokeWidth=self.previewStrokeWidth,
                    name="leftNeighbour")
                pp.setPath(glyphPath)
                hasDrawnLeft = True
            elif len(item.get('scoreRight')) > 0:
                pp = self.rightPathLayer.appendPathSublayer(
                    strokeColor=BLUE,                    
                    fillColor=None,
                    strokeWidth=self.previewStrokeWidth,
                    name="rightNeighbour")
                pp.setPath(glyphPath)
                pp.setPosition((-simGlyph.width + glyph.width, 0))
                hasDrawnRight = True
        for name in self.zoneLayerNames:
            if 'left' in name:
                l = self.leftZonesLayer.getSublayer(name)
                if l is not None:
                    l.setVisible(hasDrawnLeft)
            if 'right' in name:
                l = self.rightZonesLayer.getSublayer(name)
                if l is not None:
                    l.setVisible(hasDrawnRight)
                if self.currentGlyph is not None:
                    l.setPosition((self.currentGlyph.width, 0))

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
            self.w.l.set([])
            return
        leftMarginInteresting = []
        rightMarginInteresting = []
        limitUnicodeCategory = self.w.cbuniCat.get()
        limitUnicodeScript = self.w.cbuniScript.get()
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
            sameUnicodeScript=limitUnicodeScript,
            zones=z,
            side="left",
            clip=self.clip
            )
        rankRight = this.getRepresentation(SimilarGlyphsKey,
            threshold=self.threshold,
            sameUnicodeClass=limitUnicodeCategory,
            sameUnicodeScript=limitUnicodeScript,
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
                    lmString = ""
                else:
                    lmString = f'{lm:3.1f}'
                if font[name].unicode is not None:
                    sc = fontTools.unicodedata.script(font[name].unicode)
                    sc = fontTools.unicodedata.script_name(sc)
                else:
                    sc = ""
                items.append(dict(glyphName=name, 
                    scoreLeft=f"{k:3.5f}", 
                    scoreRight="", 
                    leftMargin = lmString,
                    leftMarginValue = lm,
                    rightMarginValue = None,
                    rightMargin = '',
                    unicodeCategory=cat,
                    unicodeScript = sc, 
                    confidenceLeft=k*100,
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
                    rmString = ""
                else:
                    rmString = f'{rm:3.1f}'
                if font[name].unicode is not None:
                    sc = fontTools.unicodedata.script(font[name].unicode)
                    sc = fontTools.unicodedata.script_name(sc)
                else:
                    sc = ""
                items.append(dict(glyphName=name, 
                    scoreRight=f"{k:3.5f}", 
                    scoreLeft="",
                    leftMargin = '',
                    leftMarginValue = None,
                    rightMargin = rmString,
                    rightMarginValue = rm,
                    unicodeCategory=cat,
                    unicodeScript = sc, 
                    confidenceRight=k*100,
                    ))
        self.w.l.set(items)
        if self.w.cbSelectInteresting.get():
            selectThese = []
            for index, item in enumerate(self.w.l):
                if item['leftMarginValue'] is not None:
                    if abs(item['leftMarginValue']) > self.interestingMarginThreshold:
                        selectThese.append(index)
                if item['rightMarginValue'] is not None:
                    if abs(item['rightMarginValue']) > self.interestingMarginThreshold:
                        selectThese.append(index)
            self.w.l.setSelection(selectThese)
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
print("hey")

