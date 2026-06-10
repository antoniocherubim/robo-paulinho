"""Extracao e reducao textual de PDFs para o pipeline NBR 12721."""
import gc
import logging
import os
import re
import sys
import tempfile
import time

from ..extraction.deterministic_extraction.patterns import (
    RE_CIDADE_UF_EVIDENCIA,
    RE_CNPJ_ROTULADO,
    RE_LINHA_CNPJ,
    linha_contem_cnpj,
)
from ..settings.config import (
    LIMITE_CHARS_LOTE,
    LIMITE_CHARS_TEXTO_FILTRADO,
    OCR_DPI,
    OCR_GRAYSCALE,
    OCR_MAX_IMAGE_PIXELS,
    OCR_MIN_CHARS_PAGINA,
    OCR_TIMEOUT_SEGUNDOS,
    OCR_USAR_ARQUIVOS_TEMP,
    POPPLER_PATH,
    TESSERACT_CMD,
    TESSERACT_LANG,
)

logger = logging.getLogger(__name__)

__all__ = [
    "extrair_evidencias_acabamentos_equipamentos",
    "extrair_texto_pdf",
    "iterar_texto_pdf_paginas",
    "MARCADOR_EVIDENCIAS_VI_VIII",
    "normalizar_ocr",
    "prefiltrar_texto",
    "separar_documentos",
    "dividir_lotes_documentos",
]


def _resolver_poppler_path():
    if POPPLER_PATH:
        logger.debug("Poppler configurado via POPPLER_PATH: %s", POPPLER_PATH)
        return POPPLER_PATH
    if sys.platform == "win32":
        for p in [r"C:\poppler\Library\bin", r"C:\poppler\bin",
                  r"C:\Program Files\poppler\Library\bin",
                  r"C:\Program Files\poppler\bin"]:
            if os.path.exists(os.path.join(p, "pdftoppm.exe")):
                logger.debug("Poppler detectado automaticamente: %s", p)
                return p
    return None


def _fechar_imagem(img):
    try:
        img.close()
    except Exception:
        pass


# OCR regional: crops do carimbo em pranchas grandes (fallback ou atalho)
OCR_REGIONAL_DPI = 80
OCR_REGIONAL_TIMEOUT = 30
OCR_PAGINA_GRANDE_AREA = 1_500_000  # width*height em pontos PDF (pdfplumber)

_REGIOES_OCR = (
    ("direita", 0.78, 0.0, 1.0, 1.0),
    ("inferior_direita", 0.70, 0.55, 1.0, 1.0),
    ("inferior", 0.0, 0.70, 1.0, 1.0),
)

_RE_CORPO_PROJETO_OCR = re.compile(
    r"APTOS?|APARTAMENTOS?|PAVIMENTOS?|PAV\.?\s*TIPO|"
    r"TOTAL\s+DE\s+VAGAS|\d+\s*[xX×]\s*\d+\s*APTOS",
    re.IGNORECASE,
)


def _ocr_texto_tem_corpo_projeto(texto: str) -> bool:
    """Indica se o OCR full-page trouxe unidades/pavimentos/vagas."""
    return bool(_RE_CORPO_PROJETO_OCR.search(texto))


def _concatenar_textos_ocr(*partes: str) -> str:
    blocos = [p.strip() for p in partes if p and p.strip()]
    return "\n\n".join(blocos)


def _pagina_muito_grande(pagina) -> bool:
    try:
        return pagina.width * pagina.height > OCR_PAGINA_GRANDE_AREA
    except Exception:
        return False


def _renderizar_pagina(convert_from_path, caminho, indice, dpi, poppler_path):
    imagens = convert_from_path(
        caminho,
        dpi=dpi,
        first_page=indice,
        last_page=indice,
        poppler_path=poppler_path,
        thread_count=1,
        grayscale=OCR_GRAYSCALE,
    )
    if not imagens:
        return None
    return imagens[0]


def _ocr_crop(img, crop_box, pytesseract, timeout):
    crop = None
    try:
        crop = img.crop(crop_box)
        return pytesseract.image_to_string(
            crop,
            lang=TESSERACT_LANG,
            timeout=timeout,
        )
    finally:
        _fechar_imagem(crop)


def _ocr_regioes_pagina(convert_from_path, pytesseract, caminho, indice, poppler_path):
    """OCR em crops fixos (carimbo lateral/inferior) para pranchas grandes."""
    nome = os.path.basename(caminho)
    logger.info(
        "%s p.%s: iniciando OCR regional (dpi=%s, timeout=%ss/regiao)",
        nome,
        indice,
        OCR_REGIONAL_DPI,
        OCR_REGIONAL_TIMEOUT,
    )
    img = None
    partes: list[str] = []
    try:
        img = _renderizar_pagina(
            convert_from_path, caminho, indice, OCR_REGIONAL_DPI, poppler_path
        )
        if img is None:
            logger.warning("%s p.%s: OCR regional sem imagem renderizada", nome, indice)
            return ""

        largura, altura = img.size
        for nome_regiao, x0f, y0f, x1f, y1f in _REGIOES_OCR:
            box = (
                int(largura * x0f),
                int(altura * y0f),
                int(largura * x1f),
                int(altura * y1f),
            )
            cw, ch = box[2] - box[0], box[3] - box[1]
            logger.info(
                "%s p.%s: OCR regional regiao=%s crop=%sx%s",
                nome,
                indice,
                nome_regiao,
                cw,
                ch,
            )
            try:
                texto_regiao = _ocr_crop(
                    img, box, pytesseract, OCR_REGIONAL_TIMEOUT
                ).strip()
                n_chars = len(texto_regiao)
                logger.info(
                    "%s p.%s: OCR regional regiao=%s chars=%s",
                    nome,
                    indice,
                    nome_regiao,
                    n_chars,
                )
                if texto_regiao:
                    partes.append(f"OCR_REGIAO: {nome_regiao}\n{texto_regiao}")
            except Exception as e:
                logger.warning(
                    "%s p.%s: OCR regional regiao=%s falhou: %s",
                    nome,
                    indice,
                    nome_regiao,
                    e,
                )
            finally:
                gc.collect()
        return "\n\n".join(partes)
    finally:
        _fechar_imagem(img)
        gc.collect()


