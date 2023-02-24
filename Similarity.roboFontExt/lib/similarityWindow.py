import ezui

windowTitleTemplate = "LTR Similarity: {name}"

sidebarOpenSymbol = ezui.makeImage(symbolName="sidebar.left")
sidebarClosedSymbol = ezui.makeImage(symbolName="rectangle")

class SimilarityWindowController(ezui.WindowController):

    def build(self):
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
            size=(915, 600),
            minSize=(400, 200),
        )

    def started(self):
        self.w.open()

    def settingsFormCallback(self, sender):
        itemValues = sender.getItemValues()

    def toggleSettingsButtonCallback(self, sender):
        # XXX toggle the pane when Splits is deployed
        sender.setImage(imageObject=sidebarClosedSymbol)

    def selectGlyphsButtonCallback(self, sender):
        pass

    def toSpaceCenterButtonCallback(self, sender):
        pass

#import objc
#objc.setVerbose(True)

#from vanilla.test.testTools import executeVanillaTest
#executeVanillaTest(SimilarityWindowController)