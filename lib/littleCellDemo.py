from lib.cells.smallGlyphPreviewCell import RFSmallGlyphPreviewCell
import vanilla

class Demo:
    
    def __init__(self):
        
        self.font = CurrentFont().asDefcon()
        
        cell = RFSmallGlyphPreviewCell.alloc().init()
        cell.setFont_(self.font)
        
        columnDescriptions = [
            dict(title="", key="glyphName", cell=cell, editable=False, width=20),
            dict(title="Name", key="glyphName")
        ]
        self.w = vanilla.Window((300, 300))
        self.w.l = vanilla.List(
            (0, 0, 0, 0), 
            items=[dict(glyphName=glyphName) for glyphName in self.font.glyphOrder], 
            columnDescriptions=columnDescriptions
        )
        
        self.w.open()
        
Demo()