def _ocr_pagina_com_arquivo_temp(convert_from_path, pytesseract, caminho, indice, poppler_path):
    with tempfile.TemporaryDirectory(prefix="nbr12721_ocr_") as tmpdir:
        caminhos = convert_from_path(
            caminho,
            dpi=OCR_DPI,
            first_page=indice,
            last_page=indice,
            poppler_path=poppler_path,
            thread_count=1,
            fmt="jpeg",
            output_folder=tmpdir,
            paths_only=True,
            grayscale=OCR_GRAYSCALE,
            jpegopt={"quality": 85, "progressive": False, "optimize": True},
        )
        texto = ""
        for caminho_img in caminhos:
            texto += pytesseract.image_to_string(
                caminho_img,
                lang=TESSERACT_LANG,
                timeout=OCR_TIMEOUT_SEGUNDOS,
            ) + "\n"
        return texto


def _ocr_pagina_em_memoria(convert_from_path, pytesseract, caminho, indice, poppler_path):
    imagens = []
    try:
        imagens = convert_from_path(
            caminho,
            dpi=OCR_DPI,
            first_page=indice,
            last_page=indice,
            poppler_path=poppler_path,
            thread_count=1,
            grayscale=OCR_GRAYSCALE,
        )
        texto = ""
        for img in imagens:
            try:
                texto += pytesseract.image_to_string(
                    img,
                    lang=TESSERACT_LANG,
                    timeout=OCR_TIMEOUT_SEGUNDOS,
                ) + "\n"
            finally:
                _fechar_imagem(img)
        return texto
    finally:
        for img in imagens:
            _fechar_imagem(img)
        gc.collect()


def iterar_texto_pdf_paginas(caminho):
    """Extrai texto de um PDF pagina a pagina, usando OCR somente quando necessario."""
    inicio_pdf = time.monotonic()
    nome = os.path.basename(caminho)
    poppler_path = _resolver_poppler_path()
    total_paginas = 0
    paginas_emitidas = 0
    paginas_nativas = 0
    paginas_ocr = 0
    paginas_parciais = 0
    paginas_sem_texto = 0

    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber nao disponivel; instale as dependencias do requirements.txt")
        return

    try:
        import PIL.Image
        PIL.Image.MAX_IMAGE_PIXELS = OCR_MAX_IMAGE_PIXELS
        from pdf2image import convert_from_path
        import pytesseract

        if TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
        ocr_disponivel = True
        logger.debug(
            "%s: OCR disponivel | dpi=%s | lang=%s | temp_files=%s | grayscale=%s | timeout=%ss",
            nome,
            OCR_DPI,
            TESSERACT_LANG,
            OCR_USAR_ARQUIVOS_TEMP,
            OCR_GRAYSCALE,
            OCR_TIMEOUT_SEGUNDOS,
        )
    except ImportError:
        convert_from_path = None
        pytesseract = None
        ocr_disponivel = False
        logger.warning("%s: OCR indisponivel; paginas rasterizadas podem ficar sem texto", nome)

    try:
        with pdfplumber.open(caminho) as pdf:
            total_paginas = len(pdf.pages)
            logger.info("%s: PDF aberto com %s pagina(s)", nome, total_paginas)
            for indice, pagina in enumerate(pdf.pages, start=1):
                texto_nativo = ""
                try:
                    texto_nativo = (pagina.extract_text() or "").strip()
                except Exception as e:
                    logger.warning("%s pagina %s: falha no texto nativo: %s", nome, indice, e)

                if len(texto_nativo) >= OCR_MIN_CHARS_PAGINA:
                    paginas_emitidas += 1
                    paginas_nativas += 1
                    logger.info(
                        "%s p.%s/%s: %s chars extraidos via texto nativo",
                        nome,
                        indice,
                        total_paginas,
                        len(texto_nativo),
                    )
                    yield indice, texto_nativo
                    continue

                if not ocr_disponivel:
                    if texto_nativo:
                        paginas_emitidas += 1
                        paginas_parciais += 1
                        logger.info(
                            "%s p.%s/%s: %s chars parciais; OCR indisponivel",
                            nome,
                            indice,
                            total_paginas,
                            len(texto_nativo),
                        )
                        yield indice, texto_nativo
                    else:
                        paginas_sem_texto += 1
                        logger.warning("%s p.%s/%s: sem texto e OCR indisponivel", nome, indice, total_paginas)
                    continue

                texto_full = ""
                texto_regional = ""
                inicio_ocr = time.monotonic()
                pagina_grande = _pagina_muito_grande(pagina)
                try:
                    logger.info(
                        "%s p.%s/%s: texto nativo insuficiente (%s chars); iniciando OCR",
                        nome,
                        indice,
                        total_paginas,
                        len(texto_nativo),
                    )
                    try:
                        if OCR_USAR_ARQUIVOS_TEMP:
                            texto_full = _ocr_pagina_com_arquivo_temp(
                                convert_from_path,
                                pytesseract,
                                caminho,
                                indice,
                                poppler_path,
                            )
                        else:
                            texto_full = _ocr_pagina_em_memoria(
                                convert_from_path,
                                pytesseract,
                                caminho,
                                indice,
                                poppler_path,
                            )
                    except Exception as e:
                        logger.warning(
                            "%s p.%s/%s: OCR full-page falhou: %s",
                            nome,
                            indice,
                            total_paginas,
                            e,
                        )

                    precisa_regional = (
                        pagina_grande
                        or not texto_full.strip()
                        or not _ocr_texto_tem_corpo_projeto(texto_full)
                    )
                    if precisa_regional:
                        motivo = (
                            "pagina grande (complemento carimbo)"
                            if pagina_grande
                            else (
                                "full-page sem corpo do projeto"
                                if texto_full.strip()
                                else "full-page vazio ou falhou"
                            )
                        )
                        logger.info(
                            "%s p.%s/%s: OCR regional como complemento (%s)",
                            nome,
                            indice,
                            total_paginas,
                            motivo,
                        )
                        try:
                            texto_regional = _ocr_regioes_pagina(
                                convert_from_path,
                                pytesseract,
                                caminho,
                                indice,
                                poppler_path,
                            )
                        except Exception as e2:
                            logger.warning(
                                "%s p.%s/%s: OCR regional falhou: %s",
                                nome,
                                indice,
                                total_paginas,
                                e2,
                            )
                finally:
                    gc.collect()

                texto_ocr = _concatenar_textos_ocr(texto_full, texto_regional)
                texto = _concatenar_textos_ocr(texto_ocr, texto_nativo)
                if texto.strip():
                    tem_full = bool(texto_full.strip())
                    tem_regional = bool(texto_regional.strip())
                    if tem_full and tem_regional:
                        origem = "OCR+regional"
                    elif tem_regional and "OCR_REGIAO:" in texto_regional:
                        origem = "OCR_regional"
                    elif tem_full or texto_ocr.strip():
                        origem = "OCR"
                    else:
                        origem = "parcial"
                    paginas_emitidas += 1
                    if texto_ocr.strip():
                        paginas_ocr += 1
                    else:
                        paginas_parciais += 1
                    logger.info(
                        "%s p.%s/%s: %s chars extraidos via %s (%.2fs)",
                        nome,
                        indice,
                        total_paginas,
                        len(texto),
                        origem,
                        time.monotonic() - inicio_ocr,
                    )
                    yield indice, texto
                else:
                    paginas_sem_texto += 1
                    logger.warning("%s p.%s/%s: sem texto apos OCR", nome, indice, total_paginas)
    except Exception as e:
        logger.error("%s: falha ao abrir/processar PDF: %s", nome, e)
    finally:
        logger.info(
            "%s: processamento finalizado | paginas=%s | emitidas=%s | nativo=%s | ocr=%s | parcial=%s | sem_texto=%s | %.2fs",
            nome,
            total_paginas,
            paginas_emitidas,
            paginas_nativas,
            paginas_ocr,
            paginas_parciais,
            paginas_sem_texto,
            time.monotonic() - inicio_pdf,
        )


