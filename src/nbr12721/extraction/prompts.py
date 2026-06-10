"""Prompts do pipeline NBR 12721 (ABNT NBR 12721:2006)."""

PROMPT_SISTEMA = """Voce e um engenheiro civil especialista em incorporacao imobiliaria no Brasil.
Extraia dados de documentos de incorporacao e gere JSON para a planilha ABNT NBR 12721:2006.
Seja preciso: extraia EXATAMENTE o que esta nos documentos. Se nao encontrou, use "" ou 0."""

PROMPT_EXTRAIR = """Analise os textos extraidos dos documentos abaixo e extraia TODOS os dados
para a planilha ABNT NBR 12721:2006.
Quando houver uma secao "EVIDENCIAS CRITICAS", trate essas linhas como os trechos mais
importantes do texto original para identificar local, cidade/UF, unidades, pavimentos,
vagas, areas, datas, alvara e responsaveis.

DOCUMENTOS:
{textos}

DADOS CUB - SINDUSCON NORTE PR (use para preencher quadro3):
{cub_contexto}

Retorne EXCLUSIVAMENTE um JSON valido (sem markdown, sem ```), com esta estrutura:
{"incorporador":{"nome":"","cnpj":"","endereco":""},
"responsavel":{"nome":"","crea":"","art":"","endereco":""},
"projeto":{"nomeEdificio":"","localConstrucao":"","cidadeUf":"",
  "projetoPadrao":{"R":false,"CS":false,"CL":false,"CG":false,"CP":false,"CP1Q":false},
  "qtdUnidades":0,"padraoAcabamento":"","numPavimentos":0,
  "vagasUA":0,"vagasAcessorio":0,"vagasComum":0,"areaTerreno":0,"dataAprovacao":"","numAlvara":""},
"quadro1":{"pavimentos":[{"nome":"","areaPrivCobPadrao":0,"areaPrivCobDifReal":0,"areaPrivCobDifEquiv":0,
  "areaComumNPCobPadrao":0,"areaComumNPCobDifReal":0,"areaComumNPCobDifEquiv":0,
  "areaComumPCobPadrao":0,"areaComumPCobDifReal":0,"areaComumPCobDifEquiv":0,"qtdPavimentos":1}]},
"quadro2":{"unidades":[{"designacao":"","areaPrivCobPadrao":0,"areaPrivCobDifReal":0,"areaPrivCobDifEquiv":0,
  "areaComumNPCobPadrao":0,"areaComumNPCobDifReal":0,"areaComumNPCobDifEquiv":0,
  "qtdUnidades":1,"outrasAreasPriv":0,"areaTerrExcl":0,"areaTerrComum":0}]},
"quadro3":{"projetoPadrao":{"designacao":"","padrao":"","numPav":"","areaEquiv":"","quartos":"","salas":"","banheiros":"","quartosEmp":""},
  "sindicato":"","mesCub":"","valorCub":0,"percMateriais":0,"percMaoObra":0,
  "fundacoes":0,"elevadores":0,"fogoes":0,"aquecedores":0,"bombasRecalque":0,"incineracao":0,
  "arCondicionado":0,"calefacao":0,"ventilacao":0,"outros6_3":0,"playground":0,"urbanizacao":0,
  "recreacao":0,"ajardinamento":0,"instCondominio":0,"outros6_5":0,"outros6_6":0,
  "impostos":0,"projArq":0,"projEstrut":0,"projInst":0,"projEsp":0,"percConstrutor":0,"percIncorporador":0},
"quadro4a":{"unidadesSubrogadas":[]},
"quadro5":{"tipoEdificacao":"","numPavimentos":"","unidadesPorPav":"","numeracao":"","pilotis":"",
  "transicao":"","garagens":"","pavComunitarios":"","outrosPav":"","dataAprovacao":"","outrasIndicacoes":""},
"quadro6":{"equipamentos":[{"nome":"","tipo":"","acabamento":"","detalhes":""}]},
"quadro7":{"acabamentos":[{"dependencia":"","pisos":"","paredes":"","tetos":"","outros":""}]},
"quadro8":{"acabamentos":[{"dependencia":"","pisos":"","paredes":"","tetos":"","outros":""}]},
"_dados_faltantes":["lista de dados nao encontrados"]}

REGRAS: Quadro I = pavimentos (qtdPavimentos para repetidos). Quadro II = unidades (qtdUnidades para repetidas).
Quadro VII = acabamentos privativos. Quadro VIII = acabamentos areas comuns.
projetoPadrao.R=true se residencial. Retorne SOMENTE o JSON."""

PROMPT_RESUMIR_LOTE = """Analise APENAS este lote de texto de documentos de incorporacao imobiliaria.
Extraia somente fatos objetivos e potencialmente uteis para preencher a ABNT NBR 12721:2006.

Lote:
{textos}

Retorne EXCLUSIVAMENTE um JSON valido (sem markdown) com esta estrutura:
{
  "resumo": {
    "identificacao": [],
    "responsaveis": [],
    "projeto": [],
    "quadro1": [],
    "quadro2": [],
    "quadro5": [],
    "quadro6": [],
    "quadro7": [],
    "quadro8": []
  },
  "dados_numericos": [],
  "pendencias": []
}

Regras:
- Cada item das listas deve ser curto, objetivo e autocontido.
- Preserve numeros, unidades, designacoes, nomes e datas como aparecem.
- Preserve especialmente cidade/UF, quantidade de unidades, pavimentos, vagas, areas totais,
  datas, alvaras e padroes de unidade quando aparecerem.
- Nao invente dados ausentes.
- Ignore repeticoes e ruido visual."""

PROMPT_ENRIQUECER_PATCH = """Voce e assistente de enriquecimento controlado para a ABNT NBR 12721:2006.
Voce NAO preenche a planilha inteira e NAO gera um JSON completo.
Voce retorna APENAS um patch JSON com campos permitidos, cada um com evidencia curta.

CAMPOS PERMITIDOS (somente estes paths podem aparecer no patch):
{campos_editaveis}

CAMPOS BLOQUEADOS (nao incluir no patch, nem sugerir alteracao):
CNPJ, CREA, unidades, pavimentos, vagas, areas, CUB, Quadros I e II, Quadro V e demais campos objetivos.

JSON DETERMINISTICO ATUAL (base — nao reescreva este objeto inteiro):
{json_deterministico}

AVISOS SEMANTICOS ATUAIS:
{avisos_semanticos}

TEXTOS / EVIDENCIAS DOS DOCUMENTOS:
{textos}

Retorne EXCLUSIVAMENTE um JSON valido (sem markdown) neste formato:
{{"patch":[{{"path":"projeto.nomeEdificio","valor":"Residencial Exemplo","evidencia":"trecho curto do documento","confianca":"alta"}}],"nao_encontrado":["quadro7.acabamentos"]}}

Regras:
- Cada item do patch deve ter path, valor, evidencia (trecho curto) e confianca (baixa|media|alta).
- Se nao houver evidencia clara no texto, NAO crie item; registre o path em nao_encontrado.
- Campos textuais: proponha valor apenas para enriquecer campos vazios ou com lixo OCR.
- quadro6.equipamentos, quadro7.acabamentos e quadro8.acabamentos: valor deve ser lista de objetos com conteudo real (nao template vazio).
- Nao altere campos bloqueados. Nao retorne o JSON deterministico completo."""
