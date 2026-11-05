import base64
import io
import os
import zipfile
from dataclasses import dataclass
from datetime import datetime
from time import sleep

import requests


@dataclass
class Leiaute:
    """Layout de importação (.nli) enviado em `leiautes` no POST /Integracao/Importar."""

    nome: str
    arquivo: str

    @classmethod
    def from_file(cls, caminho: str) -> "Leiaute":
        """Lê um arquivo .nli do disco e codifica o conteúdo em base64.

        Args:
            caminho: Caminho do arquivo .nli

        Returns:
            Leiaute com `nome` igual ao nome do arquivo e `arquivo` em base64
        """
        with open(caminho, "rb") as arq:
            conteudo = arq.read()
        return cls.from_bytes(os.path.basename(caminho), conteudo)

    @classmethod
    def from_bytes(cls, nome: str, conteudo: bytes) -> "Leiaute":
        """Monta um layout a partir de bytes já lidos.

        Args:
            nome: Nome do layout, ex: "C_LctoCtb.nli"
            conteudo: Conteúdo binário do arquivo .nli

        Returns:
            Leiaute com o conteúdo codificado em base64
        """
        return cls(nome=nome, arquivo=base64.b64encode(conteudo).decode("ascii"))

    @classmethod
    def from_base64(cls, nome: str, b64: str) -> "Leiaute":
        """Monta um layout a partir de uma string base64 já pronta.

        Args:
            nome: Nome do layout, ex: "C_LctoCtb.nli"
            b64: Conteúdo do .nli já em base64

        Returns:
            Leiaute usando o base64 informado
        """
        return cls(nome=nome, arquivo=b64)

    def to_dict(self) -> dict:
        """Retorna o par `{nome, arquivo}` esperado pela API."""
        return {"nome": self.nome, "arquivo": self.arquivo}


class nweb:
    def __init__(self, base_url: str, print_error: bool = True,
                 headers: dict | None = None, timeout: float | None = None):
        self.base_url = base_url.rstrip("/")
        self.print_error = print_error
        self._headers = headers or {}
        self._timeout = timeout

    def request(self, method="GET", url="", params=None, data=None):
        req_params = params if params is not None else {}
        req_data = data if data is not None else {}
        headers = {"Content-Type": "application/json", **self._headers}

        while True:
            match method:
                case "GET":
                    response = requests.get(url=url, params=req_params, headers=headers, json=req_data or None, timeout=self._timeout)
                case "PUT":
                    response = requests.put(url=url, params=req_params, headers=headers, json=req_data or None, timeout=self._timeout)
                case "POST":
                    response = requests.post(url=url, params=req_params, headers=headers, json=req_data or None, timeout=self._timeout)
                case "DELETE":
                    response = requests.delete(url=url, params=req_params, headers=headers, json=req_data or None, timeout=self._timeout)
                case "PATCH":
                    response = requests.patch(url=url, params=req_params, headers=headers, json=req_data or None, timeout=self._timeout)
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


