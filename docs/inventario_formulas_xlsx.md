# Inventário de fórmulas — template ABNT NBR 12721:2006

Inventário operacional das células com fórmula em `assets/ABNT_NBR_12721-2006.xlsx`. A fonte programática é [`excel_formula_inventory.py`](../src/nbr12721/outputs/excel_formula_inventory.py).

## Total por aba

| Aba | Fórmulas |
|-----|----------|
| QUADRO I | 224 |
| QUADRO II | 330 |
| QUADRO III | 33 |
| QUADRO IV A | 298 |
| QUADRO IV B | 177 |
| QUADRO IV B.1 | 203 |
| QUADRO V | 9 |
| QUADRO VI | 9 |
| QUADRO VII | 9 |
| QUADRO VIII | 9 |
| **Total** | **1301** |

Abas sem fórmula (CAPA, INSTRUÇÕES, INFORMAÇÕES PRELIMINARES) não aparecem no inventário.

## Agrupamento por quadro

### Quadro I (224 fórmulas)

- **Cabeçalho:** referências cruzadas a Informações Preliminares e numeração sequencial (`R4`, `C8`, `N8`…).
- **Linhas de dados (17–41):** totais por linha nas colunas F, G, K, L, P, Q, R, S — padrão `=SUM(Cn+Dn)`, `=SUM(Fn+Kn+Pn)` etc. Entradas do Python ficam em B, C, D, E, H, I, J, M, N, O, T.
- **Rodapé:** somatórios globais das colunas de área real e equivalente.

### Quadro II (330 fórmulas)

- **Cabeçalho:** referências ao Quadro I (`T4`, `D5`, `C8`…).
- **Linhas de dados (17–41):** totais por unidade; coeficiente de proporcionalidade (col. 31) e produtos com totais do Quadro I (cols. 32–34) quando preenchidos.
- **Rodapé:** área real global e área equivalente global (col. 37–38).

### Quadro III (33 fórmulas)

- Referências a totais dos Quadros I e II (`D5`, `L5`, `L6`, `D8`…).
- Células de custo derivado (custo global, unitário) — não sobrescrever; Python alimenta CUB, sindicato, percentuais de entrada (`QUADRO3_CELLS`, `QUADRO3_PERCENTUAIS`).

### Quadro IV A (298 fórmulas)

- Quase inteiramente calculado (custo por unidade, sub-rogação, rerrateio). **Writer não preenche** esta aba hoje.

### Quadro IV B / IV B.1 (177 / 203 fórmulas)

- Resumo de áreas reais para registro; coeficientes e totais derivados do Quadro II.
- Writer preenche colunas de **entrada** tabular (`outrasAreasPriv`, `qtdUnidades`, `areaTerrExcl`, `areaTerrComum`); demais colunas são fórmula.

### Quadros V–VIII (9 fórmulas cada)

- Poucas referências cruzadas no cabeçalho.
- Entradas tabulares nas linhas 12+ (colunas B, D, F, G, H, J, L conforme o quadro).

## Conclusões operacionais

1. **Células com fórmula não devem ser sobrescritas.** O writer tabular (`_escrever_dataframe`) verifica `celula_tem_formula` antes de escrever e registra skip em DEBUG.
2. **Python alimenta apenas entradas** mapeadas em `excel_mapping.py` (colunas de dado bruto, células fixas de Info preliminares, Quadro III/V).
3. **Auditoria** (`excel_audit.py`) compara JSON vs células de **entrada** preenchidas pelo pipeline — não vs resultados calculados por fórmula Excel.
4. **Quadro IV A** permanece fora do escopo de automação até implementação dedicada.

## Regenerar inventário

```bash
PYTHONPATH=src ./venv/bin/python - <<'PY'
from nbr12721.outputs.excel_formula_inventory import inventariar_formulas
inv = inventariar_formulas("assets/ABNT_NBR_12721-2006.xlsx")
print(inv["total_formulas"])
for aba, formulas in inv["abas"].items():
    print(aba, len(formulas))
PY
```

Este documento resume por faixa/célula-chave; a listagem completa (1301 itens) fica disponível via `inventariar_formulas()` em runtime.
