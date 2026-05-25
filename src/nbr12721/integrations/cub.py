"""Integracao CUB Sinduscon Norte PR para o pipeline NBR 12721."""
import io
import logging
import re
import urllib.request

from ..settings.config import (
    TIMEOUT_HTTP_SCRAPE,
    TIMEOUT_HTTP_DOWNLOAD,
    LIMITE_CHARS_CUB_TEXTO_COMPLETO,
)
from ..outputs.formatacao import formatar_brl

logger = logging.getLogger(__name__)

URL_PAGINA = "https://www.sinduscon-nortepr.com.br/documentos-pasta/cubs"
# URL de fallback: CUB mais recente conhecido (Janeiro/2026, publicado em Fev/2026)
URL_FALLBACK = (
    "https://cdn.prod.website-files.com/65dd079f4a204f5e248bde48/"
    "6989e713fc75525c1c421c66_2026_02_CUB.pdf"
)

__all__ = ["buscar_cub_sinduscon", "formatar_cub_contexto", "extrair_valores_cub"]

_TIPOS_CUB_LITERAL = [
    "R1-B", "R1-N", "R1-A", "R1-AL",
    "R4-B", "R4-N", "R4-A", "R4-AL",
    "PP-4", "PP-B", "PIS",
    "CSL-8", "CSL-16", "CAL-8",
    "GI", "GI-P", "GI-G",
]

_RESIDENCIAL_TRIPLO = (
    ("R-1", "R1"),
    ("PP-4", "PP4"),
    ("R-8", "R8"),
    ("R-16", "R16"),
)


def _parse_valor_cub_br(raw: str) -> float | None:
    try:
        return float(raw.replace(".", "").replace(" ", "").replace(",", "."))
    except ValueError:
        return None


def _parsear_linhas_residencial_tripla(texto: str) -> dict[str, float]:
    """Linha residencial: R-1 v1 ... R-1 v2 ... R-1 v3 -> R1-B, R1-N, R1-A."""
    valores: dict[str, float] = {}
    sufixos = ("B", "N", "A")
    for linha in texto.splitlines():
        linha_limpa = re.sub(r"\s+", " ", linha.strip())
        for rotulo, prefixo in _RESIDENCIAL_TRIPLO:
            nums = re.findall(
                rf"{re.escape(rotulo)}\s+([\d.,]+)",
                linha_limpa,
                re.IGNORECASE,
            )
            if len(nums) < 3:
                continue
            for sufixo, raw in zip(sufixos, nums[:3]):
                valor = _parse_valor_cub_br(raw)
                if valor is not None:
                    valores[f"{prefixo}-{sufixo}"] = valor
    return valores


def extrair_valores_cub(texto: str) -> dict[str, float]:
    """Parseia valores CUB do texto do PDF (testavel sem HTTP)."""
    valores: dict[str, float] = {}
    for tipo in _TIPOS_CUB_LITERAL:
        m = re.search(
            rf"\b{re.escape(tipo)}\b[:\s]+(?:R\$\s*)?(\d{{1,3}}(?:[.\s]\d{{3}})*,\d{{2}})",
            texto,
            re.IGNORECASE,
        )
        if m:
            valor = _parse_valor_cub_br(m.group(1))
            if valor is not None:
                valores[tipo] = valor
    valores.update(_parsear_linhas_residencial_tripla(texto))
    return valores


