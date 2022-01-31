import vanilla
import merz


import importlib
import cosineSimilarity
importlib.reload(cosineSimilarity)
from cosineSimilarity import cosineSimilarity, SimilarGlyphsKey
import itertools
import vanilla
import math
from glyphNameFormatter.reader import u2r, u2c


def suggestMembers(font, 
        groupName, 
        threshold= 0.9, 
        clip=200, 
        limitUnicodeCategory=True, 
        limitUnicodeRange=True,
        newOnly=True,
        ):
    members = font.groups[groupName]
    allRight = []
    allLeft = []
    for name, others in font.groups.items():
        if "public.kern1" in groupName:
            allRight += others
            continue
        if "public.kern2" in groupName:
            allRight += others
    #print('\tallLeft', allLeft)
    #print('\tallRight', allRight)
    side = None
    if "public.kern1" in groupName:
        # kern1 = left glyph in the pair, so the right side of the glyph is relevant
        side = "right"
    if "public.kern2" in groupName:
        side = "left"
    if not side: return []
    if not members: return []
    #print('\tside', side)
    #print("\tfont", font.path)
    #print("\tgroup", groupName)
    #print("\tmembers", members)
    zones = None
    suggest = []
    for name in members:
        #print(groupName, members)
        if name in font:
            this = font[name]
            similar = this.getRepresentation(SimilarGlyphsKey,
                threshold=threshold, 
                sameUnicodeClass=limitUnicodeCategory,
                sameUnicodeRange=limitUnicodeRange,
                zones=zones,
                side=side,
                clip=clip
                )
            #print(similar)
            for score, sims in similar.items():
                #print('\t\t', score)
                #print('\t\t\t', sims)
                if score < threshold: continue
                for s in sims:
                    if side is "left" and s in allRight and newOnly: 
                        #print(f"\t\t{side} skipping {s} because it is in allLeft")
                        continue
                    if side is "right" and s in allLeft and newOnly:
                        #print(f"\t\t{side} skipping {s} because it is in allRight")
                        continue
                    if s in members: continue
                    if s not in suggest:
                        suggest.append(s)
    return suggest
        
f = CurrentFont()
for name in f.groups.keys():
    suggestion = suggestMembers(f, name, threshold=0.99, clip=300, newOnly=True)
    if suggestion:
        print('suggest', name, suggestion)

