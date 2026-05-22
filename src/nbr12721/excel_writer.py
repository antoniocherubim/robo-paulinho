"""Preenchimento da planilha ABNT NBR 12721:2006 (openpyxl)."""

__all__ = ["preencher_planilha"]


def preencher_planilha(dados, modelo, saida):
    from openpyxl import load_workbook
    def N(v):
        try: return float(v) if v else 0
        except: return 0
    def S(ws, cell, val):
        try: ws[cell] = val
        except AttributeError: pass

    wb = load_workbook(modelo)
    ws = wb["INFORMAÇÕES PRELIMINARES"]
    inc, resp, proj = dados["incorporador"], dados["responsavel"], dados["projeto"]
    S(ws,"F5",inc["nome"]); S(ws,"F6",inc["cnpj"]); S(ws,"F7",inc["endereco"])
    S(ws,"G10",resp["nome"]); S(ws,"G11",resp["crea"]); S(ws,"G12",resp["art"]); S(ws,"G13",resp["endereco"])
    S(ws,"G16",proj["nomeEdificio"]); S(ws,"G17",proj["localConstrucao"]); S(ws,"G18",proj["cidadeUf"])
    pp = proj.get("projetoPadrao",{})
    S(ws,"H19","X" if pp.get("R") else ""); S(ws,"J19","X" if pp.get("CS") else "")
    S(ws,"L19","X" if pp.get("CL") else ""); S(ws,"H20","X" if pp.get("CG") else "")
    S(ws,"J20","X" if pp.get("CP") else ""); S(ws,"L20","X" if pp.get("CP1Q") else "")
    S(ws,"G21",proj.get("qtdUnidades","") or ""); S(ws,"G22",proj.get("padraoAcabamento",""))
    S(ws,"G23",proj.get("numPavimentos","") or "")
    S(ws,"I25",proj.get("vagasUA","") or ""); S(ws,"I26",proj.get("vagasAcessorio","") or "")
    S(ws,"I27",proj.get("vagasComum","") or "")
    S(ws,"H28",proj.get("areaTerreno","") or ""); S(ws,"H29",proj.get("dataAprovacao",""))
    S(ws,"H30",proj.get("numAlvara",""))

    ws = wb["QUADRO I"]
    S(ws,"D5",f"{proj.get('localConstrucao','')} - {proj.get('cidadeUf','')}")
    for i,p in enumerate(dados.get("quadro1",{}).get("pavimentos",[])[:25]):
        r=16+i
        ws.cell(r,2).value=p.get("nome",""); ws.cell(r,3).value=N(p.get("areaPrivCobPadrao"))
        ws.cell(r,4).value=N(p.get("areaPrivCobDifReal")); ws.cell(r,5).value=N(p.get("areaPrivCobDifEquiv"))
        ws.cell(r,8).value=N(p.get("areaComumNPCobPadrao")); ws.cell(r,9).value=N(p.get("areaComumNPCobDifReal"))
        ws.cell(r,10).value=N(p.get("areaComumNPCobDifEquiv"))
        ws.cell(r,13).value=N(p.get("areaComumPCobPadrao")); ws.cell(r,14).value=N(p.get("areaComumPCobDifReal"))
        ws.cell(r,15).value=N(p.get("areaComumPCobDifEquiv")); ws.cell(r,20).value=N(p.get("qtdPavimentos",1))

    ws = wb["QUADRO II"]
    for i,u in enumerate(dados.get("quadro2",{}).get("unidades",[])[:25]):
        r=17+i
        ws.cell(r,2).value=u.get("designacao",""); ws.cell(r,3).value=N(u.get("areaPrivCobPadrao"))
        ws.cell(r,4).value=N(u.get("areaPrivCobDifReal")); ws.cell(r,5).value=N(u.get("areaPrivCobDifEquiv"))
        ws.cell(r,8).value=N(u.get("areaComumNPCobPadrao")); ws.cell(r,9).value=N(u.get("areaComumNPCobDifReal"))
        ws.cell(r,10).value=N(u.get("areaComumNPCobDifEquiv")); ws.cell(r,22).value=N(u.get("qtdUnidades",1))

    ws = wb["QUADRO III"]
    q3 = dados.get("quadro3",{}); pp3 = q3.get("projetoPadrao",{})
    S(ws,"C18",pp3.get("designacao","")); S(ws,"D18",pp3.get("padrao","")); S(ws,"E18",pp3.get("numPav",""))
    S(ws,"F18",pp3.get("areaEquiv","")); S(ws,"G18",pp3.get("quartos","")); S(ws,"H18",pp3.get("salas",""))
    S(ws,"I18",pp3.get("banheiros","")); S(ws,"K18",pp3.get("quartosEmp",""))
    S(ws,"G19",q3.get("sindicato","")); S(ws,"G20",q3.get("mesCub","")); S(ws,"L20",N(q3.get("valorCub",0)))
    cub=N(q3.get("valorCub")); pm=N(q3.get("percMateriais")); po=N(q3.get("percMaoObra"))
    if cub>0 and pm>0: S(ws,"P31",round(cub*pm/100,2))
    if cub>0 and po>0: S(ws,"P32",round(cub*po/100,2))
    for cell,key in [("L34","fundacoes"),("L35","elevadores"),("L37","fogoes"),("L38","aquecedores"),
        ("L39","bombasRecalque"),("L40","incineracao"),("L41","arCondicionado"),("L42","calefacao"),
        ("L43","ventilacao"),("L44","outros6_3"),("L45","playground"),("L47","urbanizacao"),
        ("L48","recreacao"),("L49","ajardinamento"),("L50","instCondominio"),("L51","outros6_5"),
        ("L52","outros6_6"),("L54","impostos"),("L56","projArq"),("L57","projEstrut"),
        ("L58","projInst"),("L59","projEsp")]:
        v=N(q3.get(key,0)); S(ws,cell,v if v>0 else None)
    pc=N(q3.get("percConstrutor",0)); pi=N(q3.get("percIncorporador",0))
    S(ws,"P61",pc/100 if pc else None); S(ws,"P62",pi/100 if pi else None)

    ws = wb["QUADRO IV B"]
    for i,u in enumerate(dados.get("quadro2",{}).get("unidades",[])[:25]):
        ws.cell(14+i,4).value=N(u.get("outrasAreasPriv",0)); ws.cell(14+i,9).value=N(u.get("qtdUnidades",1))
    ws = wb["QUADRO IV B.1"]
    for i,u in enumerate(dados.get("quadro2",{}).get("unidades",[])[:25]):
        r=15+i; ws.cell(r,4).value=N(u.get("outrasAreasPriv",0))
        ws.cell(r,8).value=N(u.get("areaTerrExcl",0)); ws.cell(r,9).value=N(u.get("areaTerrComum",0))

    ws = wb["QUADRO V"]
    q5 = dados.get("quadro5",{})
    for row,key in [(11,"tipoEdificacao"),(13,"numPavimentos"),(15,"unidadesPorPav"),(17,"numeracao"),
        (19,"pilotis"),(20,"transicao"),(21,"garagens"),(22,"pavComunitarios"),(23,"outrosPav"),
        (26,"dataAprovacao"),(28,"outrasIndicacoes")]:
        v=q5.get(key,"");
        if v: ws.cell(row,6).value=v

    ws = wb["QUADRO VI"]
    for i,eq in enumerate(dados.get("quadro6",{}).get("equipamentos",[])[:30]):
        r=12+i; ws.cell(r,2).value=eq.get("nome",""); ws.cell(r,4).value=eq.get("tipo","")
        ws.cell(r,6).value=eq.get("acabamento",""); ws.cell(r,8).value=eq.get("detalhes","")
    ws = wb["QUADRO VII"]
    for i,ac in enumerate(dados.get("quadro7",{}).get("acabamentos",[])[:30]):
        r=12+i; ws.cell(r,2).value=ac.get("dependencia",""); ws.cell(r,4).value=ac.get("pisos","")
        ws.cell(r,7).value=ac.get("paredes",""); ws.cell(r,10).value=ac.get("tetos",""); ws.cell(r,12).value=ac.get("outros","")
    ws = wb["QUADRO VIII"]
    for i,ac in enumerate(dados.get("quadro8",{}).get("acabamentos",[])[:30]):
        r=12+i; ws.cell(r,2).value=ac.get("dependencia",""); ws.cell(r,4).value=ac.get("pisos","")
        ws.cell(r,7).value=ac.get("paredes",""); ws.cell(r,10).value=ac.get("tetos",""); ws.cell(r,12).value=ac.get("outros","")
    wb.save(saida)