def extrair_texto_pdf(caminho):
    partes = [texto for _, texto in iterar_texto_pdf_paginas(caminho)]
    return "\n".join(partes)


def normalizar_ocr(texto):
    """
    Corrige erros sistematicos comuns do Tesseract em portugues:
    - Cedilhas mal interpretadas (PROJEGAO -> PROJEÇÃO)
    - Til faltando (CONSTRUGAO -> CONSTRUÇÃO)
    - Acentos perdidos em palavras tecnicas
    - Espacos quebrados, abreviacoes inconsistentes
    """
    import re

    # Mapa de correcoes diretas (substituicao palavra por palavra)
    # Lado esquerdo: erro comum do OCR; lado direito: forma correta
    CORRECOES_DIRETAS = {
        # G -> Ç (erro classico do Tesseract)
        r"\bPROJEGAO\b": "PROJEÇÃO",
        r"\bPROJEGOES\b": "PROJEÇÕES",
        r"\bCONSTRUGAO\b": "CONSTRUÇÃO",
        r"\bCONSTRUGOES\b": "CONSTRUÇÕES",
        r"\bCIRCULAGAO\b": "CIRCULAÇÃO",
        r"\bCIRCULAGOES\b": "CIRCULAÇÕES",
        r"\bEDIFICAGAO\b": "EDIFICAÇÃO",
        r"\bEDIFICAGOES\b": "EDIFICAÇÕES",
        r"\bAPROVAGAO\b": "APROVAÇÃO",
        r"\bINSCRIGAO\b": "INSCRIÇÃO",
        r"\bOCUPAGAO\b": "OCUPAÇÃO",
        r"\bINSTALAGAO\b": "INSTALAÇÃO",
        r"\bINSTALAGOES\b": "INSTALAÇÕES",
        r"\bILUMINAGAO\b": "ILUMINAÇÃO",
        r"\bVENTILAGAO\b": "VENTILAÇÃO",
        r"\bPRESSURIZAGAO\b": "PRESSURIZAÇÃO",
        r"\bAGAO\b": "AÇÃO",
        r"\bGAO\b": "ÇÃO",
        # Acentos perdidos em palavras tecnicas
        r"\bAREA\b": "ÁREA",
        r"\bAREAS\b": "ÁREAS",
        r"\bTERREO\b": "TÉRREO",
        r"\bSUBSOLO\b": "SUBSOLO",
        r"\bPAVIMENTO\b": "PAVIMENTO",
        r"\bMAQUINAS\b": "MÁQUINAS",
        r"\bD AGUA\b": "D'ÁGUA",
        r"\bDAGUA\b": "D'ÁGUA",
        r"\bAGUA\b": "ÁGUA",
        r"\bGAS\b": "GÁS",
        r"\bMAO DE OBRA\b": "MÃO DE OBRA",
        r"\bMAOOBRA\b": "MÃO DE OBRA",
        r"\bRESPONSAVEL\b": "RESPONSÁVEL",
        r"\bTECNICO\b": "TÉCNICO",
        # Abreviacoes
        r"\bPAV\b(?!\.)": "PAV.",
        r"\bN[Iİ]VEL\b": "NÍVEL",
        # Quebras comuns
        r"M\s*[2²]\b": "m²",
        r"\bM2\b": "m²",
    }

    for padrao, correto in CORRECOES_DIRETAS.items():
        texto = re.sub(padrao, correto, texto, flags=re.IGNORECASE)

    # Normalizacao de whitespace
    texto = re.sub(r"[ \t]{2,}", " ", texto)        # multiplos espacos -> um
    texto = re.sub(r"\n{3,}", "\n\n", texto)        # multiplas linhas em branco
    texto = re.sub(r" +\n", "\n", texto)            # espacos antes de quebra
    texto = re.sub(r"\n +", "\n", texto)            # espacos depois de quebra

    return texto


