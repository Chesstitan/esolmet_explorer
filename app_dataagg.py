from shiny import App, ui, render, req, reactive
# import shinyswatch  
from components.panels import panel_subir_datos, panel_documentacion, panel_pruebas
from utils.data_processing import carga_csv
from utils.graficadores import graficado_Todo_matplotlib

#HOLA

app_ui = ui.page_fluid(
    ui.navset_card_tab(  
        panel_subir_datos(),
        panel_pruebas(),
        # panel_herramientas(),
        panel_documentacion(),
        id="tab",  
    ),
    # theme=shinyswatch.theme.journal
  
)
 

def server(input, output, session):

    @reactive.calc
    def df():
        f = req(input.archivo()) 
        return carga_csv(f[0]["datapath"])
    
    @render.plot(alt='Todos')
    def plot_matplotlib():
        return graficado_Todo_matplotlib(df())


app = App(app_ui, server)