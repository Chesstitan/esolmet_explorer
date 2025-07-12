from shiny import App, ui, render, reactive
from shinywidgets import output_widget, render_widget
from utils.config import load_settings

_, latitude, longitude, _ , _ = load_settings()

modules_pv = {
    "Longi 620W Mono": {
        "pdc0": 620,
        "gamma_pdc": -0.0028
    },
    "Canadian Solar 665W Mono PERC": {
        "pdc0": 665,
        "gamma_pdc": -0.0034
    },
    "JA Solar 605W Mono": {
        "pdc0": 605,
        "gamma_pdc": -0.0035
    },
    "Trina Solar 605W Mono": {
        "pdc0": 605,
        "gamma_pdc": -0.0034
    }
}

assembly_options = {
    "Módulo monocristalino/policristalino en rack abierto": "open_rack_glass_polymer",
    "Módulo estándar montado sobre techo": "roof_mount_glass_polymer"
}

inverters = {
    "Huawei SUN2000 480V (98.8%)": 0.988,
    "Solis GC20K 600V (98.3%)": 0.983,
    "Growatt MIN 4200TL-X2 360V (98.4%)":0.984
}

# Interfaz de usuario
pv_calc_ui = ui.page_fluid(
    ui.h2("Análisis solar fotovoltaico"),
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("model_pv","Selecciona un modelo de módulo FV", choices = list(modules_pv.keys()), selected = "Longi 620W Mono"),
            ui.input_select("assembly","Selecciona un modo de instalación", choices = list(assembly_options.keys()), selected = "Módulo monocristalino/policristalino en rack abierto" ),
            ui.input_select("inverter_model","Seleccione un modelo de inversor", choices = list(inverters.keys()), selected = "Huawei SUN2000 480V (98.8%)"),
            ui.input_numeric("tilt","Ángulo de inclinación del módulo (°)", value = latitude),
            ui.input_numeric("azimuth","Ángulo de azimuth del módulo (°)", value = 180),
            ui.input_action_button("calculate","Calcular")                    

        ),
        ui.div(
            output_widget("graph_energy_month")
        ),
        ui.div(
            output_widget("graph_irradiances"),
            output_widget("graph_ac_power")
            # ui.download_button("download_data_poa", "Descargar datos POA + Potencia")
        ),
        ui.div(
            ui.output_table("table_hsp")
            # ui.download_button("download_table_hsp", "Descargar tabla HSP")
        ),
        ui.div(
            output_widget("graph_hsp")
        )
        
    )
)