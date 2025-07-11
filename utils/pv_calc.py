import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from datetime import timedelta
# Librerias de Pvlib
from pvlib.pvsystem import pvwatts_dc # Modelo PVWatts
from pvlib.temperature import TEMPERATURE_MODEL_PARAMETERS, sapm_cell #Modelo para temperatura de celda
from pvlib.irradiance import get_total_irradiance # Modelo para calcular plane-of-array irradiance POA
from pvlib.location import Location # Para generar la posición solar para cada timestamp


# Calculo de irradiancia sobre plano inclinado
def irradiance_poa(df,lat,lon,surface_tilt,surface_azimuth):
    '''
    Calcula la irradiancia sobre un plano inclinado (plane of array -POA-) con pvlib

    Parámetros:
    - df: DataFrame con índice datetime que incluye variables como ghi, dni y dhi
    - lat, lon : latitud y longitud de la estación meteorológica para obtener la posición solar
    - surface_tilt: ángulo de inclinación del módulo FV [°]
    - surface_azimuth: ángulo de azimuth del módulo FV [°]

    solpos calcula la posición solar para cada timestamp

    Return: Devuelve la irradiancia global, directa y difusa sobre un plano inclinado 
    (poa_global, poa_direct, poa_diffuse) [W/m^2]
    '''
    location = Location(latitude=lat, longitude=lon)
    solpos = location.get_solarposition(df.index)
    irradiance = get_total_irradiance(
        surface_tilt = surface_tilt,
        surface_azimuth= surface_azimuth,
        dni = df.dni,
        ghi = df.ghi,
        dhi = df.dhi,
        solar_zenith = solpos['zenith'],
        solar_azimuth = solpos['azimuth']
        )
    return irradiance

# Cálculo de HSP
def hsp_calc(df,lat,lon,surface_tilt, surface_azimuth):
    '''
    Calcula la hora solar pico (HSP) de varios ángulos de inclinación del módulo FV

    Parámetros:
    - df: DataFrame con índice datetime que incluye variables como ghi, dni y dhi
    - lat, lon : latitud y longitud de la estación meteorológica para obtener la posición solar
    - surface_tilt: ángulo de inclinación del módulo FV [°]
    - surface_azimuth: ángulo de azimuth del módulo FV [°]

    solpos calcula la posición solar para cada timestamp

    Return: Devuelve las HSP promedio mensuales y promedio anual de los siguientes ángulos de inclinación
    (0°,lat°,lat-15°,lat+15°,90°)
    '''
    location = Location(latitude=lat, longitude=lon)
    solpos = location.get_solarposition(df.index)
    tilts= [0,surface_tilt,surface_tilt-15,surface_tilt+15,90]
    hsp_dict = {}
    for tilt in tilts:
        irradiance = get_total_irradiance(
            surface_tilt = tilt,
            surface_azimuth= surface_azimuth,
            dni = df.dni,
            ghi = df.ghi,
            dhi = df.dhi,
            solar_zenith = solpos['zenith'],
            solar_azimuth = solpos['azimuth'])

        ghi_hour = irradiance.poa_global.resample("h").mean() # type: ignore
        hsp_d = ghi_hour.resample("D").sum()/1000  
        hsp_avg_m = hsp_d.resample("ME").mean()

        hsp_dict[f"{tilt}°"] = round(hsp_avg_m,2)

    df_hsp= (pd.DataFrame(hsp_dict)).T
    df_hsp.columns = df_hsp.columns.strftime('%B') # type: ignore
    df_hsp.index.name = "Tilt"
    df_hsp["Average"]=df_hsp.mean(axis=1).round(2)
    
    return df_hsp