def _extrair_evidencias_nbr(texto, limite_linhas=100):
    """Seleciona linhas pequenas e densas que costumam alimentar campos da NBR."""
    import re

    padrao_candidato = re.compile(
        r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b|"
        r"\bCNPJ\b|\bCREA\b|\bCAU\b|\bART\b|\bRRT\b|"
        r"\balvar[aá]\b|\bprocesso\b|\baprova[cç][aã]o\b|"
        rf"{RE_CIDADE_UF_EVIDENCIA.pattern}|"
        r"\b\d+\s*APTOS?\b|\bAPTO\s*\d+\b|\bUNIDADES?\b|"
        r"\bTOTAL\s+DE\s+VAGAS\b|\bVAGAS?\b|\bPNE\b|"
        r"\bTERRENO\b|\bLOCAL\s+DA\s+OBRA\b|\bDATA\s+DO\s+PROJETO\b|"
        r"\bPAV\.?\s*(?:TIPO|N[IÍ]VEL|T[EÉ]RREO)\b|"
        r"\bTORRE\b|\bBARRILETE\b|\bCOBERTURA\b|"
        r"\b[AÁ]REA\b|\bTOTAL\b|\bCOBERTO\b|\bDESCOBERTO\b|"
        r"\bRESIDENCIAL\b|\bMULTIFAMILIAR\b|\bVERTICAL\b|"
        r"\bZONEAMENTO\b|\bTAXA\s+DE\s+OCUPA[CÇ][AÃ]O\b|"
        r"\bSINDUSCON\b|\bCUB\b|\bR\$\s*[\d.,]+",
        re.IGNORECASE,
    )
    padrao_baixo_valor = re.compile(
        r"\b(?:JANELA|PORTA|PORTA[-\s]?JANELA|PORTAJANELA|PORTAMADEIRA|"
        r"ESQUADRIA|NOMENCL|VIDRO|VENEZIANA|CORRER|BASCULANTE|FIXO)\b",
        re.IGNORECASE,
    )

    def pontuar(linha):
        score = 0
        if RE_CNPJ_ROTULADO.search(linha):
            score += 95
        elif RE_LINHA_CNPJ.search(linha):
            score += 90
        regras = [
            (r"\bCREA\b|\bCAU\b|\bART\b|\bRRT\b|RESPONS[AÁ]VEL T[EÉ]CNICO", 80),
            (r"\bALVAR[AÁ]\b|\bPROCESSO\s+APROVA", 85),
            (rf"\bLOCAL\s+DA\s+OBRA\b|\bSITUADO\b|{RE_CIDADE_UF_EVIDENCIA.pattern}", 85),
            (r"\bTERRENO\s*:\s*[\d.,]+\s*M", 80),
            (r"\bRESIDENCIAL\b.*\bMULTIFAMILIAR\b|\bVERTICAL\b|\bRMV\b", 70),
            (r"\bPAV\.?\s*TIPO\b.*\bTORRE\b|\bTIPOS?\b.*\bTORRE\b", 75),
            (r"\b\d+\s*APTOS?\b|\bAPARTAMENTOS?\b|\bAPTO\s*\d+", 80),
            (r"\bTOTAL\s+DE\s+VAGAS\b|\bVAGAS\s+COMUNS\b|\bVAGAS\s+DUPLAS\b|\bVAGAS\s+PNE\b", 90),
            (r"\bPAV\.?\s*N[IÍ]VEL\b|\bPAV\.?\s*T[EÉ]RREO\b", 55),
            (r"\bTOTAL\s+(?:COBERTO|DESCOBERTO)|\b[AÁ]REA\s+TOTAL\b", 65),
            (r"\bDATA\s+DO\s+PROJETO\b|\b\d{2}/\d{2}/\d{4}\b|\b\d{2}\s+DE\s+\w+\s+DE\s+\d{4}\b", 55),
            (r"\bSINDUSCON\b|\bCUB\b|\bR\$\s*[\d.,]+", 60),
        ]
        for padrao, valor in regras:
            if re.search(padrao, linha, re.IGNORECASE):
                score += valor
        if padrao_baixo_valor.search(linha):
            score -= 75
        if re.search(r"\d{14,}", linha) and not RE_CNPJ_ROTULADO.search(linha):
            score -= 15
        if len(re.findall(r"\b[a-zA-ZÀ-ü]{4,}\b", linha)) < 2:
            score -= 20
        if len(re.sub(r"[a-zA-ZÀ-ü\s]", "", linha)) / max(len(linha), 1) > 0.55:
            score -= 30
        return score

    doc_atual = ""
    candidatos = []
    vistos = set()
    ordem = 0

    for linha in texto.splitlines():
        ordem += 1
        linha = re.sub(r"[ \t]+", " ", linha.strip())
        if not linha:
            continue

        m_doc = re.match(r"DOCUMENTO:\s*(.+)$", linha, re.IGNORECASE)
        if m_doc:
            doc_atual = m_doc.group(1).strip()
            continue

        if not (padrao_candidato.search(linha) or linha_contem_cnpj(linha)):
            continue

        score = pontuar(linha)
        if score < 45:
            continue

        # Remove ruido visual muito longo, mas preserva o trecho informativo da linha.
        linha = re.sub(r"([A-ZÀ-Ü])\1{3,}", r"\1", linha)
        linha = re.sub(r"\b(\S{2,})(\s+\1){2,}\b", r"\1", linha)
        if len(linha) > 280:
            trechos = re.split(r"\s{2,}|\s+\|\s+", linha)
            trechos_relevantes = [t.strip() for t in trechos if pontuar(t) >= 45]
            linha = " | ".join(trechos_relevantes[:4]) or linha[:280]

        if len(linha) > 320:
            linha = linha[:317].rstrip() + "..."

        item = f"[{doc_atual}] {linha}" if doc_atual else linha
        chave = re.sub(r"\d+", "#", item.lower())
        chave = re.sub(r"\s+", " ", chave).strip()
        if chave in vistos:
            continue

        vistos.add(chave)
        candidatos.append((score, ordem, item))

    candidatos.sort(key=lambda item: (-item[0], item[1]))
    evidencias = [item for _, _, item in candidatos[:limite_linhas]]
    return "\n".join(evidencias)


