import base64
import io
import os
import zipfile
from datetime import datetime
from time import sleep

import requests


class nweb:
    """Cliente base para a API REST do Questor nWeb."""

    def __init__(self, base_url: str, print_error: bool = True):
        """
        Args:
            base_url: URL base do servidor nWeb, ex: "http://servidor:7080"
            print_error: Se True, imprime erros no console (padrão: True)
        """
        self.base_url = base_url.rstrip("/")
        self.print_error = print_error

    def request(self, method="GET", url="", params=None, data=None):
        req_params = params if params is not None else {}
        req_data = data if data is not None else {}
        headers = {"Content-Type": "application/json"}

        while True:
            match method:
                case "GET":
                    response = requests.get(url=url, params=req_params, headers=headers, json=req_data or None)
                case "PUT":
                    response = requests.put(url=url, params=req_params, headers=headers, json=req_data or None)
                case "POST":
                    response = requests.post(url=url, params=req_params, headers=headers, json=req_data or None)
                case "DELETE":
                    response = requests.delete(url=url, params=req_params, headers=headers, json=req_data or None)
                case "PATCH":
                    response = requests.patch(url=url, params=req_params, headers=headers, json=req_data or None)
                case _:
                    raise ValueError(f"Método HTTP '{method}' não suportado")

            if response.status_code in (200, 201):
                return response
            elif response.status_code == 429:
                sleep(10)
            else:
                if self.print_error:
                    try:
                        response_json = response.json()
                        message = response_json.get('mensagem') or response_json.get('message', "")
                        json_content = response_json
                    except Exception:
                        message = ""
                        json_content = response.text

                    print(f"""Erro no retorno da API do Questor nWeb
Mensagem: {message}
URL: {url}
Metodo: {method}
Parametros: {req_params}
Resposta JSON: {json_content}""")

                if response.status_code in (401, 403, 404):
                    return None
                else:
                    break

        return None


class relatorios(nweb):
    """Acesso aos relatórios do Questor nWeb via /TnWebDMRelatorio/Executar."""

    def executar(
        self,
        action_name: str,
        tipo_retorno: str = "nrwexCSV",
        body: dict | None = None,
        method: str = "POST",
        retornar_base64: bool = False,
    ) -> dict:
        """
        Executa um relatório genérico.

        Args:
            action_name: Nome da action do relatório, ex: "nFisRRDocFiscalEmitido"
            tipo_retorno: Formato de retorno — "nrwexCSV", "nrwexTXT", "nrwexJSON" (padrão: "nrwexCSV")
            body: Parâmetros do relatório como dict
            method: Método HTTP (padrão: "POST")
            retornar_base64: Se True, adiciona _ABase64=True na query string (padrão: False)

        Returns:
            dict: Resposta JSON da API ou dict vazio se falhou

        Exemplo:
            client = relatorios(base_url="http://servidor:7080")
            resultado = client.executar(
                action_name="nFisRRDocFiscalEmitido",
                tipo_retorno="nrwexCSV",
                body={"pCodigoEmpresa": 1, ...}
            )
            csv_texto = resultado.get("Data", "")
        """
        url = f"{self.base_url}/TnWebDMRelatorio/Executar"
        params = {
            "_AActionName": action_name,
            "_ATipoRetorno": tipo_retorno,
            "_ABase64": "True" if retornar_base64 else "False",
        }
        response = self.request(method, url=url, params=params, data=body or {})
        if not response:
            return {}
        return response.json()

    def doc_fiscal_emitido(
        self,
        codigo_empresa: int,
        codigo_estab: int,
        data_inicial: str,
        data_final: str,
        tipo_retorno: str = "nrwexCSV",
        **kwargs,
    ) -> dict:
        """
        Relatório de documentos fiscais emitidos (nFisRRDocFiscalEmitido).

        Args:
            codigo_empresa: Código da empresa
            codigo_estab: Código do estabelecimento (filial)
            data_inicial: Data inicial no formato DD/MM/AAAA
            data_final: Data final no formato DD/MM/AAAA
            tipo_retorno: Formato de retorno (padrão: "nrwexCSV")
            **kwargs: Parâmetros adicionais do relatório

        Returns:
            dict: Resposta JSON com campo "Data" contendo o CSV do relatório, ou dict vazio se falhou

        Exemplo:
            client = relatorios(base_url="http://servidor:7080")
            resultado = client.doc_fiscal_emitido(
                codigo_empresa=1,
                codigo_estab=1,
                data_inicial="01/01/2026",
                data_final="31/01/2026",
            )
            csv_texto = resultado.get("Data", "")
        """
        body = {
            "pDataInicial": data_inicial,
            "pDataFinal": data_final,
            "pNumeroDocIni": "",
            "pNumeroDocFim": "",
            "pEspecie": "",
            "pSerie": "",
            "pSubserie": "",
            "pCodigoEmpresa": codigo_empresa,
            "pCodigoEstab": codigo_estab,
            "oStep_1": -1,
            "pEndereco": "",
            **kwargs,
        }
        return self.executar("nFisRRDocFiscalEmitido", tipo_retorno=tipo_retorno, body=body)

    def resumo_conf_entradas(
        self,
        codigo_empresa: int,
        codigo_estab: int,
        data_inicial: str,
        data_final: str,
        tipo_retorno: str = "nrwexCSV",
        **kwargs,
    ) -> dict:
        """
        Relatório de resumo da conferência de entradas (nFisRRResumoConfLctoFisEnt).

        Args:
            codigo_empresa: Código da empresa
            codigo_estab: Código do estabelecimento (filial)
            data_inicial: Data inicial no formato DD/MM/AAAA
            data_final: Data final no formato DD/MM/AAAA
            tipo_retorno: Formato de retorno (padrão: "nrwexCSV")
            **kwargs: Parâmetros adicionais do relatório

        Returns:
            dict: Resposta JSON com campo "Data" contendo o CSV do relatório, ou dict vazio se falhou
        """
        body = {
            "pDataInicial": data_inicial,
            "pDataFinal": data_final,
            "pCodigoEmpresa": codigo_empresa,
            "pCodigoEstab": codigo_estab,
            **kwargs,
        }
        return self.executar("nFisRRResumoConfLctoFisEnt", tipo_retorno=tipo_retorno, body=body)

    def listar_produtos(
        self,
        codigo_empresa: int,
        tipo_retorno: str = "nrwexTXT",
        **kwargs,
    ) -> dict:
        """
        Lista produtos cadastrados na empresa (nFisRRProduto).

        Args:
            codigo_empresa: Código da empresa
            tipo_retorno: Formato de retorno (padrão: "nrwexTXT")
            **kwargs: Parâmetros adicionais do relatório

        Returns:
            dict: Resposta JSON com campo "Data" contendo o texto do relatório, ou dict vazio se falhou

        Exemplo:
            client = relatorios(base_url="http://servidor:7080")
            resultado = client.listar_produtos(codigo_empresa=1)
            texto = resultado.get("Data", "")
        """
        body = {
            "PCODIGOEMPRESA": codigo_empresa,
            "pListarPisCofins": "0",
            "PCODIGONCM": "9999.99.99",
            **kwargs,
        }
        return self.executar("nFisRRProduto", tipo_retorno=tipo_retorno, body=body, method="GET")