# Visualización la definición de HSP 
def hsp_visual(df_hsp,irradiance,set_date):
    '''
    Grafica la HSP promedio anual en una curva de irradiancia global (G) sobre un plano inclinado
    de una fecha específica

    Parámetros:
    - df_hsp: DataFrame de las HSP promedio mensuales y anual de diferentes inclinaciones 
    - irradiance : irradiancia global sobre un plano inclinado [W/m^2]
    - set_date: fecha específica a consultar

    Return: Gráfico de la definición de HSP sobre una curva G de un día específico
    '''
    hsp_year= df_hsp.Average.iloc[1]
    start_date = set_date
    end_date = set_date + timedelta(days=1)
    ghi_poa = irradiance.poa_global.resample("h").mean().loc[str(start_date):str(end_date)] # type: ignore
    center_time = ghi_poa.idxmax() #Tomé el max de irradiancia como valor central 
    start_time = center_time - pd.Timedelta(hours=hsp_year / 2)
    end_time = center_time + pd.Timedelta(hours=hsp_year / 2)

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=ghi_poa.index, y=ghi_poa, mode='lines', name='POA Global', line=dict(color='black')))

    fig.add_shape(type="line", x0=start_time, x1=start_time, y0=0, y1=1000,line=dict(color="red", dash="dash"), name="Inicio HSP") # type: ignore #Vertical
    fig.add_shape(type="line", x0=end_time, x1=end_time, y0=0, y1=1000,line=dict(color="red", dash="dash"), name="Fin HSP") # type: ignore #Vertical
    fig.add_shape(type="line", x0=start_time, x1=end_time, y0=1000, y1=1000,line=dict(color="red", dash="dot"), name="1000 W/m²") # type: ignore # Horizontal
    fig.add_shape(type="rect",x0=start_time, x1=end_time,y0=0, y1=1000,fillcolor="rgba(255,0,0,0.1)",line=dict(width=0),layer='below') # type: ignore # Sombreado

    fig.update_layout(
        title=f'Visualización de HSP promedio anual de la curva de irradiancia de la fecha ({set_date})',
        xaxis_title='Hora del día',
        yaxis_title='Irradiancia (W/m^2)',
        legend=dict(x=1.02, y=1, xanchor='left'),
        margin=dict(r=100),
        template='plotly_white'
    )
    return fig

# Cálculos para potencia AC
def power_calc(df,irradiance,assembly,pdc0,gamma_pdc,inv_eff):
    '''
    Calcula la potencia AC generada por un módulo FV específico

    Parámetros:
    - df: DataFrame con índice datetime que incluye variables como ghi, dni, dhi, tdb, ws
    - lat, lon : latitud y longitud de la estación meteorológica para obtener la posición solar
    - irradiance : irradiancia global sobre un plano inclinado [W/m^2]
    - assembly: tipo de montaje de los módulos de acuerdo según el modelo SAPM
    - pdc0: potencia nominal del módulo FV [W]
    - gamma_pdc: coeficiente de temperatura en potencia máxima 
    - inv_eff: eficiencia del inversor [0-1]

    -Se utiliza el modelo SAPM únicamente para calcular la temperatura de la celda
    -Se utiliza el modelo PVWatts para calcular la potencia DC

    Return: La potencia AC en un DataFrame y un Dataframe de irradiancia POA junto con la potencia AC
    '''
    # Calcular temperatura del módulo
    temp_params = TEMPERATURE_MODEL_PARAMETERS['sapm'][assembly]
    poa_global = irradiance['poa_global'] # Irradiancia sobre el plano con ángulos incluidos
    module_temp = sapm_cell(
        poa_global=poa_global,
        temp_air=df['tdb'],
        wind_speed=df['ws'],
        **temp_params
    )# modelo SAPM para obtener temperatura de la celda únicamente
    dc_power = pvwatts_dc(poa_global, module_temp, pdc0=pdc0, gamma_pdc=gamma_pdc) # Potencia DC
    ac_power = dc_power * inv_eff # Potencia AC brinda la potencia en W en intervalos de 10min de un único módulo 
    df_poa_power = irradiance[["poa_global", "poa_direct", "poa_diffuse"]].copy()
    df_poa_power["ac_power"] = ac_power

    return ac_power, df_poa_power

