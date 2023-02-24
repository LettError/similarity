import cosineSimilarity

from cosineSimilarity import cosineSimilarity, SimilarGlyphsKey

print('SimilarGlyphsKey', SimilarGlyphsKey)

# https://typesupply.github.io/ezui/containers.html#ezui.Pane


g = CurrentGlyph()
font = CurrentFont()

t = 0.95    # the confidence threshold. Only show results > t
luc = True    # only show glyphs in the same unicode category
lur = True    # only show glyphs in the same unicode script

# zones are pairs of y values of the areas we specifically want to compare.
# useful if you want to exclude certain bands.
# this is an example, your values might be different:
zones = []
zones.append((font.info.xHeight, font.info.unitsPerEm+font.info.descender))
zones.append((0, font.info.xHeight))
zones.append((font.info.descender, 0))
zones = tuple(zones)    # make sure the zones are a tuple
zones = None            # or make zones None to scane the full height

# clip is how deep the profile should be, measured from the margin inward.
clip = 300

#side = "left" # look on the left side
side = "right" # look on the right side

# get the similar representation from the glyph with SimilarGlyphsKey.
similars = g.getRepresentation(SimilarGlyphsKey,
    threshold=t, 
    sameUnicodeClass=luc,
    sameUnicodeScript=lur,
    zones=zones,
    side=side,
    clip=clip
    )

# the results are ordered by confidence:
print('similars', similars)