class importacao(nweb):
    """Importação de documentos fiscais via /TnWebDMProcesso/ProcessoExecutar."""

    ACTIONS = {
        "NFe":  "TnArqDPImportarLctoFisNFEXML",
        "NFCe": "TnArqDPImportarLctoFisNFEXML",
        "CTe":  "TnArqDPImportarArqCTe",
        "NFSe": "TnArqDPImportarArqNFEMunicLayout",
    }

    def processar(self, action_name: str, body: dict) -> dict:
        """
        Executa um processo genérico.

        Args:
            action_name: Nome da action, ex: "TnArqDPImportarLctoFisNFEXML"
            body: Corpo da requisição com os parâmetros do processo

        Returns:
            dict: Resposta JSON da API ou dict vazio se falhou
        """
        url = f"{self.base_url}/TnWebDMProcesso/ProcessoExecutar"
        params = {"_AActionName": action_name}
        response = self.request("POST", url=url, params=params, data=body)
        if not response:
            return {}
        return response.json()

    @staticmethod
    def criar_zip_base64(caminhos_xml: list) -> tuple:
        """
        Empacota arquivos XML em um ZIP em memória e retorna (nome_zip, base64_do_zip).

        Args:
            caminhos_xml: Lista de caminhos dos arquivos XML

        Returns:
            tuple[str, str]: (nome_zip, base64_do_zip)

        Exemplo:
            nome_zip, b64 = importacao.criar_zip_base64(["nota1.xml", "nota2.xml"])
        """
        buffer = io.BytesIO()
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        nome_zip = f"lote_{ts}.zip"
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for caminho in caminhos_xml:
                zf.write(caminho, arcname=os.path.basename(caminho))
        buffer.seek(0)
        return nome_zip, base64.b64encode(buffer.read()).decode("ascii")

    def importar(
        self,
        tipo: str,
        movimento: str,
        codigo_empresa: str,
        codigo_estab: str,
        data_inicial: str,
        data_final: str,
        nome_zip: str,
        base64_zip: str,
        params_extras: dict | None = None,
    ) -> dict:
        """
        Importa documentos fiscais no Questor nWeb.

        Args:
            tipo: Tipo do documento — "NFe", "NFCe", "CTe" ou "NFSe"
            movimento: "entrada" ou "saida" (usado apenas para referência; inclua pMovimento em params_extras)
            codigo_empresa: Código da empresa
            codigo_estab: Código do estabelecimento (filial)
            data_inicial: Data inicial no formato DD/MM/AAAA
            data_final: Data final no formato DD/MM/AAAA
            nome_zip: Nome do arquivo ZIP
            base64_zip: Conteúdo do ZIP em base64
            params_extras: Parâmetros adicionais da action (ex: pPermitirErros, pMovimento, pCodigoProduto, etc.)

        Returns:
            dict: Resposta JSON da API ou dict vazio se falhou

        Exemplo:
            client = importacao(base_url="http://servidor:7080")
            nome_zip, b64 = importacao.criar_zip_base64(["nota1.xml", "nota2.xml"])
            resultado = client.importar(
                tipo="NFe",
                movimento="entrada",
                codigo_empresa="1",
                codigo_estab="1",
                data_inicial="01/01/2026",
                data_final="31/01/2026",
                nome_zip=nome_zip,
                base64_zip=b64,
                params_extras={
                    "pPermitirErros": "2",
                    "pMovimento": "1",
                    "pDeletarAnteriores": "1",
                },
            )
        """
        if tipo not in self.ACTIONS:
            raise ValueError(f"Tipo '{tipo}' não suportado. Use: {list(self.ACTIONS)}")

        action = self.ACTIONS[tipo]
        body = {
            "pCodigoEmpresa": codigo_empresa,
            "pCodigoEstab": codigo_estab,
            "pDataInicial": data_inicial,
            "pDataFinal": data_final,
            **(params_extras or {}),
            "pNomeArquivo": nome_zip,
            "pNomePasta_DIRABRIR": {
                "filename": nome_zip,
                "data": base64_zip,
            },
        }
        return self.processar(action, body)