def buscar_cub_sinduscon():
    """Busca a tabela CUB mais atualizada do Sinduscon Norte PR.

    Fluxo:
      1. Faz scraping de https://www.sinduscon-nortepr.com.br/documentos-pasta/cubs
         para descobrir a URL do PDF mais recente (nao-desonerado).
      2. Baixa o PDF e extrai texto com pdfplumber.
      3. Parseia os valores CUB por tipo (R1-N, R4-N, etc.) via regex.
      4. Retorna dict {sindicato, mesAno, urlPdf, valores, textoCompleto} ou None.
    """
    logger.info("Buscando CUB Sinduscon Norte PR...")

    # --- 1. Descobrir URL do PDF mais recente ---
    url_pdf = None
    try:
        req = urllib.request.Request(URL_PAGINA, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_HTTP_SCRAPE) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        # Links de PDF na CDN do Webflow
        links = re.findall(
            r'https://cdn\.prod\.website-files\.com/[^\s"\'<>]+CUB[^\s"\'<>]*\.pdf',
            html, re.IGNORECASE
        )
        # Excluir versao desonerada
        normais = [l for l in links if "DES" not in l.upper().replace("%20", " ")]
        if normais:
            url_pdf = normais[0]
            logger.info("PDF encontrado na pagina: %s", url_pdf.split("/")[-1])
    except Exception as e:
        logger.warning("Nao foi possivel acessar pagina Sinduscon: %s", e)

    if not url_pdf:
        url_pdf = URL_FALLBACK
        logger.warning("Usando URL de fallback: %s", url_pdf.split("/")[-1])

    # --- 2. Download do PDF ---
    try:
        req = urllib.request.Request(url_pdf, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_HTTP_DOWNLOAD) as resp:
            pdf_bytes = resp.read()
        logger.info("PDF CUB baixado (%s KB)", len(pdf_bytes) // 1024)
    except Exception as e:
        logger.warning("Erro ao baixar PDF CUB: %s", e)
        return None

    # --- 3. Extrai texto com pdfplumber (texto + tabelas) ---
    texto = ""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for pg in pdf.pages:
                texto += (pg.extract_text() or "") + "\n"
                for tab in (pg.extract_tables() or []):
                    for row in tab:
                        if row:
                            texto += "  ".join(str(c or "") for c in row) + "\n"
    except Exception as e:
        logger.warning("Erro ao extrair texto do PDF CUB: %s", e)
        return None

    if not texto.strip():
        logger.error("PDF CUB sem texto extraivel")
        return None

    valores = extrair_valores_cub(texto)

    # --- 4. Mes/ano de referencia ---
    mes_ano = ""
    m = re.search(
        r'(janeiro|fevereiro|mar[cç]o|abril|maio|junho|julho|agosto'
        r'|setembro|outubro|novembro|dezembro)\s*[/,]?\s*(?:de\s+)?(\d{4})',
        texto, re.IGNORECASE
    )
    if m:
        mes_ano = f"{m.group(1).capitalize()}/{m.group(2)}"

    if not mes_ano:
        # Inferir pelo nome do arquivo: YYYY_MM_CUB.pdf => referencia = mes anterior
        arq = url_pdf.split("/")[-1]
        m2 = re.search(r'(\d{4})_(\d{2})_CUB', arq, re.IGNORECASE)
        if m2:
            meses = ["", "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
                     "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
            ano, pub = int(m2.group(1)), int(m2.group(2))
            ref = pub - 1 if pub > 1 else 12
            ano_ref = ano if pub > 1 else ano - 1
            mes_ano = f"{meses[ref]}/{ano_ref}"

    if valores:
        amostra = "; ".join(f"{t}=R${formatar_brl(v)}" for t, v in list(valores.items())[:4])
        logger.info("CUB %s: %s tipo(s) [%s]", mes_ano, len(valores), amostra)
    else:
        logger.warning(
            "CUB %s: valores nao parseados — texto bruto sera enviado ao LLM", mes_ano
        )

    return {
        "sindicato": "SINDUSCON NORTE PR",
        "mesAno": mes_ano,
        "urlPdf": url_pdf,
        "valores": valores,
        "textoCompleto": texto[:LIMITE_CHARS_CUB_TEXTO_COMPLETO],
    }

def formatar_cub_contexto(cub_info):
    """Formata o dict cub_info como texto para inclusao no prompt do Claude."""
    if not cub_info:
        return "(CUB nao disponivel — deixe valorCub=0 e registre em _dados_faltantes)"

    linhas = [
        f"Sindicato: {cub_info['sindicato']}",
        f"Mes de referencia: {cub_info['mesAno']}",
        f"Fonte: {cub_info['urlPdf']}",
    ]
    if cub_info["valores"]:
        linhas.append("Valores CUB (R$/m2):")
        for tipo, val in cub_info["valores"].items():
            linhas.append(f"  {tipo}: R$ {formatar_brl(val)}")
        linhas.append("")
        linhas.append("Instrucao: preencha quadro3.sindicato, quadro3.mesCub e quadro3.valorCub")
        linhas.append("com o tipo CUB que melhor corresponde ao projeto identificado nos documentos.")
        linhas.append("Para residencial multifamiliar padrao normal use R1-N ou R4-N conforme o porte.")
    else:
        linhas.append("Texto do documento CUB (extraia os valores diretamente):")
        linhas.append(cub_info["textoCompleto"])

    return "\n".join(linhas)
