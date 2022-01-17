# experiment 20220110-b

# make groups, each starting with a different glyph




# this is one group found in Source Sans Variable Black

names = ["Izhitsa.sc", "V.sc", "izhitsa", "v", "w", "wacute", "wcircumflex", "wdieresis", "wgrave"]

import os
import  similarGroup
import importlib
importlib.reload(similarGroup)
from similarGroup import SimilarGroup, uniqueGroups
from cosineSimilarity import cosineSimilarity



def drawProfiles(sg, shift=0, d=2):
    # for use in drawbot
    save()

    for name, (g, values) in sg.members.items():
        pts = []
        #print(name, values)
        fill(1,0,.4, 0.3)
        stroke(None)
        for y, v in zip(sg.heights, values):
            oval(v-d,y-d,2*d,2*d)
            pts.append((v,y))
        p = BezierPath()
        p.moveTo(pts[0])
        
        for xy in pts[1:]:
            p.lineTo(xy)
        fill(None)
        strokeWidth(1)
        stroke(1,0,.4, 0.3)
        drawPath(p)
            
        translate(shift,shift)


    fill(1,.4,0, 0.3)
    pts = []
    r = 4
    for y, v in zip(sg.heights, sg.profile):
        fill(0,1,.4)
        stroke(None)
        oval(v-r,y-r,2*r,2*r)
        pts.append((v,y))
        p = BezierPath()
        p.moveTo(pts[0])
        
        for xy in pts[1:]:
            p.lineTo(xy)
        fill(None)
        strokeWidth(2)
        stroke(0,1,.4, 0.3)
        drawPath(p)

    restore()
    



side = "left"
threshold = 0.99

f = CurrentFont()
ufoName = os.path.basename(f.path)

groups = {}

for n1 in names:
    g1 = f[n1]
    s = SimilarGroup(side=side, verbose=False)
    s.addMember(g1, minDistance=threshold)
    for n2 in names:
        if n2 == n1:
            continue
        s.addMember(f[n2])
    groups[f'geometrygroup_{n1}'] = s

translate(200,200)
scale(0.4)
for g in groups.values():
    translate(200,0)
    drawProfiles(g)