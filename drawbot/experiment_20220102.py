import os
import  similarGroup
import importlib
importlib.reload(similarGroup)
from similarGroup import SimilarGroup, uniqueGroups



# this is the one that calculates the similarity groups with a pdf 



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
    
    
    
f = CurrentFont()
ufoName = os.path.basename(f.path) 


groups = {}

side="right"
threshold = 0.97
font("Menlo-Regular")

useShortCut = False
pageCount = 0

for side in ['left', 'right']:
    for name in f.selection:
        g1 = f[name]
        if useShortCut:
            # check if this glyph is already in one of the groups
            # this is a bit of a shortcut which might not always work
            needsNew = True
            for cg in groups.values():
                if g1.name in cg.members:
                    #print(f'{g1.name} already in a group')
                    needsNew = False
                    break
            if not needsNew:
                continue
        s = SimilarGroup(side=side)
        s.addMember(g1)
        for g2 in f:
            if g1.name == g2.name: continue
            s.addMember(g2, minDistance=threshold)
        groups[g1.name] = s

    for gg in uniqueGroups(groups):
        pageCount += 1
        newPage("A4")
        save()
        if side == 'left':
            x = 0.2 * width()
        else:
            x = 0.8 * width()
        translate(x, 150)
        stroke(0)
        fill(None)
        strokeWidth(0.9)
        lineDash(5,5)
        line((0, f.info.descender),(0, f.info.ascender))
        scale(0.4)
        stroke(0)
        lineDash(None)
        marginHeight = 20
        for name in gg.keys():
            path = BezierPath(glyphSet=f)
            save()
            if side == "right":
                translate(-f[name].width,0)
                mx = f[name].width-f[name].rightMargin
            else:
                translate(-f[name].leftMargin,0)
                mx = -f[name].leftMargin
            stroke(0,0,1)
            fill(None)
            line((mx, 0), (mx, 40))
            f[name].draw(path)
            stroke(0)
            fill(0,0,0,0.04)
            drawPath(path)
                   
            restore()
        #print(side, gg.asString())
        drawProfiles(gg)
        restore()
        # caption
        fill(0)
        stroke(None)
        fontSize(7)
        text(f'page {pageCount}\n\nthreshold: {threshold}\nSimilarity on {side}\n{ufoName}\n/{"/".join(gg.keys())}', (0.2*width(),height()-200))
        
saveImage(f"profiles_for_{ufoName}_t_{threshold}.pdf")