
notes_cours = [
    10,
    12,
    19,
    3, 
    
    ]

notes_examen = [
    (18, 3),
    (12, 3),
    (16, 2),
    (13, 1)
]

total_points = []
total_coefficients = 0

# Calcul des notes de cours
for note_c in range(len(notes_cours)):
    total_points.append((notes_cours[note_c] + (notes_examen[note_c][0] * 2)) / 3)
    total_coefficients += notes_examen[note_c][1]
    
    
moyenne_coefficier = 0
# calcule moyenne coefficier
for n in range(len(total_points)):
    moyenne_coefficier += total_points[n] * notes_examen[n][1]

    
    
# calcule la moyenne generale de l'élève\
print(moyenne_coefficier, total_coefficients)
moyenne_generale = moyenne_coefficier / total_coefficients

print(moyenne_generale)