MARCADOR_EVIDENCIAS_VI_VIII = "EVIDENCIAS QUADROS VI-VIII:"

_PADRAO_VI_VIII = re.compile(
    r"\b(?:ELEVADOR\w*|BOMBA|PRESSUR|DUTO|ESCADA|BARRILETE|RESERVAT|"
    r"GÁS|GAS|MEDIDOR|"
    r"HALL|HALLSOCIAL|HALL\s+SOCIAL|GOURMET|SACADA|CIRC|DML|LAZER|"
    r"PISO|PAREDE|TETO|PINTURA|PORCELANATO|CERÂMICA|CERAMICA|CIMENTADO|"
    r"GRAFITE|ALUMÍNIO|ALUMINIO|VIDRO|MADEIRA|PORTA|JANELA|ACABAMENTO)\b",
    re.IGNORECASE,
)


def _linha_ocr_ruim(linha: str) -> bool:
    if len(linha) <= 24 and _PADRAO_VI_VIII.search(linha):
        return False
    palavras_longas = re.findall(r"\b[a-zA-ZÀ-ü]{4,}\b", linha)
    if len(palavras_longas) >= 2:
        return False
    nao_alfa = len(re.sub(r"[a-zA-ZÀ-ü\s]", "", linha))
    return nao_alfa / max(len(linha), 1) > 0.55


def extrair_evidencias_acabamentos_equipamentos(textos: str, limite_linhas: int = 80) -> str:
    """Seleciona linhas uteis para Quadros VI-VIII (patch LLM v2)."""
    doc_atual = ""
    candidatos: list[tuple[int, str]] = []
    vistos: set[str] = set()
    ordem = 0

    for linha in textos.splitlines():
        ordem += 1
        linha = re.sub(r"[ \t]+", " ", linha.strip())
        if not linha:
            continue

        m_doc = re.match(r"DOCUMENTO:\s*(.+)$", linha, re.IGNORECASE)
        if m_doc:
            doc_atual = m_doc.group(1).strip()
            continue

        if linha.startswith(MARCADOR_EVIDENCIAS_VI_VIII):
            continue
        if not _PADRAO_VI_VIII.search(linha):
            continue
        if _linha_ocr_ruim(linha):
            continue

        linha = re.sub(r"([A-ZÀ-Ü])\1{3,}", r"\1", linha)
        if len(linha) > 320:
            linha = linha[:317].rstrip() + "..."

        item = f"[{doc_atual}] {linha}" if doc_atual else linha
        chave = re.sub(r"\d+", "#", item.lower())
        chave = re.sub(r"\s+", " ", chave).strip()
        if chave in vistos:
            continue

        vistos.add(chave)
        candidatos.append((ordem, item))

    if not candidatos:
        return ""

    linhas = [item for _, item in candidatos[:limite_linhas]]
    return f"{MARCADOR_EVIDENCIAS_VI_VIII}\n" + "\n".join(linhas)


def _combinar_evidencias_e_corpo(evidencias, corpo, limite_chars):
    if not evidencias:
        return corpo[:limite_chars].rstrip()

    cab_evidencias = "EVIDENCIAS CRITICAS EXTRAIDAS DO TEXTO ORIGINAL:\n"
    cab_corpo = "\n\nTEXTO FILTRADO COMPLEMENTAR:\n"
    prefixo = cab_evidencias + evidencias.strip() + cab_corpo
    restante = max(0, limite_chars - len(prefixo))
    if restante <= 0:
        return (cab_evidencias + evidencias.strip())[:limite_chars].rstrip()

    if len(corpo) <= restante:
        return prefixo + corpo.strip()

    corte = corpo.rfind("\n\n", 0, restante)
    if corte < restante * 0.6:
        corte = restante
    return prefixo + corpo[:corte].rstrip()


