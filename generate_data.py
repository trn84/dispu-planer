import yaml
import pandas as pd
import random
import visualize 

def create_dummy_data(config_path='config.yaml'):
    """
    Liest die Konfiguration, erzeugt eine CSV-Datei mit gezielter Clusterbildung
    (basierend auf einem echten Durchschnitt und einer steuerbaren Varianz) und visualisiert die Rohdaten.
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    gen_params = config['generation']
    file_params = config['files']
    
    num_students = gen_params['num_students']
    num_professors = gen_params['num_professors']
    avg_joint_exams = gen_params.get('avg_joint_exams', 2)
    # Lese den neuen Parameter für die Varianz/Cluster-Stärke
    cluster_strength = gen_params.get('cluster_strength', 0.9)
    output_file = file_params['exam_data_csv']

    print(f"Generiere Daten für {num_students} Studierende und {num_professors} Professoren...")
    print(f"Ziel: Clusterbildung mit ca. {avg_joint_exams} Prüfungen pro aktivem Paar.")
    print(f"Cluster-Stärke: {cluster_strength*100:.0f}% der Prüfungen aus Arbeitsgruppen, {100-cluster_strength*100:.0f}% zufällig.")

    first_names = [
        'Anna', 'Bernd', 'Carla', 'David', 'Eva', 'Felix', 'Greta', 'Hans', 'Inga', 'Jonas', 
        'Klara', 'Leon', 'Marie', 'Niklas', 'Olivia', 'Paul', 'Quintus', 'Rita', 'Simon', 'Tina', 
        'Ulrich', 'Vera', 'Walter', 'Xenia', 'Yannick', 'Zoe', 'Alina', 'Benjamin', 'Christian',
        'Diana', 'Emil', 'Frieda', 'Gustav', 'Helena', 'Ismael', 'Julia', 'Kevin', 'Laura'
    ]
    last_names = [
        'Müller', 'Schmidt', 'Schneider', 'Fischer', 'Weber', 'Meyer', 'Wagner', 'Becker', 'Schulz', 
        'Hoffmann', 'Schäfer', 'Koch', 'Bauer', 'Richter', 'Klein', 'Wolf', 'Schröder', 'Neumann', 
        'Braun', 'Zimmermann', 'Krüger', 'Hartmann', 'Lange', 'Werner', 'Krause', 'Lehmann', 
        'Köhler', 'Herrmann', 'Walter', 'Maier', 'Huber', 'Kaiser', 'Fuchs', 'Peters', 'Lang', 
        'Scholz', 'Möller', 'Weiß', 'Jung', 'Hahn', 'Schubert', 'Vogel', 'Friedrich', 'Keller', 
        'Günther', 'Frank', 'Berger', 'Winkler', 'Roth', 'Beck', 'Lorenz', 'Baumann', 'Franke', 
        'Albrecht', 'Schuster', 'Simon', 'Ludwig', 'Böhm', 'Winter', 'Kraus', 'Martin', 'Schumacher'
    ]

    prof_names = set()
    while len(prof_names) < num_professors:
        prof_names.add(f"Prof. Dr. {random.choice(first_names)} {random.choice(last_names)}")
    professors = list(prof_names)
    
    student_names = set()
    while len(student_names) < num_students:
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        if name not in prof_names:
            student_names.add(name)
    students = list(student_names)

    pairing_pool = []
    
    ### ÜBERARBEITETE LOGIK MIT STEUERBARER VARIANZ ###
    # 1. Definiere die Anzahl der Prüfungen basierend auf der Cluster-Stärke
    num_clustered_exams = int(num_students * cluster_strength)
    num_random_exams = num_students - num_clustered_exams
    
    # 2. Erstelle die "Arbeitsgruppen"
    num_active_pairs = int(num_clustered_exams / avg_joint_exams) if avg_joint_exams > 0 else 0
    active_pairs = set()
    if num_professors > 1:
        # Sicherstellen, dass nicht mehr Paare gebildet werden, als möglich
        max_possible_pairs = (num_professors * (num_professors - 1)) / 2
        num_active_pairs = min(num_active_pairs, max_possible_pairs)
        
        while len(active_pairs) < num_active_pairs:
             pair = tuple(sorted(random.sample(professors, 2)))
             active_pairs.add(pair)
    active_pairs = list(active_pairs)

    # 3. Fülle den Pool mit Prüfungen aus den Arbeitsgruppen
    if active_pairs:
        for _ in range(num_clustered_exams):
            chosen_pair = random.choice(active_pairs)
            pairing_pool.append(chosen_pair)

    # 4. Fülle den Rest des Pools mit komplett zufälligen "Einmal-Kooperationen"
    if num_professors > 1:
        for _ in range(num_random_exams):
            pair = tuple(sorted(random.sample(professors, 2)))
            pairing_pool.append(pair)
        
    random.shuffle(pairing_pool)

    # 5. Weise die Paarungen aus dem Pool den Studierenden zu
    exam_list = []
    for i, student in enumerate(students):
        # Fallback, falls der Pool aus irgendeinem Grund leer ist
        if not pairing_pool:
            examiners = tuple(sorted(random.sample(professors, 2)))
        else:
            examiners = pairing_pool.pop()
            
        exam_list.append({
            'exam_id': i,
            'student': student,
            'prof_1': examiners[0],
            'prof_2': examiners[1]
        })

    df = pd.DataFrame(exam_list)
    df.to_csv(output_file, index=False)

    print(f"Daten erfolgreich in '{output_file}' gespeichert.")
    
    visualize.plot_prof_workload(df, filename=file_params['workload_plot'])
    visualize.plot_prof_pairs(df, filename=file_params['pairs_plot'])

if __name__ == '__main__':
    create_dummy_data()