# Módulos y energía  
def modules(ac_power,goal_year):
    '''
    Calcula variables como el número de paneles, la energía mensual y anual

    Parámetros:
    - ac_power: DataFrame con índice datetime de la potencia AC [W]
    - goal_year : Consumo/Demanda/Meta anual de energía [kWh]

    Return: número de módulos necesarios para cubrir la demanda anual, 
    energía anual del número de módulos FV [kWh], porcentaje de energía cubierta por los módulos FV
    energía anual [kWh], energía mensual de un sólo módulo [kWh].
    ''' 
    ac_power_hour = ac_power.resample("h").mean()/1000 # Energía por hora en kWh
    energy_monthly = ac_power_hour.resample("ME").sum()
    energy_year = ac_power_hour.sum()
    num_pv = (goal_year / energy_year).round()
    pvno_energy_year = (num_pv*energy_year).round(2)
    percen = ((num_pv*energy_year)/goal_year)*100

    return  num_pv, pvno_energy_year, percen, energy_year, energy_monthly

# CONSUMO ANUAL
def pvgen_demand_year(goal_year,num_pv,energy_monthly):
    '''
    Grafica la generación FV total del número de módulos y la demanda mensual promedio a lo largo de un año

    Parámetros:
    - goal_year : Consumo/Demanda/Meta anual de energía [kWh]
    - num_pv: número de módulos FV
    - energy_monthly: energía mensual de un sólo módulo FV [kWh]

    Return: Gráfico generación FV vs Demanda mensual promedio de un año
    '''
    demand = round(goal_year/12,2)
    energy_monthly_array = pd.DataFrame({"Generación FV": (energy_monthly * num_pv).round(2),
        "Demanda":  demand})
    months = energy_monthly_array.index.to_period('M').strftime('%b') # type: ignore

    fig = go.Figure([
        go.Bar(name='Generación FV', x=months, y=energy_monthly_array["Generación FV"],
            marker_color='rgb(26, 118, 255)'),
        go.Bar(name='Demanda', x=months, y=energy_monthly_array["Demanda"],
            marker_color='rgb(55, 83, 109)')
    ])

    fig.update_layout(
        title='Energía mensual: Generación FV vs Demanda',
        xaxis_title='Mes',
        yaxis_title='Energía (kWh)',
        barmode='group',
        bargap=0.15,
        bargroupgap=0.1,
        legend=dict(
            x=1.1,  # Dentro del área de trazado
            y=1,
            xanchor='right',
            yanchor='top',
            bgcolor='rgba(0,0,0,0)',  # Fondo transparente
            bordercolor='rgba(0,0,0,0)'  # Sin borde
        ),
        margin=dict(r=30)
    )
    return fig

# CONSUMO BIMESTRAL
def pvgen_demand_bimonth(goal_bimonth,num_pv,energy_monthly):
    '''
    Grafica la generación FV total del número de módulos y la demanda bimestral a lo largo de un año

    Parámetros:
    - goal_bimonth : Consumo/Demanda/Meta bimestral de energía [kWh]
    - num_pv: número de módulos FV
    - energy_monthly: energía mensual de un sólo módulo FV [kWh]

    Return: Gráfico generación FV vs Demanda bimestral de un año
    '''
    demand = goal_bimonth
    bimestres = ["Ene-Feb", "Ene-Feb", "Mar-Abr", "Mar-Abr", "May-Jun", "May-Jun",
                "Jul-Ago", "Jul-Ago", "Sep-Oct", "Sep-Oct", "Nov-Dic", "Nov-Dic"]
    energy_bimon_df = energy_monthly.copy()
    energy_bimon_df.index = bimestres
    gen_bimon = energy_bimon_df.groupby(level=0).sum()
    orden_bimestres = ["Ene-Feb", "Mar-Abr", "May-Jun", "Jul-Ago", "Sep-Oct", "Nov-Dic"]
    gen_bimon = gen_bimon.reindex(orden_bimestres)
    # demand_series = pd.Series(goal_bimonth, index=orden_bimestres)
    energy_monthly_array = pd.DataFrame({"Generación FV": (gen_bimon * num_pv).round(2),
        "Demanda": demand
    })

    fig = go.Figure([
        go.Bar(name='Generación FV', x=energy_monthly_array.index, y=energy_monthly_array["Generación FV"],
            marker_color='rgb(26, 118, 255)'),
        go.Bar(name='Demanda', x=energy_monthly_array.index, y=energy_monthly_array["Demanda"],
            marker_color='rgb(55, 83, 109)')
    ])

    fig.update_layout(
        title='Energía bimestral: Generación FV vs Demanda',
        xaxis_title='Mes',
        yaxis_title='Energía (kWh)',
        barmode='group',
        bargap=0.15,
        bargroupgap=0.1,
        legend=dict(
            x=1.1,  # Dentro del área de trazado
            y=1,
            xanchor='right',
            yanchor='top',
            bgcolor='rgba(0,0,0,0)',  # Fondo transparente
            bordercolor='rgba(0,0,0,0)'  # Sin borde
        ),
        margin=dict(r=30)
    )
    return fig