def prefiltrar_texto(texto, verbose=True):
    """
    Pre-filtragem agressiva em camadas para reduzir volume antes de enviar ao Claude.

    Camada 1: Limpeza estrutural
      - Remove marcadores (cid:NN) de PDF (glifos nao mapeados)
      - Remove linhas duplicadas consecutivas (cabecalhos/rodapes repetidos)
      - Remove linhas com apenas numeros de pagina
      - Colapsa espacos e quebras multiplas
      - Remove linhas de cotas de planta (numeros + simbolos sem texto)
      - Remove linhas de tabelas de esquadrias (codigo + dimensoes repetidas)

    Camada 2: Filtragem por relevancia semantica
      - Divide o texto em blocos (separados por linhas em branco ou marcadores)
      - Mantem apenas blocos com palavras-chave da NBR 12721 + texto coerente
      - Sempre preserva blocos com padroes especiais (CNPJ, CREA, ART, valores)

    Camada 3: Deduplicacao final (normalizando numeros)

    Retorna o texto filtrado.
    """
    import re

    if not texto or not texto.strip():
        return texto

    tam_original = len(texto)

    # ===== Camada 0: Normalizacao de OCR =====
    # Corrige erros sistematicos do Tesseract antes de qualquer filtragem
    texto = normalizar_ocr(texto)
    evidencias_criticas = _extrair_evidencias_nbr(texto)

    # ===== Camada 0.5: Remocao de sequencias repetidas (ruido grafico) =====
    # Caracteres alfabeticos repetidos 4+ vezes (SSSSSS, KKKKKK, aaaa)
    texto = re.sub(r"([a-zA-Z])\1{3,}", " ", texto)
    # Tokens repetidos 3+ vezes (vaga vaga vaga, Naga Naga Naga, 240x480 240x480)
    texto = re.sub(r"\b(\S{2,})(\s+\1){2,}\b", r"\1", texto)
    # Cotas em sequencia tipo "240x480 240x480 240x480"
    texto = re.sub(r"(\d+\s*[xX×]\s*\d+\s*){2,}", "", texto)

    # Palavras-chave de relevancia para NBR 12721
    KEYWORDS_RELEVANTES = {
        # Identificacao
        "incorporador", "incorporadora", "empreendedor", "construtora", "spe",
        "cnpj", "cpf", "rg", "inscricao", "inscrição", "proprietario", "proprietário",
        # Responsavel tecnico
        "responsavel", "responsável", "tecnico", "técnico", "engenheiro", "engenheira",
        "arquiteto", "arquiteta", "crea", "cau", "art", "rrt", "anotacao", "anotação",
        # Edificio
        "edificio", "edifício", "residencial", "comercial", "empreendimento",
        "condominio", "condomínio", "predio", "prédio", "torre", "bloco",
        # Localizacao
        "endereco", "endereço", "rua", "avenida", "alameda", "travessa",
        "quadra", "lote", "chacara", "chácara", "terreno", "matricula", "matrícula",
        "fazenda", "ribeirao", "ribeirão", "situado", "localizado",
        # Areas e medidas (mas com texto, nao so numeros)
        "metragem", "privativ", "comum", "subsolo", "terreo", "térreo",
        "cobertura", "pilotis", "mezanino", "garagem", "permeavel", "permeável",
        # Unidades
        "unidade", "apartamento", "apto", "loja", "vaga", "dormitorio",
        "dormitório", "quarto", "suite", "suíte",
        # Pavimentos especiais
        "barrilete", "guarita", "portaria", "circulacao", "circulação",
        # Custos
        "cub", "sinduscon", "custo", "preco", "preço", "valor", "real", "reais",
        "material", "construcao", "construção", "fundacao", "fundação",
        "elevador", "fogao", "fogão", "aquecedor", "bomba", "recalque",
        "playground", "urbanizacao", "urbanização", "ajardinamento",
        "instalacao", "instalação", "imposto", "projeto", "arquitetonico",
        "arquitetônico", "estrutural", "construtor", "bdi", "remuneracao",
        "remuneração",
        # Acabamentos
        "acabamento", "porcelanato", "ceramica", "cerâmica", "granito",
        "marmore", "mármore", "laminado", "vinilico", "vinílico", "pintura",
        "textura", "azulejo", "gesso", "forro", "revestimento",
        # Equipamentos
        "interfone", "raios", "cisterna", "gerador", "alarme", "incendio",
        "incêndio", "pressurizacao", "pressurização", "sprinkler",
        # Documentacao
        "alvara", "alvará", "licenca", "licença", "aprovacao", "aprovação",
        "habite", "registro", "cartorio", "cartório", "memorial",
        "descritivo", "abnt", "nbr",
        # Aprovacao
        "zoneamento", "coeficiente", "aproveitamento", "ocupacao", "ocupação",
        "permeabilidade", "recuo", "afastamento", "gabarito", "prefeitura",
        # Datas
        "janeiro", "fevereiro", "marco", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
        # Vocabulario arquitetonico expandido (areas comuns/lazer/ambientes)
        "hall", "circulacao", "circulação", "rampa", "escada", "shaft",
        "deposito", "depósito", "gourmet", "lazer", "academia", "piscina",
        "varanda", "sacada", "patio", "pátio", "quadra", "espaco", "espaço",
        "salao", "salão", "festas", "churrasqueira", "brinquedoteca",
        "fitness", "spa", "sauna", "coworking", "estacionamento",
        "subestacao", "subestação", "lixeira", "compostagem", "playground",
        "permeavel", "permeável", "jardim", "horta", "pet", "bicicletario",
        "bicicletário", "cobertura", "barrilete", "casamaquinas",
    }

    # Codigos de esquadrias (lixo de plantas) - detecta em qualquer posicao
    # Aceita variantes como "PORTAJANELA", "PORTAMADEIRA", "JANELAFERRO" (sem espaco)
    PADRAO_ESQUADRIA = re.compile(
        r"\b(?:JANELA|JANELAFERRO|PORTA[-\s]?JANELA|PORTAJANELA|PORTAMADEIRA|"
        r"PORTA\s*ALUM(?:Í|I)NIO|VENEZIANA\s+ALUM)\b",
        re.IGNORECASE
    )

    # Tabelas de cotas/dimensoes (240x480, sequencia de numeros grandes, etc)
    PADRAO_COTAS = re.compile(r"\d+\s*[xX×]\s*\d+|(?:\d{3,}[.,]?\d*\s+){3,}")

    # Codigos de profissionais sem espaco (ARQUITETOEURBANISTA, etc)
    # Nao remove tudo, mas marca como "low-value" se predominante
    PADRAO_CODIGO_PROFISSIONAL = re.compile(
        r"ARQUITETOEURBANISTA|ENGENHEIROCIVIL|ENGENHEIRACIVIL|"
        r"CAUA\d+|CREAPR-?\d+",
        re.IGNORECASE
    )

    # ===== Camada 1: Limpeza estrutural =====
    # 1a. Remover (cid:NN) - glifos nao mapeados
    texto = re.sub(r"\(cid:\d+\)", " ", texto)
    # Colapsar espacos resultantes
    texto = re.sub(r"[ \t]+", " ", texto)

    linhas = texto.split("\n")
    linhas_limpas = []
    linha_anterior = None
    contador_repeticoes = 0

    for linha in linhas:
        linha_strip = linha.strip()

        # Pular linhas vazias multiplas
        if not linha_strip:
            if linhas_limpas and linhas_limpas[-1] == "":
                continue
            linhas_limpas.append("")
            continue

        # Pular numeros de pagina isolados
        if re.match(r"^[\s\-\*]*(?:p[áa]g(?:ina)?\.?\s*)?\d{1,3}\s*(?:/\s*\d{1,3})?[\s\-\*]*$", linha_strip, re.IGNORECASE):
            continue

        # Pular linhas com so simbolos/separadores
        if re.match(r"^[\-=_\*\.\s\|\+]+$", linha_strip):
            continue

        # Pular linhas curtas demais (menos de 4 caracteres uteis)
        chars_uteis = re.sub(r"[^\wÀ-ü]", "", linha_strip)
        if len(chars_uteis) < 4:
            continue

        # Pular linhas de tabela de esquadrias (qualquer posicao)
        if PADRAO_ESQUADRIA.search(linha_strip):
            continue

        # Pular linhas com cotas tipo "240x480" ou sequencias de 3+ numeros grandes
        if PADRAO_COTAS.search(linha_strip):
            # A nao ser que tenha texto significativo (palavras de 5+ letras)
            palavras_significativas = re.findall(r"\b[a-zA-ZÀ-ü]{5,}\b", linha_strip)
            if len(palavras_significativas) < 2:
                continue

        # Pular linhas que sao majoritariamente numeros e simbolos (cotas de planta)
        # (mais de 55% nao-alfabetico = provavelmente cota)
        total = len(linha_strip)
        nao_alfa = len(re.sub(r"[a-zA-ZÀ-ü\s]", "", linha_strip))
        if total > 8 and nao_alfa / total > 0.5:
            # Checa se nao tem palavra-chave importante antes de descartar
            tem_kw = linha_contem_cnpj(linha_strip) or any(
                kw in linha_strip.lower()
                for kw in ("cpf", "crea", "cau", "art", "alvara", "alvará", "r$")
            )
            if not tem_kw:
                continue

        # Pular linhas com strings tipo "JO1", "PM3", "PJO5" isoladas (codigos de planta)
        if re.match(r"^(?:[A-Z]{1,4}\d{1,3}\s*){2,}$", linha_strip):
            continue

        # Pular linhas que sao "fragmento de planta" - poucas palavras com simbolos
        # tipo: "— A = 260.5 8, | pt" ou "4 |) g 15,08 M2 420 150 256 1!"
        palavras_reais = re.findall(r"\b[a-zA-ZÀ-ü]{4,}\b", linha_strip)
        if len(linha_strip) > 15 and len(palavras_reais) < 2:
            # Se nao tem ao menos 2 palavras com 4+ letras, eh provavelmente fragmento
            tem_kw_critica = linha_contem_cnpj(linha_strip) or any(
                kw in linha_strip.lower() for kw in ("crea", "cau", "art", "alvara")
            )
            if not tem_kw_critica:
                continue

        # Pular linhas com alto ratio de palavras curtas (fragmentacao de planta)
        # Caracteristica: pdfplumber em planta gera "579,28 HALL SOCIAL 02 | I IPAVI M ENTO"
        # onde >60% das "palavras" sao numeros isolados ou fragmentos de 1-3 chars
        if len(linha_strip) > 30:
            todas_palavras = re.findall(r"\b[\wÀ-ü]+\b", linha_strip)
            if len(todas_palavras) >= 6:
                palavras_curtas = sum(1 for p in todas_palavras if len(p) <= 3)
                ratio_curtas = palavras_curtas / len(todas_palavras)
                if ratio_curtas > 0.55:
                    # Excecoes: preservar linhas de quadro de areas e dados criticos
                    tem_excecao = bool(
                        linha_contem_cnpj(linha_strip)
                        or re.search(
                            r"crea|cau|\bart\b|alvar[aá]|r\$|"
                            r"\d{1,2}\.\d{3},\d{2}|"
                            r"\btorre\b|\btipo\b|\bsubtotal\b|\btotal\b|"
                            r"\bcoberto\b|\bdescoberto\b|\bquant\b|"
                            r"\bunidade\b|\bquantidade\b|\bprivativ\b",
                            linha_strip.lower(),
                        )
                    )
                    if not tem_excecao:
                        continue

        # Detectar cabecalho/rodape repetido
        if linha_strip == linha_anterior:
            contador_repeticoes += 1
            if contador_repeticoes >= 1:
                continue
        else:
            contador_repeticoes = 0
            linha_anterior = linha_strip

        linhas_limpas.append(linha_strip)

    texto_camada1 = "\n".join(linhas_limpas)
    tam_camada1 = len(texto_camada1)

    # ===== Camada 2: Filtragem por relevancia =====
    blocos = re.split(r"\n\s*\n", texto_camada1)
    blocos_relevantes = []

    for bloco in blocos:
        bloco_strip = bloco.strip()
        if not bloco_strip or len(bloco_strip) < 10:
            continue

        bloco_lower = bloco_strip.lower()

        # Padroes especiais SEMPRE mantidos (alta densidade de info)
        padrao_especial = bool(
            linha_contem_cnpj(bloco_strip)
            or re.search(
                r"\d{3}\.\d{3}\.\d{3}-\d{2}|"                 # CPF
                r"R\$\s*[\d.,]+|"                              # Valores em reais
                r"crea[\s\-:]*[a-z]{0,2}[-\s]*\d+|"           # CREA
                r"cau[\s\-:]*[a-z]{0,2}[-\s]*\d+|"            # CAU
                r"art[\s\-:]*\d{4,}|"                          # ART
                r"alvar[aá][\s\-:n°º.]*\d+",                   # Alvara
                bloco_lower,
            )
        )

        # Contar palavras-chave + verificar densidade textual
        palavras_bloco = set(re.findall(r"\b[a-zA-ZÀ-ü\-\']+\b", bloco_lower))
        kw_encontradas = palavras_bloco & KEYWORDS_RELEVANTES

        # Densidade textual: ratio de letras vs total
        total_chars = len(bloco_strip)
        chars_letras = len(re.findall(r"[a-zA-ZÀ-ü]", bloco_strip))
        densidade = chars_letras / total_chars if total_chars > 0 else 0

        # Quantidade de palavras com 4+ letras (filtra blocos de codigos curtos)
        palavras_longas = [p for p in palavras_bloco if len(p) >= 4]

        # Qualidade textual: razao de palavras "humanas" (4-15 letras) vs todas
        # Blocos com muitos "AREASCOBERTAS" gigantes ou "F" "R" "Z" sozinhos sao baixa qualidade
        palavras_humanas = [p for p in palavras_bloco if 3 <= len(p) <= 15]
        qualidade = len(palavras_humanas) / len(palavras_bloco) if palavras_bloco else 0

        # CRITERIOS DE RETENCAO (mais rigorosos):
        # 1. Tem padrao especial (CNPJ, CREA, etc.) — sempre mantem
        # 2. OU: 2+ keywords E densidade > 30% E 5+ palavras longas E qualidade > 60%
        # 3. OU: 4+ keywords E qualidade > 50%
        if (padrao_especial
            or (len(kw_encontradas) >= 2 and densidade > 0.30 and len(palavras_longas) >= 5 and qualidade > 0.60)
            or (len(kw_encontradas) >= 4 and qualidade > 0.50)):
            blocos_relevantes.append(bloco_strip)

    texto_camada2 = "\n\n".join(blocos_relevantes)
    tam_camada2 = len(texto_camada2)

    # ===== Camada 3: Deduplicacao normalizando numeros + codigos profissionais =====
    blocos_finais = []
    blocos_vistos = {}

    for bloco in blocos_relevantes:
        # Hash mais agressivo: substitui numeros, codigos profissionais e sequencias
        chave_norm = re.sub(r"\d+", "#", bloco[:200])
        chave_norm = PADRAO_CODIGO_PROFISSIONAL.sub("PROFISSIONAL", chave_norm)
        chave_norm = re.sub(r"\s+", " ", chave_norm).lower().strip()

        ocorrencias = blocos_vistos.get(chave_norm, 0)
        blocos_vistos[chave_norm] = ocorrencias + 1

        # Mantem so a primeira ocorrencia
        if ocorrencias == 0:
            blocos_finais.append(bloco)

    texto_final = "\n\n".join(blocos_finais)
    texto_final = _combinar_evidencias_e_corpo(
        evidencias_criticas,
        texto_final,
        LIMITE_CHARS_TEXTO_FILTRADO,
    )
    tam_final = len(texto_final)

    if verbose:
        reducao_total = (1 - tam_final / tam_original) * 100 if tam_original > 0 else 0
        logger.info(
            "Pre-filtragem: original=%s | limpeza=%s (%.1f%% reduzido) | relevancia=%s (%.1f%% reduzido) | final=%s (%.1f%% reduzido)",
            tam_original,
            tam_camada1,
            (1 - tam_camada1 / tam_original) * 100,
            tam_camada2,
            (1 - tam_camada2 / tam_original) * 100,
            tam_final,
            reducao_total,
        )
    logger.debug(
        "Pre-filtragem detalhada: evidencias=%s chars | blocos=%s | relevantes=%s | finais=%s",
        len(evidencias_criticas),
        len(blocos),
        len(blocos_relevantes),
        len(blocos_finais),
    )

    return texto_final


