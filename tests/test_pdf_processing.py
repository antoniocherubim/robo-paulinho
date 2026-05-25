import unittest

from nbr12721.documents.pdf_processing import prefiltrar_texto


class TestPrefiltrarTexto(unittest.TestCase):
    def test_preserva_evidencias_criticas_e_limita_tamanho(self):
        texto = """
========================================
DOCUMENTO: exemplo.pdf
========================================
TERRENO: 8.958,97 M2 ARQUITETO E URBANISTA - CAU A30683-9
LONDRINA-PR 24/07/2023 (MAX: 80%)
TOTAL DE VAGAS NO PAVIMENTO 73 VAGAS + 2 VAGAS PNE
(12º AO 202) PAV. TIPO - 65,985 X 80 APTOS 5.278,80
Nº de ALVARÁ: 2457/2023
""" + "\n".join("240x480 240x480 240x480" for _ in range(200))

        filtrado = prefiltrar_texto(texto, verbose=False)

        self.assertLessEqual(len(filtrado), 16000)
        self.assertIn("EVIDENCIAS CRITICAS", filtrado)
        self.assertIn("LONDRINA-PR", filtrado)
        self.assertIn("80 APTOS", filtrado)
        self.assertIn("TOTAL DE VAGAS", filtrado)
        self.assertIn("ALVARÁ: 2457/2023", filtrado)


if __name__ == "__main__":
    unittest.main()
