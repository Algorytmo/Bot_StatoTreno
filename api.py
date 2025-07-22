from bs4 import BeautifulSoup
import pandas as pd
import requests
import json
import os
import re



cwd = os.getcwd()
dbfolder = os.path.join(cwd, "API_PartenzeArrivi")

trains = {
    "CATEGORIA":[],
    "N. TRENO":[],
    "CAPOLINEA":[],
    "ORA DI ARRIVO":[],
    "RITARDO":[],
    "BINARIO":[],
    "PRONTO":[]
}


def start():

    data = {
        "id":[],
        "stazione":[],
        "scelta":[]
    }

    partenza = "arrivals=False"
    arrivo = "arrivals=True"

    localita = input("Scegli la località: ")
    part_arrivo = input("Scegli 1 per le partenze, 2 per gli arrivi: ")

    with open(os.path.join(dbfolder, "db-2.csv"), "r") as file:
        for x in file:
            ids = x.split(",", 1)[0]
            stazioni = x.split(",", 1)[1].strip()
            if localita != "" and localita.lower() in stazioni.lower() and part_arrivo == "1":
                if "ORA DI ARRIVO" in trains:
                    trains["ORA DI PARTENZA"] = trains.pop("ORA DI ARRIVO")
                data["id"].append(ids)
                data["stazione"].append(stazioni)
                data["scelta"].append(partenza)
            if localita != "" and localita.lower() in stazioni.lower() and part_arrivo == "2":
                if "PRONTO" in trains:
                    trains["IN ARRIVO"] = trains.pop("PRONTO")
                data["id"].append(ids)
                data["stazione"].append(stazioni)
                data["scelta"].append(arrivo)

    if len(data["stazione"]) > 1:
        print(f"\nScegli la stazione specifica\n")
        for y in data["stazione"]:
            print(y)
        scelta = input("\n")
        if scelta.upper() in data["stazione"]:
            indice = data["stazione"].index(scelta.upper())
            return [data["id"][indice], data['scelta'][0]]
    else:
        indice = data["stazione"].index(localita.upper())
        return [data["id"][indice], data['scelta'][0]]
    
def html_grabber():

    data = start()
    placeid = data[0]
    part_arrivo = data[1]
    url = f"https://iechub.rfi.it/ArriviPartenze/ArrivalsDepartures/Monitor?placeId={placeid}&{part_arrivo}"
    #url = "https://iechub.rfi.it/ArriviPartenze/ArrivalsDepartures/Monitor?placeId=1334&arrivals=False"
    #print(url)
    r = requests.get(url)
    if r.status_code == 200:
        html = r.content
        soup = BeautifulSoup(html, "html.parser")
        with open(os.path.join(dbfolder, "output.html"), "w", encoding="utf-8") as file:
            file.write(str(soup))
    lista_treni()