class consulta(nweb):
    """Consulta de lançamentos fiscais via /TnWebDMProcesso/ProcessoExecutar."""

    def processar(self, action_name: str, body: dict, method: str = "GET") -> dict:
        """
        Executa um processo genérico de consulta.

        Args:
            action_name: Nome da action, ex: "nFisNFSaidas"
            body: Corpo da requisição com os parâmetros do processo
            method: Método HTTP (padrão: "GET")

        Returns:
            dict: Resposta JSON da API ou dict vazio se falhou
        """
        url = f"{self.base_url}/TnWebDMProcesso/ProcessoExecutar"
        params = {"_AActionName": action_name}
        response = self.request(method, url=url, params=params, data=body)
        if not response:
            return {}
        return response.json()

    @staticmethod
    def _extrair_items(response_json: dict) -> list:
        """Extrai a lista de items do grid aninhado em Widgets.bottom[0].Itens[0].grids[0].items."""
        try:
            return response_json["Widgets"]["bottom"][0]["Itens"][0]["grids"][0]["items"]
        except (KeyError, IndexError, TypeError):
            return []

    def saidas_nf(
        self,
        codigo_empresa: str | int,
        codigo_estab: str | int,
        data_ini: str,
        data_fim: str,
        **kwargs,
    ) -> list:
        """
        Consulta lançamentos de saída via nFisNFSaidas.

        Args:
            codigo_empresa: Código da empresa (CODIGOEMPRESA)
            codigo_estab: Código do estabelecimento (CODIGOESTAB)
            data_ini: Data inicial no formato DD/MM/AAAA (DATAINI)
            data_fim: Data final no formato DD/MM/AAAA (DATAFIM)
            **kwargs: Parâmetros adicionais do body

        Returns:
            list: Lista de lançamentos (items do grid), ou lista vazia se falhou

        Campos típicos: CHAVELCTOFISSAI, CODIGOPESSOA, NOMEPESSOA, INSCRFEDERAL,
        NUMERONF, ESPECIENF, SERIENF, SUBSERIENF, DATALCTOFIS, VALORCONTABIL,
        CDMODELO, CODIGOSAT, CHAVENFESAI, EMITENTENF

        Exemplo:
            client = consulta(base_url="http://servidor:7080")
            items = client.saidas_nf("5353", "1", "31/08/2026", "31/08/2026")
        """
        body = {
            "CODIGOEMPRESA": str(codigo_empresa),
            "CODIGOESTAB": str(codigo_estab),
            "DATAINI": data_ini,
            "DATAFIM": data_fim,
            **kwargs,
        }
        return self._extrair_items(self.processar("nFisNFSaidas", body))

    def entradas_nf(
        self,
        codigo_empresa: str | int,
        codigo_estab: str | int,
        data_ini: str,
        data_fim: str,
        **kwargs,
    ) -> list:
        """
        Consulta lançamentos de entrada via nFisNFEntradas.

        Args:
            codigo_empresa: Código da empresa (CODIGOEMPRESA)
            codigo_estab: Código do estabelecimento (CODIGOESTAB)
            data_ini: Data inicial no formato DD/MM/AAAA (DATAINI)
            data_fim: Data final no formato DD/MM/AAAA (DATAFIM)
            **kwargs: Parâmetros adicionais do body

        Returns:
            list: Lista de lançamentos (items do grid), ou lista vazia se falhou

        Campos típicos: iguais a saidas_nf, exceto sem CODIGOSAT

        Exemplo:
            client = consulta(base_url="http://servidor:7080")
            items = client.entradas_nf("5353", "1", "31/08/2026", "31/08/2026")
        """
        body = {
            "CODIGOEMPRESA": str(codigo_empresa),
            "CODIGOESTAB": str(codigo_estab),
            "DATAINI": data_ini,
            "DATAFIM": data_fim,
            **kwargs,
        }
        return self._extrair_items(self.processar("nFisNFEntradas", body))

    def saidas_dp(
        self,
        codigo_empresa: str | int,
        codigo_estab: str | int,
        data_ini: str,
        data_fim: str,
        **kwargs,
    ) -> dict:
        """
        Consulta lançamentos de saída via TnFisDPConsultaLctoSai (rota antiga).

        Args:
            codigo_empresa: Código da empresa (CODIGOEMPRESA)
            codigo_estab: Código do estabelecimento (CODIGOESTAB)
            data_ini: Data inicial no formato DD/MM/AAAA (DATAINI)
            data_fim: Data final no formato DD/MM/AAAA (DATAFIM)
            **kwargs: Parâmetros adicionais do body

        Returns:
            dict: Resposta JSON bruta da API ou dict vazio se falhou

        Exemplo:
            client = consulta(base_url="http://servidor:7080")
            resultado = client.saidas_dp("5353", "1", "31/08/2026", "31/08/2026")
        """
        body = {
            "CODIGOEMPRESA": str(codigo_empresa),
            "CODIGOESTAB": str(codigo_estab),
            "DATAINI": data_ini,
            "DATAFIM": data_fim,
            **kwargs,
        }
        return self.processar("TnFisDPConsultaLctoSai", body)

    def entradas_dp(
        self,
        codigo_empresa: str | int,
        codigo_estab: str | int,
        data_ini: str,
        data_fim: str,
        **kwargs,
    ) -> dict:
        """
        Consulta lançamentos de entrada via TnFisDPConsultaLctoEnt (rota antiga).

        Args:
            codigo_empresa: Código da empresa (CODIGOEMPRESA)
            codigo_estab: Código do estabelecimento (CODIGOESTAB)
            data_ini: Data inicial no formato DD/MM/AAAA (DATAINI)
            data_fim: Data final no formato DD/MM/AAAA (DATAFIM)
            **kwargs: Parâmetros adicionais do body

        Returns:
            dict: Resposta JSON bruta da API ou dict vazio se falhou

        Exemplo:
            client = consulta(base_url="http://servidor:7080")
            resultado = client.entradas_dp("5353", "1", "31/08/2026", "31/08/2026")
        """
        body = {
            "CODIGOEMPRESA": str(codigo_empresa),
            "CODIGOESTAB": str(codigo_estab),
            "DATAINI": data_ini,
            "DATAFIM": data_fim,
            **kwargs,
        }
        return self.processar("TnFisDPConsultaLctoEnt", body)


