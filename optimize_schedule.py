import yaml
import pandas as pd
from ortools.sat.python import cp_model
import itertools
import visualize 
import time

## Helper-Klasse für die Callback-Funktion
class ObjectiveCallback(cp_model.CpSolverSolutionCallback):
    def __init__(self, objective_var):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__objective_var = objective_var
        self.__solution_count = 0
        self.__start_time = time.time()

    def on_solution_callback(self):
        current_time = time.time()
        elapsed = current_time - self.__start_time
        objective_val = self.Value(self.__objective_var)
        self.__solution_count += 1
        print(f"Lösung #{self.__solution_count} gefunden nach {elapsed:.2f}s. Neue beste Kosten: {objective_val}")

    def solution_count(self):
        return self.__solution_count

## Hauptfunktion zur Ausführung der Optimierung
def run_optimization(config_path='config.yaml'):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    constraints_cfg = config['constraints']
    files_cfg = config['files']
    opt_params = config['optimization']

    df_exams = pd.read_csv(files_cfg['exam_data_csv'])
    
    start_h, start_m = map(int, constraints_cfg['start_of_day'].split(':'))
    end_h, end_m = map(int, constraints_cfg['end_of_day'].split(':'))
    day_duration_min = (end_h - start_h) * 60 + (end_m - start_m)
    total_duration_min = day_duration_min * constraints_cfg['num_days']
    
    all_exams = df_exams['exam_id'].tolist()
    all_profs = pd.unique(df_exams[['prof_1', 'prof_2']].values.ravel('K')).tolist()
    all_rooms = list(range(constraints_cfg['num_rooms']))
    all_days = list(range(constraints_cfg['num_days']))

    ## 1. Erstellen des CP-SAT-Modells
    model = cp_model.CpModel()

    starts, ends, days, rooms, intervals = {}, {}, {}, {}, {}

    ## 2. Erstellen der Variablen für Startzeit, Endzeit, Tag und Raum für jede Prüfung im CP-SAT-Modell
    for exam_id in all_exams:
        starts[exam_id] = model.NewIntVar(0, total_duration_min, f"start_{exam_id}")
        ends[exam_id] = model.NewIntVar(0, total_duration_min, f"end_{exam_id}")
        days[exam_id] = model.NewIntVar(0, constraints_cfg['num_days'] - 1, f"day_{exam_id}")
        rooms[exam_id] = model.NewIntVar(0, constraints_cfg['num_rooms'] - 1, f"room_{exam_id}")
        intervals[exam_id] = model.NewIntervalVar(
            starts[exam_id], constraints_cfg['exam_duration_minutes'], ends[exam_id], f"interval_{exam_id}"
        )

    ## 3. Hinzufügen der harten Randbedingungen
    # a) Überprüfung der Zeitfenster für Prüfungen
    slot_duration = constraints_cfg['exam_duration_minutes'] + constraints_cfg['pause_between_exams_minutes']
    for room in all_rooms:
        room_intervals = []
        for ex_id in all_exams:
            is_in_room = model.NewBoolVar(f"exam_{ex_id}_in_room_{room}")
            model.Add(rooms[ex_id] == room).OnlyEnforceIf(is_in_room)
            model.Add(rooms[ex_id] != room).OnlyEnforceIf(is_in_room.Not())
            buffered_interval = model.NewOptionalIntervalVar(
                starts[ex_id], slot_duration, ends[ex_id] + constraints_cfg['pause_between_exams_minutes'],
                is_in_room, f"buffered_interval_{ex_id}_room_{room}"
            )
            room_intervals.append(buffered_interval)
        model.AddNoOverlap(room_intervals)

    # b) Überprüfung der Zeitfenster für Professoren
    for prof in all_profs:
        prof_exams = df_exams[(df_exams['prof_1'] == prof) | (df_exams['prof_2'] == prof)]['exam_id'].tolist()
        model.AddNoOverlap([intervals[ex_id] for ex_id in prof_exams])

    # c) Überprüfung der Zeitfenster für Studierende
    for exam_id in all_exams:
        start_in_day = model.NewIntVar(0, day_duration_min, f"start_in_day_{exam_id}")
        model.Add(starts[exam_id] == days[exam_id] * day_duration_min + start_in_day)
        model.Add(start_in_day <= day_duration_min - constraints_cfg['exam_duration_minutes'])

    # d) Überprüfung der maximalen Prüfungen pro Tag
    prof_active_days = []
    for prof in all_profs:
        for day in all_days:
            is_active = model.NewBoolVar(f"active_{prof}_day{day}")
            prof_active_days.append(is_active)
            exams_on_this_day = []
            prof_exam_ids = df_exams[(df_exams['prof_1'] == prof) | (df_exams['prof_2'] == prof)]['exam_id'].tolist()
            for ex_id in prof_exam_ids:
                exam_is_on_day = model.NewBoolVar(f"exam_{ex_id}_on_day_{day}")
                model.Add(days[ex_id] == day).OnlyEnforceIf(exam_is_on_day)
                model.Add(days[ex_id] != day).OnlyEnforceIf(exam_is_on_day.Not())
                exams_on_this_day.append(exam_is_on_day)
            model.AddBoolOr(exams_on_this_day).OnlyEnforceIf(is_active)
            model.Add(sum(exams_on_this_day) == 0).OnlyEnforceIf(is_active.Not())
            
    ## 4. Hinzufügen der weichen Randbedingungen
    # a) Minimierung der aktiven Tage für Professoren
    total_active_days_cost = sum(prof_active_days) * opt_params['weight_active_days']
    
    # b) Minimierung der Lokalität der Professorenpaare
    locality_costs = []
    if opt_params.get('weight_prof_pair_locality', 0) > 0:
        df_exams['prof_pair'] = df_exams.apply(lambda row: tuple(sorted((row['prof_1'], row['prof_2']))), axis=1)
        grouped = df_exams.groupby('prof_pair')
        prof_pair_groups = [group['exam_id'].tolist() for name, group in grouped if len(group) > 1]
        for exam_group in prof_pair_groups:
            min_start = model.NewIntVar(0, total_duration_min, f"min_start_{exam_group[0]}")
            max_end = model.NewIntVar(0, total_duration_min, f"max_end_{exam_group[0]}")
            model.AddMinEquality(min_start, [starts[ex] for ex in exam_group])
            model.AddMaxEquality(max_end, [ends[ex] for ex in exam_group])
            span = model.NewIntVar(0, total_duration_min, f"span_{exam_group[0]}")
            model.Add(span == max_end - min_start)
            locality_costs.append(span)
            for pair in itertools.combinations(exam_group, 2):
                are_rooms_different = model.NewBoolVar(f"rooms_diff_{pair[0]}_{pair[1]}")
                model.Add(rooms[pair[0]] != rooms[pair[1]]).OnlyEnforceIf(are_rooms_different)
                model.Add(rooms[pair[0]] == rooms[pair[1]]).OnlyEnforceIf(are_rooms_different.Not())
                locality_costs.append(are_rooms_different * 120)

    total_locality_cost = sum(locality_costs) * opt_params.get('weight_prof_pair_locality', 0)
    
    ## 5. Minimierung der Gesamtkosten
    total_objective = model.NewIntVar(0, 100000000, 'total_objective')
    model.Add(total_objective == total_active_days_cost + total_locality_cost)
    model.Minimize(total_objective)

    ## 6. Lösen des Modells
    print("Starte Optimierung...")
    print(f"Maximale Laufzeit: {opt_params['solver_time_limit_seconds']} Sekunden")
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(opt_params['solver_time_limit_seconds'])
    
    solution_callback = ObjectiveCallback(total_objective)
    status = solver.Solve(model, solution_callback)

    ## 7. Verarbeiten der Ergebnisse
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f"\nSuche beendet. {solution_callback.solution_count()} Lösungen gefunden. Beste Lösung wird verwendet.")
        print(f"Finaler Status: {solver.StatusName(status)}")
        schedule = []
        for exam_id in all_exams:
            start_val = solver.Value(starts[exam_id])
            day_val = solver.Value(days[exam_id])
            room_val = solver.Value(rooms[exam_id])
            day_start_minute = start_val % day_duration_min
            time_h = start_h + day_start_minute // 60
            time_m = start_m + day_start_minute % 60
            exam_info = df_exams[df_exams['exam_id'] == exam_id].iloc[0]
            schedule.append({
                'Tag': day_val + 1, 'Raum': room_val + 1, 'Startzeit': f"{time_h:02d}:{time_m:02d}",
                'Student': exam_info['student'], 'Prüfer 1': exam_info['prof_1'], 'Prüfer 2': exam_info['prof_2'],
            })
        df_schedule = pd.DataFrame(schedule)
        df_schedule.sort_values(by=['Tag', 'Raum', 'Startzeit'], inplace=True)
        df_schedule.to_csv(files_cfg['schedule_output_csv'], index=False)
        print(f"Optimierter Plan in '{files_cfg['schedule_output_csv']}' gespeichert.")
        print("\n--- Beispielhafter Auszug aus dem Plan ---")
        print(df_schedule.head(10))
        visualize.plot_schedule_gantt(df_schedule, config, filename=files_cfg['gantt_chart_plot'])
    else:
        print("Keine Lösung innerhalb des Zeitlimits gefunden.")

if __name__ == '__main__':
    run_optimization()