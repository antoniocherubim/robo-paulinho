"""Parsing JSON de respostas LLM e consolidacao de resumos por lote."""
import json

__all__ = ["parsear_json", "compactar_resumos"]


def parsear_json(texto):
    texto = texto.strip()
    if texto.startswith("```"): texto = texto.split("\n", 1)[1] if "\n" in texto else texto[3:]
    if texto.endswith("```"): texto = texto.rsplit("```", 1)[0]
    texto = texto.strip()
    inicio = texto.find("{")
    if inicio < 0: raise json.JSONDecodeError("Nenhum JSON encontrado", texto, 0)
    nivel = 0
    em_string = False
    escape = False
    for i in range(inicio, len(texto)):
        c = texto[i]
        if escape:
            escape = False; continue
        if c == '\\':
            escape = True; continue
        if c == '"':
            em_string = not em_string; continue
        if em_string: continue
        if c == '{': nivel += 1
        elif c == '}':
            nivel -= 1
            if nivel == 0:
                return json.loads(texto[inicio:i+1])
    fim = texto.rfind("}") + 1
    if fim > inicio: return json.loads(texto[inicio:fim])
    raise json.JSONDecodeError("JSON incompleto", texto, len(texto))


def compactar_resumos(resumos):
    linhas = []
    for i, resumo in enumerate(resumos, start=1):
        linhas.append(f"LOTE {i}:")
        for chave, itens in resumo.get("resumo", {}).items():
            if itens:
                linhas.append(f"[{chave}]")
                for item in itens[:20]:
                    linhas.append(f"- {item}")
        nums = resumo.get("dados_numericos", [])
        if nums:
            linhas.append("[dados_numericos]")
            for item in nums[:20]:
                linhas.append(f"- {item}")
        pend = resumo.get("pendencias", [])
        if pend:
            linhas.append("[pendencias]")
            for item in pend[:10]:
                linhas.append(f"- {item}")
        linhas.append("")
    return "\n".join(linhas).strip()