class integracao(nweb):
    """Importação genérica via POST /Integracao/Importar."""

    _CAMPOS_LCTO_CTB = (
        "chave_lcto",
        "inscr_federal",
        "data",
        "lote",
        "num_doc",
        "conta_deb",
        "desc_conta_deb",
        "conta_cred",
        "desc_conta_cred",
        "valor",
        "codigo_hist",
        "compl_hist",
    )
    _CAMPOS_LCTO_CTB_OBRIGATORIOS = (
        "chave_lcto",
        "inscr_federal",
        "data",
        "conta_deb",
        "valor",
    )

    @staticmethod
    def _normalizar_leiaute(leiaute: Leiaute | dict) -> dict:
        if isinstance(leiaute, Leiaute):
            return leiaute.to_dict()
        if isinstance(leiaute, dict) and "nome" in leiaute and "arquivo" in leiaute:
            return {"nome": leiaute["nome"], "arquivo": leiaute["arquivo"]}
        raise TypeError(
            "Cada layout deve ser um Leiaute ou um dict com as chaves 'nome' e 'arquivo'"
        )

    @staticmethod
    def _codificar_dados(dados: str | bytes) -> str:
        if isinstance(dados, str):
            conteudo = dados.encode("latin-1")
        elif isinstance(dados, bytes):
            conteudo = dados
        else:
            raise TypeError("dados deve ser str ou bytes")
        return base64.b64encode(conteudo).decode("ascii")

    @classmethod
    def _montar_linha_lcto_ctb(cls, lancamento: dict) -> str:
        faltando = [
            campo
            for campo in cls._CAMPOS_LCTO_CTB_OBRIGATORIOS
            if str(lancamento.get(campo, "") or "").strip() == ""
        ]
        if faltando:
            raise ValueError(
                "Lançamento sem campos obrigatórios: " + ", ".join(faltando)
            )
        return ";".join(
            str(lancamento.get(campo, "") or "") for campo in cls._CAMPOS_LCTO_CTB
        )

    def importar(
        self,
        leiautes: list[Leiaute | dict],
        dados: str | bytes,
        filtro: str = "",
        pode_alterar_dados: bool = True,
        executar_validacao_final: bool = True,
    ) -> dict:
        """
        Envia layouts e dados para POST /Integracao/Importar.

        Args:
            leiautes: Lista de Leiaute ou dicts `{nome, arquivo}` (arquivo em base64)
            dados: Texto CSV (ou bytes) separado por `;`. O método codifica em base64
            filtro: Filtro da importação (padrão: "")
            pode_alterar_dados: Permite alterar dados já existentes (padrão: True)
            executar_validacao_final: Executa a validação final da importação (padrão: True)

        Returns:
            dict: Resposta JSON da API ou dict vazio se falhou

        Exemplo:
            leiaute = Leiaute.from_file("/layouts/C_LctoCtb.nli")
            client = integracao(base_url="http://servidor:8080")
            resultado = client.importar(
                leiautes=[leiaute],
                dados="$99688;39.986.148/0001-82;26/07/2026;;;5003;;;;1000;0;;\\r\\n",
            )
        """
        body = {
            "leiautes": [self._normalizar_leiaute(item) for item in leiautes],
            "filtro": filtro,
            "dados": self._codificar_dados(dados),
            "podealterardados": pode_alterar_dados,
            "executarvalidacaofinal": executar_validacao_final,
        }
        url = f"{self.base_url}/Integracao/Importar"
        response = self.request("POST", url=url, data=body)
        if not response:
            return {}
        return response.json()

    def excluir_lancamentos_ctb(
        self,
        lancamentos: list[dict],
        leiaute: Leiaute | dict,
        filtro: str = "",
        pode_alterar_dados: bool = True,
        executar_validacao_final: bool = True,
    ) -> dict:
        """
        Exclui lançamentos contábeis montando o CSV do layout C_LctoCtb.nli.

        O layout não é embutido: carregue o `.nli` com `Leiaute.from_file`,
        `Leiaute.from_bytes` ou `Leiaute.from_base64`.

        Args:
            lancamentos: Lista de dicts. Obrigatórios: chave_lcto, inscr_federal,
                data, conta_deb, valor. Opcionais: lote, num_doc, desc_conta_deb,
                conta_cred, desc_conta_cred, codigo_hist, compl_hist
            leiaute: Layout `.nli` da importação
            filtro: Filtro da importação (padrão: "")
            pode_alterar_dados: Permite alterar dados já existentes (padrão: True)
            executar_validacao_final: Executa a validação final (padrão: True)

        Returns:
            dict: Resposta JSON da API ou dict vazio se falhou

        Exemplo:
            leiaute = Leiaute.from_file("/layouts/C_LctoCtb.nli")
            client = integracao(base_url="http://servidor:8080")
            resultado = client.excluir_lancamentos_ctb(
                leiaute=leiaute,
                lancamentos=[{
                    "chave_lcto": "$99688",
                    "inscr_federal": "39.986.148/0001-82",
                    "data": "26/07/2026",
                    "conta_deb": "5003",
                    "valor": "1000",
                    "codigo_hist": "0",
                }],
            )
        """
        linhas = [self._montar_linha_lcto_ctb(item) for item in lancamentos]
        dados = "\r\n".join(linhas) + "\r\n"
        return self.importar(
            leiautes=[leiaute],
            dados=dados,
            filtro=filtro,
            pode_alterar_dados=pode_alterar_dados,
            executar_validacao_final=executar_validacao_final,
        )
