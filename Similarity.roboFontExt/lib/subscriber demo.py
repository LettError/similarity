import ezui
from mojo.subscriber import (
    Subscriber,
    registerSubscriberEvent,
    registerGlyphEditorSubscriber,
    unregisterGlyphEditorSubscriber
)
from mojo.events import postEvent

DEBUG = True
DEFAULT_KEY = "SubscriberDemoForErik"
DEFAULT_FACTOR = 0.5

class DemoWindowController(ezui.WindowController):

    factor = DEFAULT_FACTOR
    threshold = 8

    def build(self):
        content = """
        * HorizontalStack
          > --X-- @valueSlider
          > Test. @valueTextBox
        (Add as Masters) @addAsMastersButton
        """
        descriptionData = dict(
            valueSlider=dict(
                minValue=0.1,
                value=self.factor,
                maxValue=2,
                # stopOnTickMarks=False,
                # tickMarks=6,
                width=150
            ),
            valueTextBox=dict(
                width=40,
                text=f"{self.factor:3.3f}"
            ),
            addAsMastersButton=dict(
                width="fill"
            )
        )
        self.w = ezui.EZPanel(
            content=content,
            descriptionData=descriptionData,
            controller=self
        )

    def started(self):
        registerGlyphEditorSubscriber(DemoSubscriber)
        self.w.open()

    def destroy(self):
        unregisterGlyphEditorSubscriber(DemoSubscriber)

    def windowWillClose(self, sender):
        self.destroy()

    def valueSliderCallback(self, sender):
        value = sender.get()
        textBox = self.w.getItem("valueTextBox")
        textBox.set(f"{value:3.3f}")
        postEvent(f"{DEFAULT_KEY}.ValueChanged", value=value)

    def addAsMastersButtonCallback(self, sender):
        postEvent(f"{DEFAULT_KEY}.SetAsMasters")


class DemoSubscriber(Subscriber):

    debug = DEBUG
    strokeWidth = 10
    strokeWidthScaleFactor = DEFAULT_FACTOR
    strokeColors = [
        (1, 0, 0, 0.5),
        (0, 1, 0, 0.5)
    ]

    def build(self):
        glyphEditor = self.getGlyphEditor()
        container = glyphEditor.extensionContainer(
            identifier=DEFAULT_KEY,
            location="background",
            clear=True
        )
        self.pathLayer = container.appendPathSublayer(
            fillColor=None,
            visible=True
        )
        self.updatePathLayer()

    def destroy(self):
        self.pathLayer.setPath(None)

    # Layers

    def updatePathLayer(self):
        glyphEditor = self.getGlyphEditor()
        glyph = glyphEditor.getGlyph()
        with self.pathLayer.propertyGroup():
            if glyph is None:
                self.pathLayer.setPath(None)
            else:
                self.pathLayer.setPath(glyph.getRepresentation("merz.CGPath"))
                self.pathLayer.setStrokeWidth(self.strokeWidth * self.strokeWidthScaleFactor)
                self.pathLayer.setStrokeColor(self.strokeColors[0])

    # Events

    def glyphEditorGlyphDidChangeOutline(self, info):
        self.process(info)

    def glyphEditorDidSetGlyph(self, info):
        self.process(info)

    def paletteValueDidChange(self, info):
        self.strokeWidthScaleFactor = info["lowLevelEvents"][-1]["value"]
        self.process(info)

    def paletteSetAsMasters(self, info):
        self.strokeColors.reverse()
        self.process(info)

    # Processing

    def process(self, info):
        self.updatePathLayer()


if __name__ == '__main__':
    registerSubscriberEvent(
        subscriberEventName=f"{DEFAULT_KEY}.ValueChanged",
        methodName="paletteValueDidChange",
        lowLevelEventNames=[f"{DEFAULT_KEY}.ValueChanged"],
        dispatcher="roboFont",
        documentation="Send when the tool palette did change parameters.",
        delay=0.01,
        debug=DEBUG
    )
    registerSubscriberEvent(
        subscriberEventName=f"{DEFAULT_KEY}.SetAsMasters",
        methodName="paletteSetAsMasters",
        lowLevelEventNames=[f"{DEFAULT_KEY}.SetAsMasters"],
        dispatcher="roboFont",
        documentation="Send when we want the masters written to the layers.",
        delay=0,
        debug=DEBUG
    )
    DemoWindowController()
