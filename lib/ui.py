import ezui

import time, math, random
from mojo.events import postEvent
from pprint import pprint
from mojo.subscriber import Subscriber, WindowController, registerSubscriberEvent, registerRoboFontSubscriber, registerGlyphEditorSubscriber, unregisterGlyphEditorSubscriber
from mojo.events import addObserver, removeObserver
from mojo.UI import CurrentSpaceCenter, OpenSpaceCenter, setDefault, getDefault, OpenGlyphWindow
from glyphNameFormatter.reader import u2r, u2c
from cosineSimilarity import cosineSimilarity, SimilarGlyphsKey
import fontTools.unicodedata

# fold out doxs:
# https://typesupply.github.io/ezui/containers.html#ezui.Pane


windowTitleTemplate = "LTR Similarity: {name}"

sidebarOpenSymbol = ezui.makeImage(symbolName="sidebar.left")
sidebarClosedSymbol = ezui.makeImage(symbolName="rectangle")

SIMILARITY_DATA_KEY = "LTRSimilarity_data"
DEBUG = True


RED = (1, 0, 0, 0.3)
BLUE = (.5, 0, 1, 0.3)
REDZone = (1, 0, 0, 0.05)
BLUEZone = (.5, 0, 1, 0.05)



class SimilarityWindowController(Subscriber, ezui.WindowController):

    thresholdPrefKey = "com.letterror.similarity.threshold"
    unicodeCategoryPrefKey = "com.letterror.similarity.unicodeCategory"
    unicodeScriptPrefKey = "com.letterror.similarity.unicodeScript"
    selectInterestingPrefKey = "com.letterror.similarity.selectInteresting"
    syncSpaceCenterPrefKey = "com.letterror.similarity.syncSpaceCenter"
    zonesPrefKey = "com.letterror.similarity.zones"
    clipPrefKey = "com.letterror.similarity.clip"

    def build(self):
        self.limitUnicodeCategory = int(getDefault(self.unicodeCategoryPrefKey, 1))
        self.limitUnicodeScript = int(getDefault(self.unicodeScriptPrefKey, 1))
        self.zonesSelection = getDefault(self.zonesPrefKey, (1, 1, 1))
        self.zones = []
        self.marginOutliers = getDefault(self.selectInterestingPrefKey, 1)
        self.threshold = float(getDefault(self.thresholdPrefKey, 1))
        self.clip = float(getDefault(self.clipPrefKey, 200))
        self.italicAngle = 0
        self.currentGlyph = None
        self.previousCurrentGlyphName = None
        self.showSimilar = 30
        self.interestingMarginThreshold = 5

        content = """
        = HorizontalStack

        * TwoColumnForm                     @settingsForm

        > !§ Similarity Parameters

        > : Threshold:
        > --X----------------------- [__]   @thresholdSlider
        > : Clip:
        > --X----------------------- [__]   @clipSlider
        > :

        > !§ Unicode

        > :
        > [X] Category                      @unicodeCategoryCheckbox
        > :
        > [X] Script                        @unicodeScriptCheckbox

        > !§ Zones

        > :
        > [X] Above X-Height                @aboveXHeightCheckbox
        > :
        > [X] Baseline to X-Height          @baselineToXHeightCheckbox
        > :
        > [X] Below Baseline                @belowBaselineCheckbox
        > :
        > [X] Select Margin Outliers (>5)   @marginOutliersCheckbox


        |-------------------------------|   @resultsTable
        |                               |
        |-------------------------------|

        =================================

        ({sidebar.left})                    @toggleSettingsButton
        !* 0.000 seconds                    @speedLabel
        (Select Glyphs)                     @selectGlyphsButton
        (To SpaceCenter)                    @toSpaceCenterButton
        """
        sliderWidth = 150
        textFieldWidth = 45
        confidenceCellDescription = dict(
            cellType="LevelIndicator",
            style="continuous",
            minValue=0,
            maxValue=100,
            warningValue=98,
            criticalValue=95,
        )
        descriptionData = dict(
            content=dict(
            ),

            settingsForm=dict(
                titleColumnWidth=65,
                itemColumnWidth=185,
                height="fit"
            ),
            thresholdSlider=dict(
                valueType="float:3",
                value=0.99,
                minValue=0.9,
                maxValue=1.0,
                sliderWidth=sliderWidth,
                textFieldWidth=textFieldWidth,
                continuous=False
            ),
            clipSlider=dict(
                valueType="integer",
                value=250,
                minValue=50,
                maxValue=800,
                sliderWidth=sliderWidth,
                textFieldWidth=textFieldWidth,
                tickMarks=11,
                stopOnTickMarks=True,
                continuous=False
            ),

            resultsTable=dict(
                selectionCallback=self.selectItemsCallback,
                doubleClickCallback=self.listDoubleClickCallback,
                allowsSorting=True,
                columnDescriptions = [
                    dict(
                        identifier="glyphName",
                        title="Name",
                        width=250
                    ),
                    dict(
                        identifier="leftMargin",
                        title="◀",
                        width=60
                    ),
                    dict(
                        identifier="confidenceLeft",
                        title="Score Left",
                        width=70,
                        cellDescription=dict(confidenceCellDescription)
                    ),
                    dict(
                        identifier="confidenceRight",
                        title="Score Right",
                        width=70,
                        cellDescription=dict(confidenceCellDescription)
                    ),
                    dict(
                        identifier="rightMargin",
                        title="▶︎",
                        width=60
                    ),
                    dict(
                        identifier="unicodeCategory",
                        title="U-Cat",
                        width=60
                    ),
                    dict(
                        identifier="unicodeScript",
                        title="U-Script",
                        width=60
                    )
                ]
            ),

            toggleSettingsButton=dict(
                gravity="leading"
            ),
            speedLabel=dict(
                gravity="center"
            ),
            selectGlyphsButton=dict(
            ),
            toSpaceCenterButton=dict(
            ),
        )
        self.w = ezui.EZWindow(
            content=content,
            descriptionData=descriptionData,
            controller=self,
            defaultButton="toSpaceCenterButton",
            title=windowTitleTemplate.format(name="<none>"),
            size=(1100, 600),
            minSize=(400, 200),
            activeItem="resultsTable",
        )
        self.w.getItem("unicodeCategoryCheckbox").set(self.limitUnicodeCategory)
        self.w.getItem("unicodeScriptCheckbox").set(self.limitUnicodeScript)
        self.w.getItem("aboveXHeightCheckbox").set(self.zonesSelection[0])
        self.w.getItem("baselineToXHeightCheckbox").set(self.zonesSelection[1])
        self.w.getItem("belowBaselineCheckbox").set(self.zonesSelection[2])
        self.w.getItem("marginOutliersCheckbox").set(self.marginOutliers)
        self.w.getItem("thresholdSlider").set(self.threshold)
        self.w.getItem("clipSlider").set(self.clip)
        self.w.bind("close", self.destroy)        
        self.table =  self.w.getItem("resultsTable")

    def selectItemsCallback(self, sender):
        #print("table selectItemsCallback", sender)
        #self.updateProfile()
        self.postSelectedItems()
        #self._updateNeighbours(self.currentGlyph)

    def listDoubleClickCallback(self, sender):
        # after double clicking, can we see the previous currentglyph
        # selected in the list?
        self.previousCurrentGlyphName = self.currentGlyph.name
        selectedItems = self.table.getSelectedItems()
        name = selectedItems[0].get('glyphName')
        OpenGlyphWindow(CurrentFont()[name])
        self.selectedPreviousGlyph()

    def roboFontDidSwitchCurrentGlyph(self, info=None):
        glyph = None
        if info is not None:
            glyph = info['glyph']
        if glyph is None:
            print("no current glyph. closing up")
            self.currentGlyph = None
            self.w.setTitle(f"LTR Similarity")
            self.table.set([])
            self.setZones()
            self.italicAngle = 0
        else:
            if self.currentGlyph != glyph:
                # new!
                self.currentGlyph = glyph
                self.italicAngle = glyph.font.info.italicAngle
                self.w.setTitle(f"LTR Similarity: {self.currentGlyph.name}")
                self.setZones()
                self.updateProfile()
            if self.marginOutliers:
                #print("setting margin outliers selection")
                self.selectGlyphsWithInterestingMargins()
        self.postSelectedItems()
        self.postZones()
    
    def started(self):
        #print("started")
        # start glypheditor subscriber when the window opens
        #self.roboFontDidSwitchCurrentGlyph()
        glyph = CurrentGlyph()
        if glyph is not None:
            self.roboFontDidSwitchCurrentGlyph(info=dict(glyph=glyph))
        registerGlyphEditorSubscriber(DrawSimilars)
        self.w.open()
    
    def destroy(self, something=None):
        #print("destroy")
        removeObserver(self, "currentGlyphChanged")
        setDefault(self.unicodeCategoryPrefKey, self.limitUnicodeCategory)
        setDefault(self.unicodeScriptPrefKey, self.limitUnicodeScript)
        setDefault(self.thresholdPrefKey, self.threshold)
        setDefault(self.clipPrefKey, self.clip)
        setDefault(self.zonesPrefKey, [int(v) for v in self.zonesSelection])
        setDefault(self.selectInterestingPrefKey, self.marginOutliers)
        unregisterGlyphEditorSubscriber(DrawSimilars)

    def setZones(self):
        aboveX = self.w.getItem('aboveXHeightCheckbox').get()
        baseToX = self.w.getItem('baselineToXHeightCheckbox').get()
        belowBase = self.w.getItem('belowBaselineCheckbox').get()
        zones = None
        if self.currentGlyph is not None:
            zones = []
            font = self.currentGlyph.font
            if aboveX:
                zones.append((font.info.xHeight, font.info.unitsPerEm+font.info.descender))
            if baseToX:
                zones.append((0, font.info.xHeight))
            if belowBase:
                zones.append((font.info.descender, 0))
        self.zonesSelection = [aboveX, baseToX, belowBase]
        self.zones = zones
        
    def settingsFormCallback(self, sender):
        itemValues = sender.getItemValues()
        self.limitUnicodeCategory = int(itemValues.get('unicodeCategoryCheckbox', 0))
        self.limitUnicodeScript = int(itemValues.get('unicodeScriptCheckbox', 0))
        self.marginOutliers = itemValues.get("marginOutliersCheckbox", 1)
        self.clip = float(itemValues.get('clipSlider'))
        self.threshold = float(itemValues.get('thresholdSlider'))
        self.setZones()
        self.updateProfile()
        self.postZones()

    def toggleSettingsButtonCallback(self, sender):
        # XXX toggle the pane when Splits is deployed
        sender.setImage(imageObject=sidebarClosedSymbol)

    def selectGlyphsButtonCallback(self, sender):
        leftNames, rightNames = self.getSelectedGlyphs()
        allNames = set.union(set(leftNames), set(rightNames))
        font = CurrentFont()
        font.selection = allNames

    def getSelectedGlyphs(self):
        s = self.table.getSelectedItems()
        leftNames = []
        rightNames = []
        if not s:
            for item in self.table:
                if item['scoreLeft']!="":
                    leftNames.append(item['glyphName'])
                else:
                    rightNames.append(item['glyphName'])
        else:
            for item in s:
                if item['scoreLeft']!="":
                    leftNames.append(item['glyphName'])
                else:
                    rightNames.append(item['glyphName'])
        return leftNames, rightNames

    def toSpaceCenterButtonCallback(self, sender):
        # put the selected names in a spacecenter
        leftNames, rightNames = self.getSelectedGlyphs()
        if self.currentGlyph is not None:
            name = self.currentGlyph.name
            text = f"/{name}/space/space{'/'+'/'.join(leftNames)} \\n/{name}/space{'/'+'/'.join(rightNames)}"
            OpenSpaceCenter(self.currentGlyph.font)
            sc = CurrentSpaceCenter(self.currentGlyph.font)
            sc.setRaw(text)

    def updateProfile(self, sender=None):
        start = time.time_ns()
        this = self.currentGlyph
        if this is None:
            # empty list
            print("no current glyph")
            #print("clear the list")
            self.currentName = None
            self.w.setTitle("LTR Similarity")
            return
        leftMarginInteresting = []
        rightMarginInteresting = []
        font = self.currentGlyph.font
        items = []
        rankLeft = this.getRepresentation(SimilarGlyphsKey,
            threshold=self.threshold, 
            sameUnicodeClass=self.limitUnicodeCategory,
            sameUnicodeScript=self.limitUnicodeScript,
            zones=tuple(self.zones),
            side="left",
            clip=self.clip
            )
        rankRight = this.getRepresentation(SimilarGlyphsKey,
            threshold=self.threshold,
            sameUnicodeClass=self.limitUnicodeCategory,
            sameUnicodeScript=self.limitUnicodeScript,
            zones=tuple(self.zones),
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
                leftData = dict(glyphName=name, 
                    scoreLeft=f"{k:3.5f}", 
                    scoreRight="", 
                    scoreLeftValue = k,
                    scoreRightValue = 0,
                    leftMargin = lmString,
                    leftMarginValue = lm,
                    rightMarginValue = None,
                    rightMargin = '',
                    unicodeCategory=cat,
                    unicodeScript = sc, 
                    confidenceLeft = int(k*100),
                    confidenceRight = 0,
                    side="left"
                    )
                items.append(leftData)
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
                rightData = dict(glyphName=name, 
                    scoreRight=f"{k:3.5f}", 
                    scoreLeft = "",
                    scoreLeftValue = 0,
                    scoreRightValue = k,
                    leftMargin = '',
                    leftMarginValue = None,
                    rightMargin = rmString,
                    rightMarginValue = rm,
                    unicodeCategory=cat,
                    unicodeScript = sc, 
                    confidenceRight = int(k*100),
                    confidenceLeft = 0,
                    side="right"
                    )
                items.append(rightData)
        # setting the items
        self.table.set(items)
        end = time.time_ns()
        duration = (end-start) / (10 ** 9)
        self.w.getItem("speedLabel").set(f'update: {duration:3.3f} seconds')
    
    def selectGlyphsWithInterestingMargins(self):        
        selectedItems = []
        selectThese = []
        for index, item in enumerate(self.table.get()):
            if item['leftMarginValue'] is not None:
                if abs(item['leftMarginValue']) > self.interestingMarginThreshold:
                    selectThese.append(index)
                    selectedItems.append(item)
            if item['rightMarginValue'] is not None:
                if abs(item['rightMarginValue']) > self.interestingMarginThreshold:
                    selectThese.append(index)
                    selectedItems.append(item)
        self.table.setSelectedIndexes(selectThese)
            
    def selectedPreviousGlyph(self):
        # what does this do?
        if self.previousCurrentGlyphName is not None:
            selectThese = []
            for index, item in enumerate(self.table.getItems()):
                if item['glyphName'] == self.previousCurrentGlyphName:
                    selectThese.append(index)
            if selectThese:
                self.table.setSelectedIndexes(selectThese)
            self.previousCurrentGlyphName = None
        
    def postSelectedItems(self):        
        postEvent(f"{SIMILARITY_DATA_KEY}.ValueChanged", value=self.table.getSelectedItems())

    def postZones(self):
        if self.currentGlyph is not None:
            width = self.currentGlyph.width
        else:
            width = 0
        data = {'zones':self.zones,
            'clip':self.clip,
            'angle':self.italicAngle,
            'width':width,
            'glyph': self.currentGlyph
            }
        postEvent(f"{SIMILARITY_DATA_KEY}.ZonesChanged", value=data)


class DrawSimilars(Subscriber):
    def build(self):
        self.previewStrokeWidth = 1.4
        self.data = []
        self.zones = []
        self.zoneLayerNames = []
        self.clip = 0
        self.glyphEditor = self.getGlyphEditor()
        #print('build DrawSimilars', self.glyphEditor)
        self.container = self.glyphEditor.extensionContainer(
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
        #self.leftClipLayer = self.container.appendLineSublayer()
        #self.rightClipLayer = self.container.appendLineSublayer()

    def started(self):
        pass
        #print('started DrawSimilars')

    def destroy(self, sender=None):
        #print('destroy DrawSimilars')
        self.leftZonesLayer.clearSublayers()
        self.rightZonesLayer.clearSublayers()
        self.leftPathLayer.clearSublayers()
        self.rightPathLayer.clearSublayers()

    def glyphEditorWillClose(self, info):
        pass
        #print('glyphEditorWillClose DrawSimilars')

    def glyphEditorDidSetGlyph(self, info):
        #print("xx glyphEditorDidSetGlyph")
        self.data = []
        #self.currentGlyph = info['glyph']
        #if self.currentGlyph is not None:
        #    self.zoneCallback()
        #    self.update()
        #    self._updateNeighbours(self.currentGlyph)

    def similiarityZonesChanged(self, info):
        data = info["lowLevelEvents"][-1]["value"]
        self.leftZonesLayer.clearSublayers()
        self.rightZonesLayer.clearSublayers()

        glyph = data.get("glyph")
        if glyph is None:
            print('no glyph')
            return
        self.zones = data['zones']
        self.clip = data['clip']
        self.italicAngle = data.get('angle')
        self.width = data.get("width", 0)
        if self.italicAngle is None:
            self.italicAngle = 0

        self.zoneLayerNames = []
        if self.zones is None: return
        for mn, mx in self.zones:
            zoneName = f'leftZone_{mn}_{mx}'
            self.zoneLayerNames.append(zoneName)
            leftZoneLayer = self.leftZonesLayer.appendPathSublayer(
                fillColor=REDZone,
                name=zoneName
                )
            zonePen = leftZoneLayer.getPen()
            mnOff = math.tan(math.radians(-self.italicAngle)) * mn
            mxOff = math.tan(math.radians(-self.italicAngle)) * mx
            zonePen.moveTo((0+mnOff, mn))
            zonePen.lineTo((self.clip+mnOff, mn))
            zonePen.lineTo((self.clip+mxOff, mx))
            zonePen.lineTo((0+mxOff, mx))
            zonePen.closePath()
            leftZoneLayer.setVisible(True)

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
            rightZoneLayer.setPosition((self.width, 0))
            rightZoneLayer.setVisible(True)

    def similiarityDataChanged(self, info):
        self.data = info["lowLevelEvents"][-1]["value"]
        self.leftPathLayer.clearSublayers()
        self.rightPathLayer.clearSublayers()
        glyph = self.glyphEditor.getGlyph()
        if glyph is None:
            #print("huh, no glyph?")
            return
            
        font = glyph.font
        
        for item in self.data:
            simGlyph = font[item['glyphName']]
            glyphPath = simGlyph.getRepresentation("merz.CGPath")
            #print(item)
            if item['side'] == "left":
                if item.get('scoreLeftValue')>0:
                    pp = self.leftPathLayer.appendPathSublayer(
                        strokeColor=RED,                    
                        fillColor=None,
                        strokeWidth=self.previewStrokeWidth,
                        name="leftNeighbour")
                    pp.setPath(glyphPath)
                    hasDrawnLeft = True
            elif item['side'] == "right":
                if item.get('scoreRightValue')>0:
                    pp = self.rightPathLayer.appendPathSublayer(
                        strokeColor=BLUE,                    
                        fillColor=None,
                        strokeWidth=self.previewStrokeWidth,
                        name="rightNeighbour")
                    pp.setPath(glyphPath)
                    pp.setPosition((-simGlyph.width + glyph.width, 0))
                    hasDrawnRight = True

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
        

registerRoboFontSubscriber(SimilarityWindowController)

if __name__ == "__main__":
    #SimilarityWindowController()
    #print("hey")



    registerSubscriberEvent(
        subscriberEventName=f"{SIMILARITY_DATA_KEY}.ValueChanged",
        methodName="similiarityDataChanged",
        lowLevelEventNames=[f"{SIMILARITY_DATA_KEY}.ValueChanged"],
        dispatcher="roboFont",
        documentation="Send new similarity data",
        delay=0.01,
        debug=DEBUG
    )
    registerSubscriberEvent(
        subscriberEventName=f"{SIMILARITY_DATA_KEY}.ZonesChanged",
        methodName="similiarityZonesChanged",
        lowLevelEventNames=[f"{SIMILARITY_DATA_KEY}.ZonesChanged"],
        dispatcher="roboFont",
        documentation="Send new zones data",
        delay=0.01,
        debug=DEBUG
    )