def lista_treni():
    with open(os.path.join(dbfolder, "output.html"), "rb") as file:
        soup = BeautifulSoup(file, "html.parser")
        last_update = soup.find("span", class_="acapo").get_text(strip=True) #Data e Orario Aggiornamento
        match = re.search(r'(\d{2}/\d{2}/\d{4})alle ore(\d{2}:\d{2}:\d{2})', last_update)
        data_update = match.group(1) #Data Ultimo Aggiornamento
        hour_update = match.group(2) #Ora Ultimo Aggiornamento
        ct = soup.find_all("img", class_="logoCategoria") #Tipo Treno
        t_id = soup.find_all(id="RTreno") #ID Treno
        sd = soup.find_all("td", id="RStazione") #Stazione Destinazione
        hr = soup.find_all("td", id="ROrario") #Orario arrivo
        #hp = soup.find_all("td", id="POrario") #Orario partenza
        m_rit = soup.find_all("td", id="RRitardo") #Ritardo
        bnr = soup.find_all("td", id="RBinario") #Binario
        rdy = soup.find_all("td", id="RExLampeggio") #InArrivo/Partenza
    
    update_info = {
        "DATA": data_update,
        "ORA": hour_update
    }

    # CATEGORIA TRENO
    for x in ct:
        cat_treno = str(x).split("class", 1)[0].split("<img alt=", 1)[1].split('"Categoria ', 1)[1].split('"', 1)[0]
        if len(cat_treno) != 0:
            trains["CATEGORIA"].append(cat_treno)
        else:
            trains["CATEGORIA"].append("-")

    # NUMERO TRENO
    for y in t_id:
        id_treno = y.text.strip()
        if len(id_treno) != 0:
            trains["N. TRENO"].append(id_treno)
        else:
            trains["N. TRENO"].append("-")

    # CAPOLINEA
    for z in sd:
        staz_dest = z.text.strip()
        if len(staz_dest) != 0:
            trains["CAPOLINEA"].append(staz_dest)
        else:
            trains["CAPOLINEA"].append("-")
    
    # ORA DI ARRIVO/PARTENZA
    for w in hr:
        h_arrivo = w.text.strip()
        try:
            if len(h_arrivo) != 0:
                trains["ORA DI ARRIVO"].append(h_arrivo)
            else:
                trains["ORA DI ARRIVO"].append("-")
        except KeyError:
            if len(h_arrivo) != 0:
                trains["ORA DI PARTENZA"].append(h_arrivo)
            else:
                trains["ORA DI PARTENZA"].append("-")

    # RITARDO   
    for v in m_rit:
        ritardo = v.text.strip()
        try:
            trains["RITARDO"].append(f"{ritardo} min." if int(ritardo) < 60 else f"{int(ritardo) // 60} h.")
        except (ValueError, TypeError):
            trains["RITARDO"].append("-")

    # BINARIO
    for p in bnr:
        binario = p.text.strip()
        if len(binario) != 0:
            trains["BINARIO"].append(binario)
        else:
            trains["BINARIO"].append("-")

    # PRONTO/IN ARRIVO
    for o in rdy:
        try:
            if "td aria-label=" in str(o):
                trains["PRONTO"].append("NO")
            else:
                trains["PRONTO"].append("SI")
        except KeyError:
            if "td aria-label=" in str(o):
                trains["IN ARRIVO"].append("NO")
            else:
                trains["IN ARRIVO"].append("SI")
            

    os.remove(os.path.join(dbfolder, "output.html"))
    table = pd.DataFrame.from_dict(trains, orient="index").transpose()

    raw_data = {
        "ULTIMO AGGIORNAMENTO": update_info,
        "TRENI": json.loads(table.to_json(orient="table", indent=4, index=False))["data"]
    }
    print(json.dumps(raw_data, indent=2))

def posizione_treno():
    num_treno = input("Inserisci il numero del treno: ")
    if num_treno:
        url = f"http://www.viaggiatreno.it/infomobilitamobile/resteasy/viaggiatreno/cercaNumeroTrenoTrenoAutocomplete/{num_treno}"
        c = requests.get(url)
        if c.status_code == 200:
            text_data = c.text
            raw_data = text_data.split("|")[1].strip().split("-")
            num_treno = raw_data[0]
            origine = raw_data[1]
            data_partenza = raw_data[2]
            api_url = f"http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno/andamentoTreno/{origine}/{num_treno}/{data_partenza}"
            s = requests.get(api_url)
            if s.status_code == 200:
                train_data = s.json()
                partenza = train_data.get("origine")
                capolinea = train_data.get("destinazione")
                ora_ultimo_rilevamento = train_data.get("compOraUltimoRilevamento")
                stazione_ultimo_rilevamento = train_data.get("stazioneUltimoRilevamento")
                circolante = train_data.get("circolante")
                arrivato = train_data.get("arrivato")
                ritardo = train_data.get("ritardo")
                treno = {
                    "Stazione di Partenza": partenza,
                    "Capolinea": capolinea,
                    "Ultimo Rilevamento": ora_ultimo_rilevamento,
                    "Stazione Corrente": stazione_ultimo_rilevamento,
                    "In Circolazione": circolante,
                    "Arrivato": arrivato,
                    "Ritardo": f"{ritardo} min."
                }
                print(json.dumps(treno, indent=2))


if __name__ == "__main__":
    scelta = input("Digita 1 per cercare treni in partenza/in arrivo - 2 per stato treno: ")
    if scelta == "1":
        html_grabber()
    if scelta == "2":
        posizione_treno()