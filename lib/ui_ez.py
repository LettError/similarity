import ezui

import time, math, random
from pprint import pprint
from mojo.subscriber import Subscriber, WindowController, registerRoboFontSubscriber
from mojo.events import addObserver, removeObserver
from mojo.UI import CurrentSpaceCenter, OpenSpaceCenter, setDefault, getDefault, OpenGlyphWindow
from glyphNameFormatter.reader import u2r, u2c
from cosineSimilarity import cosineSimilarity, SimilarGlyphsKey
import fontTools.unicodedata


windowTitleTemplate = "LTR Similarity: {name}"

sidebarOpenSymbol = ezui.makeImage(symbolName="sidebar.left")
sidebarClosedSymbol = ezui.makeImage(symbolName="rectangle")



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
        self.currentGlyph = None
        self.showSimilar = 30
        self.interestingMarginThreshold = 5
        self.previousCurrentGlyph = None

        content = """
        = HorizontalStack

        * TwoColumnForm                     @settingsForm

        > !§ Parameters

        > : Threshold:
        > --X----------------------- [__]   @thresholdSlider
        > : Clip:
        > --X----------------------- [__]   @clipSlider
        > :
        > [X] Select Margin Outliers (>5)   @marginOutliersCheckbox

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
            warningValue=95,
            criticalValue=75,
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
                value=0.5,
                minValue=0,
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
                columnDescriptions = [
                    dict(
                        identifier="glyphName",
                        title="Name",
                        width=250
                    ),
                    dict(
                        identifier="leftMargin",
                        title="◀",
                        width=50
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
                        width=50
                    ),
                    dict(
                        identifier="unicodeCategory",
                        title="U-Cat",
                        width=50
                    ),
                    dict(
                        identifier="unicodeScript",
                        title="U-Script",
                        width=50
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

    def roboFontDidSwitchCurrentGlyph(self, info):
        textBox = self.w.getItem("glyphNameTextBox")
        item = info['glyph']
        if item is None:
            self.currentGlyph = None
            self.w.setTitle(f"LTR Similarity")
            self.table.clear()
            self.setZones()
        else:
            self.currentGlyph = info['glyph']
            self.glyphName = self.currentGlyph.name
            self.w.setTitle(f"LTR Similarity: {self.glyphName}")
            self.setZones()
            self.updateProfile()

    def started(self):
        #print("started")
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
            #sc = CurrentSpaceCenter(self.currentGlyph.font)
            #if sc is None:
            OpenSpaceCenter(self.currentGlyph.font)
            sc = CurrentSpaceCenter(self.currentGlyph.font)
            sc.setRaw(text)

    
    def updateProfile(self, sender=None):
        
        testDict = dict(
                glyphName="test",
                leftMargin="test",
                leftMarginValue=0,
                rightMargin="test",
                rightMarginValue=0,
                scoreLeft="",
                scoreRight="",
                confidenceLeft=random.randint(0, 100),
                confidenceRight=random.randint(0, 100),
                unicodeCategory="test",
                unicodeScript="test",
            )
        
        start = time.time_ns()
        this = self.currentGlyph
        if this is None:
            # empty list
            print("no current glyph")
            print("clear the list")
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
                    leftMargin = lmString,
                    leftMarginValue = lm,
                    rightMarginValue = None,
                    rightMargin = '',
                    unicodeCategory=cat,
                    unicodeScript = sc, 
                    confidenceLeft = int(k*100),
                    confidenceRight = 0
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
                    leftMargin = '',
                    leftMarginValue = None,
                    rightMargin = rmString,
                    rightMarginValue = rm,
                    unicodeCategory=cat,
                    unicodeScript = sc, 
                    confidenceRight = int(k*100),
                    confidenceLeft = 0                   
                    )
                items.append(rightData)
        # setting the items
        self.table.set(items)
        if self.marginOutliers:
            selectThese = []
            for index, item in enumerate(self.table.get()):
                if item['leftMarginValue'] is not None:
                    if abs(item['leftMarginValue']) > self.interestingMarginThreshold:
                        selectThese.append(index)
                if item['rightMarginValue'] is not None:
                    if abs(item['rightMarginValue']) > self.interestingMarginThreshold:
                        selectThese.append(index)
            self.table.setSelectedIndexes(selectThese)
        end = time.time_ns()
        duration = (end-start) / (10 ** 9)
        self.w.getItem("speedLabel").set(f'update: {duration:3.3f} seconds')
        # what does this do?
        if self.previousCurrentGlyph is not None:
            selectThese = []
            for index, item in enumerate(self.table.getItems()):
                if item['glyphName'] == self.previousCurrentGlyph:
                    selectThese.append(index)
            if selectThese:
                self.table.setSelectedIndexes(selectThese)
            self.previousCurrentGlyph = None

#SimilarityWindowController()
print("hey")

registerRoboFontSubscriber(SimilarityWindowController)