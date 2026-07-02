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


class menus(nweb):
    """Acesso aos menus do Questor nWeb via /TnWebDMMenus/Pegar."""

    def pegar(self, tipo: int = 4) -> dict:
        """
        Retorna os menus disponíveis no Questor nWeb.

        Args:
            tipo: Tipo do menu (padrão: 4)

        Returns:
            dict: Resposta JSON da API ou dict vazio se falhou

        Exemplo:
            client = menus(base_url="http://servidor:7080")
            resultado = client.pegar(tipo=4)
        """
        url = f"{self.base_url}/TnWebDMMenus/Pegar"
        params = {"_ATipo": tipo}
        response = self.request("GET", url=url, params=params)
        if not response:
            return {}
        return response.json()


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

    def importar_nfse(
        self,
        codigo_empresa: str,
        codigo_estab: str,
        data_inicial: str,
        data_final: str,
        pImportar: str,
        pIntegrar: str,
        pDataImportacao: str,
        pImportarProduto: str,
        pTratamentoErro: str,
        pCfopRetidos: str,
        pCodigoImpostoIRRF: str,
        pVariacaoImpostoIRRF: str,
        pCodigoImpostoPIS: str,
        pVariacaoImpostoPIS: str,
        pCodigoImpostoCOFINS: str,
        pVariacaoImpostoCOFINS: str,
        pCodigoImpostoCSLL: str,
        pVariacaoImpostoCSLL: str,
        pTipoProcessamento: str,
        pValidaEstab: str,
        pConverterArquivos: str,
        pTipo: str,
        pNomeArquivo: str,
        nome_zip: str,
        base64_zip: str,
        pSugerirRelacDescrServico: str = "0",
        pImportarPISCOFINSOUTROS: str = "0",
        pImportarProdutoPadrao: str = "0",
        pCodigoProdutoPadrao: str = "",
        pSubSerie: str = "",
        pPessoa: str = "",
        pCfop: str = "",
        pCodigoNfseLayout: str = "",
        pConverterArquivoLote: str = "0",
        **kwargs,
    ) -> dict:
        """
        Importa Notas Fiscais de Serviço (NFS-e) via TnArqDPImportarArqNFEMunicLayout.

        Args:
            codigo_empresa: Código da empresa (pCodigoEmpresa)
            codigo_estab: Código da filial (pCodigoEstab)
            data_inicial: Data inicial dos lançamentos a importar, formato DD/MM/AAAA (pDataInicial)
            data_final: Data final dos lançamentos a importar, formato DD/MM/AAAA (pDataFinal)
            pImportar: Tipo de movimento — "1"=Emitidas (Saídas), "2"=Recebidas (Entradas)
            pIntegrar: Tipo de integração — "0"=Tributado, "1"=Isentas, "2"=Outras
            pDataImportacao: Data considerada na importação — "1"=Data Emissão, "2"=Data RPS/Prestação
            pImportarProduto: Relacionamento dos serviços com produto — "0"=Não, "1"=Sim
            pTratamentoErro: Tratamento de erros — "0"=Cancela tudo se houver erro, "1"=Importa sem erros e exibe relatório
            pCfopRetidos: Código da operação fiscal (CFOP) para os retidos
            pCodigoImpostoIRRF: Código do imposto IRRF a recolher
            pVariacaoImpostoIRRF: Variação do imposto IRRF a recolher
            pCodigoImpostoPIS: Código do imposto PIS a recolher (enviado como pCodigo)
            pVariacaoImpostoPIS: Variação do imposto PIS a recolher
            pCodigoImpostoCOFINS: Código do imposto COFINS a recolher
            pVariacaoImpostoCOFINS: Variação do imposto COFINS a recolher
            pCodigoImpostoCSLL: Código do imposto CSLL a recolher
            pVariacaoImpostoCSLL: Variação do imposto CSLL a recolher
            pTipoProcessamento: Tipo de processamento — "2"=Somente não importados, "3"=Excluir e importar novamente
            pValidaEstab: Valida empresa/filial com o emitente do arquivo
            pConverterArquivos: Converte arquivos para layout padrão — "0"=Não, "1"=Sim
            pTipo: Origem da importação — "1"=Um único arquivo, "2"=Vários arquivos
            pNomeArquivo: Caminho completo do arquivo quando pTipo="1" (ex: D:\\pasta\\arquivo.txt);
                apenas o nome do arquivo quando pTipo="2"
            nome_zip: Nome do arquivo ZIP compactado (pNomePasta_DIRABRIR.filename)
            base64_zip: Conteúdo do ZIP em base64 (pNomePasta_DIRABRIR.data)
            pSugerirRelacDescrServico: Sugerir relacionamento pela descrição do serviço — "0"=Não, "1"=Sim (padrão: "0")
            pImportarPISCOFINSOUTROS: Importar PIS/Cofins — "0"=Não, "1"=Com sugestão automática,
                "2"=Sem sugestão automática (padrão: "0")
            pImportarProdutoPadrao: Importar NFS-e com único serviço — "0"=Apenas por fornecedor,
                "1"=Fornecedor/NF (padrão: "0")
            pCodigoProdutoPadrao: Código do produto padrão (padrão: "")
            pSubSerie: Sub-série (padrão: "")
            pPessoa: Código da pessoa (padrão: "")
            pCfop: Código da operação fiscal (CFOP) (padrão: "")
            pCodigoNfseLayout: Layout de NFS-e; usar "180" quando pConverterArquivos="1"
                (Sistema Nota do Milhão - NFTS - v4.90) (padrão: "")
            pConverterArquivoLote: (padrão: "0")
            **kwargs: Parâmetros adicionais repassados ao body da requisição

        Returns:
            dict: Resposta JSON da API ou dict vazio se falhou

        Exemplo:
            client = importacao(base_url="http://servidor:7080")
            nome_zip, b64 = importacao.criar_zip_base64(["NFTS_98414666_20240701_20240731.txt"])
            resultado = client.importar_nfse(
                codigo_empresa="6",
                codigo_estab="1",
                data_inicial="01/07/2024",
                data_final="30/07/2024",
                pImportar="2",
                pIntegrar="2",
                pDataImportacao="2",
                pImportarProduto="0",
                pTratamentoErro="1",
                pCfopRetidos="1113001",
                pCodigoImpostoIRRF="1708",
                pVariacaoImpostoIRRF="6",
                pCodigoImpostoPIS="5952",
                pVariacaoImpostoPIS="3",
                pCodigoImpostoCOFINS="5952",
                pVariacaoImpostoCOFINS="7",
                pCodigoImpostoCSLL="5952",
                pVariacaoImpostoCSLL="7",
                pTipoProcessamento="3",
                pValidaEstab="0",
                pConverterArquivos="1",
                pCodigoNfseLayout="180",
                pTipo="1",
                pNomeArquivo="D:\\Costoya\\NFTS_98414666_20240701_20240731.txt",
                nome_zip=nome_zip,
                base64_zip=b64,
                pPessoa="1200",
                pCfop="1102010",
            )
        """
        body = {
            "pCodigoEmpresa": codigo_empresa,
            "pCodigoEstab": codigo_estab,
            "pDataInicial": data_inicial,
            "pDataFinal": data_final,
            "pImportar": pImportar,
            "pIntegrar": pIntegrar,
            "pDataImportacao": pDataImportacao,
            "pImportarProduto": pImportarProduto,
            "pSugerirRelacDescrServico": pSugerirRelacDescrServico,
            "pImportarPISCOFINSOUTROS": pImportarPISCOFINSOUTROS,
            "pImportarProdutoPadrao": pImportarProdutoPadrao,
            "pCodigoProdutoPadrao": pCodigoProdutoPadrao,
            "pSubSerie": pSubSerie,
            "pPessoa": pPessoa,
            "pTratamentoErro": pTratamentoErro,
            "pCfop": pCfop,
            "pCfopRetidos": pCfopRetidos,
            "pCodigoImpostoIRRF": pCodigoImpostoIRRF,
            "pVariacaoImpostoIRRF": pVariacaoImpostoIRRF,
            "pCodigo": pCodigoImpostoPIS,
            "pVariacaoImpostoPIS": pVariacaoImpostoPIS,
            "pCodigoImpostoCOFINS": pCodigoImpostoCOFINS,
            "pVariacaoImpostoCOFINS": pVariacaoImpostoCOFINS,
            "pCodigoImpostoCSLL": pCodigoImpostoCSLL,
            "pVariacaoImpostoCSLL": pVariacaoImpostoCSLL,
            "pTipoProcessamento": pTipoProcessamento,
            "pValidaEstab": pValidaEstab,
            "pConverterArquivos": pConverterArquivos,
            "pCodigoNfseLayout": pCodigoNfseLayout,
            "pTipo": pTipo,
            "pConverterArquivoLote": pConverterArquivoLote,
            "pNomeArquivo": pNomeArquivo,
            "pNomePasta_DIRABRIR": {
                "filename": nome_zip,
                "data": base64_zip,
            },
            **kwargs,
        }
        return self.processar(self.ACTIONS["NFSe"], body)