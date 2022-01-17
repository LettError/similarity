# experiment 20220110
# how do the members of a group measure up between each other,
# compared to the average?

# Hmmm ok this shows that comparing to an average is not necessarily the right thing to do. 
# members can be close to the average, and still fall below the threshold when compared to individuals.
# Learned from Lars: this method of clustering uses a 'centroid' and that means the order
# in which the tests are done creates a bias. 



# this is one group found in Source Sans Variable Black

names = ["Izhitsa.sc", "V.sc", "izhitsa", "v", "w", "wacute", "wcircumflex", "wdieresis", "wgrave"]

import os
import  similarGroup
import importlib
importlib.reload(similarGroup)
from similarGroup import SimilarGroup, uniqueGroups
from cosineSimilarity import cosineSimilarity

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


groups = uniqueGroups(groups)

print("threshold", threshold)
print(groups[0])
g = groups[0]

print(g.profile)
print(g.audit())

values = {}
for n1 in names:
    g1 = f[n1]
    for n2 in names:
        key = [n1, n2]
        key.sort()
        key = tuple(key)
        if key in values:
            v = values[key]
        else:
            g2 = f[n2]
            v = cosineSimilarity(g1, g2)
        print(f'{n1} {n2} {v[0]}')
    