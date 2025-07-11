from shiny import App, ui, render, reactive
from shinywidgets import output_widget, render_widget
from utils.config import load_settings
from utils.pv_calc import irradiance_poa, hsp_calc, hsp_visual, power_calc, pvgen_poaglobal_year, poa_visual, power_setdate
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
    
    # @reactive.event(input.calculate)

    @reactive.calc
    def calcs():
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

        return {"irradiance": irradiance,"ac_power": ac_power,"df_poa_power": df_poa_power}

    @output
    @render_widget # type: ignore
    def graph_energy_month():
        ac_power = calcs()["ac_power"]
        irradiance = calcs()["irradiance"]        
        return pvgen_poaglobal_year(ac_power, irradiance)
    
    @output
    @render_widget # type: ignore
    def graph_irradiances():
        set_date = pd.to_datetime(input.set_date()).tz_localize("America/Mexico_City")
        irradiance = calcs()["irradiance"]       
        return poa_visual(df,irradiance,set_date)
    
    @output
    @render_widget # type: ignore
    def graph_ac_power():
        set_date = pd.to_datetime(input.set_date()).tz_localize("America/Mexico_City")
        ac_power = calcs()["ac_power"]       
        return power_setdate(ac_power,set_date)

    @output
    @render_widget # type: ignore
    def graph_hsp():
        surface_tilt=input.tilt()
        surface_azimuth=input.azimuth()
        df_hsp = hsp_calc(df,lat,lon,surface_tilt, surface_azimuth)
        irradiance = calcs()["irradiance"]   
        set_date = pd.to_datetime(input.set_date()).tz_localize("America/Mexico_City")    
        return hsp_visual(df_hsp,irradiance,set_date)
    
    @output
    @render.table
    def table_hsp():
        surface_tilt=input.tilt()
        surface_azimuth=input.azimuth()
        return hsp_calc(df,lat,lon,surface_tilt, surface_azimuth)
    
    # # Botón de descarga para datos POA
    # @output
    # @render.download
    # def download_data_poa():
    #     def writer():
    #         df_poa_power = calcs()["df_poa_power"] 
    #         yield df_poa_power.to_csv()
    #     return writer

    # # Botón de descarga para tabla HSP
    # @output
    # @render.download
    # def download_table_hsp():
    #     def writer():
    #         table = table_hsp()
    #         yield table.to_csv()
    #     return writer
    
