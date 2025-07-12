from shiny import App, ui, render, reactive
from shinywidgets import output_widget, render_widget
from shiny import reactive
from utils.config import load_settings
from utils.pv_calc import irradiance_poa, hsp_calc, hsp_visual, power_calc, pvgen_poaglobal_year, poa_visual_extrdays, power_visual_extrdays
from components.pv_calc_ui import modules_pv, assembly_options, inverters
import pandas as pd
import duckdb

_, latitude, longitude, _ , _ = load_settings()
lat, lon = latitude, longitude
con = duckdb.connect('esolmet.db')
df_large = con.execute("SELECT * FROM lecturas").fetchdf()


df = df_large.pivot(index='fecha', columns='variable', values='valor')
df.index = pd.to_datetime(df.index)
df = df.sort_index()
df = df.loc["2024"]
df.index = df.index.tz_localize('America/Mexico_City') # type: ignore # Asignación de zona horaria


def pv_calc_server(input, output, session):
    
    has_clicked = reactive.Value(False)

    @reactive.effect
    @reactive.event(input.calculate)
    def on_click():
        has_clicked.set(True)

    @reactive.calc

    def calcs():
        if not has_clicked.get():
            # Usa valores por defecto antes de que se haga clic
            surface_tilt = latitude
            surface_azimuth = 180
            selected_mod = "Longi 620W Mono"
            pdc0 = modules_pv[selected_mod]["pdc0"]
            gamma_pdc = modules_pv[selected_mod]["gamma_pdc"]
            selected_asse = "Módulo monocristalino/policristalino en rack abierto"
            assembly = assembly_options[selected_asse]
            selected_inv = "Huawei SUN2000 480V (98.8%)"
            inv_eff = inverters[selected_inv]
        else:
            # Inputs
            surface_tilt=input.tilt()
            surface_azimuth=input.azimuth()
            selected_mod = input.model_pv()
            pdc0 = modules_pv[selected_mod]["pdc0"]
            gamma_pdc = modules_pv[selected_mod]["gamma_pdc"]
            selected_asse = input.assembly()
            assembly = assembly_options[selected_asse]
            selected_inv = input.inverter_model()
            inv_eff = inverters[selected_inv]

        # Funciones de cálculo
        irradiance = irradiance_poa(df,lat,lon,surface_tilt,surface_azimuth)
        ac_power, df_poa_power = power_calc(df,irradiance,assembly,pdc0,gamma_pdc,inv_eff)

        return {"irradiance": irradiance,"ac_power": ac_power,"df_poa_power": df_poa_power,
                "surface_tilt":surface_tilt,"surface_azimuth":surface_azimuth}

    @output
    @render_widget # type: ignore
    def graph_energy_month():
        ac_power = calcs()["ac_power"]
        irradiance = calcs()["irradiance"]        
        return pvgen_poaglobal_year(ac_power, irradiance)
    
    @output
    @render_widget # type: ignore
    def graph_irradiances():
        irradiance = calcs()["irradiance"]       
        return poa_visual_extrdays(irradiance)
    
    @output
    @render_widget # type: ignore
    def graph_ac_power():
        ac_power = calcs()["ac_power"]       
        return power_visual_extrdays(ac_power)

    @output
    @render_widget # type: ignore
    def graph_hsp():
        surface_tilt= calcs()["surface_tilt"]
        surface_azimuth= calcs()["surface_azimuth"]
        df_hsp = hsp_calc(df,lat,lon,surface_tilt, surface_azimuth)
        irradiance = calcs()["irradiance"]   
        return hsp_visual(df_hsp,irradiance)
    
    @output
    @render.table
    def table_hsp():
        surface_tilt= calcs()["surface_tilt"]
        surface_azimuth= calcs()["surface_azimuth"]
        return hsp_calc(df,lat,lon,surface_tilt, surface_azimuth)
    
    # Botón de descarga para datos POA
    @output
    @render.download(filename="datos_poa_potencia.csv", media_type="text/csv")
    def download_data_poa():
        df_poa_power = calcs()["df_poa_power"] 
        yield df_poa_power.to_csv(index=True)
        

    # Botón de descarga para tabla HSP
    @output
    @render.download(filename="tabla_hsp.csv",media_type="text/csv")
    def download_table_hsp():
        surface_tilt= calcs()["surface_tilt"]
        surface_azimuth= calcs()["surface_azimuth"]
        table = hsp_calc(df,lat,lon,surface_tilt, surface_azimuth)
        yield table.to_csv(index=True)
    
