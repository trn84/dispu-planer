import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
import random
from pyvis.network import Network
import plotly.express as px
from datetime import datetime, timedelta

def plot_prof_workload(df_exams, filename='professoren_auslastung.png'):
    """Erstellt ein Balkendiagramm, das die Anzahl der Prüfungen pro Professor zeigt."""
    print("Erstelle Visualisierung der Professoren-Auslastung...")
    
    prof1_counts = df_exams['prof_1'].value_counts()
    prof2_counts = df_exams['prof_2'].value_counts()
    total_counts = prof1_counts.add(prof2_counts, fill_value=0).sort_values(ascending=False)
    
    total_counts.index = total_counts.index.str.replace('Prof. Dr. ', '')

    plt.figure(figsize=(20, 10))
    total_counts.plot(kind='bar', color='skyblue')
    plt.title('Anzahl der Prüfungen pro Professor (Auslastung)', fontsize=16)
    plt.xlabel('Professor', fontsize=12)
    plt.ylabel('Anzahl der Prüfungen', fontsize=12)
    plt.xticks(rotation=90, ha='center', fontsize=8)
    plt.grid(axis='y', linestyle='--')
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    print(f"Diagramm gespeichert unter: {filename}")

def plot_prof_pairs(df_exams, filename='professoren_paare.html'):
    """
    Erstellt ein INTERAKTIVES Netzwerkdiagramm mit pyvis, das stark verbundene
    Professoren durch räumliche Nähe und Clusterbildung hervorhebt.
    """
    print("Erstelle interaktives Netzwerkdiagramm der Professoren-Paare...")

    df_exams['prof_pair'] = df_exams.apply(lambda row: tuple(sorted((row['prof_1'], row['prof_2']))), axis=1)
    edge_counts = df_exams['prof_pair'].value_counts().reset_index(name='count')
    edge_counts.rename(columns={'prof_pair': 'pair'}, inplace=True)

    nt = Network(
        height='900px', 
        width='100%', 
        bgcolor='#222222', 
        font_color='white', 
        notebook=True, 
        directed=False,
        cdn_resources='in_line'
    )

    all_profs = pd.unique(df_exams[['prof_1', 'prof_2']].values.ravel('K'))
    for prof in all_profs:
        prof_workload = len(df_exams[(df_exams['prof_1'] == prof) | (df_exams['prof_2'] == prof)])
        short_name = prof.replace('Prof. Dr. ', '')
        nt.add_node(prof, label=short_name, title=f'{prof}\nPrüfungen: {prof_workload}', value=prof_workload)

    base_length = 500
    reduction_per_exam = 80

    for index, row in edge_counts.iterrows():
        prof_pair = row['pair']
        count = row['count']
        spring_length = max(50, base_length - count * reduction_per_exam)
        
        nt.add_edge(
            prof_pair[0], 
            prof_pair[1], 
            value=count,
            title=f'Gemeinsame Prüfungen: {count}',
            length=spring_length
        )
    
    options = """
    {
        "nodes": { "borderWidth": 2, "borderWidthSelected": 4, "color": { "border": "#222222", "background": "#666666", "highlight": { "border": "#FFFFFF", "background": "#D3913B" }, "hover": { "border": "#FFFFFF", "background": "#888888" } } },
        "edges": { "color": { "highlight": "#D3913B", "hover": "#888888", "inherit": false }, "smooth": false },
        "interaction": { "hover": true, "hoverConnectedEdges": true, "multiselect": true, "navigationButtons": true, "tooltipDelay": 200 },
        "physics": { "barnesHut": { "gravitationalConstant": -30000, "centralGravity": 0.1, "springLength": 250, "springConstant": 0.05, "damping": 0.09, "avoidOverlap": 0.1 }, "minVelocity": 0.75, "solver": "barnesHut" }
    }
    """
    nt.set_options(options)
    # Fix Unicode encoding issue by writing HTML with UTF-8 encoding
    html_content = nt.generate_html()
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Interaktives Netzwerkdiagramm gespeichert unter: {filename}")


def plot_schedule_gantt(df_schedule, config, filename='optimierter_plan_interaktiv.html'):
    """
    Erstellt ein interaktives Gantt-Diagramm des finalen Prüfungsplans mit Plotly.
    """
    print("Erstelle interaktives Gantt-Diagramm des optimierten Plans...")
    
    constraints_cfg = config['constraints']
    
    df_plot = df_schedule.copy()
    
    base_date = datetime.now().date()
    df_plot['start_datetime'] = df_plot.apply(
        lambda row: datetime.combine(base_date + timedelta(days=row['Tag']-1), datetime.strptime(row['Startzeit'], '%H:%M').time()), axis=1
    )
    df_plot['end_datetime'] = df_plot['start_datetime'] + timedelta(minutes=constraints_cfg['exam_duration_minutes'])
    
    df_plot['Raum'] = 'Raum ' + df_plot['Raum'].astype(str)
    
    df_plot['prof_pair_str'] = df_plot.apply(
        lambda row: f"{row['Prüfer 1'].replace('Prof. Dr. ', '')} & {row['Prüfer 2'].replace('Prof. Dr. ', '')}", axis=1
    )
    
    df_plot['hover_text'] = df_plot.apply(
        lambda row: f"<b>{row['Student']}</b><br>Prüfer: {row['prof_pair_str']}<br>Zeit: {row['Startzeit']}", axis=1
    )
    
    ### START DER KORREKTUR: Eindeutige Farbzuweisung ###
    # 1. Finde alle einzigartigen Professorenpaare
    unique_pairs = df_plot['prof_pair_str'].unique()
    
    # 2. Erzeuge eine deterministische, einzigartige Farbe für jedes Paar
    random.seed(42) # Wichtig, damit die Farben bei jedem Lauf gleich bleiben!
    color_map = {
        pair: f'#{random.randint(0, 0xFFFFFF):06x}' for pair in unique_pairs
    }
    
    # 3. Erstelle die interaktive Grafik mit der expliziten Farb-Map
    fig = px.timeline(
        df_plot,
        x_start="start_datetime",
        x_end="end_datetime",
        y="Raum",
        color="prof_pair_str",
        hover_name="hover_text",
        title="Interaktiver Prüfungsplan",
        color_discrete_map=color_map # Dies ist die entscheidende Anweisung!
    )
    ### ENDE DER KORREKTUR ###

    fig.update_layout(
        template="plotly_dark",
        xaxis_title="Zeit",
        yaxis_title="Prüfungsraum",
        legend_title_text='Prüfer-Paare',
        font=dict(family="Arial, sans-serif", size=12, color="white")
    )
    
    fig.update_yaxes(autorange="reversed")
    
    fig.write_html(filename)
    print(f"Interaktives Gantt-Diagramm gespeichert unter: {filename}")