def separar_documentos(textos):
    import re

    partes = re.split(r"\n={10,}\nDOCUMENTO:\s*", textos)
    docs = []
    for parte in partes:
        trecho = parte.strip()
        if not trecho:
            continue
        if "\n" in trecho and trecho.split("\n", 1)[0].endswith(".pdf"):
            nome, corpo = trecho.split("\n", 1)
            corpo = re.sub(r"^=+\n", "", corpo).strip()
        else:
            nome = f"bloco_{len(docs)+1}.txt"
            corpo = trecho
        if corpo:
            docs.append({"nome": nome.strip(), "texto": corpo})
    logger.debug("Separacao de documentos: %s documento(s)", len(docs))
    return docs


def dividir_lotes_documentos(documentos, limite_chars=LIMITE_CHARS_LOTE):
    lotes = []
    lote_atual = []
    tamanho_atual = 0

    for doc in documentos:
        cabecalho = f"DOCUMENTO: {doc['nome']}\n"
        texto = doc["texto"].strip()
        if not texto:
            continue

        if len(texto) > limite_chars:
            inicio = 0
            while inicio < len(texto):
                fim = min(len(texto), inicio + limite_chars)
                corte = texto.rfind("\n", inicio, fim)
                if corte <= inicio:
                    corte = fim
                parte = texto[inicio:corte].strip()
                if parte:
                    lotes.append(cabecalho + parte)
                inicio = corte
            continue

        tamanho_doc = len(cabecalho) + len(texto) + 2
        if lote_atual and tamanho_atual + tamanho_doc > limite_chars:
            lotes.append("\n\n".join(lote_atual))
            lote_atual = []
            tamanho_atual = 0

        lote_atual.append(cabecalho + texto)
        tamanho_atual += tamanho_doc

    if lote_atual:
        lotes.append("\n\n".join(lote_atual))

    logger.debug(
        "Divisao em lotes: documentos=%s | lotes=%s | limite_chars=%s",
        len(documentos),
        len(lotes),
        limite_chars,
    )
    return lotes
