import time
from similarGroup import proposeGroupsGlyph
from mojo.UI import CurrentSpaceCenter, OpenSpaceCenter

g = CurrentGlyph()
start = time.time()
left = proposeGroupsGlyph(g, side="left")
right = proposeGroupsGlyph(g, side="right")
print(f'duration {time.time()-start}')

sp = CurrentSpaceCenter()
if sp is None:
    sp = OpenSpaceCenter(g.font)
sp.setRaw(right.asSlashString() + f"/space/{g.name}/space" + left.asSlashString())