# 8. Visualización de ghi, dni, dhi contra ghi2, dni2, dhi2 del modelo POA
def poa_visual(df,irradiance,set_date):
    '''
    Grafica las irradiancias de la estación meteorológica y las irradiancias sobre un plano inclinado (POA)

    Parámetros:
    - df: DataFrame con índice datetime que incluye variables como ghi, dni, dhi, tdb, ws
    - irradiance : irradiancia sobre un plano inclinado (global, directa y difusa) [W/m^2]
    - set_date: fecha específica a consultar

    Return: Gráfico irradiancias de mediciones meteorológicas e irradiancias sobre un plano inclinado (POA)
    '''
    start_date = set_date
    end_date = set_date + timedelta(days=1)
    # Mediciones
    ghi = df.ghi.resample("h").mean().loc[str(start_date):str(end_date)].round(2)
    dni = df.dni.resample("h").mean().loc[str(start_date):str(end_date)]
    dhi = df.dhi.resample("h").mean().loc[str(start_date):str(end_date)]
    # Del irradiance model POA sobre plano inclinado
    ghi2 = irradiance.poa_global.resample("h").mean().loc[str(start_date):str(end_date)]
    dni2 = irradiance.poa_direct.resample("h").mean().loc[str(start_date):str(end_date)] 
    dhi2 = irradiance.poa_diffuse.resample("h").mean().loc[str(start_date):str(end_date)] 

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=ghi.index, y=ghi, mode='lines', name='GHI (medido)', line=dict(color='red')))
    fig.add_trace(go.Scatter(x=dni.index, y=dni, mode='lines', name='DNI (medido)', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=dhi.index, y=dhi, mode='lines', name='DHI (medido)', line=dict(color='gold')))

    fig.add_trace(go.Scatter(x=ghi2.index, y=ghi2, mode='lines', name='POA Global', line=dict(color='purple')))
    fig.add_trace(go.Scatter(x=dni2.index, y=dni2, mode='lines', name='POA Directa', line=dict(color='cyan')))
    fig.add_trace(go.Scatter(x=dhi2.index, y=dhi2, mode='lines', name='POA Difusa', line=dict(color='green')))

    fig.update_layout(
        title=f'Comparación de Irradiancias: Medidas vs POA ({set_date})',
        xaxis_title='Hora del día',
        yaxis_title='Irradiancia (W/m2)',
        legend=dict(x=1.02, y=1, xanchor='left'),
        margin=dict(r=100),
        template='plotly_white'
    )

    return fig

# 9. Visualizacion de potencia en un día
def power_setdate(ac_power,set_date):
    '''
    Grafica la potencia AC de un día específico

    Parámetros:
    - ac_power: DataFrame con índice datetime de la potencia AC [W]
    - set_date: fecha específica a consultar

    Return: Gráfico de potencia AC de un día específico
    '''
    start_date = set_date
    end_date = set_date + timedelta(days=1)
    ac_power_day = ac_power.resample("h").mean()
    ac_power_day = ac_power_day.loc[str(start_date):str(end_date)]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=ac_power_day.index,
        y=ac_power_day.values,
        mode='lines',
        name='Potencia AC',
        line=dict(color='blue')
    ))

    fig.update_layout(
        title='Potencia AC diaria',
        xaxis_title='Hora del día',
        yaxis_title='Potencia AC [W]',
        xaxis=dict(showgrid=True),
        yaxis=dict(showgrid=True),
        template='plotly_white'
    )

    return fig
