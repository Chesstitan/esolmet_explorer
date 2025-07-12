from shiny import App, ui, render, reactive
from shinywidgets import output_widget, render_widget
from utils.config import load_settings

_, latitude, longitude, _ , _ = load_settings()

modules_pv = {
    "JA Solar 550W Mono": {
        "pdc0": 550,
        "gamma_pdc": -0.004
    },
    "Canadian Solar 500W Poly": {
        "pdc0": 500,
        "gamma_pdc": -0.0042
    },
    "Longi 450W Mono": {
        "pdc0": 450,
        "gamma_pdc": -0.0039
    },
    "Trina Solar 410W Bifacial": {
        "pdc0": 410,
        "gamma_pdc": -0.0038
    }
}

assembly_options = {
    # "Módulo bifacial o vidrio-vidrio en estructura abierta": "open_rack_glass_glass",
    "Módulo monocristalino/policristalino en rack abierto": "open_rack_glass_polymer",
    # "Módulo vidrio-vidrio montado sobre techo": "roof_mount_glass_glass",
    "Módulo estándar montado sobre techo": "roof_mount_glass_polymer",
    # "Módulo en estructura con aislamiento": "insulated_back_glass_polymer"
}

inverters = {
    "Inversor A (96%)": 0.96,
    "Inversor B (98%)": 0.98
}

# Interfaz de usuario
pv_calc_ui = ui.page_fluid(
    ui.h2("Análisis solar fotovoltaico"),
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("model_pv","Selecciona un modelo de módulo FV", choices = list(modules_pv.keys()), selected = "Longi 450W Mono"),
            ui.input_select("assembly","Selecciona un modo de instalación", choices = list(assembly_options.keys()), selected = "Módulo monocristalino/policristalino en rack abierto" ),
            ui.input_select("inverter_model","Seleccione un modelo de inversor", choices = list(inverters.keys()), selected = "Inversor A (96%)"),
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