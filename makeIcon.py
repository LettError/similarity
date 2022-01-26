# a script for drawbot.app that generates the icon


size(512, 512)

a = .6
RED = (1, 0, 0, a)
BLUE = (.5, 0, 1, a)



left = BezierPath()
left.rect(0,0,width()*.5, height())

rr = 51
sw = 4
its = 53
with savedState():
    clipPath(left)
    for i in range(its):
        m = randint(60,140)
        stroke(*RED)
        strokeWidth(sw)
        fill(None)
        oval(m+randint(-rr,rr), m+randint(-rr,rr), width()-2*m, height()-2*m)

right = BezierPath()
right.rect(width()*.5,0,width()*.5, height())

with savedState():
    clipPath(right)
    for i in range(its):
        m = randint(60,140)
        stroke(*BLUE)
        strokeWidth(sw)
        fill(None)
        oval(m+randint(-rr,rr), m+randint(-rr,rr), width()-2*m, height()-2*m)
    
    
saveImage("icon.pdf")
saveImage("SimilarityMechanicIcon.png")
saveImage("html/SimilarityMechanicIcon.png")